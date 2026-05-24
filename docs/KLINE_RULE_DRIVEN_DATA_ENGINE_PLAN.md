# 规则驱动的多周期 K 线采集与技术分析引擎实现方案（含提示词）

本文档用于指导 AI 在当前项目基础上实现“按交易体系规则自动采集各级别 K 线数据，并通过后台可配置执行计划驱动技术分析和信号扫描”的能力。

目标不是全市场采集所有周期数据，而是：

- 交易体系规则需要什么周期，就采什么周期。
- 观察股只采观察阶段需要的数据。
- 交易股只采卖点、止损阶段需要的数据。
- 数据采集任务可在后台配置、查看、手动执行。
- 技术指标统一计算，规则执行器只负责判断信号。
- 尽量避免重复采集、过度采集和无效采集。

## 1. 当前项目现状

当前系统已经具备以下基础能力：

- `TradingSystemDefinition`：交易体系定义。
- `TradingRuleDefinition`：规则定义，已有 `timeframe`、`executor_key`。
- `TradingSystemParamDefinition`：交易体系参数定义。
- `TradingSystemRuleBinding`：交易体系与规则绑定，已有 `stage`、`required`、`logic_group`、`logic_operator`、`config_json`。
- `WatchPool`：观察股，已有 `trading_system_code`、`system_stage`、`system_params_json`。
- `WatchTrade`：交易记录，已有 `trading_system_code`、`active_sell_rule_codes_json`、`active_stop_rule_codes_json`。
- `RuleExecutor`：规则执行器框架。
- `scan_watch_rules`：观察规则扫描。
- `scan_trade_rules`：交易规则扫描。
- `Provider.get_intraday_kline(stock_code, interval, start_time, end_time)`：理论上支持不同分钟级别 K 线。
- `KlineService`：已有日 K 和 15 分钟 K 的采集/查询能力。
- `IndicatorService`：已有 MA、EMA、MACD 等指标计算。

但当前仍有明显不足：

- 只有日 K 和 15 分钟 K 有专门落库表。
- 5 分钟、30 分钟 K 线主要在扫描时临时拉取，缺少统一缓存。
- `update_watch_daily_kline`、`update_watch_15m_kline` 当前仍偏空实现。
- 规则执行器里仍存在自行准备 K 线和指标的逻辑。
- 没有根据规则自动推导需要采集哪些周期。
- 后台任务没有完整表达“先准备数据，再扫描规则”的执行计划。
- 缺少 K 线数据新鲜度判断、缺口判断、采集限流和失败降级。

## 2. 需求理解

系统最终需要支持多套交易体系，例如：

- 平台突破
- 上涨趋势
- 涨停接力
- 超跌反弹
- 后续自定义体系

每套交易体系包含不同规则，每条规则可能依赖不同级别 K 线和技术指标。

例如平台突破：

- 观察阶段：
  - 不跌破箱体上沿：需要最新价或日 K。
  - 5 分钟底背离：需要 5m K 线和 MACD。
  - 15 分钟底背离：需要 15m K 线和 MACD。
- 交易阶段：
  - 5 分钟顶背离：需要 5m K 线和 MACD。
  - 30 分钟死叉：需要 30m K 线和 MACD。
  - 收破平台支撑：需要日 K 收盘价。

因此系统不能固定采集某几个周期，而应该由交易体系规则反推数据需求。

核心链路应为：

```text
交易体系规则配置
 -> 推导每只股票需要的周期和指标
 -> 后台任务按计划采集必要 K 线
 -> 技术指标统一计算
 -> 规则执行器判断信号
 -> 生成观察信号或交易提醒
```

## 3. 总体设计原则

1. 不全市场采集。
2. 不为所有自选股采全部周期。
3. 不在规则执行器里直接调用 provider。
4. 不让扫描任务无脑重复拉取 K 线。
5. 采集计划必须由当前启用规则反推。
6. 观察股和交易股的数据需求分开计算。
7. 后台执行计划必须可配置、可查看、可手动执行。
8. 数据采集必须有新鲜度判断。
9. 技术指标计算必须标准化。
10. 旧的日 K 和 15m 表先保留兼容，新引擎优先使用统一表。

