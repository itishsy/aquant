# Auto Trend Paper Trading Design

## Goal

Build a simplified automatic paper-trading system for one fixed trend strategy:

1. Select stocks that appeared in the comprehensive hot-stock Top 10 during the last 30 trading days.
2. Keep only stocks that have not broken daily MA20 and have no daily or 120m MACD top divergence.
3. Generate a buy signal on 15m MACD bottom divergence.
4. Confirm the buy when a 1m MACD bottom divergence appears without breaking the recorded 15m bottom.
5. Open a paper position at the next 1m bar open.
6. Stop out on a new low below the recorded 15m bottom.
7. Sell on 5m MACD top divergence.

This system does not connect to brokerage APIs and does not place real orders. It creates paper positions only.

## Design Direction

Use a new lightweight automatic strategy module instead of extending the existing configurable trading-system stack.

The new module should be independent from these old configuration tables:

- `TradingSystemDefinition`
- `TradingSystemRuleBinding`
- `ConfigTask`

It may copy or extract useful existing code, especially:

- `MktHotStock` as the hot-stock source.
- `MktStockKline` and `KlineRepository` as the unified K-line source.
- `IndicatorService` for MA and MACD calculation.
- Existing MACD bottom/top divergence logic as the basis for dedicated auto-strategy detectors.
- Existing signal/trade UI patterns as references for the new frontend.

## Strategy Code

Use a fixed strategy code:

```text
hot_ma20_macd_trend
```

The code-level module name should be `auto_trading`.

## System Boundary

The new system owns its own candidate, signal, run, and paper-position state. It does not require the user to manually add stocks to the old watch pool.

Core state flow:

```text
hot_candidate
  -> watching
  -> buy_signal
  -> paper_holding
  -> closed_by_stop_loss | closed_by_sell_signal
```

Default constraints:

- One stock can have at most one open paper position for this strategy.
- A stock with an open paper position is not selected again as a new active candidate.
- Stop loss has priority over sell signals.
- The system never places real brokerage orders.
- The first version exposes manual API run buttons. Fixed scheduling can be added after the strategy behavior is verified.

## Database Tables

Create four new system database tables.

### `auto_strategy_run`

Records each automatic scan for debugging and summary statistics.

Fields:

- `run_id`
- `strategy_code`
- `run_type`: `select_candidates`, `scan_buy_signal`, `confirm_buy`, `scan_exit`, or `full`
- `started_at`
- `finished_at`
- `status`: `running`, `success`, or `failed`
- `message`
- `stats_json`

### `auto_candidate`

Represents an automatically selected candidate stock.

Fields:

- `candidate_id`
- `strategy_code`
- `stock_code`
- `stock_name`
- `status`: `watching`, `buy_signal`, `holding`, `closed`, or `filtered_out`
- `selected_trade_date`
- `hot_rank_date`
- `hot_rank`
- `hot_snapshot_json`
- `filter_snapshot_json`
- `latest_signal_id`
- `position_id`
- `created_at`
- `updated_at`
- `closed_at`

Indexes should support querying by strategy, stock code, status, selected date, and hot-rank date.

The service layer should prevent duplicate active candidates for the same `strategy_code + stock_code`. Do this with an explicit query so the behavior works across SQLite and MySQL.

### `auto_signal`

Stores all strategy-generated signals.

Fields:

- `signal_id`
- `candidate_id`
- `position_id`
- `strategy_code`
- `stock_code`
- `stock_name`
- `signal_type`: `buy_signal`, `buy_confirm`, `stop_loss`, or `sell_signal`
- `timeframe`: `15m`, `1m`, or `5m`
- `trigger_time`
- `trigger_price`
- `signal_status`: `generated`, `executed`, `skipped`, or `superseded`
- `reason`
- `snapshot_json`
- `created_at`

The service layer should avoid duplicate signals for the same `candidate_id + signal_type + timeframe + trigger_time`.

### `auto_paper_position`

Stores paper positions and realized PnL.

Fields:

