# API

## Health

- `GET /api/health`

## Market

- `GET /api/market/daily?trade_date=YYYY-MM-DD`
- `GET /api/market/summary`

## Sectors

- `GET /api/sectors/top?trade_date=YYYY-MM-DD&limit=3`

## Hot Stocks

- `GET /api/hot-stocks/top?trade_date=YYYY-MM-DD&limit=10`

## Limit Up

- `GET /api/limit-up/list?trade_date=YYYY-MM-DD`
- `GET /api/limit-up/summary?trade_date=YYYY-MM-DD`

## Watch Pool

- `GET /api/watch-pool`
- `POST /api/watch-pool`
- `PATCH /api/watch-pool/{stock_code}/labels`
- `POST /api/watch-pool/{stock_code}/blacklist`
- `DELETE /api/watch-pool/{stock_code}`

## Kline

- `GET /api/stocks/{stock_code}/kline/daily?limit=100`
- `GET /api/stocks/{stock_code}/kline/15m?limit=200`

## Signals

- `GET /api/signals`
- `POST /api/signals/scan`
- `POST /api/signals/{signal_id}/confirm-trade`
- `POST /api/signals/{signal_id}/ignore`
- `POST /api/signals/{signal_id}/false-positive`

## Trades

- `GET /api/trades`
- `GET /api/trades/{trade_id}`
- `POST /api/trades/{trade_id}/sell`
- `POST /api/trades/{trade_id}/review`

## Reviews

- `GET /api/reviews/weekly?week_start=YYYY-MM-DD&week_end=YYYY-MM-DD`
- `GET /api/reviews/daily-plans`
- `POST /api/reviews/daily-plans`
- `POST /api/reviews/weekly/note`

## Admin Tasks

- `GET /api/admin/tasks/logs`
- `POST /api/admin/tasks/{task_name}/run`

Supported task names:

- `collect_market_daily_task`
- `collect_sector_daily_task`
- `collect_hot_stock_rank_task`
- `collect_limit_up_daily_task`
- `auto_update_watch_pool_task`
- `scan_signals_task`
- `generate_daily_snapshot_task`
- `generate_weekly_review_task`

Admin task APIs require `X-Admin-Token`.

## Provider Mode

- Default: `DATA_PROVIDER_MODE=mock`
- Real collection: `DATA_PROVIDER_MODE=real`
- Real mode supports public JSON collection for market snapshot, sector ranking, hot stocks, limit-up list, daily K-line, and 15-minute K-line.
- Real mode does not perform broker operations, account login, browser automation, or anti-crawler bypass.
