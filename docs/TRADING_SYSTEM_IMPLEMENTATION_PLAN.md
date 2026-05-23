# 多交易体系落地实施文档

本文档用于指导 AI 分阶段实现“多交易体系驱动的观察-信号-交易-复盘系统”。

目标不是一次性重写系统，而是在当前项目基础上逐步扩展，让系统支持：

- 后台定义交易体系
- 后台定义体系参数、买点、买点确认、卖点、止损
- 观察股必须绑定交易体系
- 后台任务按交易体系自动监控信号
- 信号触发后进入自选-信号并邮件提醒
- 人工确认买入后进入交易程序
- 交易阶段继续监控卖点和止损
- 后续可以扩展新的交易体系和新的规则

## 1. 当前项目基础

当前项目已有以下能力，应优先复用，不要推倒重做：

- `watch_pool`：观察股
- `watch_signal`：信号
- `watch_trade`：交易
- `watch_trade_execution`：交易流水
- `watch_pool_status_log`：观察状态日志
- `config_task` / `config_task_log`：后台任务
- H5 自选-观察 / 信号 / 交易页面
- admin 后台页面
- K 线、报价、后台任务基础能力
- `mkt_stock_quote` 最新报价表
- `update_watch_prices` 自选价格更新任务
- `scan_watch_signals` 自选信号扫描任务
- `auto_remove_watch_pool` 自动剔除任务
- 15 分钟低背离相关策略代码
- `SignalEngine` 信号扫描框架雏形

## 2. 总体开发原则

1. 不推翻现有表和功能。
2. 不删除 `watch_pool` / `watch_signal` / `watch_trade`。
3. 新功能以扩展为主。
4. 旧字段先保留兼容。
5. 平台突破作为第一套完整样板体系。
6. 新交易体系不能写死在前端。
7. 新规则必须走统一规则执行器。
8. 后台任务必须通用化。
9. 每一步都要可独立验证。
10. 每一步都不要过度开发。
11. 每一步完成后必须输出：
    - 修改了哪些文件
    - 新增了哪些表
    - 新增了哪些接口
    - 是否影响现有 H5
    - 如何验证
    - 哪些还没做

## 3. 推荐阶段

建议按以下顺序推进：

1. 阶段 1：新增交易体系基础模型
2. 阶段 2：admin 交易体系只读页面
3. 阶段 3：观察股绑定体系参数
4. 阶段 4：规则执行器框架
5. 阶段 5：通用观察规则扫描任务
6. 阶段 6：平台突破观察阶段真实规则
7. 阶段 7：邮件提醒
8. 阶段 8：确认买入进入交易程序
9. 阶段 9：交易阶段卖点/止损扫描
10. 阶段 10：admin 编辑交易体系

每个阶段完成后，都应先 review，再进入下一阶段。

---

## 阶段 1：新增交易体系基础模型

### 目标

新增交易体系定义、规则定义、参数定义、体系规则绑定。

只做：

- 数据模型
- Alembic 迁移
- 种子数据
- admin 只读接口

不做：

- 规则执行器
- 信号扫描
- H5 自选流程改造

### 提示词

