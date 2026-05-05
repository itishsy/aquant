# Final PRD v1 Compliance Audit

## Conclusion

结论：有条件通过。当前代码已把最新版 PRD v1 的 H5 主流程、PRD 表结构、手动自选、人工确认交易、无前台 K 线图、无自动入池和无自动交易边界落到主流程；仍有 legacy/v1.1 代码保留但已从正式路由或前台入口停用。

## Compliance Items

| 检查项 | 结果 | 证据 |
|---|---|---|
| 单用户开发就绪版 | pass | `app/api/deps.py` 使用单用户/单管理员边界 |
| 无多租户/复杂 RBAC | pass | 未新增 tenant/org/team/RBAC 主流程字段 |
| 无自动下单、报单、撤单 | pass | 未发现交易执行外部接口；交易 API 仅写内部记录 |
| 无券商接口 | pass | `real_provider.py` 明确避免券商/账号/浏览器自动化 |
| 所有买卖人工确认 | pass | `/api/h5/watch-signals/{id}/confirm-buy` 与 `/api/h5/watch-trades/{id}/confirm-sell` 均需用户调用 |
| 市场模块只展示原始数据 | pass | `/api/h5/market/**` 返回 platform/source/rank/raw_score/reason |
| 热门个股不做综合主观排序 | pass | 测试确认不返回 `total_score` |
| 自选股手动入选 | pass | 自动入池 no-op；市场页按钮调用手动 POST |
| H5 不展示系统内 K 线图 | pass | `StockDetailPage.tsx` 不再调用 K 线图组件 |
| 个股行情/K 线跳雪球 | pass | `StockLink.tsx` 与 `/api/common/stocks/{code}/xueqiu-url` |
| 交易记录采用 `watch_trade + watch_trade_execution` | pass | 新 H5 确认买入/卖出已写 PRD 表 |
| 周/月/单笔复盘 | partial | API 和表存在，交易完成生成单笔复盘；定时生成仍需增强 |
| H5 底部导航四项 | pass | `BottomTabs.tsx` 仅市场/自选/复盘/我的 |
| 后台不进入 H5 底部导航 | pass | 后台仅在“我的”页作为入口 |
| 后台写操作记录日志 | partial | `ConfigOperationLog` 和基础记录能力存在，部分后台写接口仍需补齐 |
| 敏感配置脱敏 | pass | 后台敏感摘要不返回密钥明文 |

## Text Scan

业务代码与 H5 源码未发现执行性违规交易入口。历史文档、审计文档、README 中出现的敏感词均作为“禁止项/否定说明/合规边界”出现；本报告不建议删除最新版 PRD 和历史审计文档中的禁止词说明，否则反而会降低合规可审计性。

## Legacy Risk

- `app/services/v1_1.py`、`app/api/routes/v1_1.py` 保留为 deprecated，但 `/api/v1/**` 不再注册。
- `app/services/market.py`、`app/services/sector.py` 仍有旧评分逻辑，保留给旧 API/测试兼容；H5 主流程不使用。
- `frontend/src/pages/DailyPlanPage.tsx` 等旧页面文件仍在仓库，但路由已重定向，不进入主导航。

## Recommendation

建议进入人工验收，但把“策略保存链路完全迁移到 `watch_signal`、后台管理 Web 页面、复盘定时任务”列为下一轮收尾任务。
