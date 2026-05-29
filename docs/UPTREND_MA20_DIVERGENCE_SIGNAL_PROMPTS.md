# 上涨趋势 MA20 回调 + 5/15分钟底背离信号开发提示词

## 任务背景

系统需要支持“上涨趋势”交易体系的观察股买点监控。

业务规则如下：

```text
当观察股的交易体系为“上涨趋势”时：

如果股价回调到 MA20 附近，
并且出现 5分钟底背离 或 15分钟底背离，
则系统应生成买点信号，
并在自选-信号中展示，
同时通过邮件提醒。
```

该需求应基于当前系统已有的交易体系、规则库、规则绑定、规则执行器、K线数据采集、规则扫描任务和通知能力实现。

不要重写交易体系模型，不要破坏现有“平台突破”规则流程。

## 当前系统基础能力

请先理解当前项目已有实现：

- 已有交易体系定义：`platform_breakout`、`uptrend`、`limit_relay`、`oversold_rebound`
- 已有规则执行器：
  - `macd_bottom_divergence`
  - `macd_top_divergence`
  - `macd_dead_cross`
  - `break_level`
  - `break_ma`
  - `pullback_to_level`
  - `not_break_price`
  - `break_price`
- `macd_bottom_divergence` 已支持 `5m` 和 `15m`
- `prepare_watch_kline_data` 支持按规则需求准备 K线数据
- `scan_watch_rules` 支持扫描观察股规则并生成 `WatchSignal`
- `NotificationService.notify_buy_signal` 支持买点信号邮件提醒
- 后台管理已经拆分了“交易体系”和“规则库”

本次不要重复实现已经存在的 5分钟 / 15分钟底背离执行器。

本次核心缺口是：新增“股价回调到 MA20 附近”的规则能力，并把它和底背离买点组合到“上涨趋势”交易体系中。

## 目标效果

最终系统应支持如下配置：

```text
交易体系：上涨趋势 uptrend
阶段：观察 observe

必须条件：
- 回调到 MA20 附近

买点信号：
- 5分钟底背离
- 15分钟底背离
```

触发逻辑：

```text
回调到 MA20 附近
AND
(
  5分钟底背离
  OR
  15分钟底背离
)
```

命中后：

- 在自选-信号中生成买点信号
- 信号状态为待人工确认买入
- 观察股进入买点确认阶段
- 邮件配置开启时发送买点提醒邮件
- 信号快照中记录 MA20、最新价、周期、K线时间、触发规则等信息

## 第一步：新增 near_ma 规则执行器

新增执行器文件：

```text
app/rule_executors/near_ma.py
```

执行器名称：

```text
executor_key = "near_ma"
```

作用：

判断最新价格是否接近指定均线。

默认用于：

```text
daily MA20 附近回调
```

### 输入配置

规则绑定 `config_json` 示例：

```json
{
  "data": {
    "timeframe": "daily",
    "lookback_bars": 60,
    "indicators": ["ma"]
  },
  "signal": {
    "ma": 20,
    "near_pct": 0.02,
    "price_field": "close"
  }
}
```

字段含义：

- `ma`：均线周期，默认 `20`
- `near_pct`：接近容差，默认 `0.02`，表示 MA20 上下 2%
- `price_field`：使用价格字段，默认 `close`

### 判断逻辑

从 `context.technical` 中读取：

- `bars`
- `indicators.ma.ma20`

取最新一根 K线：

```text
latest_close = 最新收盘价
latest_ma20 = 最新 MA20
```

判断：

```text
lower = latest_ma20 * (1 - near_pct)
upper = latest_ma20 * (1 + near_pct)

triggered = lower <= latest_close <= upper
```

### 返回结果

命中时：

```text
triggered = true
rule_type = filter
signal_level = B
trigger_price = latest_close
trigger_time = latest_bar.kline_time
reason = "最新收盘价已回调到 MA20 附近"
```

未命中时：

```text
triggered = false
reason = "最新收盘价未回调到 MA20 附近"
```

数据不足时：

```text
triggered = false
reason = "MA 数据不足"
```

### 快照字段

`snapshot` 至少包含：

