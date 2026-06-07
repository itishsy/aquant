# H5 自选统一列表改版实施文档

## 1. 文档目的

本文档用于指导 Aquant H5 自选页从“观察 / 信号 / 交易三个独立列表”改造为“以自选股票为主体的统一列表”。

本阶段只定义实施方案、代码结构、接口契约、清理范围、测试与验收标准，不直接修改业务代码。待方案确认后，再按本文档拆分并发送可逐步执行的 AI 提示词。

## 2. 改版目标

### 2.1 页面主结构

自选页只展示一个自选股票列表，不再显示顶部：

```text
观察 | 信号 | 交易
```

列表顶部展示：

```text
自选总数                            今日信号数 | 今日交易数
```

单只股票摘要展示：

```text
股票名称（最新价，涨跌幅）
板块 | 入选时间 | 交易体系                         状态
最新信号时间 | 触发规则
```

示例：

```text
中际旭创（1179.99，-7.81%）
光通信 | 2026-05-08 | 上涨趋势                     交易中
2026-06-03 14:30 | 跌破 MA20
```

### 2.2 列表排序与状态区分

统一自选列表不能只按加入时间排序，应优先展示当前最需要用户处理的股票。

排序优先级：

1. 交易中的股票。
2. 今日产生信号的股票。
3. 观察中的股票。
4. 已剔除的股票。

同一优先级内的排序规则：

- 交易中：最新交易信号时间倒序，其次最近交易时间倒序。
- 今日有信号：最新信号时间倒序。
- 观察中：加入观察时间倒序。
- 已剔除：剔除时间倒序，其次加入观察时间倒序。

特殊状态归类：

- `trading`、存在 `open / holding` 交易：归入交易中。
- `buy_pending_confirm`、`sell_signal_pending`、`stop_loss_pending`、今日风险信号：归入今日有信号，并排在普通今日信号之前。
- `watching`、监控暂停、等待买点：归入观察中。
- `removed`、`invalid`、`blacklist`、`archived`：归入已剔除或终止状态区域。

不同状态的个股卡片必须有克制但清晰的背景颜色区分：

- 交易中：浅红色或浅暖色背景，突出持仓与退出决策。
- 今日有信号：浅蓝色背景，突出待处理信号。
- 观察中：白色或浅绿色背景，表达正常监控。
- 已剔除：浅灰色背景，文字降低强调度。

状态颜色只能作为辅助信息，卡片仍必须明确显示中文状态，不能只依赖颜色表达。

### 2.3 统一详情抽屉

点击任意自选股票卡片后，打开以自选股票为主体的统一详情抽屉：

```text
股票名称（价格，涨幅）                         雪球图标
板块 | 入选时间 | 交易体系 | 状态

K线 | 详情 | 信号记录 | 交易记录

[当前 Tab 内容]

编辑 | 试算 | 关闭
```

### 2.4 核心原则

1. 自选股票是页面唯一主实体。
2. 信号和交易是自选股票的历史记录与当前状态，不再作为独立首页列表。
3. 保留现有观察、信号、交易业务流程与接口语义。
4. 不影响 MarketPage、AdminPage、规则扫描、确认买入、确认卖出。
5. 新代码必须按职责拆分，禁止继续扩充臃肿的 `WatchPoolPage.tsx`。
6. 新实现完成后，坚决删除被替代的旧渲染函数、旧状态和旧请求。
7. 列表排序由后端统一计算并返回，前端只按明确排序字段展示，避免不同客户端产生不同优先级。

## 3. 当前实现分析

### 3.1 当前前端结构

主要文件：

```text
frontend/src/pages/WatchPoolPage.tsx
frontend/src/components/StockDetailPopup.tsx
frontend/src/components/StockLink.tsx
frontend/src/styles/app.css
```

当前 `WatchPoolPage.tsx` 同时承担：

- 三类列表切换。
- 自选、信号、交易数据加载。
- 自选编辑。
- 规则试算。
- 信号详情。
- 确认买入。
- 交易详情。
- 确认卖出。
- 交易执行流水。
- 统一详情抽屉。
- K 线加载。

该文件已经超过合理单页组件规模。继续直接增加四个详情 Tab 和聚合逻辑，会进一步降低可维护性。

### 3.2 当前数据请求

页面当前同时请求：

```text
GET /api/h5/watch-pool
GET /api/h5/watch-signals/recent
GET /api/h5/watch-trades/recent
GET /api/h5/watch-pool/summary
GET /api/h5/watch-signals/summary
GET /api/h5/watch-trades/summary
```

