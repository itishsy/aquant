# H5 自选统一列表改版分步执行提示词

## 使用说明

本文档基于：

```text
docs/WATCH_POOL_UNIFIED_OVERVIEW_IMPLEMENTATION_PLAN.md
```

包含六个按顺序执行的开发提示词。每个阶段完成并验证后，再执行下一阶段。

所有阶段共同要求：

1. 实现生产级代码，不只完成视觉演示。
2. 开始修改前先阅读相关现有代码、接口和测试，不凭假设重写。
3. 保持 Aquant 当前 H5 页面风格，不引入新的视觉体系。
4. 优先复用现有组件、服务、状态映射和 API 客户端。
5. 新增组件必须职责单一、命名清晰、类型明确。
6. 禁止继续让 `WatchPoolPage.tsx` 膨胀。
7. 禁止使用大量 `any`；动态 JSON 使用 `Record<string, unknown>`。
8. 禁止复制现有编辑、试算、确认买入和确认卖出逻辑形成两套流程。
9. 每个阶段应删除本阶段已经被完全替代且确认无引用的旧代码。
10. 不删除仍被其他页面、接口或测试使用的兼容能力。
11. 不修改规则执行器、规则扫描、邮件通知和交易业务语义。
12. 不修改数据库结构。
13. 不影响 MarketPage、AdminPage 和其他 H5 页面。
14. 前端样式优先使用语义化 CSS 类，避免散落大量重复内联样式。
15. 所有列表和详情必须适配 360px、390px、430px 视口。
16. 不在页面显示开发说明、实现说明或操作教程。
17. 工作区可能存在用户未提交改动，不得覆盖或回退无关改动。

---

## 提示词 1：实现后端自选聚合与历史接口

