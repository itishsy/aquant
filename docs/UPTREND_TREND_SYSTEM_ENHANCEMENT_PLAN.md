# Uptrend 趋势交易体系完善开发实施文档

## 1. 需求目标

本次完善 `uptrend` 趋势交易体系，目标分为两类：

1. 观察剔除：新增 `break_ma` 的连续跌破均线能力。观察股连续 `N` 个交易日收盘价跌破指定 MA 线，自动剔除观察。默认用于 `uptrend`：连续 3 个交易日跌破 MA20。
2. 买点监控：每个交易日每 15 分钟获取最新观察股数据。`uptrend` 观察股满足“未破 MA20”且出现 5 分钟或 15 分钟底背离，并且底背离发生时间晚于加入观察时间时，生成买入信号，并邮件提醒。

目标表达式：

```text
uptrend observe 买点 =
  未破 MA20
  AND
  (5m MACD 底背离 OR 15m MACD 底背离)
  AND
  底背离触发时间 > 加入观察时间
  AND
  K 线数据充足且未过期
```

剔除表达式：

```text
uptrend observe 自动剔除 =
  最近 consecutive_bars 个日线收盘价全部 < MA{ma}
```

## 2. 当前代码能力分析

### 2.1 已有能力

- 规则执行器注册机制已存在：
  - `app/rule_executors/registry.py`
  - `app/rule_executors/__init__.py`
  - `app/rule_executors/base.py`
- `break_ma` 执行器已存在：
  - 文件：`app/rule_executors/break_ma.py`
  - 当前支持：
    - `break_type = cross_down`
    - `break_type = below`
    - `ma = 5 / 10 / 20`
  - 当前不足：
    - 不支持连续 N 根 K 线跌破。
    - 不支持自动剔除观察，仅能返回规则结果。
- `ma_trend` 执行器已存在：
  - 文件：`app/rule_executors/ma_trend.py`
  - 当前支持：
    - `bullish_stack`
    - `bearish_stack`
    - `ma20_slope_up`
    - `price_above_ma20`
  - 当前不足：
    - `price_above_ma20` 是严格大于 MA20，不等价于“未破 MA20”。
    - 只写死 MA20，不支持配置 `ma`。
- 5m / 15m MACD 底背离执行器已存在：
  - 文件：`app/rule_executors/macd_bottom_divergence.py`
  - 当前支持：
    - `executor_key = macd_bottom_divergence`
    - `supported_timeframes = {"5m", "15m"}`
  - 当前不足：
    - 不判断背离发生时间是否晚于加入观察时间。
- 规则扫描主流程已存在：
  - 文件：`app/services/tasks.py`
  - 方法：`TaskService.scan_watch_rules`
  - 当前能力：
    - 只扫描 `WatchPool.system_stage == "observe"`、`WatchPool.status == "watching"`、`monitor_enabled == true`、`signal_enabled == true` 的观察股。
    - 按规则绑定加载执行器。
    - 通过 `RuleDataRequirementService` 准备数据需求。
    - 通过 `TechnicalContextService` 获取 K 线和指标。
    - 数据不足或数据过期时不调用执行器，不生成信号。
    - 支持 required 规则作为 AND 过滤条件。
    - 支持多个 `buy_signal` 规则触发，形成 OR 买点。
    - `_save_signal` 生成买入信号并邮件提醒。
    - 邮件失败会记录 `notification_error`，不会阻断信号生成。
- 规则数据需求中心已存在：
  - 文件：`app/services/rule_data_requirements.py`
  - 当前已有 `break_ma` 的默认需求：

```python
"break_ma": {
    "timeframe": "daily",
    "indicators": ["ma"],
    "lookback_bars": 30,
}
```

- K 线准备服务已存在：
  - 文件：`app/services/kline_collection.py`
  - `KlineFreshnessService` 支持 `daily`、`5m`、`15m`、`30m`。
  - `KlineCollectionService.prepare_watch_rule_data` 能根据规则绑定自动推导需要采集的周期和指标。