存在问题：

- `/watch-signals/recent` 默认只返回最近 10 条。
- `/watch-trades/recent` 默认只返回最近 10 条。
- 无法可靠为全部自选股匹配最新信号和当前交易。
- 今日信号数由前端在有限记录中计算，可能不准确。
- 没有按自选股票读取完整信号记录的接口。
- 没有按自选股票读取完整交易执行记录的接口。

### 3.3 当前详情抽屉

当前已有统一 Popup，但内部仍根据 `watch / signal / trade` 三种入口切换展示内容。

目标改版后，应取消这种“入口决定详情类型”的设计。无论用户从哪一条数据进入，详情都应以 `watch_id` 对应的自选股票为主体。

## 4. 推荐目标架构

## 4.1 后端职责

后端负责：

- 返回准确的自选汇总数据。
- 返回每只自选股最新信号。
- 返回每只自选股当前或最近交易状态。
- 返回今日信号数和今日交易执行数。
- 按 `watch_id` 返回信号历史。
- 按 `watch_id` 返回交易与执行历史。
- 对旧数据缺少 `watch_id` 的情况提供 `stock_code` 兼容兜底。

前端不应通过读取“最近 N 条信号/交易”自行拼装全量自选状态。

## 4.2 前端职责

前端负责：

- 渲染统一自选列表。
- 打开统一详情抽屉。
- 按需加载详情 Tab 数据。
- 调用已有编辑、试算、确认买入和确认卖出接口。
- 在 K 线图中标注支撑位和目标位。

前端不负责推断复杂生命周期，不负责扫描全部记录计算聚合状态。

## 5. 后端接口设计

## 5.1 自选统一概览接口

新增：

```http
GET /api/h5/watch-pool/overview
```

建议支持参数：

```text
keyword
trading_system
status
include_terminal
```

`include_terminal` 默认应为 `true`，确保已剔除、已失效等终止状态记录能够显示在列表最后。用户明确筛选为有效自选时，才只返回活动记录。

返回结构：

```json
{
  "summary": {
    "total": 78,
    "active_total": 70,
    "terminal_total": 8,
    "today_signal_count": 8,
    "today_trade_count": 2
  },
  "items": [
    {
      "watch_id": 1,
      "stock_code": "300308",
      "stock_name": "中际旭创",
      "latest_price": 1179.99,
      "change_pct": -7.81,
      "sector_name": "光通信",
      "entry_date": "2026-05-08",
      "entry_source": "manual",
      "trading_system_code": "uptrend",
      "trading_system_name": "上涨趋势",
      "status": "trading",
      "status_name": "交易中",
      "system_stage": "trading",
      "display_group": "trading",
      "sort_priority": 10,
      "sort_time": "2026-06-03T14:30:00",
      "card_tone": "trading",
      "latest_signal": {
        "signal_id": 81,
        "signal_type": "risk",
        "signal_status": "observe_risk_pending",
        "rule_code": "observe_break_ma20",
        "rule_name": "跌破 MA20",
        "trigger_time": "2026-06-03T14:30:00"
      },
      "active_trade": {
        "trade_id": 12,
        "trade_status": "holding",
        "target_price": 1250.0,
        "stop_loss_price": 1080.0
      }
    }
  ]
}
```

### 汇总定义

- `total`：当前概览列表返回的自选记录总数，包括活动记录和已剔除等终止状态记录。
- `active_total`：当前有效自选记录数，即 `WatchPool.active = true`。
- `terminal_total`：已剔除、已失效、黑名单和归档记录数。
- `today_signal_count`：当天生成的 `WatchSignal` 数量。
- `today_trade_count`：当天生成的 `WatchTradeExecution` 数量。

### 状态显示优先级

建议由后端统一产生 `status_name`，避免多处重复映射：

1. 存在 `open / holding` 交易：交易中。
2. 存在待处理卖点或止损信号：卖出待处理。
3. `buy_pending_confirm`：买入待确认。
4. `watching`：观察中。
5. `pending_review`：待复盘。
6. 监控关闭：监控暂停。
7. 其他状态按生命周期字典显示。

### 排序字段定义

后端应直接返回排序所需字段，最终结果按以下顺序排序：

```text
sort_priority ASC
sort_time DESC
watch_id DESC
```

建议优先级：

```text
10  交易中
20  今日有待处理卖点、止损或买入确认信号
30  今日有普通信号
40  观察中、等待买点、监控暂停
90  已剔除、已失效、黑名单、归档
```

