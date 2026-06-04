# 规则执行器说明

本文档整理当前 `app/rule_executors` 下仍在使用的规则执行器、配置方式和运行链路，供规则库配置、交易体系绑定、后台任务排查和后续扩展使用。

## 1. 架构概览

规则执行器是交易体系规则的最小执行单元。规则库中的 `executor_key` 映射到一个 Python 执行器，后台任务根据交易体系绑定准备数据，然后调用执行器返回 `RuleResult`。

核心接口：

- `RuleContext`：执行输入，包含观察股/交易记录上下文、体系参数、规则绑定配置、技术数据和最新价格。
- `RuleResult`：执行输出，包含是否触发、规则信息、触发价格/时间、原因、风险说明和快照。
- `RuleExecutor.execute(context)`：每个执行器实现的判断逻辑。
- `register_executor()`：执行器注册入口，模块导入时自动注册。

运行保护：

- `TaskService.SAFE_RULE_EXECUTORS` 控制后台任务允许执行的 key。
- `TaskService.PRICE_REQUIRED_EXECUTORS` 控制必须校验实时报价新鲜度的执行器，目前包含 `profit_loss_threshold`。
- `RuleDataRequirementService.DEFAULT_EXECUTOR_REQUIREMENTS` 定义默认 K 线周期、指标和 lookback。
- 规则绑定的 `config_json.data` 会覆盖默认数据需求。

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

- `data.timeframe`：K 线周期，常用 `daily`、`5m`、`15m`、`30m`。
- `data.lookback_bars`：执行前需要准备的 K 线数量。
- `data.indicators`：技术指标，目前支持 `ma`、`macd`。
- `signal`：执行器自己的业务参数，不同执行器不同。

扫描任务会在执行前通过 `TechnicalContextService` 获取标准技术上下文。数据不足或过期时，扫描任务会返回未触发结果，不会调用执行器生成信号。

## 3. 执行器清单

| executor_key | 默认用途 | 常用规则类型 | 默认数据需求 |
| --- | --- | --- | --- |
| `always_false` | 测试/占位，永不触发 | `filter` | 无 |
| `break_level` | 跌破指定价位 | `observe_risk`、`invalid_signal`、`stop_loss` | `daily` / 5 |
| `breakout_level` | 突破指定价位 | `buy_signal`、`confirm` | `daily` / 5 |
| `break_ma` | 跌破指定均线 | `observe_risk`、`invalid_signal`、`stop_loss` | `ma` / 30 |
| `ma_trend` | 均线多头/空头/MA20 斜率/站上 MA20 | `filter` | `daily` / `ma` / 60 |
| `pullback_to_level` | 从近期高点回撤，或回踩体系参数价位 | `filter`、`observe_risk` | 20 |
| `macd_bottom_divergence` | 5m/15m MACD 底背离买点 | `buy_signal` | `macd` / 120 |
| `macd_top_divergence` | MACD 顶背离卖点 | `sell_signal` | `macd` / 120 |
| `macd_dead_cross` | MACD 死叉或动能走弱 | `sell_signal` | `macd` / 120 |
| `volume_spike` | 放量确认 | `confirm` | `daily` / 21 |
| `profit_loss_threshold` | 交易浮盈/浮亏阈值提醒 | `sell_signal`、`stop_loss` | `daily` / 1 |

## 4. 各执行器说明

### `always_false`

测试执行器，始终返回 `triggered=false`。适合测试规则扫描流程、后台预览和 required 组合逻辑。

### `break_level`

判断价格是否跌破指定目标价。适合观察风险、失效、止损类规则。

```json
{
  "target_param": "platform_support_price",
  "target_value": 10.0,
  "break_type": "close_below",
  "threshold_pct": 0
}
```

- `target_param`：从 `context.system_params` 读取目标价。
- `target_value`：当 `target_param` 不存在时使用的静态目标价。
- `break_type`：`close_below` 使用收盘价，`intraday_below` 优先使用 `latest_price`，否则使用最新 K 线最低价。
- `threshold_pct`：跌破阈值比例，触发线为 `target * (1 - threshold_pct)`。

### `breakout_level`

判断价格是否突破指定目标价。适合突破买点或确认规则。

```json
{
  "target_param": "key_observe_price",
  "target_value": 10.0,
  "breakout_type": "close_above",
  "threshold_pct": 0
}
```