- 观察池有可用于“加入观察之后”的字段：
  - `WatchPool.created_at`
  - `WatchPool.added_trade_date`

### 2.2 当前 uptrend 绑定现状

当前 `SeedService` 中 `UPTREND_RULE_BINDINGS` 仅绑定：

- `b5_divergence`
- `b15_divergence`

它们都是 `observe` 阶段的可选买点信号。由于没有 required 过滤规则，当前语义更接近：

```text
5m 底背离 OR 15m 底背离
```

尚不能表达：

```text
未破 MA20 AND (5m 底背离 OR 15m 底背离)
```

## 3. 设计原则

1. 不新增 `near_ma`、`near_level`、`not_break_price`，避免恢复已删除执行器。
2. 不把 MA20 逻辑写死在 `scan_watch_rules` 主流程。
3. 不绕过规则库和规则绑定体系。
4. 不改变平台突破 `platform_breakout` 既有规则语义。
5. 不重写交易体系模型。
6. 不重构 H5 前端。
7. 数据不足或数据过期时不生成信号。
8. 邮件失败不能影响信号生成。
9. “底背离发生在加入观察之后”应做成配置驱动能力，仅 uptrend 的对应规则启用。

## 4. 总体实现方案

### 4.1 扩展 break_ma：支持连续跌破

在 `app/rule_executors/break_ma.py` 中扩展 `break_type`：

```text
cross_down           单次由上向下跌破
below                最新收盘价低于 MA
consecutive_below    最近 N 根 K 线收盘价全部低于 MA
```

配置示例：

```json
{
  "data": {
    "timeframe": "daily",
    "lookback_bars": 60,
    "indicators": ["ma"]
  },
  "signal": {
    "ma": 20,
    "break_type": "consecutive_below",
    "consecutive_bars": 3,
    "price_field": "close"
  }
}
```

执行逻辑：

- 从 `context.technical.bars` 读取最近 K 线。
- 从 `context.technical.indicators.ma.ma{ma}` 读取 MA 序列。
- `consecutive_bars` 默认 3，必须大于 0。
- 当 `len(bars) < consecutive_bars` 或 `len(ma_values) < consecutive_bars` 时，返回 `triggered = false`，reason 明确说明数据不足。
- 取最近 `consecutive_bars` 根 K 线和对应 MA 值。
- 任意 close 或 MA 缺失时，返回 `triggered = false`。
- 所有最近 close 均 `<` 对应 MA 时，`triggered = true`。
- snapshot 记录：
  - `ma`
  - `break_type`
  - `consecutive_bars`
  - `latest_close`
  - `latest_ma`
  - `recent_closes`
  - `recent_ma_values`
  - `executor_key`

### 4.2 扩展 ma_trend：表达“未破 MA”

在 `app/rule_executors/ma_trend.py` 中新增模式：

```text
price_not_below_ma
```

配置示例：

```json
{
  "data": {
    "timeframe": "daily",
    "lookback_bars": 60,
    "indicators": ["ma"]
  },
  "signal": {
    "mode": "price_not_below_ma",
    "ma": 20,
    "price_field": "close"
  }
}
```

执行逻辑：

- `ma` 默认 20，可配置为 5、10、20。
- 读取最新收盘价和最新 MA。
- 判断 `latest_close >= latest_ma`。
- 数据不足时返回 `triggered = false`。
- snapshot 记录：
  - `mode`
  - `ma`
  - `latest_close`
  - `latest_ma`
  - `executor_key`

这样 uptrend 可以通过 required filter 表达“未破 MA20”，不需要新增 `not_break_price` 或 `near_ma`。

### 4.3 增加“触发时间晚于加入观察时间”门禁

不要把 uptrend 规则写死在执行器里，也不要污染所有规则。建议在 `scan_watch_rules` 中增加配置驱动的通用门禁：

```json
{
  "signal": {
    "after_watch_added": true
  }
}
```

适用范围：

