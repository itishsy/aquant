# 交易体系功能优化整改执行方案（含提示词）

本文档基于当前最新代码实现情况整理，用于指导 AI 分步骤修复和优化“多交易体系驱动的自选观察-信号-交易”功能。

目标不是重新设计系统，而是在当前已经实现的基础上补齐闭环，让用户能够清楚看到：

- 后台定义了什么交易体系
- 某只观察股绑定了哪个体系
- 当前处于观察、买点确认、交易、卖点/止损哪一步
- 后台任务是否真的在自动监控
- 哪条规则触发了信号
- 邮件提醒是否发送成功
- 确认买入后，交易阶段正在监控哪些卖点和止损规则

## 1. 当前实现结论

当前代码已经完成了多交易体系的主体框架：

- 已有交易体系、规则、参数、体系规则绑定相关表。
- 已有 `platform_breakout`、`uptrend`、`limit_relay`、`oversold_rebound` 种子数据。
- 已有规则执行器框架和平台突破相关执行器。
- 已有 `scan_watch_rules`、`scan_trade_rules` 任务方法。
- admin 已有交易体系管理入口。
- H5 市场页加入观察时，已支持按交易体系动态填写参数。
- H5 自选观察/信号/交易已开始展示交易体系、核心参数和阶段信息。

但仍存在以下关键缺口：

1. `scan_watch_rules` / `scan_trade_rules` 没有加入 APScheduler，不能真正自动监控。
2. 观察规则扫描没有过滤 `monitor_enabled`、`signal_enabled` 和合适的业务状态。
3. 买点信号触发后没有把 `system_stage` 推进到买点确认阶段，后续日期可能重复扫描。
4. H5 自选编辑页没有动态编辑 `trading_system_code` 和 `system_params_json`。
5. 信号和交易卡片仍显示较多规则编码，用户不容易看懂触发了什么。
6. 邮件提醒状态没有在 H5 或后台任务中清晰展示。
7. 缺少“规则试算/效果预览”，用户难以确认新需求实际生效。

## 2. 总体整改原则

1. 不推翻已有实现。
2. 不删除已新增的交易体系表。
3. 不重写 H5 自选页面，只在现有页面补齐关键展示。
4. 不新增复杂审计、权限、流程审批。
5. 后台 admin 只保证数据流可管理，不做过度低代码平台。
6. 平台突破作为第一套完整样板体系，后续体系复用同一机制。
7. 所有自动任务必须能在“我的-后台任务”看到运行情况。
8. 每一步都要可独立验证。
9. 每一步完成后必须输出：
   - 修改文件
   - 数据库迁移
   - 接口变化
   - 前端变化
   - 验证方式
   - 未完成项

## 3. 分步实施路线

建议严格按以下顺序实现：

1. 阶段 1：接入新规则扫描定时任务
2. 阶段 2：修复观察规则扫描生命周期
3. 阶段 3：补齐 H5 自选编辑体系参数
4. 阶段 4：优化信号/交易规则名称展示
5. 阶段 5：展示邮件提醒和任务运行结果
6. 阶段 6：增加规则试算/效果预览
7. 阶段 7：补充测试与最终验收

---

## 阶段 1：接入新规则扫描定时任务

### 目标

让 `scan_watch_rules` 和 `scan_trade_rules` 真正进入后台自动任务调度。

### 修改范围

- `app/tasks/scheduler.py`
- 如有需要，补充 `tests/` 中的 scheduler 测试
- 不修改前端业务页面

### 实现要求

1. 在 APScheduler 中新增两个 job：
   - `scan_watch_rules`
   - `scan_trade_rules`
2. 保留旧的 `scan_watch_signals`，除非确认已经完全被新任务替代。
3. `scan_watch_rules` 建议 5 到 15 分钟执行一次。
4. `scan_trade_rules` 建议 5 到 15 分钟执行一次。
5. job id 必须与 `config_task.task_name` 保持一致，方便后台任务页展示。
6. 增加独立函数：
   - `run_watch_rule_scan`
   - `run_trade_rule_scan`
7. 任务执行日期使用 `date.today()`。
8. 不影响已有价格更新、自动剔除、市场数据采集任务。

### 验收检查

