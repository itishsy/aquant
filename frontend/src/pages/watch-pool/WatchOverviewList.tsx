import { WatchOverviewItem } from "./WatchOverviewItem";
import type { WatchOverviewItem as WatchOverviewItemType } from "./types";

type WatchOverviewListProps = {
  items: WatchOverviewItemType[];
  onOpenDetail: (item: WatchOverviewItemType) => void;
  emptyText?: string;
};

export function WatchOverviewList({ items, onOpenDetail, emptyText = "暂无自选记录" }: WatchOverviewListProps) {
  if (!items.length) {
    return <div className="empty-panel">{emptyText}</div>;
  }

  return (
    <div className="stack-list watch-overview-list">
      {items.map((item) => (
        <WatchOverviewItem key={item.watch_id} item={item} onOpenDetail={onOpenDetail} />
      ))}
    </div>
  );
}
