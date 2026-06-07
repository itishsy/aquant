import type { WatchOverviewSummary } from "./types";

type WatchOverviewHeaderProps = {
  summary: WatchOverviewSummary;
};

export function WatchOverviewHeader({ summary }: WatchOverviewHeaderProps) {
  return (
    <div className="card-head watch-overview-head">
      <div className="card-headline watch-overview-head__total">
        <span className="icon-badge">{summary.total}</span>
        <h2>自选</h2>
      </div>
      <div className="soft-tag watch-overview-head__today">
        <span>今日信号 {summary.today_signal_count}</span>
        <span aria-hidden="true">|</span>
        <span>今日交易 {summary.today_trade_count}</span>
      </div>
    </div>
  );
}