## 4. 推荐数据结构

### 4.1 新增统一 K 线表

建议新增表：`mkt_stock_kline`

字段建议：

| 字段 | 类型 | 说明 |
|---|---|---|
| `kline_id` | Integer | 主键 |
| `stock_code` | String | 标准股票代码 |
| `timeframe` | String | `5m`、`15m`、`30m`、`60m`、`daily` |
| `kline_time` | DateTime | K 线时间。日 K 可用交易日 00:00:00 |
| `trade_date` | Date | 交易日期，便于查询 |
| `open_price` | Float | 开盘价 |
| `high_price` | Float | 最高价 |
| `low_price` | Float | 最低价 |
| `close_price` | Float | 收盘价 |
| `volume` | Float | 成交量 |
| `amount` | Float | 成交额 |
| `source` | String | 数据源 |
| `source_update_time` | DateTime | 数据源更新时间 |
| `created_at` | DateTime | 创建时间 |
| `updated_at` | DateTime | 更新时间 |

唯一约束：

```text
stock_code + timeframe + kline_time + source
```

索引建议：

```text
stock_code + timeframe + kline_time
stock_code + timeframe + trade_date
timeframe + kline_time
```

### 4.2 可选：采集计划日志表

建议新增表：`mkt_kline_collection_plan_log`

用于记录每次任务生成了什么采集计划，方便排查为什么采了某个股票、为什么没采。

字段建议：

| 字段 | 说明 |
|---|---|
| `plan_id` | 主键 |
| `task_name` | 任务名称 |
| `stock_code` | 股票代码 |
| `timeframe` | 周期 |
| `reason` | 来源原因，例如 `watch_rule:b15_divergence` |
| `stage` | `observe`、`trading`、`stop_loss` |
| `required_bars` | 需要根数 |
| `latest_local_time` | 本地最新 K 线时间 |
| `expected_latest_time` | 应有最新 K 线时间 |
| `need_fetch` | 是否需要采集 |
| `created_at` | 创建时间 |

第一阶段可不建这张表，只在任务日志里记录摘要。

### 4.3 规则配置扩展

建议在 `TradingSystemRuleBinding.config_json` 中支持数据需求配置。

示例：

```json
{
  "data": {
    "timeframe": "15m",
    "lookback_bars": 120,
    "indicators": ["macd", "ma"]
  },
  "signal": {
    "divergence_window": 8,
    "near_support_pct": 0.03
  }
}
```

如果没有配置，则使用默认推导：

| executor_key | 默认周期 | 默认指标 | 默认 lookback |
|---|---:|---|---:|
| `macd_bottom_divergence` | 规则 `timeframe` | `macd` | 120 |
| `macd_top_divergence` | 规则 `timeframe` | `macd` | 120 |
| `macd_dead_cross` | 规则 `timeframe` | `macd` | 120 |
| `not_break_price` | `daily` | 无 | 5 |
| `break_price` | `daily` | 无 | 5 |

## 5. 核心服务设计

### 5.1 `KlineRepository`

职责：

- 统一读写 `mkt_stock_kline`。
- 支持 `daily/5m/15m/30m/60m` 等周期。
- 提供 upsert 能力，避免重复数据。
- 提供最新 K 线时间查询。
- 提供按根数查询最近 K 线。

建议方法：

```python
class KlineRepository:
    def upsert_rows(self, stock_code: str, timeframe: str, rows: list[dict], source: str) -> int: ...
    def latest_time(self, stock_code: str, timeframe: str) -> datetime | None: ...
    def get_recent_bars(self, stock_code: str, timeframe: str, limit: int) -> list[KlineBar]: ...
    def count_recent_bars(self, stock_code: str, timeframe: str, since: datetime | None = None) -> int: ...
```

### 5.2 `KlineFreshnessService`

职责：

