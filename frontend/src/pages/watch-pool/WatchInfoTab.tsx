import { Button } from "antd-mobile";

import type { TradingSystemParamDefinition, WatchDetail } from "./types";

const RISK_LABELS: Record<string, string> = {
  high_position: "高位",
  weak_seal: "封板弱",
  abnormal_volume: "放量异常",
  sector_weak: "板块转弱",
  break_support: "跌破支撑",
};

const PARAM_LABELS: Record<string, string> = {
  platform_upper_price: "箱体上沿",
  platform_support_price: "平台支撑位",
  key_observe_price: "关键观察价",
  auto_remove_price: "自动剔除价",
  invalid_condition: "失效条件",
};

export function DetailSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="watch-detail-section">
      <h4>{title}</h4>
      {children}
    </section>
  );
}

export function DetailField({ label, value }: { label: string; value: unknown }) {
  if (value === undefined || value === null || value === "") return null;
  return (
    <div className="watch-detail-field">
      <span>{label}</span>
      <strong>{String(value)}</strong>
    </div>
  );
}

type WatchInfoTabProps = {
  detail: WatchDetail;
  paramDefinitions: TradingSystemParamDefinition[];
  terminal: boolean;
  onToggleMonitor: () => void;
  onMarkInvalid: () => void;
  onRemove: () => void;
  onBlacklist: () => void;
};

export function WatchInfoTab(props: WatchInfoTabProps) {
  const { detail, paramDefinitions, terminal } = props;
  const params = detail.system_params_json || {};
  const labels = new Map(paramDefinitions.map((item) => [item.param_key, item.param_name]));
  const visibleParams = Object.entries(params).filter(
    ([key, value]) => key !== "invalid_condition" && value !== undefined && value !== null && value !== "",
  );
  const riskText = (detail.risk_tags || []).map((item) => RISK_LABELS[item] || item).join(" / ");
  const observationFields = [
    detail.entry_reason || detail.reason,
    params.invalid_condition || detail.invalid_condition,
    riskText,
    detail.user_remark || detail.remark,
  ];

  return (
    <div className="watch-detail-stack">
      {visibleParams.length > 0 && (
        <DetailSection title="核心观察参数">
          <div className="watch-detail-grid">
            {visibleParams.map(([key, value]) => (
              <DetailField key={key} label={labels.get(key) || PARAM_LABELS[key] || key} value={value} />
            ))}
          </div>
        </DetailSection>
      )}

      {observationFields.some((value) => value !== undefined && value !== null && value !== "") && (
        <DetailSection title="观察依据">
          <div className="watch-detail-stack watch-detail-stack--compact">
            <DetailField label="入选原因" value={detail.entry_reason || detail.reason} />
            <DetailField label="失效条件" value={params.invalid_condition || detail.invalid_condition} />
            <DetailField label="风险标签" value={riskText} />
            <DetailField label="用户备注" value={detail.user_remark || detail.remark} />
          </div>
        </DetailSection>
      )}

      {detail.active_trade && (
        <DetailSection title="当前交易概要">
          <div className="watch-detail-grid">
            <DetailField label="交易状态" value={detail.active_trade.trade_status} />
            <DetailField label="当前阶段" value={detail.active_trade.current_stage} />
            <DetailField label="止损价" value={detail.active_trade.stop_loss_price} />
            <DetailField label="目标价" value={detail.active_trade.target_price} />
          </div>
        </DetailSection>
      )}

      {!terminal && (
        <DetailSection title="更多操作">
          <div className="watch-detail-actions watch-detail-actions--secondary">
            <Button size="small" fill="outline" onClick={props.onToggleMonitor}>
              {detail.monitor_enabled !== false && detail.signal_enabled !== false ? "关闭监控" : "开启监控"}
            </Button>
            <Button size="small" fill="outline" onClick={props.onMarkInvalid}>标记失效</Button>
            <Button size="small" fill="outline" color="danger" onClick={props.onRemove}>剔除</Button>
            <Button size="small" fill="outline" color="danger" onClick={props.onBlacklist}>加入黑名单</Button>
          </div>
        </DetailSection>
      )}
    </div>
  );
}
