import type { KeyboardEvent } from "react";

import { WATCH_CARD_TONE_CLASS } from "./constants";
import {
  changePctTone,
  formatChangePct,
  formatPrice,
  latestSignalSummary,
  overviewMeta,
  statusLabel,
} from "./formatters";
import type { WatchOverviewItem as WatchOverviewItemType } from "./types";

type WatchOverviewItemProps = {
  item: WatchOverviewItemType;
  onOpenDetail: (item: WatchOverviewItemType) => void;
};

export function WatchOverviewItem({ item, onOpenDetail }: WatchOverviewItemProps) {
  function openDetail() {
    onOpenDetail(item);
  }

  function handleKeyDown(event: KeyboardEvent<HTMLElement>) {
    if (event.key !== "Enter" && event.key !== " ") return;
    event.preventDefault();
    openDetail();
  }

  return (
    <article
      className={`watch-overview-item ${WATCH_CARD_TONE_CLASS[item.card_tone]}`}
      role="button"
      tabIndex={0}
      onClick={openDetail}
      onKeyDown={handleKeyDown}
      aria-label={`查看${item.stock_name || item.stock_code}自选详情`}
    >
      <div className="watch-overview-item__headline">
        <strong>
          {item.stock_name || item.stock_code}（{formatPrice(item.latest_price)}，
          <span className={`watch-overview-item__change watch-overview-item__change--${changePctTone(item.change_pct)}`}>
            {formatChangePct(item.change_pct)}
          </span>
          ）
        </strong>
        <span className="watch-overview-item__status">
          {statusLabel(item.status, item.status_name)}
        </span>
      </div>
      <div className="watch-overview-item__meta">
        <span>{overviewMeta(item) || "暂无补充信息"}</span>
      </div>
      <div className="watch-overview-item__signal">{latestSignalSummary(item.latest_signal)}</div>
    </article>
  );
}