- 仅当绑定规则的 `config_json.signal.after_watch_added == true` 时启用。
- uptrend 的 `b5_divergence` 和 `b15_divergence` 开启。
- platform_breakout 的 `b5_divergence` 和 `b15_divergence` 不开启，因此不受影响。

观察起点取值：

1. 优先使用 `WatchPool.created_at`。
2. 若 `created_at` 不存在，再使用 `WatchPool.added_trade_date 00:00:00`。

门禁逻辑：

- 执行器正常返回后，如果 `result.triggered == true` 且启用了 `after_watch_added`：
  - 如果 `result.trigger_time` 为空：改写为不触发，reason 说明缺少触发时间。
  - 如果 `result.trigger_time <= observe_start_time`：改写为不触发，reason 说明背离早于加入观察。
  - 否则保持触发。
- snapshot 追加：
  - `after_watch_added`
  - `observe_start_time`
  - `original_trigger_time`
  - `after_watch_added_passed`

建议实现为 `TaskService.scan_watch_rules` 内部的小 helper，避免改动规则执行器接口。

### 4.4 uptrend 默认规则定义

在 `SeedService` 默认初始化中新增规则定义。

#### 4.4.1 未破 MA20 过滤规则

```text
rule_code: uptrend_not_break_ma20
rule_name: 未破MA20
rule_type: filter
timeframe: daily
executor_key: ma_trend
enabled: true
```

`config_json`：

```json
{
  "data": {
    "timeframe": "daily",
    "lookback_bars": 60,
    "indicators": ["ma"]
  },
  "signal": {
    "mode": "price_not_below_ma",
    "ma": 20,
    "price_field": "close"
  }
}
```

#### 4.4.2 连续跌破 MA20 自动剔除规则

```text
rule_code: uptrend_break_ma20_consecutive_remove
rule_name: 连续跌破MA20自动剔除
rule_type: remove_signal
timeframe: daily
executor_key: break_ma
enabled: true
```

`config_json`：

```json
{
  "data": {
    "timeframe": "daily",
    "lookback_bars": 60,
    "indicators": ["ma"]
  },
  "signal": {
    "ma": 20,
    "break_type": "consecutive_below",
    "consecutive_bars": 3,
    "price_field": "close"
  }
}
```

#### 4.4.3 uptrend 5m 底背离规则配置

沿用已有 `b5_divergence` 规则定义，不重复创建。uptrend 绑定配置使用：

```json
{
  "data": {
    "timeframe": "5m",
    "lookback_bars": 120,
    "indicators": ["macd"]
  },
  "signal": {
    "after_watch_added": true
  }
}
```

#### 4.4.4 uptrend 15m 底背离规则配置

沿用已有 `b15_divergence` 规则定义，不重复创建。uptrend 绑定配置使用：

```json
{
  "data": {
    "timeframe": "15m",
    "lookback_bars": 120,
    "indicators": ["macd"]
  },
  "signal": {
    "after_watch_added": true
  }
}
```

### 4.5 uptrend 默认绑定

建议绑定顺序：

| system_code | stage | rule_code | required | sort_order | 说明 |
|---|---|---:|---:|---:|---|
| uptrend | observe | uptrend_not_break_ma20 | true | 1 | 买点 required 过滤规则 |
| uptrend | observe | b5_divergence | false | 2 | 5m 底背离买点 |
| uptrend | observe | b15_divergence | false | 3 | 15m 底背离买点 |
| uptrend | observe | uptrend_break_ma20_consecutive_remove | false | 10 | 连续跌破 MA20 自动剔除 |

注意：

- `uptrend_not_break_ma20` 是 required，因此买点规则必须先满足它。
- `b5_divergence` 和 `b15_divergence` 都是 `buy_signal`，二者 OR。
- `uptrend_break_ma20_consecutive_remove` 是 `remove_signal`，不参与买点 required 组合。
- 剔除规则应优先于买点保存处理。若同一轮同时出现 remove 和 buy，建议先执行剔除，并跳过买点生成，避免观察股被剔除后又进入买点确认。

### 4.6 自动剔除观察的落库行为