1. 启动后 scheduler 中能看到 `scan_watch_rules` 和 `scan_trade_rules`。
2. 手动调用对应函数不会报错。
3. “我的-后台任务”中仍能看到任务配置和日志。
4. 旧任务不被删除。

### 开发提示词

```text
请基于当前最新代码修复后台定时任务调度问题。

背景：
当前系统已经实现 TaskService.scan_watch_rules 和 TaskService.scan_trade_rules，也已经在任务配置和接口中加入了这两个任务，但 app/tasks/scheduler.py 还没有把它们加入 APScheduler，导致交易体系规则不会自动监控。

目标：
1. 在 app/tasks/scheduler.py 中新增 scan_watch_rules 和 scan_trade_rules 两个 APScheduler job。
2. 新增 run_watch_rule_scan 和 run_trade_rule_scan 两个函数，分别调用 TaskService(db).scan_watch_rules(date.today()) 和 TaskService(db).scan_trade_rules(date.today())。
3. job id 分别使用 scan_watch_rules、scan_trade_rules。
4. 保留已有 collect_all_market、update_watch_prices、scan_watch_signals、auto_remove_watch_pool，不要删除。
5. 新任务 interval 建议 10 或 15 分钟，max_instances=1，coalesce=True，misfire_grace_time 合理设置。
6. 不改数据库结构。
7. 不改前端页面。

完成后请输出：
1. 修改了哪些文件。
2. 新增了哪些 scheduler job。
3. 如何验证 scheduler 已包含新任务。
4. 是否影响旧任务。
```

---

## 阶段 2：修复观察规则扫描生命周期

### 目标

避免关闭监控的观察股被扫描，避免买点触发后持续重复扫描。

### 修改范围

- `app/services/tasks.py`
- `tests/test_scan_watch_rules.py`

### 实现要求

1. `scan_watch_rules` 查询观察股时必须过滤：
   - `WatchPool.active is True`
   - `WatchPool.monitor_enabled is True`
   - `WatchPool.signal_enabled is True`
   - `WatchPool.system_stage == "observe"`
   - `WatchPool.status` 只能是 `watching` 或明确允许的观察态
   - `trading_system_code` 非空
2. 买点信号保存成功后：
   - `watch.status = "buy_pending_confirm"`
   - `watch.system_stage = "buy_confirm"`
   - `watch.next_action = "等待人工确认买入"`
   - 可保持 `active=True`，因为仍需显示在自选路径中
   - 可设置 `signal_enabled=False`，防止买点确认前重复扫描，是否设置需与现有监控开关语义一致
3. 重复信号判断仍应基于 `watch_id + rule_code + trigger_date`。
4. 不要物理删除观察股。
5. 不要自动买入。
6. `scan_trade_rules` 只扫描交易阶段：
   - `WatchTrade.trade_status in ["open", "holding"]`
   - `current_stage == "trading"`
   - 规则启用且执行器存在

### 验收检查

1. `monitor_enabled=False` 的观察股不会产生信号。
2. `signal_enabled=False` 的观察股不会产生信号。
3. 已经 `buy_pending_confirm` 的观察股不会在下一天继续产生新的买点信号。
4. 触发买点后，H5 自选观察卡片能看到“买入待确认”或相应状态。
5. 自选-信号中能看到该买点信号。

### 开发提示词

```text
请修复交易体系观察规则扫描的生命周期问题。

背景：
当前 TaskService.scan_watch_rules 只按 active、system_stage=observe、trading_system_code 非空筛选观察股，没有过滤 monitor_enabled、signal_enabled、status。买点信号生成后只设置 status=buy_pending_confirm 和 next_action，没有推进 system_stage，导致后续日期可能重复扫描并产生重复机会。

目标：
1. 修改 app/services/tasks.py 中 scan_watch_rules 的观察股查询条件。
2. 只扫描 active=True、monitor_enabled=True、signal_enabled=True、system_stage="observe"、status="watching" 的观察股。
3. 买点信号保存成功后，把 watch.status 设置为 buy_pending_confirm，把 watch.system_stage 设置为 buy_confirm，把 watch.next_action 设置为“等待人工确认买入”。
4. 为避免买点确认前重复扫描，请合理处理 signal_enabled。可以在买点生成后设置 signal_enabled=False，确认买入或放弃信号后再由已有流程或新增逻辑恢复。
5. 保持信号写入 watch_signal，不自动买入，不自动交易。
6. 补充或更新 tests/test_scan_watch_rules.py，覆盖：
   - 监控关闭不扫描
   - 信号关闭不扫描
   - 触发买点后 system_stage 变为 buy_confirm
   - buy_pending_confirm 不会再次扫描

注意：
不要重写规则执行器框架。
不要删除旧 scan_watch_signals。
不要修改无关前端。

完成后请输出：
1. 修改文件。
2. 生命周期状态变化。
3. 新增或更新的测试。
4. 如何人工验证。
```