- 判断某股票某周期是否需要更新。
- 根据当前时间和交易时段推导“当前应该已有的最新 K 线时间”。
- 避免未形成新 K 线时重复请求 provider。

建议方法：

```python
class KlineFreshnessService:
    def expected_latest_time(self, timeframe: str, now: datetime) -> datetime | None: ...
    def is_fresh(self, stock_code: str, timeframe: str, now: datetime) -> bool: ...
    def missing_window(self, stock_code: str, timeframe: str, now: datetime) -> tuple[datetime, datetime] | None: ...
```

规则建议：

- `daily`：收盘后才认为当天日 K 应该存在。
- `5m`：当前时间超过某根 5m K 线结束时间后，才采该 bar。
- `15m`、`30m` 同理。
- 非交易时段不采分钟线，除非是补历史缺口。

### 5.3 `RuleDataRequirementService`

职责：

- 根据观察股/交易股当前阶段和绑定规则，推导所需 K 线周期、指标和 lookback。
- 合并重复需求，形成最小采集计划。

输入：

- `WatchPool` 或 `WatchTrade`
- 当前阶段：`observe`、`trading`、`stop_loss`
- 交易体系规则绑定

输出：

```json
{
  "603019.SH": {
    "daily": {
      "lookback_bars": 5,
      "indicators": [],
      "reasons": ["not_break_platform_upper"]
    },
    "15m": {
      "lookback_bars": 120,
      "indicators": ["macd"],
      "reasons": ["b15_divergence"]
    }
  }
}
```

### 5.4 `KlineCollectionService`

职责：

- 执行采集计划。
- 根据 freshness 判断只采缺失数据。
- 调用 Provider 获取数据。
- 写入 `mkt_stock_kline`。
- 记录任务影响条数和错误。

建议方法：

```python
class KlineCollectionService:
    def prepare_watch_rule_data(self, trade_date: date) -> int: ...
    def prepare_trade_rule_data(self, trade_date: date) -> int: ...
    def collect_for_requirements(self, requirements: dict) -> int: ...
```

### 5.5 `TechnicalContextService`

职责：

- 给规则执行器提供标准化技术分析上下文。
- 从 `KlineRepository` 获取 bars。
- 统一计算 MACD、MA 等指标。
- 可做指标缓存，但第一阶段可以实时计算。

建议输出：

```json
{
  "timeframe": "15m",
  "bars": [...],
  "indicators": {
    "macd": {
      "dif": [...],
      "dea": [...],
      "hist": [...]
    },
    "ma": {
      "ma5": [...],
      "ma10": [...],
      "ma20": [...]
    }
  },
  "freshness": {
    "latest_kline_time": "2026-05-24 10:30:00",
    "is_fresh": true
  }
}
```

### 5.6 规则执行器改造

当前规则执行器从 `rule_config["kline_bars"]` 中取数据，后续应逐步改为：

```python
RuleContext(
    stock_code=...,
    timeframe="15m",
    bars=[...],
    indicators={"macd": ...},
    system_params={...},
    rule_config={...}
)
```

第一阶段可以兼容旧字段：

- 新上下文优先：`context.technical`
- 旧字段兜底：`rule_config["kline_bars"]`

## 6. 后台执行计划设计

### 6.1 新增任务

建议新增任务：

| 任务名 | 说明 |
|---|---|
| `prepare_watch_kline_data` | 为观察股准备规则所需 K 线 |
| `prepare_trade_kline_data` | 为交易股准备卖点/止损所需 K 线 |

保留已有任务：

| 任务名 | 说明 |
|---|---|
| `update_watch_prices` | 更新自选股最新价 |
| `scan_watch_rules` | 扫描观察规则 |
| `scan_trade_rules` | 扫描交易规则 |
| `auto_remove_watch_pool` | 自动剔除 |

建议任务链路：

```text
update_watch_prices
 -> prepare_watch_kline_data
 -> scan_watch_rules

prepare_trade_kline_data
 -> scan_trade_rules
```

### 6.2 执行频率建议

