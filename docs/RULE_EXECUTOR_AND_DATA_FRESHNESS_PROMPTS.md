# 观察/交易规则执行器与数据新鲜度保障实现文档（含提示词）

本文档用于指导 AI 在当前 Aquant 项目基础上实现两项生产级能力：

1. 增加通用规则执行器，支持观察股/交易股的回跌、收破、跌破 MA5/MA10/MA20 等监控。
2. 确保执行规则时喂给执行器的数据是最新可用数据，避免基于旧 K 线或旧报价产生错误信号。

本文档只描述开发方案和提示词，不直接修改业务代码。

## 1. 当前系统基础

当前项目已经具备以下能力：

- 交易体系定义：`TradingSystemDefinition`
- 规则定义：`TradingRuleDefinition`
- 体系规则绑定：`TradingSystemRuleBinding`
- 观察股：`WatchPool`
- 交易记录：`WatchTrade`
- 统一 K 线表：`MktStockKline`
- K 线仓储：`KlineRepository`
- K 线采集：`KlineCollectionService`
- 数据需求推导：`RuleDataRequirementService`
- 技术上下文：`TechnicalContextService`
- 规则执行器框架：`RuleExecutor`
- 观察规则扫描：`TaskService.scan_watch_rules`
- 交易规则扫描：`TaskService.scan_trade_rules`
- 后台任务：
  - `prepare_watch_kline_data`
  - `prepare_trade_kline_data`
  - `scan_watch_rules`
  - `scan_trade_rules`
  - `update_watch_prices`

当前已有执行器：

| executor_key | 说明 |
|---|---|
| `not_break_price` | 不跌破指定平台价 |
| `break_price` | 收破平台支撑位 |
| `macd_bottom_divergence` | MACD 底背离 |
| `macd_top_divergence` | MACD 顶背离 |
| `macd_dead_cross` | MACD 死叉 |
| `always_false` | 测试执行器 |

当前不足：

- 没有通用 MA 跌破执行器。
- 没有通用价格跌破/收破执行器。
- 没有回跌/回踩类执行器。
- 观察阶段主要生成买点信号，不完整支持观察风险/失效信号。
- `TechnicalContextService` 主要检查 K 线数量，不严格检查 K 线是否最新。
- K 线 freshness 使用 `datetime.utcnow()`，A 股交易时段存在时区风险。
- 最新价 `MktStockQuote` 没有统一 freshness 校验。
- 信号快照没有足够清晰地记录数据时间和数据状态。

## 2. 目标能力

### 2.1 新增规则执行器

需要新增至少三类通用执行器：

1. `break_level`
   - 用于跌破/收破指定价格。
   - 支持观察价、平台支撑、箱体上沿、用户自定义参数。

2. `break_ma`
   - 用于跌破 MA5、MA10、MA20。
   - 可用于观察风险、观察失效、交易止损。

3. `pullback_to_level`
   - 用于回跌/回踩监控。
   - 支持从近期高点回撤一定比例，或回跌到某个参数价附近。

### 2.2 扩展观察阶段信号类型

观察阶段不应只产生买点信号，还应支持：

| rule_type | 建议 signal_type | 说明 |
|---|---|---|
| `buy_signal` | `buy` | 买点信号 |
| `observe_risk` | `risk` | 观察风险 |
| `invalid_signal` | `risk` 或 `invalid` | 观察失效 |
| `remove_signal` | `risk` | 剔除提醒 |
| `filter` | 不生成信号 | 仅作为前置条件 |

第一阶段建议把 `observe_risk`、`invalid_signal` 都写入 `WatchSignal`，`signal_type="risk"`，并通过 `rule_type` 区分具体含义。

### 2.3 数据新鲜度保障

执行器执行前必须满足：

- K 线数量足够。
- K 线最新时间达到当前周期应有时间。
- 最新价没有过期。
- 当前时间按系统配置时区判断，而不是固定 UTC。
- 如果数据不足或过期，不调用执行器，不产生信号，只记录原因。