当前 `_save_observe_risk_signal` 只保存风险/失效/剔除待确认信号，不会真正剔除观察。新需求明确要求“自动剔除观察”，因此需要新增或扩展保存逻辑。

建议新增 helper：

```text
_save_observe_remove_signal(...)
```

落库建议：

- 新增一条 `WatchSignal`：
  - `signal_type = "risk"`
  - `rule_type = "remove_signal"`
  - `signal_status = "observe_removed"`
  - `user_action = "auto_removed"`
  - `buy_point_type = rule.rule_code`
  - `trigger_time = result.trigger_time`
  - `trigger_reason = result.reason`
  - `raw_snapshot` / `snapshot_json` 记录技术数据和规则快照
- 更新 `WatchPool`：
  - `status = "removed"`
  - `active = false`
  - `monitor_enabled = false`
  - `signal_enabled = false`
  - `removed_at = now`
  - `archive_reason = result.reason`
  - `latest_signal_id = signal.signal_id`
  - `next_action = "已自动剔除观察"`
- 写入 `WatchPoolStatusLog`：
  - `from_status = 原状态`
  - `to_status = "removed"`
  - `operation_type = "auto_remove"`
  - `operator_type = "system"`
  - `change_reason = result.reason`

需要先确认当前 H5 对 `removed` 状态的展示逻辑。如果已有展示或过滤逻辑，不改 H5；如果列表默认只看 active watching，则自动剔除后自然不会出现在观察列表。

### 4.7 每 15 分钟数据获取和扫描

当前调度：

- `prepare_watch_kline_data`：每 5 分钟
- `scan_watch_rules`：每 10 分钟
- `scan_watch_signals`：每 15 分钟

需求是“每个交易日每 15 分钟获取最新数据，观察 uptrend 个股”。建议调整为：

1. `SeedService.TASK_CONFIG_DEFAULTS["prepare_watch_kline_data"]["interval_minutes"] = 15`
2. `SeedService.TASK_CONFIG_DEFAULTS["scan_watch_rules"]["interval_minutes"] = 15`
3. `app/tasks/scheduler.py` 中：
   - `prepare_watch_kline_data` job `minutes=15`
   - `scan_watch_rules` job `minutes=15`

保留 `timeframes = ["daily", "5m", "15m", "30m"]`，因为规则数据需求会筛选实际需要的周期。`uptrend` 新绑定会自动驱动：

- daily + MA
- 5m + MACD
- 15m + MACD

如果平台希望保留更高频扫描，也可以不降低 5 分钟采集频率；但这与本次需求的“每 15 分钟获取最新数据”不完全一致。建议按需求统一为 15 分钟。

## 5. 需要修改的文件

### 5.1 功能代码

- `app/rule_executors/break_ma.py`
  - 增加 `consecutive_below`。
  - 支持 `consecutive_bars`。
  - 完善 snapshot 和数据不足 reason。
- `app/rule_executors/ma_trend.py`
  - 增加 `price_not_below_ma`。
  - 支持配置 `signal.ma`。
- `app/services/tasks.py`
  - 增加 `after_watch_added` 触发时间门禁。
  - 增加 `remove_signal` 自动剔除保存逻辑。
  - 保持 `scan_watch_rules` 主流程结构不变，只在执行后结果规范化和结果保存阶段扩展。
- `app/services/prd_v1.py`
  - 新增 uptrend 默认规则定义。
  - 新增/调整 uptrend observe 默认绑定。
  - 调整任务默认 interval 到 15 分钟。
- `app/tasks/scheduler.py`
  - 调整 `prepare_watch_kline_data` 和 `scan_watch_rules` 定时器为 15 分钟。

### 5.2 数据迁移

- `alembic/versions/<timestamp>_add_uptrend_ma20_remove_and_after_watch_added.py`
  - 幂等插入新规则定义。
  - 幂等插入 uptrend 新绑定。
  - 对 uptrend 下已有 `b5_divergence` / `b15_divergence` 绑定合并 `signal.after_watch_added = true`。
  - 不修改 `platform_breakout` 绑定。