```text
请先阅读：
- docs/WATCH_POOL_UNIFIED_OVERVIEW_IMPLEMENTATION_PLAN.md
- app/api/routes/h5.py
- app/models/entities.py
- app/services/prd_v1.py
- tests/test_prd_v1_api.py

请实现 H5 自选统一列表所需的后端聚合与历史接口。

目标接口：

1. GET /api/h5/watch-pool/overview
2. GET /api/h5/watch-pool/{watch_id}/signals
3. GET /api/h5/watch-pool/{watch_id}/trade-records

一、代码结构要求

1. 不要把复杂聚合查询和状态排序逻辑继续堆入 h5.py。
2. 新增清晰的服务文件，例如：
   - app/services/watch_overview.py
3. h5.py 只负责参数接收、依赖注入、调用服务和返回结果。
4. 服务内部提取小型私有方法处理：
   - 状态分组
   - 排序优先级
   - 最新信号
   - 当前交易
   - 历史数据兼容查询
5. 复用已有 _signal_dict、_trade_dict、_execution_dict、_quote_map、
   _system_name_map、_rule_map 等序列化能力；如复用边界不合理，
   可将通用序列化函数移动到清晰的模块，但不要复制两套实现。

二、overview 接口

支持可选参数：
- keyword
- trading_system
- status
- include_terminal，默认 true

返回：

{
  "summary": {
    "total": 0,
    "active_total": 0,
    "terminal_total": 0,
    "today_signal_count": 0,
    "today_trade_count": 0
  },
  "items": []
}

每个 item 至少返回：
- watch_id
- stock_code
- stock_name
- latest_price
- change_pct
- sector_name
- entry_date
- entry_source
- trading_system_code
- trading_system_name
- status
- status_name
- system_stage
- display_group
- sort_priority
- sort_time
- card_tone
- latest_signal
- active_trade

latest_signal 至少返回：
- signal_id
- signal_type
- signal_status
- rule_code
- rule_name
- trigger_time

active_trade 至少返回：
- trade_id
- trade_status
- target_price
- stop_loss_price
- current_stage

三、排序规则

必须由后端计算并按以下规则返回：

1. 交易中
2. 今日有信号
3. 观察中
4. 已剔除或终止状态

建议 sort_priority：
- 10：存在 open / holding 交易
- 20：今日存在待处理买点、卖点或止损信号
- 30：今日存在其他信号
- 40：观察中、等待买点、监控暂停
- 90：removed、invalid、blacklist、archived

最终排序：
- sort_priority ASC
- sort_time DESC
- watch_id DESC

同组业务时间：
- 交易中：最新交易信号时间，其次最近交易时间
- 今日有信号：最新信号时间
- 观察中：加入观察时间
- 终止状态：removed_at，其次创建时间

四、汇总统计

- total：当前 overview 返回的总记录数
- active_total：active=true 的记录数
- terminal_total：终止状态记录数
- today_signal_count：系统交易时区当天生成的信号数量
- today_trade_count：系统交易时区当天的 WatchTradeExecution 数量

使用 settings.timezone 解释“今日”，不要使用 UTC 日期直接比较。

五、历史记录接口

GET /watch-pool/{watch_id}/signals：
- 优先查询 WatchSignal.watch_id
- 兼容旧数据：watch_id 为空时，使用 stock_code 兜底
- 去重
- 按 trigger_time 倒序
- 返回中文规则名称
- 不同股票数据不得串联

GET /watch-pool/{watch_id}/trade-records：
- 返回关联 WatchTrade 和 WatchTradeExecution
- 以执行流水作为主要记录
- 返回 execution_type_name、execution_reason、execution_time、
  execution_price、execution_amount、trade_status
- 尚无执行流水的交易也应返回概要记录
- 优先 watch_id，旧数据可按 stock_code 兜底
- 按业务时间倒序

六、兼容和性能要求

1. 不修改现有 /watch-pool、/watch-signals、/watch-trades 接口语义。
2. 不对每只股票单独发起数据库查询，避免明显 N+1。
3. 聚合查询应尽量批量读取信号、交易、报价、规则和体系名称。
4. 不新增数据库字段和迁移。
5. 无信号、无交易、无报价时返回合理空值，不抛未处理异常。

七、测试

新增：
- tests/test_watch_pool_overview_api.py
- tests/test_watch_pool_history_api.py

至少覆盖：
- 默认返回活动和终止状态记录
- include_terminal=false 时只返回活动记录
- 交易中排最前
- 今日有信号排在观察中之前
- 已剔除排最后
- 同组按业务时间倒序
- 最新信号和当前交易正确
- 今日信号数和今日交易数准确
- 信号历史和交易历史倒序
- 旧数据 watch_id 为空时按 stock_code 兼容
- 不同股票数据不串联
- 无历史数据返回空列表
- watch_id 不存在返回 404

运行：
- pytest tests/test_watch_pool_overview_api.py tests/test_watch_pool_history_api.py -v
- pytest tests/test_prd_v1_api.py -v

完成后输出：
1. 修改和新增文件。
2. 新增接口与返回结构。
3. 排序和状态分组规则。
4. 性能与旧数据兼容方式。
5. 测试命令和结果。
6. 已知风险。
```

---

## 提示词 2：建立前端自选模块类型与可复用列表组件

