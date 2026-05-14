import { useState } from "react";
import { Button, CenterPopup } from "antd-mobile";
import { StockDetailPopup } from "./StockDetailPopup";

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

function formatStockLabel(stockName?: string | null, stockCode?: string | null, info?: Record<string, any>) {
  const name = stockName || stockCode || "";
  const price = info?.price ?? info?.last_price ?? info?.trigger_price ?? info?.first_buy_price;
  const change = info?.change_pct;
  if (price != null && change != null) {
    const sign = change >= 0 ? "+" : "";
    return `${name} (${price}, ${sign}${change}%)`;
  }
  if (price != null) {
    return `${name} (${price})`;
  }
  return `${name} ${stockCode || ""}`;
}

export function StockLink({ stockCode, stockName, showCode = true, className, info }: StockLinkProps) {
  const [visible, setVisible] = useState(false);
  const url = toXueqiuUrl(stockCode);
  const label = formatStockLabel(stockName, showCode ? stockCode : null, info);

  if (!url) {
    return <span className={className || "stock-link"}>{label || "-"}</span>;
  }

  const ctx = info || {};

  // Use detail popup for limit-up stocks.
  if (ctx.limit_time != null) {
    return (
      <>
        <span className={className || "stock-link"} onClick={() => setVisible(true)} style={{ cursor: "pointer" }}>
          {label}
        </span>
        <StockDetailPopup visible={visible} stockCode={stockCode || ""} stockName={stockName || ""} info={ctx} onClose={() => setVisible(false)} />
      </>
    );
  }

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

          {/* Limit-up info */}
          {ctx.limit_time != null && (
            <div style={{ padding: "8px 12px", borderRadius: 10, background: "#f4f6fb", marginBottom: 10 }}>
              <InfoRow label="封板时间" value={ctx.limit_time} />
              <InfoRow label="连板数" value={ctx.board_count ? `${ctx.board_count}板` : ""} />
              {ctx.change_pct != null && <InfoRow label="涨幅" value={`${ctx.change_pct >= 0 ? "+" : ""}${ctx.change_pct}%`} />}
              {ctx.last_price != null && <InfoRow label="最新价" value={ctx.last_price} />}
              <InfoRow label="所属概念" value={ctx.concept || ctx.plate_name} />
              <InfoRow label="换手率" value={ctx.turnover_rate ? `${ctx.turnover_rate}%` : ""} />
              {ctx.limit_reason && (
                <div style={{ marginTop: 6, padding: "8px 10px", borderRadius: 8, background: "#fff4f4" }}>
                  <div style={{ fontSize: 11, color: "#999", marginBottom: 2 }}>涨停原因</div>
                  <div style={{ fontSize: 14, color: "#c0392b", lineHeight: 1.5, wordBreak: "break-word" }}>{ctx.limit_reason}</div>
                </div>
              )}
            </div>
          )}

          {/* Watch pool info */}
          {ctx.pool_status != null && (
            <div style={{ padding: "8px 12px", borderRadius: 10, background: "#f4f6fb", marginBottom: 10 }}>
              <InfoRow label="自选状态" value={ctx.lifecycle_status || ctx.pool_status} />
              <InfoRow label="交易系统" value={ctx.trading_system} />
              <InfoRow label="标签" value={(ctx.labels || []).join(" / ")} />
              <InfoRow label="来源平台" value={ctx.source_platform} />
              <InfoRow label="来源排名" value={ctx.source_rank} />
              <InfoRow label="入选理由" value={ctx.entry_reason || ctx.reason || ctx.source_reason} />
              <InfoRow label="关键观察价" value={ctx.key_observe_price} />
              <InfoRow label="失效条件" value={ctx.invalid_condition} />
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
