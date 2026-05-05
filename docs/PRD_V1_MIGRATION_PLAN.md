# Aquant PRD v1.0 迁移计划

基准文档：`Aquant PRD v1.0.md`（单用户开发就绪版）  
目标：从旧 MVP/v1.1 混合实现迁移到新版 PRD v1.0，保留可复用基础，停用冲突能力，补齐 P0 闭环。  
原则：小步迁移、保留旧数据、先并行新增 PRD 表/API，再切换前端。

## 1. 迁移总原则

- 不直接删除旧表，先新增 PRD 标准表，完成数据迁移和 API 切换后再归档旧表。
- 不继续扩展 `/api/v1/**`，新增 `/api/h5/**`、`/api/admin/**`、`/api/common/**`。
- 自选池只允许用户手动入选，市场页只提供“添加自选”入口。
- 市场模块只展示客观原始数据，不展示 Market Score、Sector Score、Watch Score。
- K 线数据只服务后台计算和策略扫描，H5 个股详情统一提供雪球链接。
- 交易记录迁移到 `watch_trade` + `watch_trade_execution`。
- 复盘迁移到 `review_form` + 周/月/单笔复盘明细。
- v1.1 每日计划、严格模式、能力评分等先停用或实验归档，不进入当前主线。

## 2. 可以保留的模块

- 后端项目骨架：FastAPI、SQLAlchemy、Alembic、pytest。
- 数据库双库结构：系统数据与 K 线数据分离。
- Provider 抽象与 mock/real provider 代码。
- 数据标准化与质量校验服务。
- K 线采集、指标计算、策略扫描内核。
- 信号策略基础类、MACD15、风险策略。
- 任务执行与日志包装思想。
- H5 移动端基础组件、样式体系、雪球链接组件。
- Dockerfile、requirements、基础 README。

## 3. 需要改造的模块

- 市场数据：从 `market_daily/sector_daily/hot_stock_rank/limit_up_daily` 改造到 `mkt_daily/mkt_hot_board/mkt_hot_stock/mkt_limit_up`。
- 热榜：保留平台原始排名、原始分数、来源链接，不做综合评分。
- 自选池：从自动/评分/分层逻辑改造成手动入选、标签、买点类型、监控开关、生命周期状态。
- 信号：从 `signal_record` 改造成 `watch_signal`，补齐 `watch_signal_performance`。
- 交易：从 `trade_record` 改造成 `watch_trade` 主表 + `watch_trade_execution` 流水。
- 复盘：从多个旧复盘表改造成 `review_form`、`review_weekly`、`review_monthly`、`review_trade`。
- 前端导航：收敛为市场、自选、复盘、我的；后台作为“我的”中的入口。
- 个股详情：移除前台 K 线图，改为雪球跳转、来源摘要、信号、交易、复盘。
- 后台任务：从硬编码任务改造成 `config_task` 配置 + `config_task_log` 日志。

## 4. 需要停用的模块

- 自动入池任务和服务：`auto_add_candidates`、`auto_update_watch_pool_task`。
- Watch Score：`watch_pool_score`、`WatchScoreService`、相关 API 和前台展示。
- Market Score / Sector Score 前台展示与排序。
- v1.1 每日计划：`daily_trade_plan`、`daily_trade_plan_item`、`/daily-plan`。
- 严格模式、交易检查清单、纪律规则、用户能力评分等 v1.1 功能。
- H5 K 线图组件在个股详情页的使用。
- `/api/v1/**` 对外正式接口定位。
- 与旧 MVP/v1.1 冲突的验收文档作为当前开发依据。

## 5. 需要新增的模块

数据库表：

- `mkt_daily`
- `mkt_hot_board`
- `mkt_hot_stock`
- `mkt_limit_up`
- `mkt_stock_kline_daily`
- `mkt_stock_kline_15m`
- `watch_signal`
- `watch_signal_performance`
- `watch_pool_status_log`
- `watch_trade`
- `watch_trade_execution`
- `review_form`
- `review_weekly`
- `review_monthly`
- `review_trade`
- `my_user_profile`
- `my_user_preference`
- `my_notification_setting`
- `config_data_source`
- `config_task`
- `config_task_log`
- `config_field_mapping`
- `config_dictionary`
- `config_strategy`
- `config_notification_template`
- `config_notification_record`
- `config_review_template`
- `config_operation_log`