```text
请先阅读：
- docs/WATCH_POOL_UNIFIED_OVERVIEW_IMPLEMENTATION_PLAN.md
- frontend/src/pages/WatchPoolPage.tsx
- frontend/src/components/PageShell.tsx
- frontend/src/components/StockLink.tsx
- frontend/src/styles/app.css
- frontend/src/api/client.ts

阶段 1 的后端 overview 接口已经可用。请建立 H5 自选统一列表的前端模块基础，
本阶段只完成类型、格式化函数和可复用列表组件，不替换现有主页、不修改详情抽屉。

一、目录结构

新增：

frontend/src/pages/watch-pool/
  types.ts
  constants.ts
  formatters.ts
  WatchOverviewHeader.tsx
  WatchOverviewList.tsx
  WatchOverviewItem.tsx

二、类型要求

在 types.ts 中定义清晰类型：
- WatchOverviewResponse
- WatchOverviewSummary
- WatchOverviewItem
- WatchLatestSignal
- WatchActiveTrade
- WatchCardTone
- WatchDisplayGroup
- WatchDetail
- WatchSignalRecord
- WatchTradeRecord
- TradingSystemDefinition
- TradingSystemParamDefinition

不得使用大面积 any。
system_params_json 等动态字段使用 Record<string, unknown>。

三、格式化和常量

在 constants.ts / formatters.ts 中集中实现：
- 中文状态名称兜底
- 交易体系名称兜底
- 日期和时间格式化
- 最新价格式化
- 涨跌幅格式化和颜色
- 列表第二行分隔文本拼接
- 最新信号摘要

要求：
- 空字段不产生多余的 “|”
- 中文规则名缺失时使用 rule_code 兜底
- 不在各组件中复制格式化逻辑

四、组件要求

WatchOverviewHeader：
- 左侧突出显示自选总数
- 右侧显示“今日信号 N | 今日交易 N”
- 风格与现有 feature-card、card-head、soft-tag 一致
- 小屏不能溢出

WatchOverviewItem：
- 第一行：股票名称（最新价，涨跌幅）
- 第二行：板块 | 入选时间 | 交易体系；右侧显示中文状态
- 第三行：最新信号时间 | 触发规则
- 无最新信号时显示“暂无信号记录”
- 整卡可点击
- 不显示雪球按钮
- 不在组件内请求接口
- 不在组件内重新计算后端排序

WatchOverviewList：
- 接收 items 和 onOpenDetail
- 处理列表和空态
- 不包含页面级接口请求

五、状态卡片背景

在 app.css 中使用语义 CSS 类：
- watch-overview-item
- watch-overview-item--trading
- watch-overview-item--today-signal
- watch-overview-item--watching
- watch-overview-item--terminal

视觉要求：
- 交易中：浅红或浅暖色背景
- 今日信号：浅蓝色背景
- 观察中：白色或浅绿色背景
- 已剔除：浅灰色背景并降低辅助文字强调度
- 保持当前 Aquant H5 的卡片圆角、阴影、字号和间距风格
- 不使用高饱和整卡背景
- 状态仍显示文字，不能只依赖颜色

六、生产质量要求

1. 组件 props 类型明确。
2. 组件职责单一。
3. 不引入新的 UI 框架。
4. 不复制 StockLink 的弹窗行为；统一列表股票名称只触发 onOpenDetail。
5. 不修改 MarketPage 中 StockLink 的默认行为。
6. 不修改现有 WatchPoolPage 业务逻辑。

七、验证

运行：
- npm.cmd run build

完成后输出：
1. 新增文件。
2. 类型和组件职责。
3. 四类卡片视觉规则。
4. 是否影响现有页面。
5. 构建结果。
```

---

## 提示词 3：替换自选主页为统一列表