## 3. 业务语义定义

### 3.1 跌破/收破

建议区分两个概念：

| 名称 | 判断依据 | 示例 |
|---|---|---|
| `intraday_below` | 最新价或周期最低价低于目标价 | 盘中跌破观察价 |
| `close_below` | 最新完成 K 线收盘价低于目标价 | 日线收破 MA20 |

### 3.2 跌破 MA

建议支持两种触发模式：

| 模式 | 说明 |
|---|---|
| `below` | 当前收盘价低于 MA |
| `cross_down` | 上一根收盘价在 MA 上方，当前收盘价跌破 MA |

生产级建议默认使用 `cross_down`，避免每天重复提醒。

### 3.3 回跌/回踩

“回跌”有多种业务语义，建议通过配置表达：

1. 从近期高点回撤超过 N%
2. 回跌到某个参数价附近
3. 回跌到某条均线附近
4. 回踩但未跌破支撑

第一阶段建议实现两种：

- `from_recent_high`：从近期高点回撤超过阈值。
- `near_param_level`：回跌到参数价附近。

## 4. 推荐配置格式

### 4.1 `break_level`

```json
{
  "data": {
    "timeframe": "daily",
    "lookback_bars": 5,
    "indicators": []
  },
  "signal": {
    "target_param": "platform_support_price",
    "break_type": "close_below",
    "threshold_pct": 0
  }
}
```

### 4.2 `break_ma`

```json
{
  "data": {
    "timeframe": "daily",
    "lookback_bars": 30,
    "indicators": ["ma"]
  },
  "signal": {
    "ma": 5,
    "break_type": "cross_down"
  }
}
```

### 4.3 `pullback_to_level`

```json
{
  "data": {
    "timeframe": "daily",
    "lookback_bars": 20,
    "indicators": []
  },
  "signal": {
    "mode": "from_recent_high",
    "pullback_pct": 0.03
  }
}
```

或：

```json
{
  "data": {
    "timeframe": "daily",
    "lookback_bars": 20,
    "indicators": []
  },
  "signal": {
    "mode": "near_param_level",
    "target_param": "key_observe_price",
    "near_pct": 0.01
  }
}
```

## 5. 分阶段实现路线

建议按以下顺序开发：

1. 修复数据时间与 freshness 基础能力。
2. 扩展 `TechnicalContextService`，强校验数据最新性。
3. 扩展扫描任务，数据不新鲜时不调用执行器。
4. 新增 `break_level` 执行器。
5. 新增 `break_ma` 执行器。
6. 新增 `pullback_to_level` 执行器。
7. 扩展观察阶段风险/失效信号生成。
8. 增加默认规则种子或后台配置示例。
9. 补充测试与前端验证。

---

## 阶段 1：修复时间与 freshness 基础能力

### 目标

统一使用系统配置时区判断交易时段和最新 K 线时间，避免 A 股交易时段被 UTC 时间误判。

### 改动范围

- `app/services/kline_collection.py`
- `app/core/config.py`
- 测试文件

### 实现要求

1. `KlineCollectionService` 不要默认使用 `datetime.utcnow()` 判断交易时段。
2. 使用 `settings.timezone`，默认 `Asia/Shanghai`。
3. 引入 timezone-aware 当前时间：

   ```python
   datetime.now(ZoneInfo(settings.timezone))
   ```

4. `KlineFreshnessService.expected_latest_time` 接收的 `now` 应明确为系统交易时区时间。
5. 所有比较前要保证时间语义一致。
6. 测试覆盖：
   - 中国时间 10:17，5m 应有最新 10:15。
   - 中国时间 14:46，15m 应有最新 14:45。
   - 中国时间 08:00，分钟线 expected 为 None。
   - 中国时间 15:10，daily expected 为当天 00:00。

### 开发提示词