```json
{
  "executor_key": "near_ma",
  "ma": 20,
  "near_pct": 0.02,
  "latest_close": 12.34,
  "latest_ma": 12.10,
  "lower": 11.86,
  "upper": 12.34,
  "timeframe": "daily",
  "latest_kline_time": "2026-05-29T15:00:00"
}
```

## 第二步：注册 near_ma 执行器

修改：

```text
app/rule_executors/__init__.py
```

要求：

- 导入 `NearMaExecutor`
- 确保执行器启动时被注册
- 不影响现有执行器注册

## 第三步：加入安全执行器列表

修改：

```text
app/services/tasks.py
```

在 `TaskService.SAFE_RULE_EXECUTORS` 中加入：

```text
near_ma
```

确保后台规则扫描任务可以执行该规则。

## 第四步：补充规则数据需求

修改：

```text
app/services/rule_data_requirements.py
```

在 `DEFAULT_EXECUTOR_REQUIREMENTS` 中加入：

```python
"near_ma": {
    "timeframe": "daily",
    "indicators": ["ma"],
    "lookback_bars": 60,
}
```

目的：

- 观察股绑定 `near_ma` 后，后台自动采集 daily K线
- 自动计算 MA 指标
- 确保执行规则前有足够 K线数据

## 第五步：在规则库中增加规则定义

在默认初始化逻辑中新增规则定义。

建议规则：

```text
rule_code: near_ma20_pullback
rule_name: 回调到MA20附近
rule_type: filter
timeframe: daily
executor_key: near_ma
description: 上涨趋势观察阶段，股价回调到 MA20 附近的前置过滤条件。
enabled: true
```

注意：

- 不要把该规则写死为只能用于上涨趋势。
- 它是规则库里的可复用规则。
- 未来其他交易体系也可以复用。

## 第六步：给上涨趋势交易体系增加默认参数

建议给 `uptrend` 新增参数定义：

```text
ma_window
ma_near_pct
```

建议默认：

```text
ma_window = 20
ma_near_pct = 0.02
```

也可以先不依赖体系参数，直接在规则绑定 `config_json` 中配置：

```json
{
  "signal": {
    "ma": 20,
    "near_pct": 0.02,
    "price_field": "close"
  }
}
```

优先建议：

第一版使用规则绑定 `config_json`，减少模型复杂度。

## 第七步：给上涨趋势绑定观察阶段规则

在默认初始化中，为 `uptrend` 增加观察阶段规则绑定：

### 绑定 1：回调到 MA20 附近

```text
system_code: uptrend
rule_code: near_ma20_pullback
stage: observe
required: true
logic_group: trend_pullback
logic_operator: AND
sort_order: 1
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
    "near_pct": 0.02,
    "price_field": "close"
  }
}
```

### 绑定 2：5分钟底背离

```text
system_code: uptrend
rule_code: b5_divergence
stage: observe
required: false
logic_group: bottom_divergence
logic_operator: OR
sort_order: 2
enabled: true
```

`config_json`：

```json
{
  "data": {
    "timeframe": "5m",
    "lookback_bars": 120,
    "indicators": ["macd"]
  }
}
```

### 绑定 3：15分钟底背离

```text
system_code: uptrend
rule_code: b15_divergence
stage: observe
required: false
logic_group: bottom_divergence
logic_operator: OR
sort_order: 3
enabled: true
```

`config_json`：

```json
{
  "data": {
    "timeframe": "15m",
    "lookback_bars": 120,
    "indicators": ["macd"]
  }
}
```

## 第八步：确认扫描逻辑满足组合条件

当前 `scan_watch_rules` 的逻辑是：

```text
required 规则全部触发
并且
存在 buy_signal 规则触发
则生成买点信号
```

因此该需求可以通过以下配置实现：

```text
near_ma20_pullback required = true
b5_divergence required = false
b15_divergence required = false
```

实现：

```text
MA20附近 AND (5分钟底背离 OR 15分钟底背离)
```

请确认：

- 不要为了本需求重写规则组合引擎。
- 如果当前逻辑已经满足，不要过度开发。
- 如果同一天 5分钟和15分钟同时触发，优先保持现有去重逻辑；如需要优化，只做轻量处理。