```text
请先阅读：
- docs/WATCH_POOL_UNIFIED_OVERVIEW_IMPLEMENTATION_PLAN.md
- frontend/src/pages/WatchPoolPage.tsx
- frontend/src/pages/watch-pool/ 下阶段 2 已新增的文件

请将 H5 自选主页替换为统一自选股票列表。

目标：
- 页面不再显示“观察 | 信号 | 交易”顶部 Tab
- 首页只展示自选概览和统一列表
- 列表数据来自 GET /h5/watch-pool/overview
- 点击卡片或股票名称打开同一个自选详情入口

一、页面数据加载

首次加载请求：
- GET /h5/watch-pool/overview
- GET /h5/trading-systems（仅现有编辑功能仍需要时保留）

不再在首页请求：
- /h5/watch-signals/recent
- /h5/watch-trades/recent
- /h5/watch-signals/summary
- /h5/watch-trades/summary

不要使用最近 10 条数据拼装列表状态。

二、页面展示

使用阶段 2 的：
- WatchOverviewHeader
- WatchOverviewList
- WatchOverviewItem

保持后端返回顺序，不在前端重新计算 sort_priority。

列表必须展示：
- 交易中
- 今日有信号
- 观察中
- 已剔除或终止状态

已剔除记录仍可点击查看历史详情，但不可显示不适用的编辑和试算操作。

三、详情入口

点击任意列表项时：
- 使用 watch_id 加载完整观察详情
- 打开现有详情抽屉
- 不再以 signal 或 trade 作为详情主目标
- 暂时保留现有详情内容，阶段 4 再替换为四 Tab

四、清理要求

本阶段完成后，删除已经不再使用的：
- tab 状态
- PageShell segments 配置
- buySignals
- riskSignals
- pendingTradeSignals
- watchingItems
- signalSummary
- tradeSummary
- todaySignals 的旧前端计算
- 三类列表页面 JSX
- 首页对 recent signal/trade 的请求

如果旧信号卡片和交易卡片函数已经完全不可达，必须删除：
- renderSignalCard
- renderTradeCard
- renderSignalCardV2
- renderTradeCardV2
- renderSignalCardV3
- renderTradeCardV3

不要删除确认买入、确认卖出等仍会在详情中使用的业务函数。

五、代码结构

1. WatchPoolPage 只保留页面数据协调和详情打开逻辑。
2. 不把统一列表 JSX 再写回 WatchPoolPage。
3. 不复制阶段 2 组件。
4. 删除未使用导入和辅助函数。

六、验证

运行：
- npm.cmd run build

浏览器验证：
- /watch-pool 不再显示观察、信号、交易 Tab
- 列表顺序为交易中、今日有信号、观察中、已剔除
- 四类卡片背景正确
- 点击卡片和股票名称打开同一详情
- 已剔除记录可打开详情
- MarketPage、AdminPage 可正常访问

完成后输出：
1. 修改文件。
2. 删除的旧状态、函数和请求。
3. 新首页的数据流。
4. 浏览器验证结果。
5. 构建结果。
```

---

## 提示词 4：实现统一四 Tab 详情抽屉并迁移业务操作