```text
请基于当前项目实现“多交易体系”的第一阶段：交易体系基础模型。

重要限制：
1. 只做数据模型、迁移、种子数据和 admin 只读接口。
2. 不实现规则执行器。
3. 不实现信号扫描。
4. 不改 H5 自选业务流程。
5. 不删除或重命名任何现有表和字段。
6. 不影响现有 watch_pool / watch_signal / watch_trade。
7. 平台突破只是第一套样板体系，不要把逻辑写死。

需要实现：

一、新增表
1. trading_system_definition
2. trading_rule_definition
3. trading_system_param_definition
4. trading_system_rule_binding

二、字段要求

trading_system_definition：
- system_id
- system_code，唯一
- system_name
- description
- lifecycle_desc
- enabled
- sort_order
- created_at
- updated_at

trading_rule_definition：
- rule_id
- rule_code，唯一
- rule_name
- rule_type：buy_signal / sell_signal / stop_loss / filter / confirm
- timeframe：5m / 15m / 30m / daily
- executor_key
- description
- enabled
- created_at
- updated_at

trading_system_param_definition：
- param_id
- system_code
- param_key
- param_name
- param_type：number / text / select / boolean
- required
- default_value
- description
- sort_order
- enabled
- created_at
- updated_at

trading_system_rule_binding：
- binding_id
- system_code
- rule_code
- stage：observe / buy_confirm / trading / sell / stop_loss
- required
- logic_group
- logic_operator：AND / OR
- enabled
- sort_order
- config_json
- created_at
- updated_at

三、写 Alembic 迁移。

四、初始化种子数据

交易体系：
- platform_breakout：平台突破
- uptrend：上涨趋势
- limit_relay：涨停接力
- oversold_rebound：超跌反弹

平台突破参数：
- platform_upper_price：箱体上沿，number，必填
- platform_support_price：平台支撑位，number，必填
- key_observe_price：关键观察价，number，必填
- auto_remove_price：自动剔除价，number，非必填
- invalid_condition：失效条件，text，必填

平台突破规则：
- not_break_platform_upper：不跌破箱体上沿，filter，daily，executor_key=not_break_price
- b5_divergence：5分钟底背离，buy_signal，5m，executor_key=macd_bottom_divergence
- b15_divergence：15分钟底背离，buy_signal，15m，executor_key=macd_bottom_divergence
- m5_top_divergence：5分钟顶背离，sell_signal，5m，executor_key=macd_top_divergence
- m30_dead_cross：30分钟死叉，sell_signal，30m，executor_key=macd_dead_cross
- break_platform_support：收破平台支撑位，stop_loss，daily，executor_key=break_price

平台突破规则绑定：
observe 阶段：
- not_break_platform_upper，required=true，logic_group=platform_retest，logic_operator=AND
- b5_divergence，required=false，logic_group=bottom_divergence，logic_operator=OR
- b15_divergence，required=false，logic_group=bottom_divergence，logic_operator=OR

trading 阶段：
- m5_top_divergence，logic_group=sell_signal，logic_operator=OR
- m30_dead_cross，logic_group=sell_signal，logic_operator=OR

stop_loss 阶段：
- break_platform_support，logic_group=stop_loss，logic_operator=OR

五、新增 admin 只读接口：
- GET /api/admin/trading-systems
- GET /api/admin/trading-systems/{system_code}
- GET /api/admin/trading-rules
- GET /api/admin/trading-systems/{system_code}/params
- GET /api/admin/trading-systems/{system_code}/rules

六、完成后请输出：
- 修改了哪些文件
- 新增了哪些表
- 新增了哪些接口
- 如何执行迁移
- 如何验证种子数据
- 是否影响 H5
- 尚未实现哪些内容

七、请运行可用的检查：
- git status -sb
- 如果前端没改，不需要 npm build
- 如果本地 Python 环境可用，运行后端基础测试；不可用请说明原因
```

### 验收检查

```text
能看到四套交易体系。
能看到平台突破参数。
能看到平台突破规则。
H5 自选页面原功能不受影响。
```

---

## 阶段 2：admin 交易体系只读页面

### 目标

后台能查看交易体系、参数、规则绑定，但不能编辑。

### 提示词

```text
请基于阶段 1 已完成的交易体系基础模型，在 admin 后台增加“交易体系管理”只读页面。

要求：
1. 不新增编辑、新增、删除能力。
2. 不影响现有 admin 页面。
3. 在 admin 菜单增加“交易体系管理”。
4. 页面展示：
   - 交易体系列表
   - 点击某个体系后展示体系详情
   - 展示参数定义
   - 展示规则绑定
5. 平台突破详情页能清楚看到：
   - 观察参数
   - 观察阶段规则
   - 交易阶段卖点规则
   - 止损规则
6. 样式保持当前 admin 风格，避免大重构。
7. 不改 H5。
8. 不实现规则执行逻辑。

完成后请输出：
- 修改文件
- 页面入口
- 调用哪些接口
- 如何验证
```

### 验收检查

```text
进入 admin。
能看到交易体系管理。
能看到平台突破完整配置。
不能编辑。
H5 不受影响。
```

---

## 阶段 3：观察股绑定体系参数

### 目标

加入观察股时，必须选择交易体系，并保存体系参数。

### 提示词