```text
请修复 K 线 freshness 判断的时区问题。

背景：
当前 KlineCollectionService 默认使用 datetime.utcnow()，但系统交易对象是 A 股，交易时段应按 Asia/Shanghai 判断。使用 UTC 可能导致交易时间内 expected_latest_time 为 None，从而误判数据新鲜。

目标：
1. 修改 app/services/kline_collection.py。
2. KlineCollectionService 默认 now 使用 settings.timezone，例如 datetime.now(ZoneInfo(settings.timezone))。
3. KlineFreshnessService.expected_latest_time 的 now 参数应按系统交易时区解释。
4. 保持已有 API 兼容，测试中仍可以注入 now。
5. 补充单元测试：
   - 2026-05-27 10:17 Asia/Shanghai，5m expected_latest_time = 10:15。
   - 2026-05-27 14:46 Asia/Shanghai，15m expected_latest_time = 14:45。
   - 2026-05-27 08:00 Asia/Shanghai，5m expected_latest_time = None。
   - 2026-05-27 15:10 Asia/Shanghai，daily expected_latest_time = 当日 00:00。

限制：
不要改业务规则扫描逻辑。
不要改前端。

完成后请输出修改文件、测试命令和测试结果。
```

---

## 阶段 2：执行规则前强校验数据新鲜度

### 目标

`TechnicalContextService` 不只检查 K 线数量，还要检查 K 线是否最新。

### 改动范围

- `app/services/technical_context.py`
- `app/services/kline_collection.py`
- `app/services/tasks.py`
- 测试文件

### 实现要求

1. `TechnicalContextService.get_context` 增加 freshness 校验。
2. 返回状态至少支持：
   - `ok`
   - `insufficient_bars`
   - `stale_data`
   - `missing_data`
3. 如果最新 K 线时间小于 expected_latest_time，返回：

   ```text
   status = stale_data
   ```

4. `freshness` 中返回：
   - `latest_kline_time`
   - `expected_latest_time`
   - `bar_count`
   - `required_bars`
   - `enough_bars`
   - `is_fresh`
5. `scan_watch_rules` 和 `scan_trade_rules` 只有在 `technical.status == "ok"` 时才调用执行器。
6. 数据不新鲜时不生成信号，只写入任务日志 warning。
7. 不能因为旧数据足够多就触发信号。

### 开发提示词

```text
请增强 TechnicalContextService，让规则执行前强制校验 K 线数据是否最新。

背景：
当前 TechnicalContextService 主要检查 bars 数量是否满足 lookback_bars。如果本地有足够多的旧 K 线，仍可能返回 ok，导致执行器基于旧数据产生信号。需要增加 freshness 校验。

目标：
1. 修改 app/services/technical_context.py。
2. TechnicalContextService.get_context 支持 freshness 校验。
3. 复用 KlineFreshnessService.expected_latest_time。
4. 返回 freshness 字段：
   - latest_kline_time
   - expected_latest_time
   - bar_count
   - required_bars
   - enough_bars
   - is_fresh
5. status 规则：
   - 无数据：missing_data
   - 数量不足：insufficient_bars
   - 数量足够但 latest_kline_time < expected_latest_time：stale_data
   - 数量足够且数据新鲜：ok
6. 修改 scan_watch_rules 和 scan_trade_rules：只有 technical.status == ok 才调用执行器。
7. stale_data/insufficient_bars/missing_data 不得生成信号，要进入任务日志错误摘要。
8. 补充测试：
   - 本地 K 线足够但最新时间落后，status=stale_data。
   - stale_data 时 scan_watch_rules 不生成信号。
   - 数据新鲜且足够时仍能正常触发原有测试。

限制：
不要修改执行器业务逻辑。
不要改前端。

完成后请输出修改文件、测试覆盖和结果。
```

---

## 阶段 3：最新价 freshness 校验

### 目标

依赖 `latest_price` 的执行器不能使用过期报价。

### 改动范围

