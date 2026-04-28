# Compliance Check

## Product Boundary

- Aquant remains a market monitoring, auxiliary analysis, signal reminder, manual confirmation, trade record, and review system.
- The system does not implement automatic order placement, broker trading APIs, automatic cancellation, automatic execution, revenue promises, or deterministic investment advice.
- All trade records must be confirmed manually by the user.

## Signal Copy Rules

- Buy-side signal copy must use `买入观察信号`.
- Risk signal copy must use `风险提醒`.
- Sell-side signal copy must use `卖出观察提醒`.
- Signal descriptions must include `仅作为交易辅助`.

## Data Provider Boundary

- External data access is encapsulated behind Provider interfaces.
- `DATA_PROVIDER_MODE=mock` remains the default local development mode.
- `DATA_PROVIDER_MODE=real` enables public JSON market data collection based on the reference `fupan.py` implementation.
- The real provider does not include broker access, account login, Selenium/browser automation, private credentials, or anti-crawler bypass logic.
- Upstream failures are surfaced as task failures and written to `system_task_log`; failed or missing data must not silently create effective trading signals.

## Current Real Collection Scope

- Market snapshot: real index, breadth, turnover, limit-up and limit-down emotion data.
- Sector ranking: real industry plate data.
- Hot stocks: real public hot-rank JSON sources.
- Limit-up list: real public limit-up analysis data.
- K-line: real Eastmoney public K-line endpoint for daily and 15-minute bars.

## Checked Items

- [x] No automatic order entry.
- [x] No broker interface.
- [x] No automatic trading button in H5.
- [x] Admin task APIs keep `X-Admin-Token` entry point.
- [x] `signal_record.raw_snapshot` is required.
- [x] Real provider keeps data collection separate from signal generation.
