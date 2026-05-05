# Aquant MVP AI Implementation Plan

## Phase Summary

| Phase | Goal | Status |
|---|---|---|
| 0 | 仓库体检、需求提炼、计划初始化 | completed |
| 1 | FastAPI 后端基础骨架 | completed |
| 2 | SQLAlchemy 模型与 Alembic 迁移 | completed |
| 3 | Provider 抽象与 MockProvider | completed |
| 4 | 数据标准化与质量校验 | completed |
| 5 | 市场行情与 Market Score | completed |
| 6 | 热门板块 TOP3 | completed |
| 7 | 热门股 TOP10 | completed |
| 8 | 涨停股分析 | completed |
| 9 | 自选池 Watch Pool | completed |
| 10 | K 线与技术指标 | completed |
| 11 | 信号引擎框架 | completed |
| 12 | 15 分钟 MACD 底背离买入观察策略 | completed |
| 13 | 卖出/风险信号策略 | completed |
| 14 | 人工确认交易与交易记录 | completed |
| 15 | 周度复盘 | completed |
| 16 | 后台任务调度与任务日志 | completed |
| 17 | H5 前端骨架 | completed |
| 18 | H5 市场行情页 | completed |
| 19 | H5 自选池、个股详情、信号页 | completed |
| 20 | H5 交易记录与复盘页 | completed |
| 21 | API 文档、验收清单、集成测试 | completed |
| 22 | Docker 本地开发环境 | completed |
| 23 | 稳定性、安全性、合规检查 | completed |

## MVP Scope Extracted From PRD

- 核心闭环：行情监测 -> 板块/热门股筛选 -> 自选池 -> 信号提醒 -> 人工确认交易 -> 交易记录 -> 周复盘。
- 买入观察信号必须遵循五层决策：市场环境 -> 板块强度 -> 个股状态 -> 技术触发 -> 风险过滤。
- 热度数据仅可作为候选参考，不可单独触发买入观察信号。
- 数据源必须通过 Provider 抽象，MVP 仅允许 MockProvider。
- 信号记录必须保存 `raw_snapshot`，数据质量失败时不得生成有效信号。
- 合规边界：不实现自动下单/撤单/券商接口，不输出收益承诺或确定性荐股文案。

## Architecture Decision

- Backend: FastAPI + SQLAlchemy + Alembic + APScheduler
- Database: 默认 SQLite 便于本地运行，同时兼容 MySQL `DATABASE_URL`
- Cache/Queue: 预留 Redis 配置
- Frontend: React + Vite
- Tests: pytest + vitest

## Delivery Strategy

1. 先建立可运行最小后端与数据模型。
2. 使用稳定 Mock 数据打通采集、计算、信号与交易闭环。
3. 在后端 API 稳定后接入 H5 页面。
4. 最后补齐集成测试、Docker、文档与合规检查。

## Final Notes

- 后端默认使用 SQLite 方便本地直接跑通，同时通过 `DATABASE_URL` 兼容 MySQL。
- 前端页面已完成移动端骨架与关键业务流，但图表展示在 MVP 中先以数据卡片/指标文本为主，未引入复杂 ECharts 配置。