- `app/services/tasks.py`
- `app/services/technical_context.py` 或新增 `QuoteFreshnessService`
- 测试文件

### 实现要求

1. 新增报价 freshness 判断。
2. 默认报价最大过期时间建议 10 分钟，可配置。
3. `scan_watch_rules` 中构建 `quote_map` 时，不只读取价格，也要读取 `source_update_time`。
4. 如果某规则依赖 `latest_price`，但报价过期，则不调用执行器。
5. 对 `not_break_price` 这类依赖最新价的规则尤其重要。
6. 如果规则也能用最新 K 线收盘价兜底，应明确优先级：
   - 盘中规则优先使用 fresh quote。
   - 收盘规则优先使用 K 线 close。

### 开发提示词

```text
请为规则扫描增加最新价 freshness 校验，避免执行器使用过期 MktStockQuote.latest_price。

背景：
当前 scan_watch_rules 和 scan_trade_rules 会读取 MktStockQuote.latest_price 作为 latest_price，但没有检查 source_update_time 是否过期。像 not_break_price 这类规则如果使用旧报价，可能误判。

目标：
1. 新增 QuoteFreshnessService 或在 tasks.py 中实现清晰的报价新鲜度校验。
2. 默认报价最大过期时间为 10 分钟，可从任务 config_json 中配置 quote_max_age_minutes。
3. quote_map 不只保存 latest_price，还要保存 source_update_time 和 freshness 状态。
4. 当规则需要 latest_price 且报价过期时：
   - 不调用执行器。
   - 返回 RuleResult(triggered=False)，reason 说明 quote stale。
   - 任务日志记录 warning。
5. 对使用 daily close 的规则，不强制要求 latest_price。
6. 补充测试：
   - 报价过期时 not_break_price 不触发。
   - 报价新鲜时 not_break_price 正常执行。

限制：
不要影响已有 K 线规则。
不要改前端。

完成后请输出修改文件、配置项和测试结果。
```

---

## 阶段 4：新增 `break_level` 执行器

### 目标

实现通用价格跌破/收破执行器，支持观察价、平台支撑、箱体上沿、自定义价格。

### 改动范围

- `app/rule_executors/break_level.py`
- `app/rule_executors/__init__.py`
- `app/services/rule_data_requirements.py`
- `app/services/tasks.py`
- 测试文件

### 实现要求

1. 新增执行器：

   ```text
   executor_key = "break_level"
   ```

2. 支持配置：

   ```json
   {
     "signal": {
       "target_param": "key_observe_price",
       "target_value": 12.34,
       "break_type": "close_below",
       "threshold_pct": 0
     }
   }
   ```

3. `target_param` 优先从 `context.system_params` 读取。
4. 如果没有 `target_param`，可使用 `target_value`。
5. `break_type` 支持：
   - `close_below`
   - `intraday_below`
6. `close_below` 使用最新完成 K 线 close。
7. `intraday_below` 优先使用 fresh latest_price；没有 fresh quote 时使用最新 K 线 low 或 close。
8. 返回 `RuleResult`，包含：
   - `triggered`
   - `trigger_price`
   - `trigger_time`
   - `reason`
   - `snapshot`
9. 数据不足或配置缺失时不触发，reason 清楚。
10. 注册到执行器 registry。
11. 加入 safe executor 列表。
12. `RuleDataRequirementService.DEFAULT_EXECUTOR_REQUIREMENTS` 增加默认：

    ```text
    break_level -> daily, lookback 5
    ```

### 开发提示词