字段说明：

- `display_group`：`trading / today_signal / watching / terminal`。
- `sort_priority`：后端计算的数值优先级，数字越小越靠前。
- `sort_time`：当前分组用于倒序排列的业务时间。
- `card_tone`：前端卡片配色标识，取值与展示分组保持一致。

前端不应重新计算排序优先级，只在接口结果缺少排序字段时使用原始返回顺序。

## 5.2 自选信号记录接口

新增：

```http
GET /api/h5/watch-pool/{watch_id}/signals
```

返回该自选记录关联的信号，按触发时间倒序。

旧数据兼容：

- 优先使用 `WatchSignal.watch_id = watch_id`。
- 对 `watch_id` 为空的历史数据，可使用相同 `stock_code` 查询作为兼容兜底。
- 兜底查询结果必须避免重复。

返回字段至少包括：

```text
signal_id
signal_type
signal_status
rule_code
rule_name
rule_timeframe
trigger_time
trigger_price
trigger_reason
risk_desc
notification_sent
notification_error
related_trade_id
```

## 5.3 自选交易记录接口

新增：

```http
GET /api/h5/watch-pool/{watch_id}/trade-records
```

返回内容建议以交易执行流水为主要记录，同时包含所属交易状态：

```json
[
  {
    "execution_id": 23,
    "trade_id": 12,
    "execution_type": "stop_loss",
    "execution_type_name": "止损",
    "execution_reason": "跌破 MA20",
    "execution_time": "2026-05-23T13:23:19",
    "execution_price": 1080.0,
    "execution_amount": 100,
    "trade_status": "completed"
  }
]
```

若某笔 `WatchTrade` 尚无执行记录，也应返回一个交易概要记录，避免交易 Tab 完全空白。

旧数据兼容规则与信号记录一致：优先 `watch_id`，必要时使用 `stock_code` 兜底。

## 5.4 现有接口处理原则

保留以下接口，不改变业务语义：

```text
GET  /api/h5/watch-pool/{watch_id}
PUT  /api/h5/watch-pool/{watch_id}
POST /api/h5/watch-pool/{watch_id}/rule-preview
POST /api/h5/watch-signals/{signal_id}/confirm-buy
POST /api/h5/watch-signals/{signal_id}/abandon
POST /api/h5/watch-trades/{trade_id}/confirm-sell
GET  /api/h5/market/stocks/{stock_code}/kline-daily
```

旧列表接口暂不删除，因为其他页面或测试可能仍在使用。

## 6. 前端代码结构设计

## 6.1 页面目录

新增目录：

```text
frontend/src/pages/watch-pool/
```

建议组件结构：

```text
WatchPoolPage.tsx
watch-pool/
  types.ts
  constants.ts
  formatters.ts
  WatchOverviewHeader.tsx
  WatchOverviewList.tsx
  WatchOverviewItem.tsx
  WatchDetailDrawer.tsx
  WatchKlineTab.tsx
  WatchInfoTab.tsx
  WatchSignalHistoryTab.tsx
  WatchTradeHistoryTab.tsx
  WatchEditForm.tsx
  WatchRulePreview.tsx
```

### 组件职责

`WatchPoolPage.tsx`

- 页面级数据请求。
- 筛选状态。
- 当前详情目标。
- 业务操作后的刷新协调。
- 不直接包含大段详情 JSX。

`WatchOverviewHeader.tsx`

- 展示自选总数、今日信号数、今日交易数。

`WatchOverviewList.tsx`

- 列表空态。
- 遍历自选概要数据。

`WatchOverviewItem.tsx`

- 单只股票三行摘要。
- 状态颜色。
- 根据 `card_tone` 渲染交易中、今日信号、观察中和已剔除四类背景。
- 点击打开详情。

`WatchDetailDrawer.tsx`

- 详情头部。
- 雪球入口。
- 四个 Tab。
- 底部固定按钮栏。
- 不直接实现各 Tab 的业务内容。

`WatchKlineTab.tsx`

- 加载日 K 数据。
- 从观察参数和当前交易提取支撑位、目标位。
- 调用 KlineChart。

`WatchInfoTab.tsx`

- 展示核心参数和入选原因。
- 空值不展示。

`WatchSignalHistoryTab.tsx`

- 加载并展示信号记录。
- 待确认买点可以调用现有确认买入和放弃操作。

`WatchTradeHistoryTab.tsx`

- 加载交易执行记录。
- 显示交易类型、原因和时间。
- 对持仓交易保留确认卖出入口。

