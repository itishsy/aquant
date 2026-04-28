# API

## Health

- `GET /api/health`

## Market API

- `GET /api/market/daily?trade_date=YYYY-MM-DD`
- `GET /api/market/summary`

## Sectors API

- `GET /api/sectors/top?trade_date=YYYY-MM-DD&limit=3`

## Hot Stocks API

- `GET /api/hot-stocks/top?trade_date=YYYY-MM-DD&limit=10`

## Limit Up API

- `GET /api/limit-up/list?trade_date=YYYY-MM-DD`
- `GET /api/limit-up/summary?trade_date=YYYY-MM-DD`

## Watch Pool API

- `GET /api/watch-pool`
- `POST /api/watch-pool`
- `PATCH /api/watch-pool/{stock_code}/labels`
- `POST /api/watch-pool/{stock_code}/blacklist`
- `DELETE /api/watch-pool/{stock_code}`

## Kline API

- `GET /api/stocks/{stock_code}/kline/daily?limit=100`
- `GET /api/stocks/{stock_code}/kline/15m?limit=200`

## Signals API

- `GET /api/signals`
- `POST /api/signals/scan`
- `POST /api/signals/{signal_id}/confirm-trade`
- `POST /api/signals/{signal_id}/ignore`
- `POST /api/signals/{signal_id}/false-positive`

## Trades API

- `GET /api/trades`
- `GET /api/trades/{trade_id}`
- `POST /api/trades/{trade_id}/sell`
- `POST /api/trades/{trade_id}/review`

## Reviews API

- `GET /api/reviews/weekly?week_start=YYYY-MM-DD&week_end=YYYY-MM-DD`

## Admin Task API

- `GET /api/admin/tasks/logs`
- `POST /api/admin/tasks/{task_name}/run`

## Notes

- 管理任务接口预留 `X-Admin-Token` 鉴权入口。
- 所有买入/卖出/风险信号均为观察/提醒性质，仅作为交易辅助。
- 系统数据写入 `a_quant`，K 线数据写入 `a_candle`。