| 任务 | 频率 | 时间窗口 |
|---|---:|---|
| `update_watch_prices` | 5 分钟 | 交易时段 |
| `prepare_watch_kline_data` | 5 分钟 | 交易时段 |
| `scan_watch_rules` | 5-10 分钟 | 交易时段 |
| `prepare_trade_kline_data` | 5 分钟 | 交易时段 |
| `scan_trade_rules` | 5 分钟 | 交易时段 |
| `auto_remove_watch_pool` | 15 分钟 | 交易时段 |
| `daily_kline_close_update` | 每日一次 | 收盘后 |

第一阶段可以使用 APScheduler 固定配置。  
第二阶段再把 interval、时间窗口、启用状态完全交给后台配置。

### 6.3 后台配置项

建议 `config_task` 或扩展表支持以下配置：

| 配置项 | 说明 |
|---|---|
| `enabled` | 是否启用 |
| `interval_minutes` | 执行间隔 |
| `run_window` | 执行窗口，例如 `09:30-15:05` |
| `timeframes` | 允许采集周期 |
| `max_stocks_per_run` | 单次最大股票数 |
| `max_requests_per_run` | 单次最大请求数 |
| `retry_times` | 失败重试 |
| `source_priority` | 数据源优先级 |
| `only_trade_day` | 是否仅交易日执行 |

可以先放在 `ConfigTask.config_json`。如果当前表没有该字段，则新增字段。

示例：

```json
{
  "interval_minutes": 5,
  "run_window": "09:30-15:05",
  "timeframes": ["5m", "15m", "30m", "daily"],
  "max_stocks_per_run": 80,
  "max_requests_per_run": 200,
  "source_priority": ["eastmoney", "cls"],
  "only_trade_day": true
}
```

## 7. 数据源设计

当前系统已有 Provider 抽象，应继续沿用。

建议数据源分层：

1. 主数据源  
   默认用于日常采集。

2. 备用数据源  
   主源失败时自动降级。

3. 数据质量校验  
   写入前校验：
   - open/high/low/close 是否存在
   - high 是否大于等于 open/close/low
   - low 是否小于等于 open/close/high
   - volume/amount 是否合理
   - kline_time 是否属于交易时段
   - 是否重复

4. 数据源健康状态  
   后台应能看到：
   - 最近成功时间
   - 最近失败时间
   - 错误摘要
   - 是否启用
   - 优先级

第一阶段可以继续使用当前已有真实 provider。  
但业务代码必须继续通过 Provider 接口，不要直接在规则或任务里写死数据源 URL。

## 8. 避免无效采集的策略

### 8.1 观察股采集条件

只处理：

- `WatchPool.active=True`
- `WatchPool.status="watching"`
- `WatchPool.system_stage="observe"`
- `WatchPool.monitor_enabled=True`
- `WatchPool.signal_enabled=True`
- `trading_system_code` 非空

不处理：

- 已剔除
- 黑名单
- 已失效
- 已进入买点确认
- 已进入交易
- 监控关闭
- 信号关闭

### 8.2 交易股采集条件

只处理：

- `WatchTrade.trade_status in ["open", "holding"]`
- `WatchTrade.current_stage="trading"`
- `trading_system_code` 非空

不处理：

- 已全部卖出
- 已归档
- 已复盘完成

### 8.3 周期合并

如果多个规则需要同一股票同一周期，只采一次。

例如：

```text
603019.SH:
  b5_divergence 需要 5m 120 根
  m5_top_divergence 需要 5m 80 根
```

最终只生成：

```text
603019.SH 5m 120 根
```

### 8.4 新鲜度判断

如果本地最新 K 线已经满足当前周期要求，不请求 provider。

示例：

```text
当前时间 10:17
5m 应有最新 K 线为 10:15
本地最新 5m K 线为 10:15
=> 不采
```

## 9. 分阶段落地步骤

### 阶段 1：新增统一 K 线表和 Repository

目标：

- 新增 `mkt_stock_kline`。
- 新增 `KlineRepository`。
- 保留旧表兼容。

不做：

- 不改规则扫描逻辑。
- 不改前端。