API：

- `/api/common/auth/login`
- `/api/common/auth/logout`
- `/api/common/auth/current-user`
- `/api/common/system/status`
- `/api/common/dictionaries`
- `/api/common/stocks/search`
- `/api/common/stocks/{stock_code}/brief`
- `/api/common/stocks/{stock_code}/xueqiu-url`
- `/api/h5/market/**`
- `/api/h5/watch-pool/**`
- `/api/h5/watch-signals/**`
- `/api/h5/watch-trades/**`
- `/api/h5/reviews/**`
- `/api/h5/me/**`
- `/api/h5/notifications/**`
- `/api/admin/dashboard/**`
- `/api/admin/data-sources/**`
- `/api/admin/tasks/**`
- `/api/admin/field-mappings/**`
- `/api/admin/dictionaries/**`
- `/api/admin/strategies/**`
- `/api/admin/review-templates/**`
- `/api/admin/notification-templates/**`
- `/api/admin/logs/**`
- `/api/admin/account/**`

H5 页面：

- 市场页：大盘、人气榜、涨停榜，全部基于原始数据。
- 自选页：观察区、信号区、交易区。
- 复盘页：周复盘、月复盘、单笔交易复盘入口。
- 我的页：资料、待办、偏好、系统状态、后台入口。
- 后台管理 Web：工作台、数据源、任务、字段映射、策略、字典、复盘模板、消息模板、日志、账号安全。

## 6. 推荐开发顺序

### Phase 1：冻结旧 v1.1 主线

- 标记 `/api/v1/**` 为实验接口，不再扩展。
- 从前台导航隐藏 `/daily-plan`、`/monthly-review` 等非新版 v1.0 主线入口。
- 停用自动入池任务入口。
- 更新测试标签，先把冲突测试标记为待迁移。

### Phase 2：新增 PRD 标准数据库迁移

- 新增 `mkt_*`、`watch_*`、`review_*`、`my_*`、`config_*` 表。
- 保持字段 nullable 或默认值，避免破坏旧库。
- 为 PRD 指定唯一约束和索引建索引。
- 编写迁移验证测试。

### Phase 3：市场数据迁移

- 将现有 `MarketService`、`HotStockService`、`LimitUpService` 改为写入 `mkt_*` 表。
- 热榜只保存平台原始排名/分数，不计算综合分。
- 保留历史旧表读取兼容，新增 `/api/h5/market/**`。
- 市场页切换到 `/api/h5/market/**`。

### Phase 4：自选池手动入选闭环

- 改造 `watch_pool` 字段和服务。
- 市场页“添加自选”弹框接入 `/api/h5/watch-pool`。
- 删除前台自动入池入口。
- 写入 `watch_pool_status_log`。

### Phase 5：信号迁移

- `SignalEngine` 输出改写 `watch_signal`。
- 补齐 `watch_signal_performance` 统计任务。
- H5 信号区改接 `/api/h5/watch-signals/**`。
- 保证所有信号有 raw snapshot、触发原因、风险点、止损位、失效条件。

### Phase 6：交易主表 + 执行流水

- 新增 `watch_trade`、`watch_trade_execution` 服务。
- 确认买入写主表和买入流水。
- 确认卖出/减仓/清仓写执行流水并同步主表汇总。
- 迁移旧 `trade_record` 数据。
- H5 交易区改接 `/api/h5/watch-trades/**`。

### Phase 7：复盘表单体系

- 实现 `review_form` 统一表单生命周期。
- 周/月/单笔复盘分别落到 `review_weekly`、`review_monthly`、`review_trade`。
- 复盘页改成 PRD 表单结构。
- 增加每周五、每月 1 日、每日提醒任务。

