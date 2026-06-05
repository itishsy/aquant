# 规则执行器说明

本文档整理 `app/rule_executors` 下当前所有规则执行器的 executor_key、信号参数、运行链路和默认数据需求，供规则库配置、交易体系绑定、后台任务排查和后续扩展使用。

## 1. 架构概览

规则执行器是交易体系规则的最小执行单元。规则库中的 `executor_key` 映射到一个 Python 执行器，后台任务根据交易体系绑定准备 K 线和技术指标数据，调用执行器返回 `RuleResult`。

核心接口：

- `RuleContext` — 执行输入，包含观察股/交易记录上下文、体系参数、规则绑定配置、技术数据和最新价格。
- `RuleResult` — 执行输出，包含 `triggered`、规则信息、触发价格/时间、`reason`、`risk_desc` 和 `snapshot`。
- `RuleExecutor.execute(context)` — 每个执行器实现的判断逻辑。
- `register_executor()` — 执行器注册入口，模块导入时自动注册到全局 registry。

运行保护：

- `TaskService.SAFE_RULE_EXECUTORS` — 后台任务 `scan_watch_rules` / `scan_trade_rules` 允许执行的 executor_key 白名单。不在名单内的规则会被跳过。
- `TaskService.PRICE_REQUIRED_EXECUTORS` — 需要校验实时报价新鲜度的执行器。当前仅 `profit_loss_threshold`。
- `RuleDataRequirementService.DEFAULT_EXECUTOR_REQUIREMENTS` — 定义默认 K 线周期、指标和 lookback。规则绑定的 `config_json.data` 会覆盖默认值。
- `after_watch_added` gate — 当绑定 `config_json.signal.after_watch_added == true` 时，若 `trigger_time <= watch.created_at`，信号被抑制。可选回到 `added_trade_date` 的 00:00:00。

扫描流程：

1. 查询活跃观察股 → 加载其交易体系的 `observe` 阶段绑定规则
2. `RuleDataRequirementService` 解析每个 rule 的 K 线数据需求（timeframe / lookback_bars / indicators）
3. `TechnicalContextService` 获取 K 线并计算 MA / MACD 指标，检查数据新鲜度
4. 构建 `RuleContext`，调用 `executor.execute(context)` 得到 `RuleResult`
5. 检查 `required` 规则 → 处理 `remove_signal`（自动剔除优先）→ 处理 `observe_risk` / `invalid_signal` → 处理 `buy_signal`
6. 若 `remove_signal` 触发，自动将 watch 置为 `removed` 并写入 `WatchPoolStatusLog`，跳过买点生成

## 2. 通用配置格式

```json
{
  "data": {
    "timeframe": "daily",
    "lookback_bars": 60,
    "indicators": ["ma"]
  },
  "signal": {
    "mode": "bullish_stack"
  }
}
```

- `data.timeframe` — K 线周期，常用 `daily`、`5m`、`15m`、`30m`。
- `data.lookback_bars` — 执行前需要准备的 K 线数量。
- `data.indicators` — 技术指标，目前支持 `ma`（返回 ma5/ma10/ma20）、`macd`。
- `signal` — 执行器自身的业务参数，不同执行器不同字段。

## 3. 执行器清单

| executor_key | 文件 | 常用规则类型 | 默认 K 线周期 | 默认 lookback | 默认指标 |
| --- | --- | --- | --- | --- | --- |
| `always_false` | `always_false.py` | `filter` | — | 0 | — |
| `break_level` | `break_level.py` | `observe_risk`、`invalid_signal`、`stop_loss` | `daily` | 5 | — |
| `breakout_level` | `breakout_level.py` | `buy_signal`、`confirm` | `daily` | 5 | — |
| `break_ma` | `break_ma.py` | `observe_risk`、`invalid_signal`、`stop_loss`、`remove_signal` | — | 30 | `ma` |
| `ma_trend` | `ma_trend.py` | `filter` | `daily` | 60 | `ma` |
| `pullback_to_level` | `pullback_to_level.py` | `filter`、`observe_risk` | — | 20 | — |
| `macd_bottom_divergence` | `macd_bottom_divergence.py` | `buy_signal` | — | 120 | `macd` |
| `macd_top_divergence` | `macd_top_divergence.py` | `sell_signal` | — | 120 | `macd` |
| `macd_dead_cross` | `macd_dead_cross.py` | `sell_signal` | — | 120 | `macd` |
| `volume_spike` | `volume_spike.py` | `confirm` | `daily` | 21 | — |
| `profit_loss_threshold` | `profit_loss_threshold.py` | `sell_signal`、`stop_loss` | `daily` | 1 | — |