```text
请新增通用规则执行器 break_level，用于观察股/交易股的跌破或收破指定价格监控。

背景：
当前系统只有 break_price，且主要绑定 platform_support_price，不够通用。需要新增 break_level，支持 target_param/target_value，并支持 close_below 和 intraday_below。

目标：
1. 新增 app/rule_executors/break_level.py。
2. executor_key = "break_level"。
3. 从 binding.config_json.signal 中读取：
   - target_param
   - target_value
   - break_type
   - threshold_pct
4. target_param 优先从 context.system_params 获取；否则使用 target_value。
5. close_below 使用最新 K 线 close 判断。
6. intraday_below 优先使用 context.latest_price 判断；无 latest_price 时使用最新 K 线 low/close。
7. 触发条件为 price < target * (1 - threshold_pct)。
8. 返回 RuleResult，reason 和 snapshot 必须清晰。
9. 注册执行器，并加入 SAFE_RULE_EXECUTORS。
10. RuleDataRequirementService 增加默认需求：daily，lookback_bars=5，indicators=[]。
11. 补充测试：
    - 收破 key_observe_price 会触发。
    - 未跌破不触发。
    - target_param 缺失时不触发且 reason 清晰。
    - intraday_below 使用 latest_price。

完成后请输出修改文件和测试结果。
```

---

## 阶段 5：新增 `break_ma` 执行器

### 目标

实现跌破 MA5/MA10/MA20 的通用执行器。

### 改动范围

- `app/rule_executors/break_ma.py`
- `app/rule_executors/__init__.py`
- `app/services/rule_data_requirements.py`
- 测试文件

### 实现要求

1. 新增执行器：

   ```text
   executor_key = "break_ma"
   ```

2. 支持配置：

   ```json
   {
     "data": {
       "timeframe": "daily",
       "lookback_bars": 30,
       "indicators": ["ma"]
     },
     "signal": {
       "ma": 5,
       "break_type": "cross_down"
     }
   }
   ```

3. 支持 `ma=5/10/20`。
4. 支持 `break_type`：
   - `below`
   - `cross_down`
5. 默认 `cross_down`。
6. 使用 `context.technical["indicators"]["ma"]`。
7. 如果 MA 数据不足，不触发并返回清晰原因。
8. 触发后 snapshot 记录：
   - latest_close
   - latest_ma
   - previous_close
   - previous_ma
   - ma
   - break_type
   - latest_kline_time

### 开发提示词

```text
请新增通用规则执行器 break_ma，用于跌破 MA5/MA10/MA20 的观察风险、观察失效或交易止损监控。

背景：
TechnicalContextService 已能计算 ma5/ma10/ma20，但目前没有执行器使用这些指标。需要新增 break_ma。

目标：
1. 新增 app/rule_executors/break_ma.py。
2. executor_key = "break_ma"。
3. 从 binding.config_json.signal 中读取：
   - ma: 5/10/20
   - break_type: below/cross_down，默认 cross_down
4. 从 context.technical["bars"] 获取最新 K 线。
5. 从 context.technical["indicators"]["ma"] 获取 ma5/ma10/ma20。
6. below：latest_close < latest_ma。
7. cross_down：previous_close >= previous_ma 且 latest_close < latest_ma。
8. MA 数据不足时不触发，reason 清楚。
9. 返回 RuleResult，trigger_price 使用 latest_close，trigger_time 使用最新 K 线时间。
10. 注册执行器，并加入 SAFE_RULE_EXECUTORS。
11. RuleDataRequirementService 增加默认需求：timeframe 使用 rule.timeframe，lookback_bars=30，indicators=["ma"]。
12. 补充测试：
    - 跌破 MA5 cross_down 触发。
    - 一直在 MA5 下方但没有 cross_down 时不触发。
    - below 模式下低于 MA5 触发。
    - MA10/MA20 均可配置。

完成后请输出修改文件和测试结果。
```

---

## 阶段 6：新增 `pullback_to_level` 执行器

### 目标

实现观察股“回跌/回踩”类监控。

### 改动范围

- `app/rule_executors/pullback_to_level.py`
- `app/rule_executors/__init__.py`
- `app/services/rule_data_requirements.py`
- 测试文件

### 实现要求

1. 新增执行器：

   ```text
   executor_key = "pullback_to_level"
   ```