`WatchEditForm.tsx`

- 从原页面迁移现有动态参数编辑表单。
- 保持原保存接口和校验规则。

`WatchRulePreview.tsx`

- 从原页面迁移试算展示。

## 6.2 类型定义

禁止继续大量使用 `any`。

在 `types.ts` 中至少定义：

```text
WatchOverviewResponse
WatchOverviewItem
WatchLatestSignal
WatchActiveTrade
WatchDetail
WatchSignalRecord
WatchTradeRecord
KlineLevelMarker
TradingSystemDefinition
TradingSystemParamDefinition
```

仅对确实动态的 `system_params_json`、`snapshot_json` 使用：

```ts
Record<string, unknown>
```

## 6.3 数据加载策略

页面首次加载：

```text
GET /h5/watch-pool/overview
GET /h5/trading-systems
```

打开详情时：

```text
GET /h5/watch-pool/{watch_id}
```

切换 Tab 时按需加载：

```text
K线      -> /h5/market/stocks/{stock_code}/kline-daily?limit=100
信号记录 -> /h5/watch-pool/{watch_id}/signals
交易记录 -> /h5/watch-pool/{watch_id}/trade-records
```

同一详情内已经加载的数据应缓存，避免每次切换 Tab 重复请求。

## 7. 页面展示规则

## 7.1 列表头

左侧突出自选总数，右侧显示今日数据：

```text
78                         今日信号 8 | 今日交易 2
```

不再显示“观察”“观察中数量”“今日新增”等旧头部信息。

## 7.2 自选列表项

第一行：

- 股票名称。
- 最新价。
- 涨跌幅。

第二行：

- 板块。
- 入选时间。
- 交易体系名称。
- 右侧当前状态。

第三行：

- 最新信号时间。
- 最新规则中文名。

空值处理：

- 无最新信号时，第三行显示“暂无信号记录”。
- 板块、交易体系缺失时不显示多余分隔符。
- 不显示原始规则编码，中文名缺失时才使用编码兜底。

### 卡片状态背景

卡片应通过明确 CSS 类实现，禁止在列表组件中散落大量内联颜色：

```text
watch-overview-item
watch-overview-item--trading
watch-overview-item--today-signal
watch-overview-item--watching
watch-overview-item--terminal
```

建议视觉规则：

- `trading`：浅红或浅暖色底，左侧可使用红色状态边。
- `today-signal`：浅蓝色底，左侧可使用蓝色状态边。
- `watching`：白色或浅绿色底，保持常规阅读权重。
- `terminal`：浅灰色底，名称、状态和辅助文字降低对比度。

不得使用高饱和整卡背景，不得仅凭背景颜色区分状态。

## 7.3 详情头部

第一行：

```text
股票名称（最新价，涨跌幅）                 雪球图标
```

第二行：

```text
板块 | 入选时间 | 交易体系 | 状态
```

不再重复显示：

- 股票代码独立行。
- 当前阶段标签。
- 交易体系标签。
- 当前状态信息块。

## 7.4 K线 Tab

显示：

- 日 K。
- MA5、MA10、MA20。
- 成交量。
- MACD。
- 支撑位横线。
- 目标位横线。

价格线来源：

支撑位优先级：

1. `system_params_json.platform_support_price`
2. 当前交易 `stop_loss_price`
3. `key_observe_price`

目标位优先级：

1. 当前交易 `target_price`
2. `system_params_json.platform_upper_price`

KlineChart 应通过可选参数支持标记线，不能把业务字段读取逻辑写入通用图表组件。

## 7.5 详情 Tab

展示：

- 核心观察参数。
- 入选原因。
- 失效条件。
- 风险标签。
- 用户备注。
- 当前交易概要（仅存在交易时）。

空值字段不展示。

## 7.6 信号记录 Tab

单条显示：

```text
信号类型 | 触发规则 | 触发时间
```

可补充：

- 触发价。
- 信号状态。
- 触发原因。

待处理操作：

- 买入待确认：确认买入、放弃机会。
- 风险与失效：仅提示人工处理。
- 卖点和止损：显示待人工处理状态。

## 7.7 交易记录 Tab

单条显示：

```text
交易类型 | 交易原因 | 交易时间
```

可补充：

- 成交价。
- 数量。
- 盈亏。

对当前持仓交易，保留确认卖出入口。

## 7.8 底部按钮

固定主按钮：

```text
编辑 | 试算 | 关闭
```

规则：