---

## 阶段 3：补齐 H5 自选编辑体系参数

### 目标

用户在“自选-观察详情-编辑”中可以直接修改当前交易体系和该体系的参数，并真正保存到 `trading_system_code`、`system_params_json`。

### 修改范围

- `frontend/src/pages/WatchPoolPage.tsx`
- `app/api/routes/h5.py`
- `app/services/prd_v1.py`
- 相关前端类型或辅助函数

### 实现要求

1. H5 自选编辑弹层不要只编辑旧字段。
2. 进入编辑时加载：
   - `/h5/trading-systems`
   - `/h5/trading-systems/{system_code}/params`
3. 交易体系选择使用后端返回的体系列表，不再只依赖前端写死数组。
4. 编辑表单根据参数定义动态渲染：
   - number 使用数字输入
   - text 使用文本框或 TextArea
   - boolean 使用开关或选择项
5. 保存时提交：
   - `trading_system_code`
   - `trading_system`
   - `system_params_json`
   - `key_observe_price`
   - `auto_remove_price`
   - `invalid_condition`
   - `adjust_reason`
6. 后端 `update_watch` 必须能重新校验必填体系参数。
7. 参数校验失败时，前端显示清晰错误。
8. 保留“剔除”按钮，不做物理删除，除已有硬删除入口外不要新增物理删除。

### 验收检查

1. 打开观察股详情，点击编辑，不弹新页面，仍在当前底部抽屉内编辑。
2. 平台突破能看到箱体上沿、平台支撑、观察价、自动剔除价、失效条件等参数。
3. 修改箱体上沿保存后，重新打开详情能看到新值。
4. 后端 `watch_pool.system_params_json` 中同步更新。
5. 必填参数为空时不能保存。

### 开发提示词

```text
请优化 H5 自选-观察详情编辑功能，让它支持交易体系动态参数编辑。

背景：
当前 MarketPage 加入观察时已经支持从 /h5/trading-systems 和 /h5/trading-systems/{system_code}/params 获取体系和参数定义；但 WatchPoolPage 的观察股编辑仍只编辑 trading_system、key_observe_price、auto_remove_price、invalid_condition 等旧字段，保存时没有提交 trading_system_code 和 system_params_json。

目标：
1. 在 frontend/src/pages/WatchPoolPage.tsx 中复用 MarketPage 的交易体系和参数加载思路。
2. 打开观察股详情后点击“编辑”，仍在当前底部抽屉内直接编辑，不再打开额外弹层。
3. 编辑表单中交易体系选择来自 /h5/trading-systems。
4. 根据 /h5/trading-systems/{system_code}/params 动态渲染参数输入项。
5. 编辑保存时提交 trading_system_code、trading_system、system_params_json、key_observe_price、auto_remove_price、invalid_condition、risk_tags、user_remark、adjust_reason。
6. 切换交易体系时，保留通用字段 key_observe_price、invalid_condition、auto_remove_price，其他参数按新体系定义重新组织。
7. 后端如已有 update_watch 支持 trading_system_code 和 system_params_json，则不要重复造接口；如校验不足，只补必要校验。
8. 错误提示要能告诉用户缺少哪个参数。
9. 保持现有自选观察、信号、交易列表功能不受影响。

完成后请输出：
1. 修改文件。
2. 前端编辑表单变化。
3. 后端保存字段。
4. 手工验证步骤。
```

---

## 阶段 4：优化信号/交易规则名称展示

### 目标

让用户看到中文业务含义，而不是规则编码。

### 修改范围

- `app/api/routes/h5.py`
- `frontend/src/pages/WatchPoolPage.tsx`
- 可选：新增规则名称映射 helper