2. 支持模式：
   - `from_recent_high`
   - `near_param_level`

3. `from_recent_high` 配置：

   ```json
   {
     "signal": {
       "mode": "from_recent_high",
       "pullback_pct": 0.03
     }
   }
   ```

   判断：

   ```text
   recent_high = 最近 lookback_bars 内最高价
   latest_close <= recent_high * (1 - pullback_pct)
   ```

4. `near_param_level` 配置：

   ```json
   {
     "signal": {
       "mode": "near_param_level",
       "target_param": "platform_upper_price",
       "near_pct": 0.01
     }
   }
   ```

   判断：

   ```text
   latest_close 在 target * (1 ± near_pct) 区间内
   ```

5. 返回 reason 和 snapshot。
6. 默认 timeframe 使用规则 timeframe。
7. 默认 lookback_bars=20。

### 开发提示词

```text
请新增 pullback_to_level 执行器，用于观察股回跌/回踩类监控。

背景：
交易体系中常需要监控观察股是否从近期高点回跌，或者是否回踩到箱体上沿、关键观察价附近。当前系统没有通用回跌执行器。

目标：
1. 新增 app/rule_executors/pullback_to_level.py。
2. executor_key = "pullback_to_level"。
3. 支持 mode=from_recent_high：
   - 从最新 technical.bars 中找 recent_high。
   - latest_close <= recent_high * (1 - pullback_pct) 时触发。
4. 支持 mode=near_param_level：
   - 从 context.system_params[target_param] 获取目标价。
   - latest_close 在 target * (1 ± near_pct) 范围内时触发。
5. 返回 RuleResult，snapshot 包含 mode、recent_high、target、latest_close、threshold。
6. 注册执行器，并加入 SAFE_RULE_EXECUTORS。
7. RuleDataRequirementService 增加默认需求：timeframe 使用 rule.timeframe，lookback_bars=20，indicators=[]。
8. 补充测试：
   - 从近期高点回撤 3% 触发。
   - 未达到回撤比例不触发。
   - 回踩到 platform_upper_price 附近触发。
   - 缺少 target_param 时不触发且 reason 清晰。

完成后请输出修改文件和测试结果。
```

---

## 阶段 7：观察阶段风险/失效信号生成

### 目标

观察股规则扫描不只支持买点信号，还要支持观察风险和失效提醒。

### 改动范围

- `app/services/tasks.py`
- `app/models/entities.py` 如需枚举说明，不一定改表
- `frontend/src/pages/WatchPoolPage.tsx`
- 测试文件

### 实现要求

1. `scan_watch_rules` 支持以下 `rule_type`：
   - `buy_signal`
   - `observe_risk`
   - `invalid_signal`
   - `remove_signal`
   - `filter`
2. `filter` 仍只作为前置条件，不生成信号。
3. `buy_signal` 逻辑保持不变。
4. `observe_risk` 触发后生成：

   ```text
   WatchSignal.signal_type = "risk"
   WatchSignal.signal_status = "observe_risk_pending"
   ```

5. `invalid_signal` 触发后生成：

   ```text
   WatchSignal.signal_type = "risk"
   WatchSignal.signal_status = "observe_invalid_pending"
   ```

6. `remove_signal` 触发后第一阶段只生成提醒，不自动剔除。
7. 风险/失效信号不应把观察股推进到 `buy_confirm`。
8. 可更新 `watch.next_action`，例如：

   ```text
   出现观察风险，请人工确认是否继续观察
   ```

9. 去重逻辑应按：

   ```text
   watch_id + rule_code + trigger_date
   ```

10. H5 自选-信号能展示这些信号。

### 开发提示词