```text
请基于当前项目，让 watch_pool 支持交易体系实例参数，但要兼容已有数据，不破坏现有 H5 自选功能。

要求：
1. 扩展 watch_pool，不删除旧字段。
2. 新增字段：
   - trading_system_code，nullable，兼容旧数据
   - system_stage，默认 observe
   - system_params_json，JSON，默认 {}
   - active_rule_codes_json，JSON，默认 []
   - next_action，Text，可空

3. 写 Alembic 迁移。
4. 新增后端逻辑：
   - 新增观察股时，如果传入 trading_system_code，则校验该体系存在且启用。
   - 根据 trading_system_param_definition 校验必填参数。
   - 保存参数到 system_params_json。
   - 同步兼容旧字段 trading_system = trading_system_code。
   - 旧流程仍然可用。

5. H5 加入观察流程改造：
   - 加入观察时必须选择交易体系。
   - 选择交易体系后，从接口获取参数定义。
   - 动态展示参数输入项。
   - 必填参数未填不能提交。
   - 平台突破必须填写：
     - 箱体上沿
     - 平台支撑位
     - 关键观察价
     - 失效条件

6. 自选-观察卡片展示：
   - 交易体系名称
   - 当前阶段
   - next_action
   - 核心参数

7. 不实现规则扫描。
8. 不改信号、交易确认逻辑。
9. 保证已有观察股仍能显示。

完成后请输出：
- 数据库字段变化
- 后端校验逻辑
- H5 改动
- 老数据兼容方式
- 验证步骤
```

### 验收检查

```text
旧观察股仍能打开。
新增观察股必须选择交易体系。
选择平台突破后出现箱体上沿、平台支撑位等字段。
不填必填参数无法提交。
提交后 watch_pool.system_params_json 有数据。
```

---

## 阶段 4：规则执行器框架

### 目标

建立规则执行器接口，但不实现真实复杂规则。

### 提示词

```text
请实现交易规则执行器框架，只做框架和一个测试规则，不接入真实交易信号，不影响现有 scan_watch_signals。

要求：
1. 新增目录：
   - app/rule_executors/

2. 新增：
   - base.py
   - registry.py

3. 定义 RuleContext：
   - watch_id
   - stock_code
   - stock_name
   - trading_system_code
   - stage
   - system_params
   - rule_config
   - trade_date
   - latest_price

4. 定义 RuleResult：
   - triggered
   - rule_code
   - rule_name
   - rule_type
   - signal_level
   - trigger_price
   - trigger_time
   - reason
   - risk_desc
   - snapshot

5. 定义 RuleExecutor 基类：
   - execute(context) -> RuleResult

6. 定义 registry：
   - register_executor
   - get_executor
   - list_executors

7. 实现测试执行器：
   - executor_key=always_false
   - 永远返回 triggered=false

8. 添加简单单元测试或脚本验证 registry 能正常找到执行器。

9. 不接入后台任务。
10. 不改 H5。
11. 不生成 watch_signal。

完成后请输出：
- 新增文件
- 执行器接口说明
- 如何新增一个执行器
- 如何验证 registry
```

### 验收检查

```text
能 import registry。
能 get_executor("always_false")。
执行后返回 triggered=false。
现有功能不受影响。
```

---

## 阶段 5：通用观察规则扫描任务

### 目标

实现 `scan_watch_rules`，先只跑 `always_false`，验证任务链路。

### 提示词

```text
请实现通用观察规则扫描任务 scan_watch_rules，先只验证框架链路，不实现真实信号。

要求：
1. 新增 TaskService.scan_watch_rules。
2. 新增 config_task 种子：
   - scan_watch_rules
   - owner_module=signal
   - task_type=scheduled

3. H5 我的-后台任务和 admin 手动执行任务映射支持 scan_watch_rules。

4. scan_watch_rules 逻辑：
   - 找出 active=true 且 system_stage=observe 的 watch_pool
   - 根据 trading_system_code 查询启用的 observe 阶段规则绑定
   - 根据 rule.executor_key 找执行器
   - 构造 RuleContext
   - 执行规则
   - 如果 triggered=false，不生成信号
   - 记录任务日志 affected_rows

5. 当前只允许使用 always_false 或已存在的安全执行器。
6. 不生成真实信号。
7. 不发送邮件。
8. 不替换 scan_watch_signals。
9. scan_watch_signals 保持现状。

完成后请输出：
- 新增任务名称
- 扫描逻辑
- 是否影响旧任务
- 如何手动执行
- 如何查看任务日志
```

### 验收检查

```text
我的-后台任务能看到 scan_watch_rules。
手动执行成功。
任务日志 success。
不会生成 watch_signal。
旧 scan_watch_signals 仍可运行。
```

---

## 阶段 6：平台突破观察阶段真实规则

### 目标

实现平台突破的观察阶段信号。

### 提示词