## 4. 各执行器说明

### `always_false`

测试执行器，始终返回 `triggered=false`。用于测试规则扫描流程、规则预览和 required 组合逻辑。

### `break_level`

判断价格是否跌破指定目标价。适合观察风险、失效、止损类规则。

```json
{
  "signal": {
    "target_param": "platform_support_price",
    "target_value": 23.0,
    "break_type": "close_below",
    "threshold_pct": 0
  }
}
```

- `target_param` — 从 `context.system_params` 读取目标价（优先）。
- `target_value` — 当 `target_param` 不存在或不合法时使用的静态目标价。
- `break_type` — `close_below`（最新 K 线收盘价）、`intraday_below`（优先 `latest_price`，否则 K 线最低价）。
- `threshold_pct` — 跌破阈值比例，触发线为 `target * (1 - threshold_pct)`。

### `breakout_level`

判断价格是否突破指定目标价。适合突破买点或确认规则。

```json
{
  "signal": {
    "target_param": "key_observe_price",
    "target_value": 24.5,
    "breakout_type": "close_above",
    "threshold_pct": 0
  }
}
```

- `breakout_type` — `close_above`（最新 K 线收盘价）、`intraday_above`（优先 `latest_price`，否则 K 线最高价）。
- 触发条件：`price > target * (1 + threshold_pct)`。

### `break_ma`

判断价格与均线的关系。支持三种 `break_type`。

```json
{
  "signal": {
    "ma": 20,
    "break_type": "consecutive_below",
    "consecutive_bars": 3
  }
}
```

| break_type | 判断逻辑 | 最少 K 线 | 典型用途 |
| --- | --- | --- | --- |
| `cross_down`（默认） | 前一根收盘价 ≥ 均线 且 最新收盘价 < 均线 | 2 | 观察风险、失效 |
| `below` | 最新收盘价 < 最新均线 | 2 | 观察风险 |
| `consecutive_below` | 最近 N 根收盘价**全部** < 对应均线 | N | 自动剔除 |

- `ma` — 支持 `5`、`10`、`20`，默认 `5`。
- `consecutive_bars` — 仅 `consecutive_below` 使用，默认 `3`，必须为正整数。
- 数据不足（K 线或 MA 值不够、close/MA 缺失）返回 `triggered=false` 并给出明确 reason。
- snapshot 记录 `ma`、`break_type`、`latest_close`、`latest_ma`；`consecutive_below` 额外记录 `consecutive_bars`、`recent_closes`、`recent_ma_values`。

### `ma_trend`

判断均线趋势状态。支持五种模式。

```json
{
  "signal": {
    "mode": "price_not_below_ma",
    "ma": 20,
    "slope_bars": 3
  }
}
```

| mode | 判断逻辑 | 需要的 MA |
| --- | --- | --- |
| `bullish_stack`（默认） | MA5 > MA10 > MA20 | MA5, MA10, MA20 |
| `bearish_stack` | MA5 < MA10 < MA20 | MA5, MA10, MA20 |
| `price_above_ma20` | 最新收盘价 > MA20 | MA20 |
| `ma20_slope_up` | 最新 MA20 > N 根前 MA20 | MA20（需要 N+1 个值） |
| `price_not_below_ma` | 最新收盘价 ≥ 指定 MA | 指定 MA（默认 20） |

- `ma` — `price_not_below_ma` 模式使用，支持 `5`、`10`、`20`，默认 `20`。其他模式固定使用 MA20。
- `slope_bars` — `ma20_slope_up` 模式使用，默认 `3`。
- `price_not_below_ma` 不校验 MA5/MA10/MA20 全部存在，只校验目标 MA。
- 数据不足返回 `triggered=false` 并给出明确 reason。
- snapshot 记录 `mode`、`ma`、`latest_close`、`latest_ma`（`price_not_below_ma`），或 `ma5`/`ma10`/`ma20`（其他模式）。

### `pullback_to_level`

判断价格是否从近期高点回撤，或接近体系参数中的指定价位。

```json
{
  "signal": {
    "mode": "from_recent_high",
    "pullback_pct": 0.03
  }
}
```

```json
{
  "signal": {
    "mode": "near_param_level",
    "target_param": "platform_upper_price",
    "near_pct": 0.01
  }
}
```

