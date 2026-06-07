import { Button, SpinLoading } from "antd-mobile";

import { formatDateTime, formatPrice } from "./formatters";
import type { WatchSignalRecord } from "./types";
import { DetailField } from "./WatchInfoTab";

const SIGNAL_TYPE_LABELS: Record<string, string> = {
  buy: "买入信号",
  sell: "卖出信号",
  risk: "风险信号",
};

const SIGNAL_STATUS_LABELS: Record<string, string> = {
  buy_pending_confirm: "买点待确认",
  observe_risk_pending: "观察风险待确认",
  observe_invalid_pending: "观察失效待确认",
  observe_remove_pending: "观察剔除待确认",
  sell_signal_pending: "卖点待处理",
  stop_loss_pending: "止损待处理",
  confirmed_buy: "已确认买入",
  abandoned: "已放弃",
};

type Props = {
  records: WatchSignalRecord[] | null;
  loading: boolean;
  onConfirmBuy: (signal: WatchSignalRecord) => void;
  onAbandon: (signal: WatchSignalRecord) => void;
};

export function WatchSignalHistoryTab({ records, loading, onConfirmBuy, onAbandon }: Props) {
  if (loading || records === null) return <div className="watch-detail-loading"><SpinLoading /></div>;
  if (!records.length) return <div className="empty-panel">暂无信号记录</div>;

  return (
    <div className="watch-detail-stack">
      {records.map((signal) => {
        const isBuyPending = signal.signal_status === "buy_pending_confirm";
        const isRisk = signal.signal_type === "risk";
        const isSellPending = ["sell_signal_pending", "stop_loss_pending"].includes(signal.signal_status);
        return (
          <article className="watch-history-item" key={signal.signal_id}>
            <div className="watch-history-item__head">
              <strong>{SIGNAL_TYPE_LABELS[signal.signal_type] || signal.signal_type}</strong>
              <span>{SIGNAL_STATUS_LABELS[signal.signal_status] || signal.signal_status}</span>
            </div>
            <p>{signal.rule_display_name || signal.rule_name || signal.rule_code || "未知规则"} | {formatDateTime(signal.trigger_time || signal.trigger_date)}</p>
            <div className="watch-detail-grid">
              <DetailField label="触发价" value={signal.trigger_price != null ? formatPrice(signal.trigger_price) : null} />
              <DetailField label="规则周期" value={signal.rule_timeframe} />
            </div>
            <DetailField label="触发原因" value={signal.trigger_reason} />
            {isBuyPending && (
              <div className="watch-detail-actions">
                <Button size="small" color="primary" onClick={() => onConfirmBuy(signal)}>确认买入</Button>
                <Button size="small" fill="outline" onClick={() => onAbandon(signal)}>放弃机会</Button>
              </div>
            )}
            {isRisk && <div className="watch-detail-notice">风险与失效信号仅提示人工处理，不会自动交易。</div>}
            {isSellPending && <div className="watch-detail-notice watch-detail-notice--risk">卖点或止损信号等待人工处理。</div>}
          </article>
        );
      })}
    </div>
  );
}