```text
请实现平台突破观察阶段的真实规则执行器，但只覆盖观察阶段买点，不实现卖点和止损。

要求：
1. 新增或改造执行器：
   - not_break_price
   - macd_bottom_divergence

2. macd_bottom_divergence 支持配置 timeframe：
   - 5m
   - 15m

3. 可复用当前已有 macd15.py 逻辑，但要封装为 RuleExecutor。
4. not_break_price 用于判断：
   - 最新价或最新K线收盘价不低于 system_params_json.platform_upper_price

5. scan_watch_rules 支持逻辑组合：
   - not_break_platform_upper 必须满足
   - b5_divergence 或 b15_divergence 任一满足

6. 触发后生成 watch_signal：
   - stock_code
   - watch_id
   - trading_system_code
   - rule_code
   - rule_type=buy_signal
   - signal_type=buy
   - signal_status=buy_pending_confirm
   - trigger_price
   - trigger_time
   - trigger_reason
   - snapshot_json

7. 防重复：
   - 同一 watch_id、rule_code、trigger_date 不重复生成

8. 更新 watch_pool：
   - latest_signal_id
   - status=buy_pending_confirm 或 signal_generated
   - next_action=等待人工确认买入

9. 不发送邮件，邮件下一阶段做。
10. 不影响旧 scan_watch_signals。

完成后请输出：
- 新增执行器
- 信号生成逻辑
- 防重复逻辑
- 如何准备测试数据
- 如何验证平台突破信号出现
```

### 验收检查

```text
平台突破观察股能被扫描。
满足条件后生成 watch_signal。
自选-信号能看到。
重复执行不会重复生成。
非平台突破股票不走平台突破规则。
```

---

## 阶段 7：邮件提醒

### 目标

信号触发后邮件提醒，且防重复。

### 提示词

```text
请为 watch_signal 增加邮件提醒能力，先只支持买点信号提醒。

要求：
1. 新增 NotificationService。
2. 新增邮件配置读取方式，优先复用项目现有配置风格。
3. watch_signal 新增字段：
   - notification_sent
   - notification_sent_at
   - notification_error

4. scan_watch_rules 生成新信号后，调用 NotificationService。
5. 邮件内容包含：
   - 股票名称
   - 股票代码
   - 交易体系
   - 规则名称
   - 触发价
   - 触发时间
   - 触发原因
   - 系统链接或提示

6. 如果邮件发送成功：
   - notification_sent=true
   - notification_sent_at=now

7. 如果发送失败：
   - 不影响信号生成
   - 记录 notification_error
   - 任务日志能看到错误摘要

8. 防重复：
   - notification_sent=true 的信号不重复发送

9. 不做复杂消息中心。
10. 不做多渠道通知。

完成后请输出：
- 配置项
- 服务文件
- 字段迁移
- 邮件模板
- 失败处理
- 验证方法
```

### 验收检查

```text
触发平台突破信号后收到邮件。
重复执行任务不会重复发送。
邮件失败不影响信号展示。
```

---

## 阶段 8：确认买入进入交易程序

### 目标

确认买入后，按交易体系进入交易阶段。

### 提示词

```text
请改造确认买入流程，让交易记录继承交易体系和规则上下文。

要求：
1. 扩展 watch_trade：
   - trading_system_code
   - entry_rule_code
   - system_params_json
   - active_sell_rule_codes_json
   - active_stop_rule_codes_json
   - current_stage
   - latest_trade_signal_id

2. 确认买入时：
   - 从 watch_signal 获取 trading_system_code、rule_code
   - 从 watch_pool 获取 system_params_json
   - 创建或更新 watch_trade
   - 设置 trading_system_code
   - 设置 entry_rule_code
   - 复制 system_params_json
   - 根据体系绑定加载 trading/sell/stop_loss 阶段规则
   - 写入 active_sell_rule_codes_json 和 active_stop_rule_codes_json

3. 更新状态：
   - signal_status=confirmed_buy
   - user_action=confirmed_buy
   - watch_pool.system_stage=trading
   - watch_pool.status=trading
   - watch_pool.monitor_enabled=false
   - watch_pool.signal_enabled=false

4. H5 交易页展示：
   - 交易体系
   - 当前阶段
   - 进入交易的规则
   - 当前监控的卖点/止损规则

5. 不实现卖点/止损扫描。
6. 保持旧确认买入接口兼容。

完成后请输出：
- 数据迁移
- 确认买入流程变化
- H5 展示变化
- 兼容旧数据方式
- 验证步骤
```

### 验收检查

```text
买点信号确认买入后进入交易页。
交易记录带 trading_system_code。
交易记录带 entry_rule_code。
交易记录带卖点/止损规则列表。
```

---

## 阶段 9：交易阶段卖点/止损扫描

### 目标

交易中按体系规则监控卖点和止损。