```text
请先阅读：
- docs/WATCH_POOL_UNIFIED_OVERVIEW_IMPLEMENTATION_PLAN.md
- frontend/src/pages/WatchPoolPage.tsx
- frontend/src/pages/watch-pool/
- app/api/routes/h5.py 中现有自选、试算、信号确认和交易确认接口

请把自选详情改造成以 watch_id 为主体的统一四 Tab 抽屉。

一、新增组件

新增：
- frontend/src/pages/watch-pool/WatchDetailDrawer.tsx
- frontend/src/pages/watch-pool/WatchInfoTab.tsx
- frontend/src/pages/watch-pool/WatchSignalHistoryTab.tsx
- frontend/src/pages/watch-pool/WatchTradeHistoryTab.tsx
- frontend/src/pages/watch-pool/WatchEditForm.tsx
- frontend/src/pages/watch-pool/WatchRulePreview.tsx

如需要，可新增小型通用组件：
- DetailSection
- DetailField
- HistoryRecordItem

不要创建只有一两行包装且没有复用价值的组件。

二、抽屉头部

显示：
- 股票名称（最新价，涨跌幅）
- 右上角无边框雪球图标按钮
- 副标题：板块 | 入选时间 | 交易体系 | 状态

不要重复显示：
- 独立股票代码行
- 当前阶段标签
- 交易体系标签
- 当前状态信息块

三、Tab

顺序固定：
1. K线
2. 详情
3. 信号记录
4. 交易记录

默认打开 K线。

本阶段 K线可先复用现有 KlineChart，支撑位和目标位标记在阶段 5 实现。

按需加载：
- 打开抽屉：GET /h5/watch-pool/{watch_id}
- 信号记录 Tab：GET /h5/watch-pool/{watch_id}/signals
- 交易记录 Tab：GET /h5/watch-pool/{watch_id}/trade-records

同一抽屉会话内缓存已加载的 Tab 数据，避免重复请求。
切换不同 watch_id 时必须清空旧缓存，不能串数据。

四、详情 Tab

展示：
- 核心观察参数
- 入选原因
- 失效条件
- 风险标签
- 用户备注
- 当前交易概要（存在 active_trade 时）

空字段不展示。
动态参数应按已有参数定义或可读名称展示，避免只展示原始 JSON。

五、信号记录 Tab

单条主要显示：
- 信号类型
- 触发规则中文名
- 触发时间

可补充：
- 触发价
- 信号状态
- 触发原因

操作：
- buy_pending_confirm：保留确认买入和放弃机会
- 风险与失效：仅提示人工处理
- 卖点与止损：显示待处理状态

必须复用现有确认买入和放弃接口语义，不得新造业务流程。

六、交易记录 Tab

单条主要显示：
- 交易类型
- 交易原因
- 交易时间

可补充：
- 成交价
- 数量
- 盈亏

对当前 open / holding 交易保留确认卖出入口。
复用现有确认卖出接口语义。

七、底部操作栏

固定主操作：
- 编辑
- 试算
- 关闭

规则：
- 活动自选显示编辑和试算
- 已剔除或终止状态不显示不适用操作
- 编辑继续使用当前抽屉，不额外打开新的 Popup
- 试算结果在详情抽屉内显示

将现有低频操作保留到详情 Tab 的“更多操作”区域：
- 开启/关闭监控
- 标记失效
- 剔除
- 加入黑名单

八、组件和代码质量

1. 将现有动态参数编辑 JSX 迁移到 WatchEditForm。
2. 将现有试算结果 JSX 迁移到 WatchRulePreview。
3. WatchDetailDrawer 负责骨架和协调，不包含大量业务字段 JSX。
4. WatchPoolPage 负责打开、关闭和刷新，不包含详情布局。
5. 删除被替代的旧 DetailKind、DetailTarget.kind 和按 watch/signal/trade
   切换的大型详情分支。
6. 删除不可达旧函数和未使用导入。
7. 保持当前 antd-mobile Popup 与 H5 风格。

九、验证

运行：
- npm.cmd run build

浏览器验证：
- 四个 Tab 均可切换
- 切换不同股票不会显示上一只股票的历史
- 编辑和试算可用
- 买点确认和放弃可用
- 当前交易确认卖出可用
- 已剔除记录只展示适用操作
- 抽屉在 360px、390px、430px 不贴边、不溢出

完成后输出：
1. 新增和修改组件。
2. 四个 Tab 数据来源。
3. 迁移和保留的业务操作。
4. 删除的旧详情代码。
5. 浏览器验证和构建结果。
```

---

## 提示词 5：为 K线增加支撑位和目标位标记

```text
请先阅读：
- docs/WATCH_POOL_UNIFIED_OVERVIEW_IMPLEMENTATION_PLAN.md
- frontend/src/components/StockDetailPopup.tsx
- frontend/src/pages/watch-pool/WatchKlineTab.tsx
- frontend/src/pages/watch-pool/types.ts

请为自选详情 K线 Tab 增加支撑位和目标位标记，同时保持 KlineChart 可复用。

一、组件设计

扩展 KlineChart，使其支持可选标记线参数，例如：

type KlineLevelMarker = {
  name: string;
  price: number;
  color?: string;
};

KlineChart props 增加可选：
- levels?: KlineLevelMarker[]

要求：
- KlineChart 只负责绘制 levels
- 不在 KlineChart 中读取 platform_support_price、target_price 等业务字段
- 未传 levels 时保持其他页面原行为
- 无效、非数字、重复价格应在调用侧或图表侧安全过滤

二、自选详情标记线来源

在 WatchKlineTab 中计算：

支撑位优先级：
1. system_params_json.platform_support_price
2. active_trade.stop_loss_price
3. key_observe_price

目标位优先级：
1. active_trade.target_price
2. system_params_json.platform_upper_price

规则：
- 找不到价格时不显示对应标记线
- 不猜测、不生成默认价格
- 支撑位和目标位相同时合并或避免重叠标签

三、视觉要求

- 支撑位使用克制的绿色或蓝绿色虚线
- 目标位使用克制的红色或橙色虚线
- 标签显示中文名称和价格
- 不遮挡 K 线主体
- 不引起横向溢出
- 保持现有 MA、成交量、MACD 正常显示

四、兼容要求

- 不影响 MarketPage 或其他调用 KlineChart 的页面
- 不修改 K线后端接口
- 不修改规则执行器
- 不引入新的图表库

五、验证

运行：
- npm.cmd run build

浏览器验证：
- 有支撑位和目标位的股票显示标记线
- 缺少价格时不显示错误标记
- 360px、390px、430px 图表不横向溢出
- 图表切换股票后标记线正确更新
- 其他使用 KlineChart 的页面正常

完成后输出：
1. 修改文件。
2. KlineChart 新增 props。
3. 支撑位和目标位来源优先级。
4. 兼容性说明。
5. 浏览器验证和构建结果。
```