```text
请扩展 scan_watch_rules，让观察阶段能够生成观察风险和观察失效信号，而不只是买点信号。

背景：
当前 scan_watch_rules 主要对 buy_signal 生成买点信号。现在新增 break_level、break_ma、pullback_to_level 后，需要支持观察股的风险/失效提醒，例如跌破 MA5、收破 MA20、回跌到关键价。

目标：
1. 修改 app/services/tasks.py 的 scan_watch_rules。
2. 支持 rule_type：
   - buy_signal
   - observe_risk
   - invalid_signal
   - remove_signal
   - filter
3. filter 不生成信号。
4. buy_signal 保持现有逻辑：生成 signal_type=buy，推进 buy_pending_confirm/buy_confirm。
5. observe_risk 触发时生成 WatchSignal：
   - signal_type=risk
   - signal_status=observe_risk_pending
   - user_action=pending
6. invalid_signal 触发时生成 WatchSignal：
   - signal_type=risk
   - signal_status=observe_invalid_pending
7. remove_signal 第一阶段只生成 risk 信号，不自动剔除。
8. 风险/失效信号不改变 system_stage 为 buy_confirm。
9. 风险/失效信号可以更新 watch.next_action 为“出现观察风险，请人工确认是否继续观察”。
10. 去重仍按 watch_id + rule_code + trigger_date。
11. H5 自选-信号页面应能正常展示这些 risk 信号，必要时补充中文状态映射。
12. 补充测试：
    - observe_risk 规则触发后生成 risk 信号。
    - invalid_signal 触发后生成 risk 信号。
    - 风险信号不推进 buy_confirm。
    - 同一天重复扫描不重复生成。

完成后请输出修改文件、测试结果和 H5 展示说明。
```

---

## 阶段 8：默认规则与配置示例

### 目标

为平台突破、上涨趋势等体系提供可参考的规则配置。

### 建议新增规则

| rule_code | rule_name | rule_type | timeframe | executor_key |
|---|---|---|---|---|
| `observe_break_key_price` | 跌破关键观察价 | `observe_risk` | `daily` | `break_level` |
| `observe_close_break_platform_support` | 收破平台支撑 | `invalid_signal` | `daily` | `break_level` |
| `observe_break_ma5` | 跌破 MA5 | `observe_risk` | `daily` | `break_ma` |
| `observe_break_ma10` | 跌破 MA10 | `observe_risk` | `daily` | `break_ma` |
| `observe_break_ma20` | 收破 MA20 | `invalid_signal` | `daily` | `break_ma` |
| `observe_pullback_recent_high` | 从近期高点回跌 | `observe_risk` | `daily` | `pullback_to_level` |

### 开发提示词

```text
请为新增规则执行器补充默认规则定义和示例绑定。

背景：
已经新增 break_level、break_ma、pullback_to_level 执行器。现在需要在种子数据中增加一些可配置示例，让后台可以直接看到这些规则并绑定到交易体系。

目标：
1. 在 SeedService 中新增规则定义：
   - observe_break_key_price
   - observe_close_break_platform_support
   - observe_break_ma5
   - observe_break_ma10
   - observe_break_ma20
   - observe_pullback_recent_high
2. 不要默认把所有规则强制绑定到所有交易体系。
3. 可以默认绑定部分规则到 platform_breakout 或 uptrend，但必须 enabled=True/False 的策略要谨慎。
4. 每条规则必须有合理 config_json 示例：
   - break_level 配 target_param 和 break_type
   - break_ma 配 ma 和 break_type
   - pullback_to_level 配 mode 和 pullback_pct
5. admin 后台能看到这些规则。
6. 补充测试：
   - SeedService 初始化后规则存在。
   - executor_key 均已注册。
   - 绑定规则后 RuleDataRequirementService 能推导 daily + ma。

完成后请输出新增规则列表和测试结果。
```

---

## 阶段 9：信号快照增强

### 目标

每个信号要能追溯它基于什么时间的数据触发。

### 实现要求

信号 `snapshot_json` 中至少记录：