### 阶段 2：实现规则数据需求推导

目标：

- 新增 `RuleDataRequirementService`。
- 能根据观察股和交易股规则推导周期需求。
- 支持从 `config_json.data` 读取 `timeframe/lookback_bars/indicators`。
- 没配置时按 `executor_key` 默认推导。

### 阶段 3：实现 K 线采集服务

目标：

- 新增 `KlineCollectionService`。
- 按需求采集 `daily/5m/15m/30m`。
- 写入 `mkt_stock_kline`。
- 有 freshness 判断。

### 阶段 4：新增后台数据准备任务

目标：

- 新增 `prepare_watch_kline_data`。
- 新增 `prepare_trade_kline_data`。
- 加入 `ConfigTask` 种子数据。
- 加入 admin 任务手动执行。
- 加入 APScheduler。

### 阶段 5：接入技术分析上下文

目标：

- 新增 `TechnicalContextService`。
- 统一计算 MACD、MA。
- 规则执行器优先使用技术上下文。

### 阶段 6：改造规则扫描

目标：

- `scan_watch_rules` 不再直接拉 provider。
- `scan_trade_rules` 不再直接拉 provider。
- 扫描前从 `TechnicalContextService` 取数据。
- 数据不足时返回明确原因，不生成误报。

### 阶段 7：后台可配置执行计划

目标：

- 扩展任务配置。
- 支持 interval、run_window、timeframes、max_requests 等配置。
- 前端后台任务页可查看和编辑关键配置。

### 阶段 8：补充测试和验收

目标：

- 覆盖规则需求推导。
- 覆盖 K 线去重写入。
- 覆盖 freshness 判断。
- 覆盖观察股/交易股按需采集。
- 覆盖数据准备任务。
- 覆盖规则扫描不再临时拉取 provider。

## 10. 验收标准

完成后应满足：

1. 后台能看到 `prepare_watch_kline_data`、`prepare_trade_kline_data`。
2. 后台能手动执行 K 线准备任务。
3. 后台能看到任务最近运行时间、状态、影响条数、错误摘要。
4. 平台突破观察股只采 `daily/5m/15m`。
5. 平台突破交易股只采 `daily/5m/30m`。
6. 已关闭监控的观察股不采数据。
7. 已进入买点确认的观察股不采观察阶段分钟线。
8. 已完成交易不再采交易阶段分钟线。
9. 同一股票同一周期不会重复请求 provider。
10. 本地数据新鲜时不会重复采集。
11. 规则执行器能从统一技术上下文获取 bars 和 MACD。
12. 信号扫描仍能产生观察信号和交易提醒。
13. 前端构建通过。
14. 后端测试通过。

## 11. AI 编码提示词

### 提示词 1：新增统一 K 线表和 Repository

```text
请基于当前项目实现规则驱动 K 线引擎的第一阶段：新增统一 K 线表和 KlineRepository。

背景：
当前项目已有 mkt_stock_kline_daily 和 mkt_stock_kline_15m，但后续需要支持 5m、15m、30m、60m、daily 等多周期数据。不要删除旧表，先新增统一表并逐步接入。

目标：
1. 新增表 mkt_stock_kline。
2. 字段包括：kline_id、stock_code、timeframe、kline_time、trade_date、open_price、high_price、low_price、close_price、volume、amount、source、source_update_time、created_at、updated_at。
3. 增加唯一约束：stock_code + timeframe + kline_time + source。
4. 增加常用索引：stock_code + timeframe + kline_time、stock_code + timeframe + trade_date。
5. 新增 KlineRepository，支持：
   - upsert_rows(stock_code, timeframe, rows, source)
   - latest_time(stock_code, timeframe)
   - get_recent_bars(stock_code, timeframe, limit)
   - count_recent_bars(stock_code, timeframe, since=None)
6. 保留旧 KlineService，不要破坏现有日 K 和 15m 查询。
7. 补充测试，验证 upsert 去重和按周期查询。

限制：
不要改规则扫描逻辑。
不要改前端。
不要删除旧表。

完成后请输出：
1. 修改文件。
2. 新增迁移。
3. 新增 Repository 方法。
4. 测试命令和结果。
```

