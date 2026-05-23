import { useEffect, useMemo, useState } from "react";
import { Button, CenterPopup, SpinLoading } from "antd-mobile";
import * as echarts from "echarts";
import { apiGet } from "../api/client";

type Props = {
  visible: boolean;
  stockCode: string;
  stockName: string;
  info?: Record<string, any>;
  onClose: () => void;
};

export function StockDetailPopup({ visible, stockCode, stockName, info, onClose }: Props) {
  const [tab, setTab] = useState<"kline" | "reason">("kline");
  const [klineData, setKlineData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const xueqiuCode = (() => {
    const s = stockCode.trim().toUpperCase();
    if (/^(SH|SZ|BJ)\d{6}$/.test(s)) return s;
    const m = s.match(/^(\d{6})\.(SH|SZ|BJ)$/);
    return m ? `${m[2]}${m[1]}` : stockCode;
  })();
  const xueqiuUrl = `https://xueqiu.com/S/${xueqiuCode}`;

  useEffect(() => {
    if (!visible || !stockCode) return;
    setLoading(true);
    apiGet<any[]>(`/h5/market/stocks/${stockCode}/kline-daily?limit=100`)
      .then((data) => setKlineData(data || []))
      .catch(() => setKlineData([]))
      .finally(() => setLoading(false));
  }, [visible, stockCode]);

  return (
    <CenterPopup visible={visible} onClose={onClose} closeOnMaskClick>
      <div style={{ padding: "10px 12px", maxHeight: "80vh", display: "flex", flexDirection: "column" }}>
        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
          <div>
            <strong style={{ fontSize: 18 }}>{stockName}</strong>
            <span style={{ fontSize: 12, color: "#888", marginLeft: 6 }}>{stockCode}</span>
          </div>
          <a href={xueqiuUrl} target="_blank" rel="noreferrer"
            style={{ fontSize: 12, color: "#4b63ee", textDecoration: "none", fontWeight: 700 }}>雪球 ↗</a>
        </div>

        {/* Tabs */}
        <div style={{ display: "flex", gap: 8, marginBottom: 10 }}>
          {[
            { key: "kline" as const, label: "日K线" },
            { key: "reason" as const, label: "涨停原因" },
          ].map((t) => (
            <button key={t.key} onClick={() => setTab(t.key)}
              style={{
                flex: 1, padding: "6px 0", border: 0, borderRadius: 10,
                fontSize: 13, fontWeight: 700,
                background: tab === t.key ? "linear-gradient(135deg, #5570ff, #4052d2)" : "#f4f6fb",
                color: tab === t.key ? "#fff" : "#64748b",
              }}>{t.label}</button>
          ))}
        </div>

        {/* Content */}
        <div style={{ flex: 1, overflow: "auto" }}>
          {tab === "kline" && (
            <KlineChart data={klineData} loading={loading} />
          )}
          {tab === "reason" && (
            <div style={{ padding: "4px 0" }}>
              {info?.limit_reason ? (
                <div style={{ padding: "10px 12px", borderRadius: 10, background: "#fff4f4" }}>
                  <div style={{ fontSize: 12, color: "#999", marginBottom: 4 }}>涨停原因明细</div>
                  <div style={{ fontSize: 15, color: "#c0392b", lineHeight: 1.6 }}>{info.limit_reason}</div>
                </div>
              ) : null}
              <div style={{ marginTop: 10, display: "grid", gap: 4 }}>
                {[["封板时间", info?.limit_time], ["连板数", info?.board_count ? `${info.board_count}板` : "-"], ["所属概念", info?.concept || info?.plate_name], ["涨幅", info?.change_pct != null ? `${info.change_pct >= 0 ? "+" : ""}${info.change_pct}%` : "-"], ["最新价", info?.last_price], ["换手率", info?.turnover_rate != null ? `${info.turnover_rate}%` : "-"]].filter(([, v]) => v != null && v !== "").map(([label, value]) => (
                  <div key={label} style={{ display: "flex", justifyContent: "space-between", padding: "4px 0", fontSize: 13, borderBottom: "1px solid #f0f0f0" }}>
                    <span style={{ color: "#888" }}>{label}</span><span style={{ color: "#334", fontWeight: 500 }}>{value}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </CenterPopup>
  );
}

function calculateEma(values: number[], period: number) {
  const alpha = 2 / (period + 1);
  const result: number[] = [];
  values.forEach((value, index) => {
    result.push(index === 0 ? value : value * alpha + result[index - 1] * (1 - alpha));
  });
  return result;
}

function calculateMacd(closes: number[]) {
  if (!closes.length) return { dif: [], dea: [], hist: [] };
  const ema12 = calculateEma(closes, 12);
  const ema26 = calculateEma(closes, 26);
  const dif = closes.map((_, index) => Number((ema12[index] - ema26[index]).toFixed(4)));
  const dea = calculateEma(dif, 9).map((value) => Number(value.toFixed(4)));
  const hist = dif.map((value, index) => Number(((value - dea[index]) * 2).toFixed(4)));
  return { dif, dea, hist };
}

export function KlineChart({ data, loading }: { data: any[]; loading: boolean }) {
  const containerRef = (el: HTMLDivElement | null) => {
    if (!el || !data.length) return;
    const chart = echarts.init(el);
    const dates = data.map((d) => d.trade_date);
    const values = data.map((d) => [d.open, d.close, d.low, d.high]);
    const volumes = data.map((d) => d.volume || 0);
    const ma5 = data.map((d) => d.ma5 ?? null);
    const ma10 = data.map((d) => d.ma10 ?? null);
    const ma20 = data.map((d) => d.ma20 ?? null);
    const closes = data.map((d) => Number(d.close || 0));
    const macd = calculateMacd(closes);

    chart.setOption({
      animation: false,
      tooltip: { trigger: "axis" },
      legend: { top: 0, itemWidth: 10, itemHeight: 6, textStyle: { fontSize: 10 } },
      grid: [
        { left: 36, right: 12, top: 28, height: 132 },
        { left: 36, right: 12, top: 184, height: 48 },
        { left: 36, right: 12, top: 258, height: 56 },
      ],
      xAxis: [
        { type: "category", data: dates, boundaryGap: true, axisLabel: { fontSize: 10, interval: Math.max(1, Math.floor(data.length / 6)) } },
        { type: "category", data: dates, gridIndex: 1, axisLabel: { show: false } },
        { type: "category", data: dates, gridIndex: 2, axisLabel: { fontSize: 10, interval: Math.max(1, Math.floor(data.length / 6)) } },
      ],
      yAxis: [
        { type: "value", scale: true, axisLabel: { fontSize: 10 } },
        { type: "value", gridIndex: 1, axisLabel: { fontSize: 10 } },
        { type: "value", gridIndex: 2, scale: true, axisLabel: { fontSize: 10 } },
      ],
      dataZoom: [{ type: "inside", xAxisIndex: [0, 1, 2] }],
      series: [
        { name: "日K", type: "candlestick", data: values,
          itemStyle: { color: "#e34d59", color0: "#00b578", borderColor: "#e34d59", borderColor0: "#00b578" } },
        { name: "MA5", type: "line", data: ma5, smooth: true, symbol: "none", lineStyle: { width: 1, color: "#f59e0b" } },
        { name: "MA10", type: "line", data: ma10, smooth: true, symbol: "none", lineStyle: { width: 1, color: "#4b63ee" } },
        { name: "MA20", type: "line", data: ma20, smooth: true, symbol: "none", lineStyle: { width: 1, color: "#64748b" } },
        { name: "量", type: "bar", data: volumes, xAxisIndex: 1, yAxisIndex: 1,
          itemStyle: { color: (params: any) => { const d = data[params.dataIndex]; return d.close >= d.open ? "#e34d59" : "#00b578"; } } },
        { name: "MACD", type: "bar", data: macd.hist, xAxisIndex: 2, yAxisIndex: 2,
          itemStyle: { color: (params: any) => (params.data >= 0 ? "#e34d59" : "#00b578") } },
        { name: "DIF", type: "line", data: macd.dif, xAxisIndex: 2, yAxisIndex: 2, symbol: "none", lineStyle: { width: 1, color: "#4b63ee" } },
        { name: "DEA", type: "line", data: macd.dea, xAxisIndex: 2, yAxisIndex: 2, symbol: "none", lineStyle: { width: 1, color: "#f59e0b" } },
      ],
    });

    const handleResize = () => chart.resize();
    window.addEventListener("resize", handleResize);
    return () => { window.removeEventListener("resize", handleResize); chart.dispose(); };
  };

  if (loading) return <div style={{ height: 350, display: "grid", placeItems: "center" }}><SpinLoading /></div>;
  if (!data.length) return <div style={{ height: 120, display: "grid", placeItems: "center", color: "#888" }}>暂无K线数据</div>;

  return <div ref={containerRef} style={{ width: "100%", height: 350 }} />;
}
