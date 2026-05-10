import { useState } from "react";
import { Button, CenterPopup } from "antd-mobile";

type StockLinkProps = {
  stockCode?: string | null;
  stockName?: string | null;
  showCode?: boolean;
  className?: string;
  info?: Record<string, any>;
};

function normalizeXueqiuCode(stockCode: string): string {
  const normalized = stockCode.trim().toUpperCase();
  if (/^(SH|SZ|BJ)\d{6}$/.test(normalized)) return normalized;
  const match = normalized.match(/^(\d{6})\.(SH|SZ|BJ)$/);
  if (match) return `${match[2]}${match[1]}`;
  return "";
}

export function toXueqiuUrl(stockCode?: string | null) {
  if (!stockCode) return "";
  const code = normalizeXueqiuCode(stockCode);
  return code ? `https://xueqiu.com/S/${code}` : "";
}

function InfoRow({ label, value }: { label: string; value: any }) {
  if (value === null || value === undefined || value === "") return null;
  return (
    <div style={{ display: "flex", justifyContent: "space-between", padding: "4px 0", fontSize: 13 }}>
      <span style={{ color: "#888" }}>{label}</span>
      <span style={{ color: "#334", fontWeight: 500, textAlign: "right", maxWidth: "60%" }}>{value}</span>
    </div>
  );
}

export function StockLink({ stockCode, stockName, showCode = true, className, info }: StockLinkProps) {
  const [visible, setVisible] = useState(false);
  const url = toXueqiuUrl(stockCode);
  const label = [stockName || stockCode, showCode && stockCode ? stockCode : ""].filter(Boolean).join(" ");

  if (!url) {
    return <span className={className || "stock-link"}>{label || "-"}</span>;
  }

  const ctx = info || {};

  return (
    <>
      <span className={className || "stock-link"} onClick={() => setVisible(true)} style={{ cursor: "pointer" }}>
        {label}
      </span>

      <CenterPopup visible={visible} onClose={() => setVisible(false)}>
        <div style={{ padding: "16px 20px", maxHeight: "70vh", overflowY: "auto" }}>
          <div style={{ fontSize: 20, fontWeight: 800, textAlign: "center", marginBottom: 2 }}>
            {stockName || stockCode}
          </div>
          {stockCode && <div style={{ fontSize: 13, color: "#888", textAlign: "center", marginBottom: 10 }}>{stockCode}</div>}

          {/* Hot stock info */}
          {ctx.total_score != null && (
            <div style={{ padding: "8px 12px", borderRadius: 10, background: "#f4f6fb", marginBottom: 10 }}>
              <InfoRow label="综合得分" value={ctx.total_score} />
              <InfoRow label="最佳排名" value={`#${ctx.best_rank}`} />
              <InfoRow label="多平台共振" value={ctx.cross_platform ? "是" : "否"} />
              {(ctx.platforms || []).map((p: any) => (
                <InfoRow key={p.platform} label={p.platform} value={`#${p.rank} (${p.score}分)`} />
              ))}
              <InfoRow label="原始分数" value={ctx.raw_score} />
              <InfoRow label="所属板块" value={ctx.board_name} />
            </div>
          )}

          {/* Limit-up info */}
          {ctx.limit_time != null && (
            <div style={{ padding: "8px 12px", borderRadius: 10, background: "#f4f6fb", marginBottom: 10 }}>
              <InfoRow label="封板时间" value={ctx.limit_time} />
              <InfoRow label="连板数" value={ctx.board_count ? `${ctx.board_count}板` : ""} />
              <InfoRow label="涨停原因" value={<span style={{ color: "#e34d59" }}>{ctx.limit_reason}</span>} />
              <InfoRow label="所属概念" value={ctx.concept} />
              <InfoRow label="换手率" value={ctx.turnover_rate ? `${ctx.turnover_rate}%` : ""} />
              <InfoRow label="开板次数" value={ctx.open_limit_count} />
            </div>
          )}

          {/* Watch pool info */}
          {ctx.pool_status != null && (
            <div style={{ padding: "8px 12px", borderRadius: 10, background: "#f4f6fb", marginBottom: 10 }}>
              <InfoRow label="自选状态" value={ctx.pool_status} />
              <InfoRow label="标签" value={(ctx.labels || []).join(" / ")} />
              <InfoRow label="操作策略" value={(ctx.operation_strategies || []).join(",")} />
              <InfoRow label="买点类型" value={(ctx.buy_point_types || []).join(",")} />
              <InfoRow label="来源平台" value={ctx.source_platform} />
              <InfoRow label="来源排名" value={ctx.source_rank} />
              <InfoRow label="入选理由" value={ctx.reason || ctx.source_reason} />
            </div>
          )}

          {/* Signal info */}
          {ctx.signal_type != null && (
            <div style={{ padding: "8px 12px", borderRadius: 10, background: "#f4f6fb", marginBottom: 10 }}>
              <InfoRow label="信号类型" value={ctx.signal_type} />
              <InfoRow label="信号等级" value={ctx.signal_level} />
              <InfoRow label="触发时间" value={ctx.trigger_time} />
              <InfoRow label="触发价格" value={ctx.trigger_price} />
              <InfoRow label="触发原因" value={ctx.trigger_reason} />
              <InfoRow label="风险说明" value={ctx.risk_desc} />
              <InfoRow label="信号状态" value={ctx.signal_status} />
            </div>
          )}

          {/* Trade info */}
          {ctx.trade_status != null && (
            <div style={{ padding: "8px 12px", borderRadius: 10, background: "#f4f6fb", marginBottom: 10 }}>
              <InfoRow label="交易状态" value={ctx.trade_status} />
              <InfoRow label="剩余持仓" value={ctx.remaining_amount} />
              <InfoRow label="盈亏" value={ctx.pnl_amount} />
            </div>
          )}

          <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
            <Button block fill="none" size="small" onClick={() => setVisible(false)}>关闭</Button>
            <Button block color="primary" size="small" onClick={() => { window.open(url, "_blank"); setVisible(false); }}>雪球查看</Button>
          </div>
        </div>
      </CenterPopup>
    </>
  );
}