- 编辑：打开现有动态参数编辑表单。
- 试算：调用现有规则试算接口。
- 关闭：关闭详情抽屉。

标记失效、关闭监控、剔除、黑名单等低频操作建议放入详情 Tab 的“更多操作”区域，避免丢失现有能力。

## 8. 必须清理的旧代码

新页面验收通过后，应删除以下已被替代代码，禁止新旧逻辑并存。

### 8.1 页面状态

删除：

```text
tab
buySignals
riskSignals
pendingTradeSignals
watchingItems
signalSummary
tradeSummary
```

如新实现不再使用，也删除：

```text
DetailKind
DetailTarget.kind
activeDetailKind
```

### 8.2 旧列表渲染函数

删除被替代函数：

```text
renderSignalCard
renderTradeCard
renderSignalCardV2
renderTradeCardV2
renderSignalCardV3
renderTradeCardV3
renderWatchCard
```

### 8.3 旧详情分支

删除：

- `renderDetailBody(item, kind)` 中按 `watch / signal / trade` 切换的大型分支。
- 只为三类详情入口服务的标签和阶段展示函数。
- 不再使用的旧样式和辅助函数。

### 8.4 旧请求

首页不再请求：

```text
/h5/watch-signals/recent
/h5/watch-trades/recent
/h5/watch-signals/summary
/h5/watch-trades/summary
```

注意：仅移除自选页调用，不删除后端接口。

## 9. 不允许的实现方式

1. 不允许继续把所有新 JSX 写入 `WatchPoolPage.tsx`。
2. 不允许为每只自选股分别请求最新信号和交易，避免 N+1 请求。
3. 不允许使用最近 10 条信号或交易拼接全量列表状态。
4. 不允许复制现有编辑、试算、确认买入、确认卖出业务函数形成两套逻辑。
5. 不允许保留不可达的旧列表函数。
6. 不允许修改规则扫描和交易执行器。
7. 不允许新增数据库字段，除非实施中发现现有数据无法表达明确业务需求并单独确认。
8. 不允许在通用 KlineChart 内写死平台突破字段。

## 10. 测试计划

## 10.1 后端测试

新增测试至少覆盖：

1. 自选概览返回全部有效自选股。
2. 默认概览同时返回终止状态记录，并把已剔除记录排在最后。
3. 交易中的股票排在最前面。
4. 今日有信号的股票排在交易中之后、观察中之前。
5. 同一分组按对应业务时间倒序。
6. 每只自选股返回最新信号。
7. 每只自选股返回当前交易状态。
8. 今日信号数准确。
9. 今日交易执行数准确。
10. 信号记录按时间倒序。
11. 交易记录按时间倒序。
12. 旧数据 `watch_id` 缺失时可按 `stock_code` 兼容。
13. 不同股票之间的数据不会串联。
14. 无信号、无交易时返回空列表而不是报错。

建议测试文件：

```text
tests/test_watch_pool_overview_api.py
tests/test_watch_pool_history_api.py
```

## 10.2 前端测试与构建

至少执行：

```bash
cd frontend
npm.cmd run build
```

若项目已有可复用测试基础，再补充组件测试；否则以构建和浏览器验收为主。

## 10.3 浏览器验收

视口：

```text
360px
390px
430px
桌面宽度
```

验收项：

- 页面不再显示观察、信号、交易顶部 Tab。
- 列表总数、今日信号数、今日交易数正确。
- 列表顺序为交易中、今日有信号、观察中、已剔除。
- 同组内的排序符合业务时间倒序规则。
- 四类状态卡片有清晰但克制的背景差异。
- 已剔除卡片降低视觉权重但仍可点击查看历史。
- 列表卡片不贴边、不横向溢出。
- 状态右对齐且不会挤压左侧信息。
- 点击列表项打开统一详情。
- 四个详情 Tab 均可切换。
- K 线图不溢出，并显示支撑位和目标位。
- 信号记录和交易记录按时间倒序。
- 编辑、试算、关闭可用。
- 确认买入和确认卖出原流程仍可用。
- MarketPage、AdminPage 不受影响。

## 11. 分阶段实施顺序

### 阶段 1：后端自选聚合接口

- 新增概览接口。
- 实现统一状态分组和后端排序优先级。
- 默认纳入已剔除等终止状态记录，并排在列表最后。
- 新增信号历史接口。
- 新增交易历史接口。
- 提取必要的序列化和聚合服务。
- 补充后端测试。

### 阶段 2：前端类型与基础组件

