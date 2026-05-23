import { useEffect, useState } from "react";
import { Button, Popup } from "antd-mobile";
import { apiGet } from "../api/client";
import { KlineChart } from "./StockDetailPopup";

type StockLinkProps = {
  stockCode?: string | null;
  stockName?: string | null;
  showCode?: boolean;
  className?: string;
  info?: Record<string, any>;
  onEdit?: (info: Record<string, any>) => void | Promise<void>;
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

function formatNumber(value: unknown, digits = 2) {
  const num = Number(value);
  return Number.isFinite(num) ? num.toFixed(digits) : "-";
}

function formatPct(value: unknown) {
  const num = Number(value);
  if (!Number.isFinite(num)) return "-";
  return `${num >= 0 ? "+" : ""}${num.toFixed(2)}%`;
}

function formatStockLabel(stockName?: string | null, stockCode?: string | null, info?: Record<string, any>) {
  const name = stockName || stockCode || "";
  const price = info?.last_price ?? info?.price ?? info?.trigger_price ?? info?.first_buy_price;
  const change = info?.change_pct ?? info?.change;
  return `${name}(${formatNumber(price)}，${change != null ? formatPct(change) : "-%"})`;
}

function InfoRow({ label, value }: { label: string; value: any }) {
  if (value === null || value === undefined || value === "") return null;
  return (
    <div style={{ display: "flex", justifyContent: "space-between", gap: 12, padding: "8px 0", borderBottom: "1px solid #eef2f7", fontSize: 13 }}>
      <span style={{ color: "#8792a8", flexShrink: 0 }}>{label}</span>
      <span style={{ color: "#283653", fontWeight: 600, textAlign: "right", wordBreak: "break-word" }}>{value}</span>
    </div>
  );
}

function DetailPanel({ ctx }: { ctx: Record<string, any> }) {
  const detailRows: Array<[string, any]> = [
    ["最新价", ctx.last_price ?? ctx.price],
    ["涨幅", ctx.change_pct != null ? formatPct(ctx.change_pct) : null],
    ["所属板块", ctx.sector_name || ctx.concept || ctx.plate_name || ctx.assoc_plate],
    ["自选状态", ctx.status],
    ["交易体系", ctx.trading_system],
    ["信号类型", ctx.signal_type],
    ["信号等级", ctx.signal_level],
    ["信号状态", ctx.signal_status],
    ["买点类型", ctx.buy_point_type],
    ["触发价", ctx.trigger_price],
    ["交易状态", ctx.trade_status],
    ["买入均价", ctx.average_buy_price ?? ctx.first_buy_price],
    ["剩余数量", ctx.remaining_amount],
    ["盈亏", ctx.pnl_amount],
    ["观察价", ctx.key_observe_price],
    ["自动剔除价", ctx.auto_remove_price],
    ["止损价", ctx.stop_loss_price],
    ["目标价", ctx.target_price],
    ["封板时间", ctx.limit_time],
    ["连板数", ctx.board_count ? `${ctx.board_count}板` : null],
    ["更新时间", ctx.price_updated_at ? String(ctx.price_updated_at).replace("T", " ").slice(0, 16) : null],
  ];
  const reason = ctx.entry_reason || ctx.trigger_reason || ctx.buy_reason || ctx.limit_reason || ctx.reason;

  return (
    <div style={{ display: "grid", gap: 12 }}>
      <div style={{ borderRadius: 22, background: "#fff", padding: "8px 14px", boxShadow: "0 10px 30px rgba(31,43,77,0.07)" }}>
        {detailRows.map(([label, value]) => <InfoRow key={label} label={label} value={value} />)}
      </div>
      {(reason || ctx.invalid_condition || ctx.risk_desc || ctx.trade_plan) && (
        <div style={{ borderRadius: 22, background: "#fff", padding: 14, boxShadow: "0 10px 30px rgba(31,43,77,0.07)", display: "grid", gap: 10 }}>
          {reason && (
            <div style={{ borderRadius: 14, background: "#f7f9ff", padding: 12 }}>
              <div style={{ fontSize: 11, color: "#6d7b95", fontWeight: 800, marginBottom: 4 }}>核心原因</div>
              <div style={{ color: "#263653", fontSize: 14, lineHeight: 1.6, wordBreak: "break-word" }}>{reason}</div>
            </div>
          )}
          {ctx.invalid_condition && (
            <div style={{ borderRadius: 14, background: "#fff8e8", padding: 12 }}>
              <div style={{ fontSize: 11, color: "#b26b00", fontWeight: 800, marginBottom: 4 }}>失效条件</div>
              <div style={{ color: "#66410a", fontSize: 14, lineHeight: 1.6 }}>{ctx.invalid_condition}</div>
            </div>
          )}
          {ctx.risk_desc && (
            <div style={{ borderRadius: 14, background: "#fff4f4", padding: 12 }}>
              <div style={{ fontSize: 11, color: "#c0392b", fontWeight: 800, marginBottom: 4 }}>风险说明</div>
              <div style={{ color: "#9a2f2f", fontSize: 14, lineHeight: 1.6 }}>{ctx.risk_desc}</div>
            </div>
          )}
          {ctx.trade_plan && (
            <div style={{ borderRadius: 14, background: "#eefaf4", padding: 12 }}>
              <div style={{ fontSize: 11, color: "#00885d", fontWeight: 800, marginBottom: 4 }}>交易计划</div>
              <div style={{ color: "#1f5949", fontSize: 14, lineHeight: 1.6 }}>{ctx.trade_plan}</div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function StockLink({ stockCode, stockName, showCode = true, className, info, onEdit }: StockLinkProps) {
  const [visible, setVisible] = useState(false);
  const [tab, setTab] = useState<"detail" | "kline">("detail");
  const [klineData, setKlineData] = useState<any[]>([]);
  const [loadingKline, setLoadingKline] = useState(false);
  const url = toXueqiuUrl(stockCode);
  const ctx = info || {};
  const label = formatStockLabel(stockName, showCode ? stockCode : null, ctx);

  useEffect(() => {
    if (!visible || tab !== "kline" || !stockCode) return;
    setLoadingKline(true);
    apiGet<any[]>(`/h5/market/stocks/${encodeURIComponent(stockCode)}/kline-daily?limit=100`)
      .then((rows) => setKlineData(rows || []))
      .catch(() => setKlineData([]))
      .finally(() => setLoadingKline(false));
  }, [visible, tab, stockCode]);

  if (!url) {
    return <span className={className || "stock-link"}>{label || "-"}</span>;
  }

  async function handleEdit() {
    if (!onEdit) return;
    setVisible(false);
    await onEdit(ctx);
  }

  return (
    <>
      <span className={className || "stock-link"} onClick={(event) => { event.stopPropagation(); setVisible(true); }} style={{ cursor: "pointer" }}>
        {label}
      </span>

      <Popup
        visible={visible}
        onMaskClick={() => setVisible(false)}
        bodyStyle={{
          borderTopLeftRadius: 28,
          borderTopRightRadius: 28,
          padding: 0,
          height: "84vh",
          overflow: "hidden",
          background: "linear-gradient(180deg, #f7f9ff 0%, #ffffff 38%)",
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", height: "84vh" }}>
          <div style={{ padding: "8px 16px 10px" }}>
            <div style={{ width: 42, height: 5, borderRadius: 999, background: "#d9dfef", margin: "0 auto 12px" }} />
            <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "flex-start" }}>
              <div style={{ minWidth: 0 }}>
                <div style={{ color: "#141d36", fontSize: 20, fontWeight: 900, lineHeight: 1.25 }}>{stockName || stockCode}</div>
                <div style={{ marginTop: 4, color: "#6b7894", fontSize: 13 }}>
                  {stockCode}
                  {(ctx.last_price ?? ctx.price) != null && <span style={{ marginLeft: 8, color: "#17213b", fontWeight: 800 }}>{formatNumber(ctx.last_price ?? ctx.price)}</span>}
                  {ctx.change_pct != null && <span style={{ marginLeft: 6, color: Number(ctx.change_pct) >= 0 ? "#e34d59" : "#00a870", fontWeight: 800 }}>{formatPct(ctx.change_pct)}</span>}
                </div>
              </div>
              <span style={{ borderRadius: 999, padding: "7px 11px", background: "#eef2ff", color: "#4052d2", fontSize: 12, fontWeight: 800, whiteSpace: "nowrap" }}>
                {ctx.trading_system || ctx.status || ctx.trade_status || ctx.signal_status || "个股"}
              </span>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginTop: 14 }}>
              {[
                { key: "detail" as const, label: "详情" },
                { key: "kline" as const, label: "日K线" },
              ].map((item) => (
                <button
                  key={item.key}
                  type="button"
                  onClick={() => setTab(item.key)}
                  style={{
                    border: 0,
                    borderRadius: 14,
                    padding: "9px 0",
                    fontSize: 13,
                    fontWeight: 800,
                    background: tab === item.key ? "linear-gradient(135deg, #5570ff, #4052d2)" : "#eef2f8",
                    color: tab === item.key ? "#fff" : "#64748b",
                  }}
                >
                  {item.label}
                </button>
              ))}
            </div>
          </div>

          <div style={{ flex: 1, overflowY: "auto", padding: "0 16px 92px", WebkitOverflowScrolling: "touch" }}>
            {tab === "detail" ? (
              <DetailPanel ctx={ctx} />
            ) : (
              <div style={{ borderRadius: 24, background: "#fff", boxShadow: "0 12px 36px rgba(31,43,77,0.08)", overflow: "hidden" }}>
                <div style={{ padding: "12px 14px 0", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <strong style={{ color: "#18223d", fontSize: 16 }}>日K线</strong>
                  <span style={{ color: "#8a94a8", fontSize: 12 }}>复用市场页行情</span>
                </div>
                <KlineChart data={klineData} loading={loadingKline} />
              </div>
            )}
          </div>

          <div
            style={{
              position: "absolute",
              left: 0,
              right: 0,
              bottom: 0,
              padding: "10px 14px calc(10px + env(safe-area-inset-bottom))",
              background: "rgba(255,255,255,0.94)",
              borderTop: "1px solid rgba(226,232,240,0.9)",
              boxShadow: "0 -12px 32px rgba(31,43,77,0.1)",
              backdropFilter: "blur(14px)",
            }}
          >
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
              <Button block fill="outline" onClick={() => setVisible(false)} style={{ borderRadius: 14 }}>关闭</Button>
              <Button block color="primary" disabled={!onEdit} onClick={handleEdit} style={{ borderRadius: 14, fontWeight: 800 }}>编辑</Button>
              <Button block fill="outline" onClick={() => { window.open(url, "_blank"); }} style={{ borderRadius: 14 }}>雪球</Button>
            </div>
          </div>
        </div>
      </Popup>
    </>
  );
}