### 5.3 测试

- `tests/test_rule_executors.py`
  - `break_ma consecutive_below` 命中。
  - `break_ma consecutive_below` 未命中：只有 2 天跌破。
  - `break_ma consecutive_below` 未命中：最近 N 天存在一天未跌破。
  - MA 数据不足不触发。
  - `ma_trend price_not_below_ma` 命中：close 等于或高于 MA20。
  - `ma_trend price_not_below_ma` 未命中：close 低于 MA20。
- `tests/test_rule_data_requirements.py`
  - 确认 uptrend 新规则数据需求可被正确推导。
- `tests/test_scan_watch_rules.py`
  - uptrend 未破 MA20 + 5m 底背离且触发时间晚于加入观察：生成买入信号。
  - uptrend 未破 MA20 + 15m 底背离且触发时间晚于加入观察：生成买入信号。
  - uptrend 跌破 MA20 + 底背离：不生成买入信号。
  - uptrend 未破 MA20 + 底背离发生在加入观察前：不生成买入信号。
  - 数据不足或过期：不生成信号。
  - 邮件关闭或邮件发送失败：不影响买入信号生成。
  - 连续 3 个交易日跌破 MA20：自动剔除观察。
  - 只有 2 个交易日跌破 MA20：不自动剔除。
  - platform_breakout 原有规则仍可生成买点，不受 `after_watch_added` 和 uptrend filter 影响。

## 6. 不需要修改的地方

- 不需要新增 `near_ma` 执行器。
- 不需要恢复 `near_level`、`not_break_price`。
- 不需要重写 `TradingSystem` / `TradingRuleDefinition` / `TradingSystemRuleBinding` 模型。
- 不需要重构 H5 前端。
- 不需要修改平台突破规则定义和绑定。
- 不需要把 MA20 逻辑写死在 `scan_watch_rules`。
- 不需要人工填写静态 MA20 价格。
- 不需要绕过 `RuleDataRequirementService` 和 `TechnicalContextService`。
- 不需要新增自动交易或券商接口。

## 7. 风险与边界

1. `WatchPool.created_at` 是 UTC 时间，K 线时间可能是本地交易时间。实现 `after_watch_added` 时需要确认项目中已有时间约定。最小可行做法是使用当前项目已有 naive datetime 比较，测试覆盖同类型时间；后续如需严格处理时区，再统一时间标准。
2. `WatchSignal` 有唯一约束：`stock_code + buy_point_type + signal_type + trigger_date`。同一股票同一规则同一天可能只保存一条信号。现有逻辑如此，本次不改变。
3. 自动剔除会改变观察池生命周期，比原有待确认风险信号更强。必须用测试确认 H5 自选观察、自选信号、自选交易查询不报错。
4. 如果同一轮同时触发剔除和买点，应先处理剔除并跳过买点，避免状态冲突。
5. 默认初始化和 Alembic 迁移都要幂等。不能覆盖用户已经修改过的非目标配置。

## 8. 验证命令

建议先运行相关单测：

```powershell
$env:DATABASE_URL='sqlite:///./test_aquant.db'
$env:CANDLE_DATABASE_URL='sqlite:///./test_a_candle.db'
$env:DATA_PROVIDER_MODE='mock'
D:\Python\Python312\python.exe -m pytest tests\test_rule_executors.py tests\test_rule_data_requirements.py tests\test_scan_watch_rules.py -q
```

再按风险范围补充运行：

```powershell
$env:DATABASE_URL='sqlite:///./test_aquant.db'
$env:CANDLE_DATABASE_URL='sqlite:///./test_a_candle.db'
$env:DATA_PROVIDER_MODE='mock'
D:\Python\Python312\python.exe -m pytest tests\test_prd_v1_api.py tests\test_trading_system_acceptance.py -q
```

## 9. AI 逐步开发提示词

### Prompt 1：扩展 break_ma 连续跌破能力