- `position_id`
- `candidate_id`
- `strategy_code`
- `stock_code`
- `stock_name`
- `status`: `open` or `closed`
- `entry_signal_id`
- `entry_time`
- `entry_price`
- `entry_amount_cash`
- `quantity`
- `stop_loss_price`
- `exit_signal_id`
- `exit_time`
- `exit_price`
- `exit_reason`: `stop_loss` or `m5_top_divergence`
- `pnl_amount`
- `pnl_ratio`
- `created_at`
- `updated_at`

Default paper cash per trade is `10000`.

Quantity calculation:

```text
floor(10000 / entry_price / 100) * 100
```

If the result is less than 100 shares, skip the buy confirmation and mark the signal as `skipped`.

## K-Line Support

Extend the unified K-line repository and context services to support:

- `1m`
- `120m`

The strategy requires these timeframes:

- `daily` for MA20 and daily top-divergence filtering.
- `120m` for higher-timeframe top-divergence filtering.
- `15m` for the primary buy signal and stop-loss base.
- `1m` for buy confirmation and paper execution prices.
- `5m` for sell signals.

## Strategy Flow

Implement the fixed strategy in a service such as `AutoTrendStrategyService`.

Suggested methods:

- `run_full()`
- `select_candidates()`
- `scan_buy_signals()`
- `confirm_buys()`
- `scan_exits()`

Each method should create an `auto_strategy_run` row and write summary counts to `stats_json`.

### 1. Candidate Selection

Input:

- `MktHotStock` rows from the last 30 trading days.

Selection condition:

- The stock appeared in the comprehensive hot-stock Top 10 on any trading day in the last 30 trading days.

Ranking interpretation:

- Prefer an explicit comprehensive rank if one exists.
- If no explicit comprehensive rank exists, derive daily Top 10 from available hot-stock fields using the same ordering the current market service uses, with `score desc` and platform rank fields as fallbacks.

Filter conditions:

- Latest daily close is not below MA20.
- No recent daily MACD top divergence.
- No recent 120m MACD top divergence.
- No open paper position already exists for the same strategy and stock.

Output:

- Create or update `auto_candidate` with `status = watching`.
- Store MA20 and divergence checks in `filter_snapshot_json`.
- Store hot-rank source data in `hot_snapshot_json`.

### 2. Buy Signal

Input:

- `auto_candidate.status = watching`.

Trigger:

- 15m MACD bottom divergence.

Output:

- Create `auto_signal.signal_type = buy_signal`.
- Set candidate status to `buy_signal`.
- Store the detected 15m bottom time and low price in `snapshot_json`.
- Treat the 15m bottom low price as the stop-loss base for later stages.

### 3. Buy Confirmation And Paper Buy

Input:

- `auto_candidate.status = buy_signal`.

Trigger:

- 1m MACD bottom divergence.
- The 1m divergence price action does not break the recorded 15m bottom low.

Execution:

- Do not execute on the same 1m bar that produced the signal.
- Use the next 1m bar open as the paper entry price.
- Use `10000` paper cash per trade.
- Round quantity down to whole A-share lots of 100 shares.

Output:

- Create `auto_signal.signal_type = buy_confirm`.
- If quantity is at least 100, create `auto_paper_position.status = open`.
- Set candidate status to `holding`.
- Store `stop_loss_price` from the 15m bottom low.
- If no next 1m bar exists yet, keep the confirmation signal generated but do not open the position until a later scan can find the execution bar.

### 4. Stop Loss

Input:

- `auto_paper_position.status = open`.

Trigger:

- Latest 15m bar makes a new low below `stop_loss_price`.

Execution:

- Stop loss has priority over sell signals.
- Use the next 1m bar open after the stop-loss signal as the paper exit price.
- If no next 1m bar exists yet, keep the stop-loss signal generated and wait for a later scan.

Output:

- Create `auto_signal.signal_type = stop_loss`.
- Close the position when an execution bar is available.
- Set candidate status to `closed`.
- Set `exit_reason = stop_loss`.

### 5. Sell Signal

Input:

- Open positions that did not trigger stop loss in the same scan.

Trigger:

- 5m MACD top divergence.

Execution:

- Use the next 1m bar open after the sell signal as the paper exit price.
- If no next 1m bar exists yet, keep the sell signal generated and wait for a later scan.

