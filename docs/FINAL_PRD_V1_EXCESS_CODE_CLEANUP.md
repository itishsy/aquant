# Final PRD v1 Excess Code Cleanup

本报告记录与最新版 `Aquant PRD v1.0.md` 不一致或暂不属于主流程的旧能力处理结果。

| 文件路径 | 冲突类型 | 是否仍被引用 | 处理方式 | 处理原因 | 验证结果 |
|---|---|---|---|---|---|
| `app/api/routes/v1_1.py` | v1.1 每日计划、严格模式、Watch Score、检查清单等超出当前 PRD | 不再被正式路由注册 | deprecated | `/api/v1/**` 已从 `app/api/router.py` 移除，避免进入主流程；保留文件便于历史数据迁移参考 | `pytest -q` 通过 |
| `app/services/v1_1.py` | Watch Score、每日计划、严格模式等 v1.1 能力 | 仅旧测试直接引用 | deprecated | 当前 PRD 不要求，且可能与“手动自选、无主观评分”冲突；暂不删除，等待旧测试迁移完成 | `pytest -q` 通过 |
| `app/services/watch_pool.py::auto_add_candidates` | 自动入池 | 旧任务/测试引用 | disable/deprecated | 改为 no-op，不再写 `watch_pool` | `test_auto_add_candidates_is_disabled_by_prd_v1` 通过 |
| `app/services/tasks.py::auto_update_watch_pool_task` | 自动更新自选池任务 | 旧任务入口引用 | disable/deprecated | 改为 deprecated no-op，不再自动入池 | `pytest -q` 通过 |
| `frontend/src/pages/DailyPlanPage.tsx` | v1.1 今日计划页 | 不在底部导航；路由已重定向 | hide/deprecated | 当前 PRD H5 一级导航只有市场/自选/复盘/我的 | `npm run build` 通过 |
| `frontend/src/pages/SectorsPage.tsx` | 旧板块评分页 | 不在底部导航；路由已重定向 | hide/deprecated | 当前 PRD 市场页二级 Tab 是大盘/人气榜/涨停榜，板块只作为原始数据展示 | `npm run build` 通过 |
| `frontend/src/pages/SignalsPage.tsx` | 旧独立信号页 | 不在底部导航；路由已重定向至自选 | hide/deprecated | 信号应整合到自选页二级 Tab | `npm run build` 通过 |
| `frontend/src/pages/TradesPage.tsx` | 旧独立交易页 | 不在底部导航；路由已重定向至自选 | hide/deprecated | 交易应整合到自选页二级 Tab | `npm run build` 通过 |
| `frontend/src/pages/StockDetailPage.tsx` | 旧系统内 K 线图 | 已整改 | hide/remove usage | 不再调用前台 K 线图，仅提供雪球链接和来源摘要 | `npm run build` 通过 |
| `app/services/market.py`, `app/services/sector.py` | 旧 Market/Sector Score | 老 API/旧测试仍引用 | keep_with_reason | 历史兼容保留，但 H5 PRD 主流程使用 `/api/h5/market/**` 原始数据接口 | `pytest -q` 通过 |
| `app/models/entities.py` 中 v1.1 历史表 | PRD 未要求的 v1.1 表 | 迁移历史可能依赖 | keep_with_reason | 不删除旧迁移/旧表，避免破坏历史库；正式主流程使用 PRD v1 表 | Alembic 验证通过 |

## 扫描结论

- 自动入池：正式主流程已停用，市场页只通过用户点击写入 `/api/h5/watch-pool`。
- 主观评分：H5 主流程不再展示 Market Score、Sector Score、Watch Score；旧服务保留为 legacy。
- H5 K 线图：个股详情不再展示系统内 K 线图，统一提供雪球链接。
- 多用户复杂权限：未引入多租户/RBAC，保留单用户登录和单管理员边界。
- 自动交易/券商接口：未发现可执行下单、报单、撤单或券商接口路由。