```json
{
  "data_status": "ok",
  "timeframe": "daily",
  "latest_kline_time": "2026-05-27T00:00:00",
  "expected_latest_time": "2026-05-27T00:00:00",
  "bar_count": 30,
  "required_bars": 30,
  "quote_update_time": "2026-05-27T10:16:00",
  "executor_key": "break_ma"
}
```

### 开发提示词

```text
请增强 WatchSignal.snapshot_json，让每个规则信号都能追溯数据时间和 freshness 状态。

背景：
为了确认信号不是基于旧数据触发，信号快照中需要记录 K 线最新时间、expected_latest_time、bar_count、required_bars、报价更新时间等信息。

目标：
1. 修改 scan_watch_rules 和 scan_trade_rules 保存信号时的 snapshot_json。
2. 合并 result.snapshot 和 technical.freshness。
3. 如规则使用 latest_price，也记录 quote_update_time 和 quote_is_fresh。
4. snapshot_json 至少包含：
   - data_status
   - timeframe
   - latest_kline_time
   - expected_latest_time
   - bar_count
   - required_bars
   - executor_key
5. H5 信号详情如已有 snapshot 展示，可显示这些字段；没有也不强制新增页面。
6. 补充测试，确认生成信号后 snapshot_json 包含 freshness 信息。

完成后请输出修改文件和测试结果。
```

---

## 阶段 10：最终验收测试

### 必测场景

1. 中国交易时间 freshness 判断正确。
2. K 线足够但过期时，规则不执行。
3. 报价过期时，依赖最新价的规则不执行。
4. `break_level` 能判断收破关键价。
5. `break_ma` 能判断跌破 MA5/MA10/MA20。
6. `pullback_to_level` 能判断从近期高点回撤。
7. 观察阶段 `observe_risk` 能生成 risk 信号。
8. 观察阶段 `invalid_signal` 能生成 risk 信号。
9. 风险信号不推进 `buy_confirm`。
10. 买点信号原有流程不被破坏。
11. 交易阶段卖点/止损原有流程不被破坏。
12. 信号快照包含 freshness 信息。
13. 前端构建通过。
14. 后端测试通过。

### 最终总提示词

```text
请基于当前 Aquant 项目，实现生产级的观察/交易规则执行器扩展和规则执行数据新鲜度保障。

必须实现两大目标：
1. 增加通用规则执行器：
   - break_level：跌破/收破指定价格。
   - break_ma：跌破 MA5/MA10/MA20。
   - pullback_to_level：回跌/回踩监控。
2. 确保执行规则时喂给执行器的数据是最新可用数据：
   - 修复 K 线 freshness 时区问题。
   - TechnicalContextService 强校验 K 线是否最新。
   - 扫描任务遇到 stale_data/insufficient_bars/missing_data 不调用执行器、不生成信号。
   - 增加最新价 freshness 校验。
   - 信号 snapshot_json 记录数据时间和 freshness 状态。

当前系统已有：
- RuleExecutor 框架。
- TradingRuleDefinition.executor_key。
- TradingSystemRuleBinding.config_json。
- RuleDataRequirementService。
- KlineCollectionService。
- TechnicalContextService。
- scan_watch_rules。
- scan_trade_rules。
- mkt_stock_kline。

实现要求：
1. 不推翻现有架构。
2. 不删除旧执行器。
3. 不破坏平台突破现有买点、卖点、止损流程。
4. 新执行器必须注册到 registry，并加入 SAFE_RULE_EXECUTORS。
5. 新规则必须能通过 admin 后台配置和绑定。
6. 观察阶段必须支持 observe_risk、invalid_signal、remove_signal。
7. filter 规则仍不生成信号。
8. 数据不新鲜时不得产生信号。
9. 所有新增能力必须有测试。
10. 前端构建必须通过。

请按阶段实现，每阶段完成后输出：
1. 修改文件。
2. 数据库是否变更。
3. 新增 executor_key。
4. 新增或修改的测试。
5. 测试结果。
6. 已知风险。
```