- 新增 `watch-pool` 子目录。
- 定义类型、格式化函数和状态映射。
- 新增统一列表头与列表项组件。
- 新增四类状态卡片背景样式。

### 阶段 3：替换自选主页

- 接入概览接口。
- 移除三类顶部 Tab。
- 移除三类独立列表。
- 确认列表点击行为。

### 阶段 4：统一详情抽屉

- 新增四 Tab 详情结构。
- 按需加载 Tab 数据。
- 迁移编辑和试算功能。
- 保留原业务操作。

### 阶段 5：K线标记线

- 扩展 KlineChart 可选标记线接口。
- 在自选详情计算支撑位和目标位。
- 完成小屏图表验收。

### 阶段 6：旧代码清理与最终回归

- 删除旧状态、旧渲染函数、旧请求和无用样式。
- 检查未使用导入和重复辅助函数。
- 运行后端测试。
- 运行前端构建。
- 浏览器完成多尺寸回归。

## 12. 预计修改文件

后端：

```text
app/api/routes/h5.py
app/services/prd_v1.py 或新增 app/services/watch_overview.py
tests/test_watch_pool_overview_api.py
tests/test_watch_pool_history_api.py
```

前端：

```text
frontend/src/pages/WatchPoolPage.tsx
frontend/src/pages/watch-pool/types.ts
frontend/src/pages/watch-pool/constants.ts
frontend/src/pages/watch-pool/formatters.ts
frontend/src/pages/watch-pool/WatchOverviewHeader.tsx
frontend/src/pages/watch-pool/WatchOverviewList.tsx
frontend/src/pages/watch-pool/WatchOverviewItem.tsx
frontend/src/pages/watch-pool/WatchDetailDrawer.tsx
frontend/src/pages/watch-pool/WatchKlineTab.tsx
frontend/src/pages/watch-pool/WatchInfoTab.tsx
frontend/src/pages/watch-pool/WatchSignalHistoryTab.tsx
frontend/src/pages/watch-pool/WatchTradeHistoryTab.tsx
frontend/src/pages/watch-pool/WatchEditForm.tsx
frontend/src/pages/watch-pool/WatchRulePreview.tsx
frontend/src/components/StockDetailPopup.tsx
frontend/src/styles/app.css
```

## 13. 已知风险与决策点

### 13.1 今日交易数定义

推荐定义为“今日交易执行流水数量”，即今日发生的买入、卖出、止损执行次数。

如希望表示“今日新建交易数量”，应改为统计 `WatchTrade.created_at`。

### 13.2 历史数据关联

旧信号和交易可能没有 `watch_id`。按 `stock_code` 兜底可能把股票多次加入自选期间的历史记录合并显示。

第一阶段可接受该兼容方式，但界面应按时间展示，不错误归因到其他股票。

### 13.3 支撑位和目标位

不同交易体系的参数名称不同。第一阶段按明确优先级提取，未找到时不显示标记线，不应猜测价格。

### 13.4 当前状态

`WatchPool.status`、`WatchTrade.trade_status` 和待处理信号可能同时存在。状态显示必须由后端按统一优先级生成，避免前端各处产生不同结论。

## 14. 完成定义

只有同时满足以下条件，改版才算完成：

1. 自选页首页只有统一自选列表。
2. 列表严格按交易中、今日有信号、观察中、已剔除排序。
3. 不同状态卡片具有清晰且克制的背景颜色区分。
4. 概览和历史数据来自准确的后端聚合接口。
5. 详情抽屉包含 K线、详情、信号记录、交易记录四个 Tab。
6. K线能显示可用的支撑位和目标位。
7. 原有关键业务操作仍可用。
8. 被替代的旧三列表代码已删除。
9. `WatchPoolPage.tsx` 只保留页面编排职责，不再包含大段业务详情 JSX。
10. 后端测试通过。
11. 前端构建通过。
12. 360px、390px、430px 和桌面视口验收通过。

## 15. 分步执行提示词

已按第 11 节的六个阶段生成可直接交给 AI 执行的提示词：

```text
docs/WATCH_POOL_UNIFIED_OVERVIEW_EXECUTION_PROMPTS.md
```

每个提示词将明确：

- 本阶段目标。
- 允许修改的文件和职责边界。
- 必须保留的现有行为。
- 必须删除的旧代码。
- 测试命令。
- 验收输出格式。
- 下一阶段依赖。

提示词应按顺序执行。每阶段完成测试和验收后，再进入下一阶段，避免前后端契约、组件结构和旧代码清理同时失控。