### Phase 8：我的模块

- 新增 `my_user_profile`、`my_user_preference`、`my_notification_setting`。
- 将 `/settings` 改造成“我的”。
- 接入待办、消息设置、系统状态、后台入口。

### Phase 9：后台管理系统

- 新增后台 Web 路由和页面。
- 实现数据源、采集任务、字段映射、字典、策略、复盘模板、消息模板、日志中心。
- 后台写操作写 `config_operation_log`。

### Phase 10：回归与清理

- 重写测试基准，移除旧评分/自动入池主线测试。
- 完成数据迁移脚本和验收清单。
- 更新 README/API/验收/合规文档。
- 归档旧 `V1_1_*` 文档。

## 7. 数据迁移建议

- `market_daily` -> `mkt_daily`：迁移客观字段，忽略或归档 `market_score/market_status`。
- `sector_daily` -> `mkt_hot_board`：迁移板块名称、平台、排名、涨幅、龙头、原始 payload；忽略 `sector_score`。
- `hot_stock_rank` -> `mkt_hot_stock`：迁移平台、平台排名、原始分数、来源字段；忽略综合分。
- `limit_up_daily` -> `mkt_limit_up`：迁移涨停时间、封单、换手、题材、原因、类型；补 platform/source 字段。
- `stock_kline_daily` -> `mkt_stock_kline_daily`：字段名映射为 `open_price/high_price/low_price/close_price`。
- `stock_kline_15m` -> `mkt_stock_kline_15m`：`trade_time` 映射为 `kline_time`。
- `signal_record` -> `watch_signal`：保留 raw snapshot、信号等级、触发原因、风险说明。
- `trade_record` -> `watch_trade` + `watch_trade_execution`：买入生成一条买入流水，已卖出记录生成一条卖出流水。
- `trade_review/weekly_review/monthly_review/trade_review_detail` -> `review_form` + 具体复盘表。

## 8. 测试迁移建议

- 删除或重写自动入池测试。
- 删除或重写 Market Score / Sector Score / Watch Score 断言。
- 新增市场原始数据入库和展示测试。
- 新增手动添加自选弹框 API 测试。
- 新增 `watch_trade_execution` 多次买卖流水测试。
- 新增 H5 不展示 K 线、雪球链接存在的测试。
- 新增 `/api/h5/**`、`/api/common/**`、`/api/admin/**` 路由测试。
- 新增后台任务日志、操作日志测试。

## 9. 风险与缓解

- 风险：表名体系差异大，直接重命名会破坏旧数据。  
  缓解：新增 PRD 表，并行迁移，旧表只读兼容一段时间。

- 风险：旧前端依赖旧 API。  
  缓解：先新增 `/api/h5/**` 适配层，再逐页切换。

- 风险：停用评分后部分页面信息密度下降。  
  缓解：改展示平台原始排名、原始分数、来源平台、涨停原因、更新时间。

- 风险：停用自动入池后自选池增长依赖用户操作。  
  缓解：市场页提供清晰“添加自选”弹框，自动带入来源信息，但最终由用户确认。

- 风险：真实数据源授权和字段稳定性。  
  缓解：优先落地 `config_data_source`、`config_field_mapping`、数据质量日志，再扩展采集范围。

- 风险：敏感配置当前写在默认配置和 docker-compose。  
  缓解：迁移到 `.env`，仓库只保留 `.env.example`。

## 10. 当前优先级建议

最高优先级：

- 停用自动入池。
- 停用前台评分展示。
- 移除 H5 K 线图展示。
- 新增 PRD 标准表迁移。
- 新增 `/api/h5/market/**` 和 `/api/h5/watch-pool/**`。

第二优先级：

- 交易主表 + 执行流水。
- 信号表与信号表现统计。
- 复盘统一表单。
- 我的模块。

第三优先级：

- 后台管理系统完整页面。
- 字段映射、复盘模板、消息模板。
- 旧数据批量迁移与旧 API 下线。