### 提示词 2：实现规则数据需求推导

```text
请实现 RuleDataRequirementService，用于根据交易体系规则推导观察股和交易股需要采集哪些周期 K 线和指标。

背景：
当前 TradingRuleDefinition 已有 timeframe 和 executor_key，TradingSystemRuleBinding 已有 config_json。需要根据当前观察股/交易股绑定的交易体系规则自动生成数据需求，避免采集无关周期。

目标：
1. 新增 RuleDataRequirementService。
2. 支持 build_watch_requirements(trade_date)：
   - 只处理 active=True、status=watching、system_stage=observe、monitor_enabled=True、signal_enabled=True、trading_system_code 非空的 WatchPool。
   - 读取该体系 observe 阶段启用规则。
3. 支持 build_trade_requirements(trade_date)：
   - 只处理 trade_status in open/holding、current_stage=trading、trading_system_code 非空的 WatchTrade。
   - 读取 active_sell_rule_codes_json、active_stop_rule_codes_json 对应规则。
4. 每条规则的数据需求优先读取 binding.config_json.data。
5. 没有 config_json.data 时根据 executor_key 默认推导：
   - macd_bottom_divergence/macd_top_divergence/macd_dead_cross：需要 rule.timeframe、macd、lookback 120
   - not_break_price/break_price：需要 daily、lookback 5
6. 合并同一股票同一周期需求，取最大 lookback_bars，合并 indicators 和 reasons。
7. 补充测试：
   - 平台突破观察股推导 daily/5m/15m
   - 平台突破交易股推导 daily/5m/30m
   - 关闭监控的观察股不产生需求
   - 重复周期需求会合并

限制：
不要采集数据。
不要改规则扫描。
不要改前端。

完成后请输出：
1. 新增服务文件。
2. 数据需求返回结构示例。
3. 测试覆盖说明。
```

### 提示词 3：实现 K 线采集服务和新鲜度判断

```text
请实现 KlineFreshnessService 和 KlineCollectionService，用于按规则需求采集必要的多周期 K 线。

背景：
已经有 KlineRepository 和 RuleDataRequirementService。现在需要根据数据需求，判断本地 K 线是否新鲜，只采缺失或过期的数据，写入 mkt_stock_kline。

目标：
1. 新增 KlineFreshnessService：
   - expected_latest_time(timeframe, now)
   - is_fresh(stock_code, timeframe, now)
   - missing_window(stock_code, timeframe, now)
2. 支持 daily、5m、15m、30m。
3. 非交易时段默认不采分钟线，除非补历史缺口。
4. 新增 KlineCollectionService：
   - collect_for_requirements(requirements)
   - prepare_watch_rule_data(trade_date)
   - prepare_trade_rule_data(trade_date)
5. collect_for_requirements 根据 requirements 调用 Provider.get_daily_kline 或 Provider.get_intraday_kline。
6. 采集结果写入 KlineRepository。
7. 本地数据已新鲜时不请求 provider。
8. 单次任务要有基础限流，例如 max_requests_per_run。
9. 采集失败不要中断全部股票，记录错误摘要。
10. 补充测试：
    - freshness 命中时不调用 provider
    - 缺失时调用 provider 并写入
    - 同一股票同一周期不会重复写入

限制：
不要改前端。
不要直接在规则执行器里调用 provider。

完成后请输出：
1. 新增服务文件。
2. 支持的 timeframe。
3. 新鲜度判断规则。
4. 测试命令和结果。
```

### 提示词 4：新增后台数据准备任务