### 提示词

```text
请实现通用交易规则扫描任务 scan_trade_rules，并实现平台突破的卖点/止损规则。

要求：
1. 新增 TaskService.scan_trade_rules。
2. 新增 config_task：
   - scan_trade_rules

3. 支持执行交易中的规则：
   - m5_top_divergence
   - m30_dead_cross
   - break_platform_support

4. m5_top_divergence：
   - executor_key=macd_top_divergence
   - timeframe=5m

5. m30_dead_cross：
   - executor_key=macd_dead_cross
   - timeframe=30m

6. break_platform_support：
   - executor_key=break_price
   - 使用 system_params_json.platform_support_price
   - daily 收盘价跌破才触发

7. 触发后生成 watch_signal：
   - signal_type=sell 或 risk
   - rule_type=sell_signal 或 stop_loss
   - signal_status=sell_signal_pending 或 stop_loss_pending
   - related_trade_id

8. 邮件提醒。
9. 防重复：
   - 同一 trade_id、rule_code、trigger_date 不重复生成

10. H5 交易页能展示卖点/止损提醒。
11. 不自动卖出，必须人工确认。

完成后请输出：
- 新增任务
- 新增执行器
- 信号类型定义
- 防重复方式
- H5 展示位置
- 验证步骤
```

### 验收检查

```text
交易中的平台突破股票能被扫描。
触发卖点后生成提醒。
触发止损后生成提醒。
邮件能收到。
不会自动卖出。
```

---

## 阶段 10：admin 编辑交易体系

### 目标

后台支持维护交易体系配置。

### 提示词

```text
请在 admin 后台实现交易体系编辑能力，但保持简单，不做复杂低代码表达式编辑器。

要求：
1. 交易体系：
   - 新增
   - 编辑名称、描述、生命周期说明
   - 启用/停用

2. 规则定义：
   - 新增规则
   - 编辑规则
   - 选择 rule_type
   - 选择 timeframe
   - 填 executor_key
   - 启用/停用

3. 参数定义：
   - 新增参数
   - 编辑参数
   - 设置是否必填
   - 设置排序

4. 体系规则绑定：
   - 选择已有规则绑定到体系
   - 设置 stage
   - 设置 required
   - 设置 logic_group
   - 设置 logic_operator
   - 启用/停用

5. 如果 executor_key 没有注册执行器，前端要提示：
   - 该规则暂无执行器，不能参与自动监控

6. 不实现复杂拖拽。
7. 不实现表达式编辑器。
8. 不影响 H5。

完成后请输出：
- 新增/修改接口
- 前端页面入口
- 表单校验
- 如何验证新增体系
```

### 验收检查

```text
后台能新增一个测试体系。
能绑定已有 always_false 规则。
H5 能选择该体系。
任务扫描不会报错。
```

---

## 4. 每一步通用验收模板

每完成一步，让 AI 按这个格式回复：

```text
## 完成内容

## 修改文件

## 数据库变化

## 新增接口

## 前端入口

## 后台任务变化

## 兼容性说明

## 验证命令

## 验证结果

## 尚未实现
```

必须要求 AI 执行：

```bash
git status -sb
```

前端改动必须执行：

```bash
cd frontend
npm run build
```

后端如果本地 Python 环境可用，执行：

```bash
pytest
```

如果 Python 环境不可用，必须说明原因。

数据库改动必须说明：

```bash
alembic upgrade head
```

## 5. 禁止 AI 做的事

明确禁止：

1. 不要一次性实现所有阶段。
2. 不要删除旧表。
3. 不要重命名旧字段。
4. 不要把平台突破写死到 H5。
5. 不要新建另一套观察/信号/交易表。
6. 不要绕过 `watch_signal` 生成信号。
7. 不要让规则执行器直接发送邮件。
8. 不要自动确认买入。
9. 不要自动卖出。
10. 不要做复杂低代码表达式引擎。
11. 不要大范围重构 UI。
12. 不要影响现有自选-观察/信号/交易使用。

## 6. 推进方式

建议每次只下发一个阶段。

推荐节奏：

```text
第一轮：只做阶段 1
第二轮：检查阶段 1
第三轮：只做阶段 2
第四轮：检查阶段 2
第五轮：只做阶段 3
第六轮：检查阶段 3
```

每一阶段完成后，可以让另一个 AI 或人工 review：

```text
请拉取最新代码，检查阶段 X 是否符合验收标准，不修改代码，先输出分析。
```

每一阶段确认通过后，再进入下一阶段。