- `from_recent_high` — 最新收盘价低于 `recent_high * (1 - pullback_pct)` 时触发。`recent_high` 取最近 20 根 K 线最高价。
- `near_param_level` — 最新收盘价在体系参数价位 ± `near_pct` 范围内触发。

### `macd_bottom_divergence`

判断 5m 或 15m MACD 底背离买点。触发需要同时满足：价格低点创近期新低、MACD 柱状图动能改善、DIF 转强、量能配合、靠近支撑位等条件。timeframe 由规则绑定配置决定。

### `macd_top_divergence`

判断 MACD 顶背离卖点。触发需要同时满足：价格高点创近期新高、MACD 动能走弱、DIF 转弱、量能配合等条件。

### `macd_dead_cross`

判断 MACD 死叉或动能走弱。触发条件为 DIF 下穿 DEA，或 DIF / MACD 柱连续走弱。timeframe 由规则绑定配置决定（常用 30m）。

### `volume_spike`

判断最新成交量是否相对历史均量明显放大。

```json
{
  "signal": {
    "lookback_bars": 20,
    "multiplier": 1.5
  }
}
```

触发条件：`latest_volume >= average(history_volume) * multiplier`。默认 `multiplier = 1.5`，`lookback_bars = 20`。

### `profit_loss_threshold`

根据交易持仓的浮盈/浮亏比例或金额触发提醒。唯一需要校验实时报价新鲜度的执行器（`PRICE_REQUIRED_EXECUTORS`）。

```json
{
  "signal": {
    "mode": "profit_ratio_ge",
    "threshold": 0.1
  }
}
```

| mode | 触发条件 |
| --- | --- |
| `profit_ratio_ge` | 浮盈比例 ≥ threshold |
| `loss_ratio_le` | 浮亏比例 ≤ threshold（threshold 为负值） |
| `profit_amount_ge` | 浮盈金额 ≥ threshold |
| `loss_amount_le` | 浮亏金额 ≥ abs(threshold) |

数据来源：
- `context.latest_price` 或 `rule_config.latest_price`
- `rule_config.average_buy_price` 或 `rule_config.first_buy_price`
- `rule_config.remaining_amount`

## 5. 种子数据默认规则与绑定

`SeedService.init_defaults()` 创建的默认规则和绑定：

**平台突破 (breakout)**：
- `b5_divergence` / `b15_divergence`（observe, buy_signal）
- `m5_top_divergence` / `m30_dead_cross`（trading, sell_signal）
- `break_platform_support`（stop_loss）

**趋势 (uptrend)**：
- `uptrend_not_break_ma20`（observe, required filter，ma_trend / price_not_below_ma）
- `b5_divergence` / `b15_divergence`（observe, buy_signal，`after_watch_added: true`）
- `uptrend_break_ma20_consecutive_remove`（observe, remove_signal，break_ma / consecutive_below, ma=20, bars=3）

**通用执行器规则**（未绑定体系）：
- `breakout_key_level`（breakout_level）、`volume_spike_confirm`（volume_spike）
- `ma_bullish_trend`（ma_trend）、`profit_loss_threshold`（profit_loss_threshold）

**观察风险通用规则**（绑定到 breakout observe 阶段）：
- `observe_break_key_price`、`observe_close_break_platform_support`
- `observe_break_ma5`、`observe_break_ma10`、`observe_break_ma20`
- `observe_pullback_recent_high`

扫描信号生成逻辑：
1. 所有 `required=true` 的规则必须同时触发
2. 若 `remove_signal` 触发 → 自动剔除并跳过买点生成
3. 若 `buy_signal` 触发 → 生成买入待确认信号，watch 切换为 `buy_pending_confirm`

## 6. 扩展新执行器

1. 在 `app/rule_executors/` 新增文件，继承 `RuleExecutor`，定义唯一 `executor_key`。
2. 实现 `execute(context) -> RuleResult`。数据不足必须返回 `triggered=false` 和明确的 `reason`。
3. 文件末尾调用 `register_executor(MyExecutor())`。
4. 在 `app/rule_executors/__init__.py` 导入并加入 `__all__`。
5. 在 `TaskService.SAFE_RULE_EXECUTORS` 中加入 key。
6. 如需校验实时报价，在 `TaskService.PRICE_REQUIRED_EXECUTORS` 中加入 key。
7. 在 `RuleDataRequirementService.DEFAULT_EXECUTOR_REQUIREMENTS` 中加入默认数据需求。
8. 通过 SeedService 或后台规则库手动创建规则定义，绑定到交易体系。
9. 补充执行器单测、数据需求测试和扫描组合测试。