```text
请把规则驱动 K 线准备能力接入后台任务系统。

背景：
当前已有 config_task/config_task_log、TaskService、admin 手动运行任务和 APScheduler。现在需要新增 prepare_watch_kline_data 和 prepare_trade_kline_data 两个任务。

目标：
1. 在 SeedService.TASKS 中新增：
   - prepare_watch_kline_data，owner_module 可为 kline 或 market
   - prepare_trade_kline_data，owner_module 可为 kline 或 market
2. 在 TaskService 中新增：
   - prepare_watch_kline_data(trade_date)
   - prepare_trade_kline_data(trade_date)
3. 方法内部调用 KlineCollectionService。
4. 在 admin_prd.py 的任务运行 fn_map 中加入两个任务。
5. 在 h5 我的任务运行入口中加入两个任务（如果已有）。
6. 在 scheduler.py 中加入两个 job：
   - prepare_watch_kline_data：交易时段每 5 分钟
   - prepare_trade_kline_data：交易时段每 5 分钟
7. 后台任务页应能看到任务最近运行状态、影响条数、错误信息。
8. 补充测试：
   - SeedService 初始化后任务存在
   - admin 手动运行任务成功
   - scheduler 注册两个 job

限制：
不要删除旧 update_watch_daily_kline/update_watch_15m_kline。
不要破坏已有 scan_watch_rules/scan_trade_rules。

完成后请输出：
1. 修改文件。
2. 新增任务名称。
3. scheduler 配置。
4. 验证方式。
```

### 提示词 5：实现技术分析上下文

```text
请实现 TechnicalContextService，为规则执行器统一提供 K 线和技术指标。

背景：
当前规则执行器直接从 rule_config["kline_bars"] 获取 K 线，并自行计算 MACD。后续需要统一由 TechnicalContextService 从 mkt_stock_kline 获取 bars，并计算指标。

目标：
1. 新增 TechnicalContextService。
2. 支持 get_context(stock_code, timeframe, lookback_bars, indicators)。
3. 从 KlineRepository 读取最近 bars。
4. 支持计算：
   - macd
   - ma
5. 返回结构包括：
   - timeframe
   - bars
   - indicators
   - freshness/latest_kline_time
6. 数据不足时返回明确状态，不抛出未处理异常。
7. 扩展 RuleContext，增加 technical 或 bars/indicators 字段。
8. 保持兼容旧 rule_config["kline_bars"]。
9. 补充测试：
   - 能返回 bars 和 macd
   - bars 不足时能给出不足状态

限制：
不要一次性重写所有规则执行器。
先兼容旧逻辑。

完成后请输出：
1. 新增服务文件。
2. RuleContext 变更。
3. 返回结构示例。
4. 测试结果。
```

### 提示词 6：改造观察和交易规则扫描

```text
请改造 scan_watch_rules 和 scan_trade_rules，让它们优先使用 TechnicalContextService，不再在扫描过程中直接临时拉取 provider。

背景：
当前 scan_watch_rules/scan_trade_rules 中存在直接调用 provider.get_intraday_kline 的逻辑。新的设计要求先由 prepare_watch_kline_data/prepare_trade_kline_data 准备数据，再由扫描任务使用本地 K 线和技术指标执行规则。

目标：
1. scan_watch_rules：
   - 继续只扫描 active=True、status=watching、system_stage=observe、monitor_enabled=True、signal_enabled=True 的观察股。
   - 根据规则 timeframe 和 executor_key 获取 TechnicalContext。
   - 把技术上下文传入 RuleContext。
   - 数据不足时，该规则 result.triggered=False，reason 说明数据不足。
2. scan_trade_rules：
   - 继续只扫描 open/holding、current_stage=trading 的交易。
   - 使用 TechnicalContextService 获取卖点/止损规则所需数据。
3. 删除或隔离扫描任务中直接 provider.get_intraday_kline 的逻辑。
4. 保持现有信号生成、去重、邮件提醒、状态推进逻辑。
5. 规则执行器先兼容旧字段，不要大规模重写。
6. 补充测试：
   - 准备好 K 线后能产生信号
   - 数据不足时不产生信号且 reason 清晰
   - provider 不在扫描阶段被调用

完成后请输出：
1. 修改文件。
2. 扫描流程变化。
3. 是否影响现有 H5。
4. 测试结果。
```

### 提示词 7：后台可配置执行计划

