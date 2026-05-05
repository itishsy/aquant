# Aquant PRD v1.0 Final API

Only these business API prefixes are active:

- `/api/common/**`
- `/api/h5/**`
- `/api/admin/**`

Unified response shape:

```json
{
  "success": true,
  "code": "SUCCESS",
  "message": "操作成功",
  "data": {},
  "trace_id": "req_xxx"
}
```

## Common

- `POST /api/common/auth/login`
- `POST /api/common/auth/logout`
- `GET /api/common/auth/current-user`
- `GET /api/common/system/status`
- `GET /api/common/dictionaries`
- `GET /api/common/stocks/search`
- `GET /api/common/stocks/{stock_code}/brief`
- `GET /api/common/stocks/{stock_code}/xueqiu-url`

## H5 Market

- `GET /api/h5/market/trading-dates`
- `GET /api/h5/market/overview`
- `GET /api/h5/market/hot-boards`
- `GET /api/h5/market/hot-stocks`
- `GET /api/h5/market/limit-ups`
- `GET /api/h5/market/stocks/{stock_code}/source-summary`
- `GET /api/h5/market/stocks/{stock_code}/latest-source`

Market APIs expose raw source/platform data. They do not calculate or expose subjective market, sector, watch, or comprehensive hot-stock scores.

## H5 Watch Pool

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

Watch-pool creation is manual only. Market hot lists may provide an add entry, but must not automatically write to `watch_pool`.

## H5 Signals

- `GET /api/h5/watch-signals`
- `GET /api/h5/watch-signals/recent`
- `GET /api/h5/watch-signals/summary`
- `GET /api/h5/watch-signals/{signal_id}`
- `POST /api/h5/watch-signals/{signal_id}/confirm-buy`
- `POST /api/h5/watch-signals/{signal_id}/ignore`
- `POST /api/h5/watch-signals/{signal_id}/mark-false-positive`
- `POST /api/h5/watch-signals/{signal_id}/invalidate`
- `GET /api/h5/watch-signals/{signal_id}/performance`

Signals are auxiliary reminders only. Confirm-buy is a user-confirmed internal record action and does not connect to any broker.

## H5 Trades

- `GET /api/h5/watch-trades`
- `GET /api/h5/watch-trades/recent`
- `GET /api/h5/watch-trades/summary`
- `GET /api/h5/watch-trades/{trade_id}`
- `GET /api/h5/watch-trades/{trade_id}/executions`
- `POST /api/h5/watch-trades/{trade_id}/confirm-sell`
- `POST /api/h5/watch-trades/{trade_id}/cancel`
- `POST /api/h5/watch-trades/{trade_id}/close`
- `PUT /api/h5/watch-trades/{trade_id}`

Trades use `watch_trade` and `watch_trade_execution`.

## H5 Reviews

- `GET /api/h5/reviews`
- `GET /api/h5/reviews/todos`
- `GET /api/h5/reviews/summary`
- `GET /api/h5/reviews/weekly`
- `GET /api/h5/reviews/monthly`
- `GET /api/h5/reviews/trade`
- `GET /api/h5/reviews/{review_id}`
- `PUT /api/h5/reviews/{review_id}`
- `POST /api/h5/reviews/{review_id}/complete`
- `POST /api/h5/reviews/{review_id}/archive`
- `GET /api/h5/reviews/weekly/{review_id}`
- `GET /api/h5/reviews/monthly/{review_id}`
- `GET /api/h5/reviews/trade/{trade_review_id}`
- `PUT /api/h5/reviews/trade/{trade_review_id}`
- `POST /api/h5/reviews/trade/{trade_review_id}/complete`

## H5 My And Notifications

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

## Admin

Admin APIs live under `/api/admin/**` and cover:

- Dashboard
- Data sources
- Collection tasks
- Field mappings
- Dictionaries
- Strategies
- Review templates
- Notification templates and records
- Logs
- Account/security basics
- Manual data maintenance

Admin write operations should record `config_operation_log`; sensitive config should be masked before returning to frontend.

## Removed Legacy Prefixes

These old prefixes are not part of the final PRD v1 API surface:

- `/api/market`
- `/api/sectors`
- `/api/hot-stocks`
- `/api/limit-up`
- `/api/watch-pool`
- `/api/stocks`
- `/api/signals`
- `/api/trades`
- `/api/reviews`
- `/api/v1/**`
