# Final PRD v1 Requirement Traceability Matrix

基准文档：`Aquant PRD v1.0.md`。本矩阵只以最新版 PRD 为准，旧 MVP/v1.1 文档仅作为迁移背景。

| PRD 章节 | 需求点 | 优先级 | 应实现内容 | 当前实现状态 | 对应代码位置 | 对应 API | 对应数据表 | 对应页面 | 对应测试 | 结论 |
|---|---|---:|---|---|---|---|---|---|---|---|
| 产品定位 | 单用户开发就绪版 | P0 | 不做多租户、团队权限、复杂 RBAC | done | `app/api/deps.py` | `/api/common/auth/*` | `my_user_profile` | 我的 | `tests/test_prd_v1_api.py` | 符合，保留单管理员边界 |
| 合规边界 | 无自动下单/券商接口/跟单 | P0 | 只记录人工确认交易 | done | `app/api/routes/h5.py` | `/api/h5/watch-signals/{id}/confirm-buy`, `/api/h5/watch-trades/{id}/confirm-sell` | `watch_trade`, `watch_trade_execution` | 自选-交易 | 全量 pytest + 文案扫描 | 未发现执行交易接口 |
| 市场数据 | 展示客观原始数据 | P0 | 原始采集、标准化、入库、展示，不做主观评分 | done | `app/services/prd_v1.py`, `app/api/routes/h5.py` | `/api/h5/market/**` | `mkt_daily`, `mkt_hot_board`, `mkt_hot_stock`, `mkt_limit_up` | 市场 | `test_h5_market_uses_raw_hot_stock_fields` | H5 主流程已改为原始数据 |
| 市场数据 | 热门个股只展示平台原始排名/分数 | P0 | 保留 platform/source、rank、raw_score、reason | done | `PrdMarketDataService.get_hot_stocks` | `/api/h5/market/hot-stocks` | `mkt_hot_stock` | 市场-人气榜 | `test_h5_market_uses_raw_hot_stock_fields` | 不返回 `total_score` |
| 市场数据 | 涨停榜保留平台原因 | P0 | 展示涨停时间、连板、原因 | done | `PrdMarketDataService.get_limit_ups` | `/api/h5/market/limit-ups` | `mkt_limit_up` | 市场-涨停榜 | `tests/test_prd_v1_api.py` | 已有 API 和页面入口 |
| 自选池 | 全部自选由用户手动入选 | P0 | 市场页仅提供“+ 自选”入口，POST 后才写库 | done | `PrdWatchPoolService.add_watch`, `MarketPage.tsx` | `/api/h5/watch-pool` | `watch_pool`, `watch_pool_status_log` | 市场、自选 | `test_h5_watch_pool_manual_add_only` | 自动入池主流程已停用 |
| 自选池 | 重复添加幂等 | P0 | 有效状态同股不重复创建 | done | `PrdWatchPoolService.add_watch` | `/api/h5/watch-pool` | `watch_pool` | 自选 | `tests/test_watch_pool.py` | 重复时更新已有记录 |
| 自选池 | 状态变化写日志 | P0 | 添加、剔除、黑名单、恢复写状态日志 | done | `PrdWatchPoolService._log` | `/api/h5/watch-pool/{id}/status-logs` | `watch_pool_status_log` | 自选 | `tests/test_watch_pool.py` | 已覆盖手动添加日志 |
| K 线 | H5 不展示系统内 K 线图 | P0 | K 线只供后台计算，前台跳雪球 | done | `StockDetailPage.tsx`, `StockLink.tsx` | `/api/common/stocks/{code}/xueqiu-url` | `mkt_stock_kline_daily`, `mkt_stock_kline_15m` | 个股详情 | 前端构建 + 扫描 | 旧详情页已移除图表调用 |
| 信号 | 信号关联手动自选 | P0 | `watch_signal.watch_id`，确认买入人工触发 | partial | `app/api/routes/h5.py` | `/api/h5/watch-signals/**` | `watch_signal`, `watch_signal_performance` | 自选-信号 | `test_h5_signal_confirm_buy_creates_watch_trade_and_execution` | API 闭环已补，策略引擎仍需进一步切到 `watch_signal` |
| 信号 | 卖出/风险优先 | P0 | H5 分开展示买入观察与风险/卖出提醒 | partial | `WatchPoolPage.tsx` | `/api/h5/watch-signals` | `watch_signal` | 自选-信号 | 构建通过 | 展示层符合，策略生成链路仍部分沿用旧实现 |
| 交易 | 使用 `watch_trade + watch_trade_execution` | P0 | 确认买入/卖出写主表和流水 | done | `app/api/routes/h5.py` | `/api/h5/watch-signals/{id}/confirm-buy`, `/api/h5/watch-trades/{id}/confirm-sell` | `watch_trade`, `watch_trade_execution` | 自选-交易 | `test_h5_signal_confirm_buy_creates_watch_trade_and_execution`, `test_h5_confirm_sell_generates_trade_review` | H5 新主流程已对齐 |
| 交易 | 同一信号只能确认买入一次 | P0 | 重复确认返回已有交易 | done | `confirm_buy` | `/api/h5/watch-signals/{id}/confirm-buy` | `watch_trade` | 自选-信号 | `test_h5_signal_confirm_buy_creates_watch_trade_and_execution` | 幂等通过 |
| 复盘 | 周/月/单笔交易复盘 | P0 | 周复盘、月复盘列表；交易完成生成单笔复盘 | partial | `app/api/routes/h5.py`, `ReviewsPage.tsx` | `/api/h5/reviews/**` | `review_form`, `review_weekly`, `review_monthly`, `review_trade` | 复盘 | `test_h5_confirm_sell_generates_trade_review`, `test_h5_reviews_are_exposed_by_period` | 复盘 API 可用，定时生成任务仍需增强 |
| 我的 | 我的页轻量配置 | P0 | 用户信息、待办、偏好、系统摘要、后台入口 | done | `SettingsPage.tsx`, `app/api/routes/h5.py` | `/api/h5/me/**` | `my_user_profile`, `my_user_preference`, `my_notification_setting` | 我的 | 构建通过 | 不返回敏感配置 |
| 后台管理 | 后台不进 H5 底部导航 | P0 | H5 仅从“我的”进入后台入口 | done | `BottomTabs.tsx`, `SettingsPage.tsx` | `/api/h5/me/backend-entry`, `/api/admin/**` | `config_*` | 我的/后台 | 构建通过 | 底部导航为四项 |
| 后台管理 | 后台写操作记录操作日志 | P0 | 配置写接口记录 `config_operation_log` | partial | `app/api/routes/admin_prd.py`, `record_operation` | `/api/admin/**` | `config_operation_log` | 后台 API | 全量 pytest | 基础接口有记录能力，部分写接口仍需补全二次确认 |
| 数据库 | PRD 表和唯一约束 | P0 | `mkt_*`, `watch_*`, `review_*`, `my_*`, `config_*` | done | `app/models/entities.py`, `alembic/versions/20260505_0003_prd_v1_alignment.py` | n/a | 全部 PRD 表 | n/a | Alembic upgrade head | 迁移验证通过 |
| 旧版残留 | v1.1 每日计划/严格模式/Watch Score | P0 | 不进入当前 PRD 主流程 | deprecated | `app/api/router.py`, `app/api/routes/v1_1.py`, `app/services/v1_1.py` | `/api/v1/**` 已取消注册 | v1.1 历史表 | 无主导航入口 | 全量 pytest | 保留代码但正式路由停用 |

## 统计

- 总需求数：18
- done：13
- partial：4
- deprecated：1
- conflict：0（已从主流程解除）
- missing：0 个 P0 主入口缺失，但信号策略、复盘定时、后台页面仍为 partial。