### 实现要求

1. H5 信号列表返回时补充：
   - `trading_system_name`
   - `rule_name`
   - `rule_timeframe`
   - `rule_display_name`
2. H5 交易列表返回时补充：
   - `active_sell_rules`
   - `active_stop_rules`
   - 每项包含 `rule_code`、`rule_name`、`timeframe`
3. 前端展示：
   - 买点类型：`15分钟底背离`，而不是 `b15_divergence`
   - 卖点规则：`5分钟顶背离 / 30分钟死叉`
   - 止损规则：`收破平台支撑位`
4. 缺少规则定义时，才回退显示编码。
5. 不改变数据库结构，优先通过接口查询规则定义补全显示字段。

### 验收检查

1. 自选-信号卡片显示“平台突破 / 15分钟底背离 / 待确认买入”。
2. 自选-交易卡片显示“卖点规则：5分钟顶背离、30分钟死叉”。
3. 自选-交易卡片显示“止损规则：收破平台支撑位”。
4. 不再把主要信息暴露为 `b15_divergence`、`break_platform_support`。

### 开发提示词

```text
请优化 H5 自选-信号/交易的规则显示，让用户看到中文规则名称。

背景：
当前 watch_signal 和 watch_trade 已保存 rule_code、active_sell_rule_codes_json、active_stop_rule_codes_json，但前端主要显示编码，用户不容易理解新交易体系实际触发了什么。

目标：
1. 在 app/api/routes/h5.py 的 _signal_dict 或相关列表接口中补充 rule_name、rule_timeframe、trading_system_name、rule_display_name。
2. 在 _trade_dict 或交易列表接口中补充 active_sell_rules、active_stop_rules，内容来自 TradingRuleDefinition。
3. 前端 WatchPoolPage.tsx 使用中文规则名展示信号和交易规则。
4. 保留编码作为兜底，不要因为规则定义缺失导致页面报错。
5. 不改数据库结构。
6. 不改变确认买入、确认卖出等业务接口。

完成后请输出：
1. 修改文件。
2. 新增返回字段示例。
3. 自选-信号卡片展示效果。
4. 自选-交易卡片展示效果。
```

---

## 阶段 5：展示邮件提醒和任务运行结果

### 目标

用户能确认后台任务是否运行、信号邮件是否发送成功。

### 修改范围

- `frontend/src/pages/WatchPoolPage.tsx`
- 我的/后台任务页面相关文件
- `app/api/routes/h5.py`
- 如有需要，`app/services/tasks.py`

### 实现要求

1. 自选-信号卡片显示邮件状态：
   - 已发送
   - 未启用
   - 发送失败
2. 如果 `notification_error` 存在，显示简短错误，例如“邮件未启用”。
3. 后台任务页面中，“自选监控”下展示：
   - 观察规则扫描
   - 交易规则扫描
   - 自动剔除
   - 自选价格更新
4. 每个任务显示：
   - 最近运行时间
   - 最近状态
   - 影响条数
   - 错误摘要
   - 手动运行按钮
5. 不在 H5 前端暴露 SMTP 密码等敏感配置。

### 验收检查

1. 手动运行 `scan_watch_rules` 后，任务页能看到运行日志。
2. 邮件未配置时，信号卡片能看到“邮件未启用/发送失败”，但信号仍正常展示。
3. 邮件配置正确时，信号卡片显示“邮件已发送”。

### 开发提示词

```text
请优化后台任务和信号邮件提醒状态展示。

背景：
当前 NotificationService 已能尝试发送邮件，并把 notification_sent、notification_sent_at、notification_error 写入 WatchSignal。但 H5 信号卡片和后台任务页面没有清晰展示这些结果，用户不知道后台任务是否真的运行、邮件是否真的发送。

目标：
1. 在 H5 自选-信号卡片中展示邮件提醒状态：
   - notification_sent=true：显示“邮件已发送”
   - notification_error 存在：显示“邮件发送失败：简短错误”
   - 未发送且无错误：显示“邮件待发送”或“不需要提醒”
2. 在后台任务页面中，把 scan_watch_rules、scan_trade_rules、auto_remove_watch_pool、update_watch_prices 归类到“自选监控”。
3. 每个任务显示最近运行时间、运行状态、影响条数、错误摘要。
4. 保留已有手动运行任务能力。
5. 不暴露 SMTP 密码等敏感信息。
6. 不改变邮件发送核心逻辑，除非发现明显 bug。

完成后请输出：
1. 修改文件。
2. 信号卡片新增字段。
3. 后台任务页新增展示。
4. 手工验证步骤。
```

