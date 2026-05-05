# Aquant PRD v1.0 API 最终文档

状态：阶段性交付，核心 PRD v1 API 骨架已新增，旧 API 保留兼容。

目标 API 分组：

- `/api/common/**`：登录、系统状态、字典、股票简要信息。
- `/api/h5/**`：H5 前台市场、自选、信号、交易、复盘、我的、通知。
- `/api/admin/**`：后台管理、任务、日志、数据维护。

统一返回结构：

```json
{
  "success": true,
  "code": "SUCCESS",
  "message": "操作成功",
  "data": {},
  "trace_id": "req_xxx"
}
```

本文件会随迁移阶段持续更新，以当前代码为准。

## 公共接口

- `POST /api/common/auth/login`
- `POST /api/common/auth/logout`
- `GET /api/common/auth/current-user`
- `GET /api/common/system/status`
- `GET /api/common/dictionaries`
- `GET /api/common/stocks/search`
- `GET /api/common/stocks/{stock_code}/brief`
- `GET /api/common/stocks/{stock_code}/xueqiu-url`

## H5 市场接口

- `GET /api/h5/market/trading-dates`
- `GET /api/h5/market/overview`
- `GET /api/h5/market/hot-boards`
- `GET /api/h5/market/hot-stocks`
- `GET /api/h5/market/limit-ups`
- `GET /api/h5/market/stocks/{stock_code}/source-summary`
- `GET /api/h5/market/stocks/{stock_code}/latest-source`

## H5 自选接口

- `GET /api/h5/watch-pool`
- `GET /api/h5/watch-pool/summary`
- `GET /api/h5/watch-pool/{watch_id}`
- `POST /api/h5/watch-pool`
- `PUT /api/h5/watch-pool/{watch_id}`
- `DELETE /api/h5/watch-pool/{watch_id}`
- `POST /api/h5/watch-pool/{watch_id}/restore`
- `POST /api/h5/watch-pool/{watch_id}/blacklist`
- `POST /api/h5/watch-pool/{watch_id}/unblacklist`
- `POST /api/h5/watch-pool/{watch_id}/monitor/enable`
- `POST /api/h5/watch-pool/{watch_id}/monitor/disable`
- `GET /api/h5/watch-pool/{watch_id}/status-logs`

## H5 我的与通知接口

- `GET /api/h5/me/profile`
- `PUT /api/h5/me/profile`
- `GET /api/h5/me/preferences`
- `PUT /api/h5/me/preferences`
- `GET /api/h5/me/notification-settings`
- `PUT /api/h5/me/notification-settings`
- `GET /api/h5/me/todos`
- `GET /api/h5/me/system-summary`
- `GET /api/h5/me/backend-entry`
- `GET /api/h5/notifications`
- `GET /api/h5/notifications/unread-count`
- `POST /api/h5/notifications/{notification_id}/read`
- `POST /api/h5/notifications/read-all`
- `DELETE /api/h5/notifications/{notification_id}`

## 后台基础接口

- `GET /api/admin/dashboard/overview`
- `GET /api/admin/dashboard/task-summary`
- `GET /api/admin/dashboard/data-source-summary`
- `GET /api/admin/dashboard/error-top`
- `GET /api/admin/data-sources`
- `POST /api/admin/data-sources`
- `GET /api/admin/data-sources/{source_id}`
- `PUT /api/admin/data-sources/{source_id}`
- `POST /api/admin/data-sources/{source_id}/enable`
- `POST /api/admin/data-sources/{source_id}/disable`
- `POST /api/admin/data-sources/{source_id}/test`
- `GET /api/admin/tasks`
- `POST /api/admin/tasks`
- `GET /api/admin/tasks/{task_id}`
- `PUT /api/admin/tasks/{task_id}`
- `POST /api/admin/tasks/{task_id}/run`
- `GET /api/admin/task-logs`
- `GET /api/admin/dictionaries`
- `POST /api/admin/dictionaries`
- `PUT /api/admin/dictionaries/{dict_id}`
- `GET /api/admin/field-mappings`
- `POST /api/admin/field-mappings`
- `PUT /api/admin/field-mappings/{mapping_id}`
- `GET /api/admin/strategies`
- `GET /api/admin/strategies/defaults`
- `GET /api/admin/notification-templates`
- `GET /api/admin/review-templates`
- `GET /api/admin/logs/operations`
- `GET /api/admin/account/profile`
- `GET /api/admin/security/sensitive-summary`

## 保留兼容接口

旧 `/api/market`、`/api/watch-pool`、`/api/signals`、`/api/trades`、`/api/reviews`、`/api/v1` 暂时保留，后续不作为最新 PRD v1 正式主线扩展。
