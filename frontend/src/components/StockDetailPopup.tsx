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
  const xueqiuUrl = `https://xueqiu.com/S/${stockCode.replace(".", "")}`;

  useEffect(() => {
    if (!visible || !stockCode) return;
    setLoading(true);
    apiGet<any[]>(`/h5/market/stocks/${stockCode}/kline-daily?limit=60`)
      .then((data) => setKlineData(data || []))
      .catch(() => setKlineData([]))
      .finally(() => setLoading(false));
  }, [visible, stockCode]);

  return (
    <CenterPopup visible={visible} onClose={onClose} closeOnMaskClick>
      <div style={{ padding: "12px 16px", maxHeight: "80vh", display: "flex", flexDirection: "column" }}>
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
                  <div style={{ fontSize: 15, color: "#c0392b", lineHeight: 1.6, wordBreak: "break-word" }}>
                    {info.limit_reason}
                  </div>
                </div>
              ) : (
                <div style={{ textAlign: "center", padding: 30, color: "#888", fontSize: 14 }}>暂无涨停原因</div>
              )}
              <div style={{ marginTop: 10, display: "grid", gap: 4 }}>
                {[
                  ["封板时间", info?.limit_time],
                  ["连板数", info?.board_count ? `${info.board_count}板` : "-"],
                  ["所属概念", info?.concept || info?.plate_name],
                  ["涨幅", info?.change_pct != null ? `${info.change_pct >= 0 ? "+" : ""}${info.change_pct}%` : "-"],
                  ["最新价", info?.last_price],
                  ["换手率", info?.turnover_rate != null ? `${info.turnover_rate}%` : "-"],
                ].filter(([, v]) => v != null && v !== "").map(([label, value]) => (
                  <div key={label} style={{ display: "flex", justifyContent: "space-between", padding: "4px 0", fontSize: 13, borderBottom: "1px solid #f0f0f0" }}>
                    <span style={{ color: "#888" }}>{label}</span>
                    <span style={{ color: "#334", fontWeight: 500 }}>{value}</span>
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

function KlineChart({ data, loading }: { data: any[]; loading: boolean }) {
  const containerRef = (el: HTMLDivElement | null) => {
    if (!el || !data.length) return;
    const chart = echarts.init(el);
    const dates = data.map((d) => d.trade_date);
    const values = data.map((d) => [d.open, d.close, d.low, d.high]);
    const volumes = data.map((d) => d.volume || 0);

    chart.setOption({
      tooltip: { trigger: "axis" },
      grid: [
        { left: 8, right: 8, top: 8, height: "60%" },
        { left: 8, right: 8, top: "75%", height: "18%" },
      ],
      xAxis: [
        { type: "category", data: dates, gridIndex: 0, axisLabel: { fontSize: 10, rotate: 30, interval: Math.max(1, Math.floor(data.length / 8)) } },
        { type: "category", data: dates, gridIndex: 1, axisLabel: { show: false } },
      ],
      yAxis: [
        { type: "value", gridIndex: 0, scale: true, axisLabel: { fontSize: 10 } },
        { type: "value", gridIndex: 1, axisLabel: { fontSize: 10 } },
      ],
      dataZoom: [
        { type: "inside", xAxisIndex: [0, 1], zoomOnMouseWheel: true, moveOnMouseMove: true },
        { type: "slider", xAxisIndex: [0, 1], bottom: 0, height: 16, borderColor: "#ddd", fillerColor: "rgba(75,99,238,0.1)", handleSize: "80%" },
      ],
      series: [
        {
          name: "K线",
          type: "candlestick",
          data: values,
          xAxisIndex: 0, yAxisIndex: 0,
          itemStyle: { color: "#e34d59", color0: "#00b578", borderColor: "#e34d59", borderColor0: "#00b578" },
        },
        {
          name: "成交量",
          type: "bar",
          data: volumes,
          xAxisIndex: 1, yAxisIndex: 1,
          itemStyle: { color: (params: any) => {
            const idx = params.dataIndex;
            const d = data[idx];
            return d.close >= d.open ? "#e34d59" : "#00b578";
          }},
        },
      ],
    });

    const handleResize = () => chart.resize();
    window.addEventListener("resize", handleResize);
    return () => {
      window.removeEventListener("resize", handleResize);
      chart.dispose();
    };
  };

  if (loading) return <div style={{ textAlign: "center", padding: 40 }}><SpinLoading /></div>;
  if (!data.length) return <div style={{ textAlign: "center", padding: 40, color: "#888" }}>暂无K线数据</div>;

  return <div ref={containerRef} style={{ width: "100%", height: 380 }} />;
}