---

## 阶段 6：增加规则试算/效果预览

### 目标

让用户或管理员可以对某只观察股手动执行一次规则检测，看到每条规则通过/未通过原因，但不写入信号。

这是让用户清晰看到新需求实际效果的关键功能。

### 修改范围

- `app/api/routes/h5.py`
- `app/services/tasks.py` 或新增 `app/services/rule_preview.py`
- `frontend/src/pages/WatchPoolPage.tsx`
- 可选：admin 交易体系页面

### 实现要求

1. 新增只读试算接口，例如：
   - `POST /h5/watch-pool/{watch_id}/rule-preview`
2. 接口行为：
   - 读取观察股当前交易体系和参数
   - 读取该体系 observe 阶段规则
   - 调用同一套 RuleExecutor
   - 返回每条规则结果
   - 不写入 `watch_signal`
   - 不修改 `watch_pool`
   - 不发送邮件
3. 返回字段建议：
   - `system_code`
   - `system_name`
   - `stage`
   - `rules`
   - `required_passed`
   - `buy_signal_triggered`
   - `would_generate_signal`
4. 每条规则返回：
   - `rule_code`
   - `rule_name`
   - `rule_type`
   - `timeframe`
   - `required`
   - `logic_group`
   - `logic_operator`
   - `triggered`
   - `trigger_price`
   - `reason`
5. H5 观察详情中增加“试算”或“检测”按钮。
6. 试算结果在底部抽屉内展示，不跳页。

### 验收检查

1. 点击某个观察股“试算”，能看到：
   - 不跌破箱体上沿：通过/未通过
   - 15分钟底背离：通过/未通过
   - 5分钟底背离：通过/未通过
2. 试算不会新增 `watch_signal`。
3. 试算不会改变观察股状态。
4. 试算不会发送邮件。
5. 用户能看懂“为什么当前没有信号”或“如果正式扫描会产生什么信号”。

### 开发提示词

```text
请实现观察股规则试算功能，用于让用户清晰看到交易体系规则当前是否满足。

背景：
当前系统已经有 scan_watch_rules，会真实扫描并写入 watch_signal。但用户希望清晰看到新交易体系实际效果，因此需要一个 dry-run 试算接口：执行同一套规则，但不写信号、不改状态、不发邮件。

目标：
1. 新增 POST /h5/watch-pool/{watch_id}/rule-preview。
2. 该接口读取 watch_pool 当前交易体系、system_params_json、observe 阶段规则绑定。
3. 调用与 scan_watch_rules 相同的 RuleExecutor 逻辑。
4. 返回每条规则的执行结果，包括 rule_code、rule_name、rule_type、timeframe、required、logic_group、logic_operator、triggered、trigger_price、reason、snapshot 的简化信息。
5. 返回整体结论：
   - required_passed
   - buy_signal_triggered
   - would_generate_signal
6. 试算接口不能写入 watch_signal。
7. 试算接口不能修改 watch_pool。
8. 试算接口不能发送邮件。
9. 前端 WatchPoolPage.tsx 在观察详情底部抽屉增加“试算”按钮，并在抽屉内展示试算结果。
10. 试算展示要使用中文规则名，用户能看懂每条规则为什么通过或不通过。

建议：
如 scan_watch_rules 内部逻辑重复较多，可以抽出一个轻量 RuleEvaluationService，但不要过度抽象。

完成后请输出：
1. 新增接口。
2. 试算返回 JSON 示例。
3. 前端展示效果说明。
4. 如何验证不会写入信号。
```

---

## 阶段 7：补充测试与最终验收

### 目标

确保新交易体系闭环达到可生产使用的最低标准。

### 修改范围

- `tests/test_scan_watch_rules.py`
- `tests/test_scan_trade_rules.py`
- `tests/test_prd_v1_api.py`
- 可新增：
  - `tests/test_rule_preview.py`
  - `tests/test_scheduler_jobs.py`