Output:

- Create `auto_signal.signal_type = sell_signal`.
- Close the position when an execution bar is available.
- Set candidate status to `closed`.
- Set `exit_reason = m5_top_divergence`.

## API Design

Add a new route module mounted under:

```text
/api/auto-trading
```

Endpoints:

- `POST /api/auto-trading/run/full`
- `POST /api/auto-trading/run/select-candidates`
- `POST /api/auto-trading/run/scan-buy-signals`
- `POST /api/auto-trading/run/confirm-buys`
- `POST /api/auto-trading/run/scan-exits`
- `GET /api/auto-trading/overview`
- `GET /api/auto-trading/candidates?status=...`
- `GET /api/auto-trading/signals?stock_code=...`
- `GET /api/auto-trading/positions?status=...`
- `GET /api/auto-trading/runs`

The API response should expose only the simplified automatic trading concepts. It should not expose old rule-binding or admin task configuration fields.

## Frontend Design

Add a new route:

```text
/auto-trading
```

The page is a work-focused operations view, not a marketing page.

Main areas:

- Summary metrics: watching candidates, buy-signal candidates, open paper positions, closed positions, cumulative PnL.
- Run controls: full scan, select candidates, scan buy signals, confirm buys, scan exits.
- Candidate table: stock, status, hot-rank date, hot rank, MA20 filter, daily top-divergence filter, 120m top-divergence filter, latest signal.
- Position table: entry time, entry price, quantity, stop-loss price, exit price, PnL, exit reason.
- Signal timeline: per-stock signal history for buy signal, buy confirmation, stop loss, and sell signal.

The first version should not include editable strategy parameters. Parameters stay fixed in code or environment variables.

## Scheduler

First version:

- Implement manual API triggers only.

Later fixed scheduler:

- Candidate selection: pre-market or after market close.
- Buy-signal scan: every 15 minutes during trading.
- Buy confirmation: every 1 to 3 minutes during trading.
- Exit scan: every 5 minutes during trading.

Environment variables for later scheduling:

```env
ENABLE_AUTO_TRADING_SCHEDULER=false
AUTO_TRADING_PAPER_CASH_PER_TRADE=10000
```

## Testing Strategy

Backend tests should cover:

- A stock that appeared in the last 30 trading days' hot Top 10 becomes a candidate.
- A stock below daily MA20 is filtered out.
- A stock with daily MACD top divergence is filtered out.
- A stock with 120m MACD top divergence is filtered out.
- A 15m bottom divergence creates a `buy_signal` and records the 15m bottom low.
- A 1m bottom divergence above the 15m bottom creates a paper position at the next 1m open.
- Paper quantity uses `floor(10000 / entry_price / 100) * 100`.
- A too-expensive stock that cannot buy 100 shares is skipped.
- A 15m new low below the recorded bottom closes the paper position before sell-signal evaluation.
- A 5m top divergence closes the paper position when stop loss is not triggered.
- Duplicate active candidates, duplicate signals, and duplicate open positions are prevented.
- Each API run endpoint invokes the correct service step and returns the run summary.
- Overview returns candidate, signal, position, and PnL counts.

Frontend tests can be lighter in the first pass:

- The `/auto-trading` route renders summary cards and tables.
- Run buttons call the expected API endpoints.
- Candidate, position, and signal rows render returned data.

## Implementation Split

1. Create models and migration for the four new auto-trading tables.
2. Extend unified K-line support for `1m` and `120m`.
3. Create dedicated auto-trading MACD divergence detectors by copying and simplifying existing executor logic.
4. Implement candidate selection.
5. Implement 15m buy-signal scanning.
6. Implement 1m buy confirmation and paper position opening.
7. Implement stop-loss and sell-signal closing.
8. Add `/api/auto-trading` routes.
9. Add the `/auto-trading` frontend page.
10. Add fixed scheduler support only after manual API behavior is verified.

## Out Of Scope

- Real brokerage integration.
- Real order placement.
- Editable strategy builder UI.
- Reusing the old admin task configuration screen.
- Multi-strategy portfolio optimization.
- Position sizing beyond fixed paper cash per trade.