## 第九步：信号内容优化

生成买点信号时，建议在 `snapshot_json` 中保留：

- 触发的底背离周期
- MA20 值
- 最新收盘价
- MA20 容差区间
- K线最新时间
- 数据新鲜度信息
- 执行器 key

信号展示中如果已有通用展示，不要大改 H5。

可以在触发原因中包含：

```text
上涨趋势：股价回调到 MA20 附近，并出现 5分钟底背离。
```

或者：

```text
上涨趋势：股价回调到 MA20 附近，并出现 15分钟底背离。
```

## 第十步：邮件提醒确认

买点信号生成后，系统已有：

```text
NotificationService.notify_buy_signal
```

请确认：

- `scan_watch_rules` 生成买点信号后会调用邮件提醒。
- 邮件关闭时，不影响信号生成。
- 邮件失败时，错误写入任务日志或信号通知字段。
- 不要因为邮件发送失败回滚信号生成。

## 第十一步：后台 UI 配置支持

请确认后台“规则库”页面能看到：

```text
回调到MA20附近
```

请确认后台“交易体系”页面中：

```text
上涨趋势 -> 观察阶段
```

能看到：

```text
必须条件：回调到MA20附近
买点信号：5分钟底背离
买点信号：15分钟底背离
```

如果当前规则配置编辑器支持 JSON，请确保可以编辑上述 `config_json`。

如果已有结构化配置编辑器，请给 `near_ma` 增加基础表单项：

- 均线：MA5 / MA10 / MA20 / MA30
- 容差比例：1% / 2% / 3% / 自定义
- 数据周期：daily
- 使用价格：收盘价

本次不要为了这个需求大幅重构后台 UI。

## 第十二步：人工后台配置指引

如果默认初始化没有自动配置成功，用户可以按以下方式在后台手动配置。

### 1. 进入规则库

路径：

```text
我的 -> 后台管理 -> 规则库
```

新增规则：

```text
规则编码：near_ma20_pullback
规则名称：回调到MA20附近
规则类型：过滤条件 filter
周期级别：daily
执行器：near_ma
是否启用：启用
```

配置 JSON：

```json
{
  "data": {
    "timeframe": "daily",
    "lookback_bars": 60,
    "indicators": ["ma"]
  },
  "signal": {
    "ma": 20,
    "near_pct": 0.02,
    "price_field": "close"
  }
}
```

### 2. 进入交易体系

路径：

```text
我的 -> 后台管理 -> 交易体系
```

选择：

```text
上涨趋势
```

进入：

```text
观察阶段
```

绑定规则 1：

```text
规则：回调到MA20附近
阶段：观察
是否必需：是
逻辑分组：trend_pullback
逻辑关系：AND
排序：1
启用：是
```

绑定规则 2：

```text
规则：5分钟底背离
阶段：观察
是否必需：否
逻辑分组：bottom_divergence
逻辑关系：OR
排序：2
启用：是
```

绑定规则 3：

```text
规则：15分钟底背离
阶段：观察
是否必需：否
逻辑分组：bottom_divergence
逻辑关系：OR
排序：3
启用：是
```

### 3. 加入观察股

路径：

```text
自选 -> 观察 -> 添加
```

添加股票时选择：

```text
交易体系：上涨趋势
```

确认该观察股满足：

```text
monitor_enabled = true
signal_enabled = true
status = watching
system_stage = observe
```

### 4. 确认后台任务

路径：

```text
我的 -> 后台任务管理
```

确认以下任务启用：

```text
更新自选股价格
准备观察股K线数据
扫描观察股规则
```

任务名称通常对应：

```text
update_watch_prices
prepare_watch_kline_data
scan_watch_rules
```

### 5. 确认邮件配置

如果需要邮件提醒，需要配置：

```text
email_enabled = true
smtp_host
smtp_port
smtp_username
smtp_password
smtp_from
smtp_to
```

邮件未配置时，系统仍应生成信号，只是邮件发送失败。

## 第十三步：测试要求

请至少新增或补充以下测试。