- `breakout_type`：`close_above` 使用收盘价，`intraday_above` 优先使用 `latest_price`，否则使用最新 K 线最高价。
- 触发条件：`price > target * (1 + threshold_pct)`。

### `break_ma`

判断价格是否跌破指定均线。

```json
{
  "ma": 20,
  "break_type": "cross_down"
}
```

- `ma`：支持 `5`、`10`、`20`，默认 `5`。
- `cross_down`：上一根收盘价在均线上方或等于均线，最新收盘价跌破均线。
- `below`：最新收盘价低于均线即可。

### `ma_trend`

判断均线趋势状态。

```json
{
  "mode": "bullish_stack",
  "slope_bars": 3
}
```

支持模式：

- `bullish_stack`：`MA5 > MA10 > MA20`。
- `bearish_stack`：`MA5 < MA10 < MA20`。
- `price_above_ma20`：最新收盘价高于 MA20。
- `ma20_slope_up`：最新 MA20 高于 N 根前 MA20，`slope_bars` 默认 `3`。

### `pullback_to_level`

判断价格是否从近期高点回撤，或接近体系参数中的指定价位。

```json
{
  "mode": "from_recent_high",
  "pullback_pct": 0.03
}
```

```json
{
  "mode": "near_param_level",
  "target_param": "platform_upper_price",
  "near_pct": 0.01
}
```

- `from_recent_high`：最新收盘价低于 `recent_high * (1 - pullback_pct)` 时触发。
- `near_param_level`：最新收盘价在体系参数价位上下 `near_pct` 范围内触发。

### `macd_bottom_divergence`

判断 5m 或 15m MACD 底背离买点。触发需要价格低点、MACD 动能、DIF 转强、量能和支撑附近等条件同时通过。

### `macd_top_divergence`

判断 MACD 顶背离卖点。触发需要价格高点、MACD 动能走弱、DIF 转弱和量能风险条件同时通过。

### `macd_dead_cross`

判断 MACD 死叉或动能走弱。触发条件为 DIF 下穿 DEA，或 DIF/柱状图连续走弱。

### `volume_spike`

判断最新成交量是否相对历史均量明显放大。

```json
{
  "lookback_bars": 20,
  "multiplier": 1.5
}
```

触发条件：`latest_volume >= average(history_volume) * multiplier`。

### `profit_loss_threshold`

根据交易持仓的浮盈/浮亏比例或金额触发提醒。

```json
{
  "mode": "profit_ratio_ge",
  "threshold": 0.1
}
```

支持模式：

- `profit_ratio_ge`
- `loss_ratio_le`
- `profit_amount_ge`
- `loss_amount_le`

数据来源：

- `context.latest_price` 或 `rule_config.latest_price`
- `rule_config.average_buy_price` 或 `rule_config.first_buy_price`
- `rule_config.remaining_amount`

## 5. 默认规则与交易体系绑定

当前默认初始化中保留：

- 平台突破规则：`b5_divergence`、`b15_divergence`、`m5_top_divergence`、`m30_dead_cross`、`break_platform_support`。
- 上涨趋势观察规则：`b5_divergence`、`b15_divergence`。
- 通用执行器规则：`breakout_key_level`、`volume_spike_confirm`、`ma_bullish_trend`、`profit_loss_threshold`。

观察股扫描仍复用现有组合逻辑：required 规则全部触发，且存在买点规则触发，则生成买点信号。若没有 required 规则，则任一买点规则触发即可生成买点信号。

## 6. 扩展新执行器的步骤

1. 在 `app/rule_executors/` 新增执行器文件，继承 `RuleExecutor`。
2. 定义稳定唯一的 `executor_key`。
3. 实现 `execute(context) -> RuleResult`，数据不足必须返回 `triggered=false` 和明确 `reason`。
4. 文件末尾调用 `register_executor(Executor())`。
5. 在 `app/rule_executors/__init__.py` 导入执行器并加入 `__all__`。
6. 在 `TaskService.SAFE_RULE_EXECUTORS` 加入 key。
7. 如依赖实时价格，在 `PRICE_REQUIRED_EXECUTORS` 加入 key。
8. 在 `RuleDataRequirementService.DEFAULT_EXECUTOR_REQUIREMENTS` 加入默认数据需求。
9. 在默认 seed 中新增规则定义或通过后台规则库手动创建。
10. 补充执行器单测、数据需求测试和扫描组合测试。
