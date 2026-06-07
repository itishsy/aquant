import { Button, SpinLoading } from "antd-mobile";

import { formatDateTime, formatPrice } from "./formatters";
import type { WatchTradeRecord } from "./types";
import { DetailField } from "./WatchInfoTab";

type Props = {
  records: WatchTradeRecord[] | null;
  loading: boolean;
  onConfirmSell: (tradeId: number) => void;
};

export function WatchTradeHistoryTab({ records, loading, onConfirmSell }: Props) {
  if (loading || records === null) return <div className="watch-detail-loading"><SpinLoading /></div>;
  if (!records.length) return <div className="empty-panel">暂无交易记录</div>;

  return (
    <div className="watch-detail-stack">
      {records.map((record) => {
        const isOpen = ["open", "holding"].includes(record.trade_status);
        const recordName = record.execution_type_name || record.execution_type || "交易概要";
        return (
          <article className="watch-history-item" key={`${record.record_type}-${record.execution_id || record.trade_id}`}>
            <div className="watch-history-item__head">
              <strong>{recordName}</strong>
              <span>{record.trade_status}</span>
            </div>
            <p>{record.execution_reason || "暂无交易原因"} | {formatDateTime(record.execution_time || record.record_time)}</p>
            <div className="watch-detail-grid">
              <DetailField label="成交价" value={record.execution_price != null ? formatPrice(record.execution_price) : null} />
              <DetailField label="数量" value={record.execution_amount} />
              <DetailField label="盈亏" value={record.pnl_amount} />
              <DetailField label="盈亏比例" value={record.pnl_ratio != null ? `${(record.pnl_ratio * 100).toFixed(2)}%` : null} />
            </div>
            {isOpen && (
              <div className="watch-detail-actions">
                <Button size="small" color="danger" fill="outline" onClick={() => onConfirmSell(record.trade_id)}>确认全部卖出</Button>
              </div>
            )}
          </article>
        );
      })}
    </div>
  );
}
