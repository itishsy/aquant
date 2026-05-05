# Final PRD v1 Test Report

## Commands

| 命令 | 结果 | 说明 |
|---|---|---|
| `python -m compileall app` | passed | 后端 Python 编译通过 |
| `python -m pytest tests/test_prd_v1_api.py -q` | passed, 6 tests | PRD v1 新增接口闭环测试通过 |
| `python -m pytest -q` | passed, 30 tests | 后端全量测试通过 |
| `npm run test` | passed, 1 test | 前端单测通过 |
| `npm run build` | passed | H5 生产构建通过 |
| `python -m alembic upgrade head` with temp SQLite URLs | passed | 干净库迁移验证通过 |
| `rg` 合规关键词扫描 | reviewed | 业务代码未发现执行性违规入口；历史/审计文档中存在禁止词作为负面说明 |

## Failure And Fix Record

- `tests/test_prd_v1_api.py` 初次新增交易测试失败：测试手工创建 `WatchPool` 时缺少旧表必填字段 `reason`。
- 修复：测试数据补充 `reason="用户手动加入"`。
- 复测：`tests/test_prd_v1_api.py` 6 项全部通过。
- Alembic 第一次在沙箱中运行因本地 Python 执行权限被拒绝失败；按权限流程提升后重跑通过。

## Coverage Notes

- 已覆盖：市场原始人气榜字段、手动自选、重复自选、自选状态日志、H5 信号确认买入、买入流水、重复确认买入、确认卖出、全部卖出生成单笔复盘、复盘列表、前端构建。
- 部分覆盖：K 线后台计算、B15 策略、旧交易复盘仍由历史测试覆盖；最终主流程还需继续把策略保存链路统一到 `watch_signal`。
- 未覆盖：后台管理 Web 页面可视化测试、Docker 容器启动实测。本轮未启动 Docker，原因是当前任务重点为代码和 PRD 一致性整改；替代验证为后端/前端/迁移全量通过。