### near_ma 执行器测试

1. 最新收盘价在 MA20 上下 2% 范围内，触发。
2. 最新收盘价高于 MA20 过多，不触发。
3. 最新收盘价低于 MA20 过多，不触发。
4. MA 数据不足，不触发并返回明确原因。
5. 支持从 `config_json.signal.ma` 读取 MA 周期。
6. 支持从 `config_json.signal.near_pct` 读取容差。

### 数据需求测试

1. `near_ma` 默认需要 `daily`、`ma`、`60` 根 K线。
2. `uptrend` 观察股绑定规则后，会产生：
   - `daily`
   - `5m`
   - `15m`
3. 数据不足时，扫描不生成信号。
4. 数据过期时，扫描不生成信号。

### 扫描任务测试

1. MA20 附近，但没有 5m/15m 底背离，不生成买点信号。
2. 不在 MA20 附近，即使出现 5m 底背离，也不生成买点信号。
3. MA20 附近，并出现 5m 底背离，生成买点信号。
4. MA20 附近，并出现 15m 底背离，生成买点信号。
5. MA20 附近，5m 和 15m 同时触发，不产生异常重复。
6. 生成信号后，观察股进入买点确认阶段。
7. 邮件关闭时，信号生成成功，任务日志记录邮件关闭或发送失败。

### 回归测试

确认不影响：

- 平台突破观察信号
- 平台突破买点信号
- 自选观察列表
- 自选信号列表
- 自选交易列表
- 后台任务管理
- 规则库管理
- 交易体系管理

## 第十四步：验收标准

实现完成后，请按以下标准验收：

1. 后台规则库能看到 `回调到MA20附近`。
2. 后台交易体系中，`上涨趋势` 的观察阶段能看到三条规则：
   - 回调到MA20附近
   - 5分钟底背离
   - 15分钟底背离
3. 添加观察股时选择 `上涨趋势`。
4. 后台任务能自动准备 daily / 5m / 15m K线。
5. 当观察股回调到 MA20 附近但无底背离时，不生成买点信号。
6. 当观察股有底背离但未回调到 MA20 附近时，不生成买点信号。
7. 当观察股回调到 MA20 附近且出现 5m 或 15m 底背离时，生成买点信号。
8. 自选-信号中能看到该信号。
9. 信号中能看到交易体系为 `上涨趋势`。
10. 信号中能看到触发规则为 `5分钟底背离` 或 `15分钟底背离`。
11. 邮件配置开启时收到买点提醒邮件。
12. 邮件配置关闭时不影响信号生成。

## 第十五步：输出结果要求

开发完成后，请输出：

1. 修改了哪些文件。
2. 新增了哪些执行器。
3. 新增了哪些规则定义。
4. 新增了哪些交易体系绑定。
5. 数据采集如何满足 daily / 5m / 15m。
6. 人工如何在后台确认配置。
7. 执行了哪些测试。
8. 是否还有未完成事项。

## 禁止事项

请不要做以下事情：

1. 不要重写交易体系核心模型。
2. 不要删除或破坏平台突破规则。
3. 不要把 MA20 回调逻辑写死在 `scan_watch_rules` 里。
4. 不要绕过规则库和规则绑定体系。
5. 不要只靠人工填写静态 MA20 价格。
6. 不要在数据不足或数据过期时生成信号。
7. 不要因为邮件失败导致信号生成失败。
8. 不要大规模重构 H5 前端。
9. 不要引入新的大型依赖。
10. 不要破坏已有测试。

## 推荐实现总结

最小生产级实现路径：

```text
新增 near_ma 执行器
注册 near_ma
加入规则数据需求
新增规则 near_ma20_pullback
给 uptrend 绑定 near_ma20_pullback + b5_divergence + b15_divergence
复用 scan_watch_rules 的 required + buy_signal 逻辑
复用 prepare_watch_kline_data 的规则驱动采集
复用 NotificationService 的买点邮件提醒
补齐测试
```

实现后系统即可支持：

```text
上涨趋势观察股：
回调到 MA20 附近
并出现 5分钟或15分钟底背离
生成买点信号并邮件提醒
```