### 必测场景

1. 交易体系种子数据存在。
2. 平台突破参数定义存在。
3. 平台突破观察规则绑定存在。
4. 加入观察必须保存 `trading_system_code` 和 `system_params_json`。
5. 缺少必填体系参数时不能加入观察。
6. `scan_watch_rules` 能产生买点信号。
7. 买点信号触发后进入 `buy_confirm` 阶段。
8. 关闭监控不会扫描。
9. 关闭信号不会扫描。
10. 确认买入后生成交易记录，并带入卖点/止损规则。
11. `scan_trade_rules` 能产生卖点或止损提醒。
12. 规则试算不写信号、不改状态、不发邮件。
13. scheduler 包含 `scan_watch_rules` 和 `scan_trade_rules`。
14. 前端构建通过。

### 最终验收路径

1. 在 admin 定义或确认“平台突破”交易体系。
2. 在市场页选择股票加入观察，选择“平台突破”。
3. 填写箱体上沿、平台支撑、观察价、失效条件。
4. 到自选-观察查看该股票：
   - 交易体系显示为平台突破
   - 阶段显示观察
   - 核心参数正确
   - 下一步清晰
5. 点击详情中的“试算”：
   - 能看到每条规则通过/未通过
6. 手动运行或等待 `scan_watch_rules`：
   - 满足条件后自选-信号出现买点信号
   - 显示中文规则名
   - 显示邮件状态
7. 确认买入：
   - 该股票进入自选-交易
   - 显示卖点规则和止损规则
8. 手动运行或等待 `scan_trade_rules`：
   - 满足卖点/止损时出现交易提醒
9. 后台任务页能看到任务运行记录。

### 开发提示词

```text
请为多交易体系观察-信号-交易闭环补充测试和最终验收保障。

背景：
当前系统已经逐步实现交易体系、观察规则扫描、交易规则扫描、H5 展示和规则试算。现在需要补齐测试，确保功能达到可生产使用的最低标准。

目标：
1. 补充后端测试，覆盖交易体系种子数据、观察股加入、规则扫描、生命周期推进、确认买入、交易规则扫描、规则试算、scheduler job。
2. 保留已有测试，不要删除旧测试。
3. 对新增接口补充至少一个成功用例和一个关键失败用例。
4. 确保 scan_watch_rules 不扫描 monitor_enabled=False、signal_enabled=False、非 watching 状态的数据。
5. 确保规则试算不写 watch_signal、不修改 watch_pool、不发送邮件。
6. 确保确认买入后 watch_trade 带入 system_params_json、active_sell_rule_codes_json、active_stop_rule_codes_json。
7. 前端执行 npm run build 并修复构建错误。

完成后请输出：
1. 新增或修改的测试文件。
2. 覆盖了哪些业务场景。
3. 测试命令和结果。
4. 前端构建命令和结果。
5. 仍未覆盖的风险点。
```

## 4. 交付标准

全部阶段完成后，系统应达到以下标准：

1. 后台能定义交易体系、参数、规则、绑定关系。
2. H5 加入观察必须选择交易体系。
3. H5 编辑观察股可以修改体系参数。
4. 观察股卡片能显示当前体系、阶段、核心参数、下一步。
5. 后台任务会自动扫描观察规则和交易规则。
6. 平台突破出现 5/15 分钟底背离时，自选-信号能显示买点信号。
7. 邮件配置正确时能发送提醒；配置错误时页面能看到失败原因。
8. 确认买入后进入交易阶段，并继承体系卖点/止损规则。
9. 卖点/止损触发后，自选-交易能显示提醒。
10. 用户可以通过“规则试算”看到规则是否满足，且试算不改变业务数据。
11. 前端构建通过。
12. 后端测试通过。

## 5. 给 AI 的通用约束

每一步开发都必须遵守：

```text
请基于当前项目现状实现，不要推翻重写。
不要删除现有表和字段。
不要破坏 H5 自选-观察/信号/交易现有功能。
不要自动买入、自动卖出或对接券商。
不要添加复杂权限、审计、审批流程。
后台 admin 只需要保证数据流可管理。
前端展示要让普通用户看懂，不要主要展示规则编码。
每次修改后必须说明修改文件、验证步骤和未完成风险。
```