```text
请只修改 break_ma 规则执行器。

目标：
1. 在 app/rule_executors/break_ma.py 中为 BreakMaExecutor 增加 break_type = "consecutive_below"。
2. 支持 config_json.signal.consecutive_bars，默认 3，必须为正整数。
3. 支持 config_json.signal.ma，沿用当前 ma 校验。
4. 从 context.technical.bars 和 context.technical.indicators.ma.ma{ma} 读取数据。
5. 判断最近 consecutive_bars 根 K 线收盘价是否全部低于对应 MA。
6. 数据不足、close 缺失、MA 缺失时返回 triggered=false，并给出明确 reason。
7. snapshot 记录 ma、break_type、consecutive_bars、latest_close、latest_ma、recent_closes、recent_ma_values、executor_key。
8. 不改变 cross_down 和 below 现有行为。

完成后补充 tests/test_rule_executors.py 中 break_ma 的单元测试。
```

### Prompt 2：扩展 ma_trend 未破 MA 过滤能力

```text
请只修改 ma_trend 规则执行器及对应测试。

目标：
1. 在 app/rule_executors/ma_trend.py 中新增 mode = "price_not_below_ma"。
2. 支持 config_json.signal.ma，默认 20，允许 5、10、20。
3. 判断 latest_close >= latest_ma。
4. 数据不足时 triggered=false，reason 清晰。
5. snapshot 记录 mode、ma、latest_close、latest_ma、executor_key。
6. 不改变 bullish_stack、bearish_stack、ma20_slope_up、price_above_ma20 现有行为。

完成后补充 tests/test_rule_executors.py 中 ma_trend 的命中和未命中测试。
```

### Prompt 3：增加 after_watch_added 触发时间门禁

```text
请在 app/services/tasks.py 的 TaskService.scan_watch_rules 中增加配置驱动的 after_watch_added 门禁。

要求：
1. 不改变 scan_watch_rules 主流程结构。
2. 只在 binding/rule 的 config_json.signal.after_watch_added == true 时启用。
3. 观察起点优先用 watch.created_at；没有时用 watch.added_trade_date 的 00:00:00。
4. 如果 result.triggered=true 但 result.trigger_time 为空，改写为 triggered=false。
5. 如果 result.trigger_time <= observe_start_time，改写为 triggered=false。
6. snapshot 追加 after_watch_added、observe_start_time、original_trigger_time、after_watch_added_passed。
7. platform_breakout 未配置 after_watch_added，因此不能受影响。

完成后补充 scan_watch_rules 测试：
- uptrend 背离时间早于加入观察，不生成买点。
- uptrend 背离时间晚于加入观察，正常生成买点。
- platform_breakout 原行为不受影响。
```

### Prompt 4：实现 remove_signal 自动剔除观察

```text
请在 app/services/tasks.py 中实现 observe 阶段 remove_signal 的自动剔除逻辑。

目标：
1. 当 observe 阶段规则结果 triggered=true 且 rule.rule_type == "remove_signal" 时，自动剔除观察。
2. 新增或扩展保存 helper，生成 WatchSignal，并更新 WatchPool。
3. WatchPool 更新为：
   - status = "removed"
   - active = false
   - monitor_enabled = false
   - signal_enabled = false
   - removed_at = now
   - archive_reason = result.reason
   - latest_signal_id = signal.signal_id
   - next_action = "已自动剔除观察"
4. 写入 WatchPoolStatusLog，operation_type="auto_remove"，operator_type="system"。
5. 如果同一轮同时触发 remove_signal 和 buy_signal，优先剔除并跳过买点生成。
6. 不影响 invalid_signal、risk_signal 和 buy_signal 现有处理。

完成后补充测试：
- 连续 3 日跌破 MA20 自动剔除。
- 只有 2 日跌破 MA20 不剔除。
- 自动剔除时不生成买点信号。
```

### Prompt 5：新增 uptrend 默认规则定义与绑定

