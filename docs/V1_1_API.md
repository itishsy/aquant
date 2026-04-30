# Aquant v1.1 API 文档

本文件记录 v1.1 新增 `/api/v1/...` API。v1.0 API 保持兼容。

## Watch Lifecycle

- `GET /api/v1/watch-pool/{stock_code}/lifecycle`
- `POST /api/v1/watch-pool/{stock_code}/transition`
- `POST /api/v1/watch-pool/{stock_code}/archive`
- `POST /api/v1/watch-pool/{stock_code}/blacklist`
- `POST /api/v1/watch-pool/{stock_code}/restore`

## Watch Score

- `GET /api/v1/watch-pool/scores?trade_date=YYYY-MM-DD`
- `GET /api/v1/watch-pool/{stock_code}/score`
- `POST /api/v1/watch-pool/score-candidates`
- `GET /api/v1/watch-pool/layers`
- `GET /api/v1/watch-pool?layer=L1_core&status=watching`

## Discipline And Strict Mode

- `GET /api/v1/discipline/rules`
- `PATCH /api/v1/discipline/rules/{rule_id}`
- `GET /api/v1/discipline/evaluate`
- `POST /api/v1/discipline/strict-mode`
- `GET /api/v1/strict-mode`
- `POST /api/v1/strict-mode/enable`
- `POST /api/v1/strict-mode/disable`
- `POST /api/v1/strict-mode/evaluate`

## Daily Trade Plan

- `GET /api/v1/daily-plans/today`
- `GET /api/v1/daily-plans/{trade_date}`
- `POST /api/v1/daily-plans/generate`
- `GET /api/v1/daily-plans/{plan_id}/items`
- `POST /api/v1/daily-plans/{plan_id}/items`
- `PATCH /api/v1/daily-plans/items/{item_id}`
- `POST /api/v1/daily-plans/items/{item_id}/cancel`
- `POST /api/v1/daily-plans/items/{item_id}/trigger`
- `POST /api/v1/daily-plans/items/{item_id}/invalidate`
- `POST /api/v1/daily-plans/{plan_id}/complete`

## Trade Checklist And Unplanned Trades

- `POST /api/v1/trade-checklists/build`
- `GET /api/v1/trade-checklists/{checklist_id}`
- `POST /api/v1/trade-checklists/{checklist_id}/confirm`
- `GET /api/v1/trades/unplanned`
- `POST /api/v1/trades/{trade_id}/mark-unplanned`
- `GET /api/v1/trades/unplanned/stats`

## Sell Plan

- `GET /api/v1/sell-plans`
- `GET /api/v1/trades/{trade_id}/sell-plans`
- `POST /api/v1/trades/{trade_id}/sell-plans/generate`
- `POST /api/v1/sell-plans/{sell_plan_id}/trigger`
- `POST /api/v1/sell-plans/{sell_plan_id}/confirm`
- `POST /api/v1/sell-plans/{sell_plan_id}/cancel`

## Review

- `GET /api/v1/trades/{trade_id}/review-detail`
- `POST /api/v1/trades/{trade_id}/review-detail/generate`
- `PATCH /api/v1/trades/{trade_id}/review-detail`
- `POST /api/v1/trades/{trade_id}/review-detail/error-tags`
- `POST /api/v1/trades/{trade_id}/review-detail/complete`
- `GET /api/v1/reviews/weekly`
- `POST /api/v1/reviews/weekly/generate`
- `GET /api/v1/reviews/monthly?month=YYYY-MM`
- `POST /api/v1/reviews/monthly/generate`
- `GET /api/v1/trading-score/monthly?month=YYYY-MM`

## Error Tags And Notifications

- `GET /api/v1/error-tags`
- `POST /api/v1/error-tags`
- `PATCH /api/v1/error-tags/{tag_id}`
- `DELETE /api/v1/error-tags/{tag_id}`
- `GET /api/v1/error-tags/stats`
- `GET /api/v1/error-tags/repeated-alerts`
- `GET /api/v1/notifications`
- `POST /api/v1/notifications/{notification_id}/read`
- `POST /api/v1/notifications/daily-plan/{plan_id}`
- `POST /api/v1/notifications/review-reminder`

## Admin Tasks

- `POST /api/v1/admin/tasks/{task_name}/run`
- `GET /api/v1/admin/tasks/v1-1/logs`