---

## 提示词 6：旧代码清理、生产级回归与最终验收

```text
请先阅读：
- docs/WATCH_POOL_UNIFIED_OVERVIEW_IMPLEMENTATION_PLAN.md
- docs/WATCH_POOL_UNIFIED_OVERVIEW_EXECUTION_PROMPTS.md
- 本次前五阶段所有修改

请对 H5 自选统一列表改版做最终代码清理、测试和浏览器验收。

一、代码清理

重点检查并删除：
- 已不使用的观察 / 信号 / 交易顶部 Tab 状态与 JSX
- 已不使用的 recent signal/trade 首页请求
- 已被替代的列表卡片渲染函数
- 已被替代的三类详情分支
- 不可达业务代码
- 重复状态映射
- 重复日期、金额、涨跌幅格式化函数
- 未使用 import、state、useMemo、useEffect
- 已无引用的 CSS 类

必须保留：
- 仍由详情记录操作使用的确认买入、放弃、确认卖出逻辑
- 编辑参数、试算、监控、失效、剔除、黑名单操作
- 其他页面使用的兼容接口和组件行为

不要为了减少文件数量，把组件重新合并回 WatchPoolPage。

二、代码结构验收

要求：
- WatchPoolPage 主要负责页面级请求、选中项和刷新协调
- 列表、详情抽屉、四个 Tab、编辑、试算均为独立清晰组件
- 公共类型集中管理
- 公共格式化逻辑集中管理
- 无明显大面积 any
- 无同一业务逻辑的重复实现
- 无 N+1 前端请求或数据库查询
- 无新旧实现并存

三、后端测试

运行至少：
- pytest tests/test_watch_pool_overview_api.py tests/test_watch_pool_history_api.py -v
- pytest tests/test_prd_v1_api.py -v

如本次改动影响其他已有测试，应修复真实回归，不得删除旧测试规避失败。

四、前端构建

运行：
- cd frontend
- npm.cmd run build

修复全部构建错误。

五、浏览器验收

启动前后端并使用浏览器检查：
- /watch-pool
- /market
- /admin

视口：
- 360px
- 390px
- 430px
- 桌面宽度

自选主页验收：
- 只显示统一自选列表
- 总数、今日信号数、今日交易数正确
- 排序严格为交易中、今日有信号、观察中、已剔除
- 同组按业务时间倒序
- 四类状态卡片背景清晰但不过度
- 已剔除记录可查看历史
- 卡片和文字不贴边、不溢出

详情抽屉验收：
- 头部格式正确且有无边框雪球图标
- 副标题为板块 | 入选时间 | 交易体系 | 状态
- K线、详情、信号记录、交易记录四 Tab 可用
- 支撑位和目标位标记正确
- 编辑、试算、关闭可用
- 信号确认买入、放弃操作可用
- 当前交易确认卖出可用
- 不同股票切换不串数据
- 小屏抽屉和底部按钮不溢出

全局回归：
- MarketPage 正常
- AdminPage 正常
- StockLink 在其他页面保持原行为
- 后端接口无未处理异常

六、最终输出

请输出：
1. 最终新增和修改文件。
2. 删除的旧代码和无用能力。
3. 最终组件结构与职责。
4. 后端接口和排序规则。
5. 后端测试命令与结果。
6. 前端构建命令与结果。
7. 浏览器验收视口与结果。
8. 仍未覆盖的风险。
9. 是否影响其他模块。
```