```text
请修改 SeedService 默认初始化逻辑，并新增 Alembic 数据迁移。

目标：
1. 新增规则定义 uptrend_not_break_ma20：
   - rule_type = filter
   - timeframe = daily
   - executor_key = ma_trend
   - enabled = true
   - config_json 使用 daily / ma / 60，signal.mode=price_not_below_ma，ma=20。
2. 新增规则定义 uptrend_break_ma20_consecutive_remove：
   - rule_type = remove_signal
   - timeframe = daily
   - executor_key = break_ma
   - enabled = true
   - config_json 使用 daily / ma / 60，signal.break_type=consecutive_below，ma=20，consecutive_bars=3。
3. 给 uptrend observe 阶段绑定：
   - uptrend_not_break_ma20，required=true，sort_order=1
   - b5_divergence，required=false，sort_order=2，signal.after_watch_added=true
   - b15_divergence，required=false，sort_order=3，signal.after_watch_added=true
   - uptrend_break_ma20_consecutive_remove，required=false，sort_order=10
4. 不重复创建已有规则。
5. 不覆盖用户已修改过的非目标配置。
6. 不修改 platform_breakout 现有绑定。

完成后补充初始化和迁移相关测试。
```

### Prompt 6：调整 15 分钟数据获取与扫描节奏

```text
请调整观察股 K 线准备和规则扫描的默认节奏为 15 分钟。

目标：
1. app/services/prd_v1.py 中 TASK_CONFIG_DEFAULTS：
   - prepare_watch_kline_data.interval_minutes = 15
   - scan_watch_rules.interval_minutes = 15
2. app/tasks/scheduler.py：
   - prepare_watch_kline_data job minutes=15
   - scan_watch_rules job minutes=15
3. 不修改 prepare_trade_kline_data 和 scan_trade_rules，除非现有设计要求同步。
4. 保留 prepare_watch_kline_data.timeframes 中 daily、5m、15m、30m。

完成后补充或更新测试，确认默认任务配置符合预期。
```

### Prompt 7：补齐回归测试并运行

```text
请补齐并运行本次 uptrend 趋势体系测试。

必须覆盖：
1. break_ma consecutive_below 命中。
2. break_ma consecutive_below 未命中：价格未连续跌破。
3. break_ma 数据不足不触发。
4. ma_trend price_not_below_ma 命中。
5. ma_trend price_not_below_ma 未命中。
6. uptrend 未破 MA20 且 5m 底背离发生在加入观察之后，生成买点信号。
7. uptrend 未破 MA20 且 15m 底背离发生在加入观察之后，生成买点信号。
8. uptrend 跌破 MA20 即使有底背离，也不生成买点信号。
9. uptrend 底背离发生在加入观察之前，不生成买点信号。
10. 数据不足或过期时不生成信号。
11. 邮件关闭或邮件失败不影响信号生成。
12. 连续 3 个交易日跌破 MA20 自动剔除观察。
13. platform_breakout 现有买点规则不受影响。

运行：
$env:DATABASE_URL='sqlite:///./test_aquant.db'
$env:CANDLE_DATABASE_URL='sqlite:///./test_a_candle.db'
$env:DATA_PROVIDER_MODE='mock'
D:\Python\Python312\python.exe -m pytest tests\test_rule_executors.py tests\test_rule_data_requirements.py tests\test_scan_watch_rules.py -q

输出修改文件、测试结果、未完成事项和风险。
```

## 10. 最终验收清单

- [ ] `break_ma` 支持连续 N 日跌破指定 MA。
- [ ] `ma_trend` 支持“未破 MA”过滤。
- [ ] `uptrend` 观察阶段能表达 `未破 MA20 AND (5m 底背离 OR 15m 底背离)`。
- [ ] 底背离必须发生在加入观察之后。
- [ ] 连续 3 个交易日跌破 MA20 自动剔除观察。
- [ ] 每 15 分钟准备观察股 K 线数据。
- [ ] 每 15 分钟扫描观察股规则。
- [ ] 数据不足或过期时不生成信号。
- [ ] 邮件失败不影响买点信号生成。
- [ ] 不影响平台突破。
- [ ] 不影响 H5 自选观察 / 信号 / 交易。
- [ ] 单元测试和扫描流程测试通过。