```text
请为 K 线准备任务和规则扫描任务增加后台可配置执行计划。

背景：
当前后台任务能展示和手动运行，但执行频率、时间窗口、限流、采集周期等配置还不完整。需要让后台能配置规则驱动数据采集计划。

目标：
1. 给 ConfigTask 增加 config_json 字段，如果已有类似字段则复用。
2. 支持配置：
   - interval_minutes
   - run_window
   - timeframes
   - max_stocks_per_run
   - max_requests_per_run
   - retry_times
   - source_priority
   - only_trade_day
3. 后台 admin 任务页展示这些配置。
4. 后台 admin 任务页支持编辑关键配置。
5. TaskService 和 KlineCollectionService 读取 config_json。
6. scheduler 第一阶段可以仍用固定 interval，但任务执行内部必须尊重 enabled、run_window、only_trade_day、max_requests_per_run。
7. 补充测试：
   - run_window 外不执行采集
   - max_requests_per_run 生效
   - disabled 任务不执行

限制：
不要引入复杂工作流引擎。
不要做权限审批。
只做当前系统需要的任务配置。

完成后请输出：
1. 数据库变更。
2. 后台页面变化。
3. 配置示例。
4. 测试结果。
```

## 12. 最终给 AI 的总提示词

```text
请在当前 Aquant 项目基础上，实现“规则驱动的多周期 K 线采集与技术分析引擎”。

业务目标：
1. 系统支持多套交易体系，每套体系的规则可能依赖不同级别 K 线和技术指标。
2. 系统不能全市场、全周期无差别采集。
3. 系统应根据观察股/交易股当前绑定的交易体系规则，自动推导需要采集哪些 K 线周期和指标。
4. 后台任务按计划准备 K 线数据，然后规则扫描基于本地数据和技术指标生成信号。
5. 后台需要能查看和配置执行计划，包括启用状态、执行窗口、采集周期、限流和最近运行状态。

当前已有能力：
- TradingSystemDefinition
- TradingRuleDefinition
- TradingSystemParamDefinition
- TradingSystemRuleBinding
- WatchPool
- WatchTrade
- RuleExecutor
- scan_watch_rules
- scan_trade_rules
- KlineService
- IndicatorService
- Provider.get_daily_kline
- Provider.get_intraday_kline
- config_task/config_task_log
- admin 后台任务页面

请按阶段实现：
1. 新增统一 K 线表 mkt_stock_kline 和 KlineRepository。
2. 新增 RuleDataRequirementService，根据规则推导数据需求。
3. 新增 KlineFreshnessService 和 KlineCollectionService，只采缺失或过期数据。
4. 新增 prepare_watch_kline_data 和 prepare_trade_kline_data 后台任务。
5. 新增 TechnicalContextService，统一提供 bars 和 indicators。
6. 改造 scan_watch_rules 和 scan_trade_rules，优先使用技术上下文，不在扫描阶段直接拉 provider。
7. 增强后台任务配置，支持执行窗口、间隔、限流、周期、数据源优先级。
8. 补充测试和验收。

重要限制：
1. 不删除旧表。
2. 不破坏现有 H5 自选-观察/信号/交易功能。
3. 不自动买入或自动卖出。
4. 不引入复杂审批或权限系统。
5. 不把数据源 URL 写死在规则执行器或任务扫描里。
6. 第一阶段可以保留旧 KlineService 兼容，但新引擎应优先使用 mkt_stock_kline。
7. 每一步完成后必须说明修改文件、数据库迁移、接口变化、测试结果和未完成风险。

验收标准：
1. 平台突破观察股能推导 daily/5m/15m 数据需求。
2. 平台突破交易股能推导 daily/5m/30m 数据需求。
3. 后台能手动运行 prepare_watch_kline_data 和 prepare_trade_kline_data。
4. 数据已新鲜时不会重复请求 provider。
5. 数据不足时规则不会误触发，原因清晰。
6. 规则扫描能基于本地 K 线和 MACD 生成信号。
7. 前端构建通过。
8. 后端测试通过。
```

