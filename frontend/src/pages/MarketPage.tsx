import { useEffect, useMemo, useRef, useState } from "react";
import { Button, DatePicker, Dialog, ErrorBlock, Input, Picker, Popup, Selector, SpinLoading, TextArea, Toast } from "antd-mobile";
import * as echarts from "echarts";
import { useLocation, useNavigate } from "react-router-dom";
import { apiGet, apiPost } from "../api/client";
import { PageShell } from "../components/PageShell";
import { StockLink } from "../components/StockLink";
import { dateToString, shiftTradeDate, stringToDate, todayString } from "../lib/tradeDates";

type MarketSummary = {
  source: string;
  total_amount: number;
  up_count: number;
  down_count: number;
  flat_count: number;
  limit_up_count: number;
  limit_down_count: number;
  max_continue_board: number;
  sh_index?: number;
  sz_index?: number;
  cyb_index?: number;
  market_comment?: string;
  index_change_pct?: number;
  sh_index_change_pct?: number;
  sh_index_change_px?: number;
  sz_index_change_pct?: number;
  sz_index_change_px?: number;
  cyb_index_change_pct?: number;
  cyb_index_change_px?: number;
  today_chances?: any[];
  today_tuyeres?: any[];
  topic_list?: any[];
  limit_up_ladder?: any[];
};

type WatchDraft = {
  stock_code: string;
  stock_name: string;
  source_type: "hot_stock" | "limit_up";
  source_platform?: string;
  source_rank?: number;
  source_score?: number;
  source_reason: string;
  sector_name?: string;
  trading_system: "platform_breakout" | "uptrend" | "relay";
  entry_reason: string;
  key_observe_price: string;
  invalid_condition: string;
  risk_tags: string[];
  user_remark: string;
  raw_item: any;
};

const tradingSystemOptions = [
  { label: "平台突破", value: "platform_breakout" },
  { label: "上涨趋势", value: "uptrend" },
  { label: "追涨接力", value: "relay" },
];

const riskTagOptions = [
  { label: "高位", value: "high_position" },
  { label: "封板弱", value: "weak_seal" },
  { label: "放量异常", value: "abnormal_volume" },
  { label: "板块转弱", value: "sector_weak" },
  { label: "跌破支撑", value: "break_support" },
];

function formatPct(value?: number | null) {
  if (value == null) return "";
  return `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;
}

function formatPx(value?: number | null) {
  if (value == null) return "";
  return ` ${value >= 0 ? "+" : ""}${value.toFixed(2)}`;
}

function pctColor(value?: number | null) {
  return value == null ? "#7687a4" : value >= 0 ? "#e34d59" : "#00b578";
}

function limitHeight(row: any) {
  return row.ladder_height || row.board_count || 1;
}

function recommendTradingSystem(item: any, sourceType: "hot_stock" | "limit_up"): WatchDraft["trading_system"] {
  const reason = `${item.raw_reason || ""} ${item.limit_reason || ""} ${item.reason || ""}`;
  if (reason.includes("突破") || reason.toLowerCase().includes("breakout")) return "platform_breakout";
  if (sourceType === "limit_up") return "relay";
  return "uptrend";
}

function tradingSystemLabel(value: string) {
  return tradingSystemOptions.find((item) => item.value === value)?.label || value;
}

function buildWatchDraft(item: any, sourceType: "hot_stock" | "limit_up"): WatchDraft {
  const sourceReason = item.raw_reason || item.limit_reason || item.reason || item.up_reason || "";
  const tradingSystem = recommendTradingSystem(item, sourceType);
  const price = item.last_price ?? item.price ?? item.trigger_price ?? "";
  return {
    stock_code: item.stock_code,
    stock_name: item.stock_name,
    source_type: sourceType,
    source_platform: item.platform,
    source_rank: item.platform_rank,
    source_score: item.raw_score,
    source_reason: sourceReason,
    sector_name: item.board_name || item.concept || item.plate_name,
    trading_system: tradingSystem,
    entry_reason: sourceReason || (sourceType === "limit_up" ? "涨停榜手动加入观察" : "人气榜手动加入观察"),
    key_observe_price: price ? String(price) : "",
    invalid_condition: sourceType === "limit_up" ? "涨停结构走弱或跌破关键观察价" : "跌破关键观察价或人气逻辑失效",
    risk_tags: sourceType === "limit_up" ? ["high_position"] : [],
    user_remark: "",
    raw_item: item,
  };
}

function LimitUpKlineChart({ stockCode }: { stockCode?: string }) {
  const chartRef = useRef<HTMLDivElement | null>(null);
  const [rows, setRows] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!stockCode) return;
    setLoading(true);
    apiGet<any[]>(`/h5/market/stocks/${encodeURIComponent(stockCode)}/kline-daily?limit=100`)
      .then((data) => setRows(data || []))
      .catch(() => setRows([]))
      .finally(() => setLoading(false));
  }, [stockCode]);

  useEffect(() => {
    if (!chartRef.current || !rows.length) return;
    const chart = echarts.init(chartRef.current);
    const dates = rows.map((row) => row.trade_date);
    const values = rows.map((row) => [row.open, row.close, row.low, row.high]);
    const volumes = rows.map((row) => row.volume || 0);
    const ma5 = rows.map((row) => row.ma5 ?? null);
    const ma10 = rows.map((row) => row.ma10 ?? null);
    const ma20 = rows.map((row) => row.ma20 ?? null);

    chart.setOption({
      animation: false,
      tooltip: { trigger: "axis" },
      legend: { top: 0, itemWidth: 10, itemHeight: 6, textStyle: { fontSize: 10 } },
      grid: [
        { left: 34, right: 12, top: 28, height: 150 },
        { left: 34, right: 12, top: 205, height: 52 },
      ],
      xAxis: [
        { type: "category", data: dates, boundaryGap: true, axisLabel: { fontSize: 10, interval: Math.max(1, Math.floor(rows.length / 6)) } },
        { type: "category", data: dates, gridIndex: 1, axisLabel: { show: false } },
      ],
      yAxis: [
        { type: "value", scale: true, axisLabel: { fontSize: 10 } },
        { type: "value", gridIndex: 1, axisLabel: { fontSize: 10 } },
      ],
      dataZoom: [{ type: "inside", xAxisIndex: [0, 1], start: 55, end: 100 }],
      series: [
        {
          name: "日K",
          type: "candlestick",
          data: values,
          itemStyle: { color: "#e34d59", color0: "#00b578", borderColor: "#e34d59", borderColor0: "#00b578" },
        },
        { name: "MA5", type: "line", data: ma5, smooth: true, symbol: "none", lineStyle: { width: 1, color: "#f59e0b" } },
        { name: "MA10", type: "line", data: ma10, smooth: true, symbol: "none", lineStyle: { width: 1, color: "#4b63ee" } },
        { name: "MA20", type: "line", data: ma20, smooth: true, symbol: "none", lineStyle: { width: 1, color: "#64748b" } },
        {
          name: "成交量",
          type: "bar",
          data: volumes,
          xAxisIndex: 1,
          yAxisIndex: 1,
          itemStyle: {
            color: (params: any) => {
              const row = rows[params.dataIndex];
              return row.close >= row.open ? "#e34d59" : "#00b578";
            },
          },
        },
      ],
    });

    const resize = () => chart.resize();
    window.addEventListener("resize", resize);
    return () => {
      window.removeEventListener("resize", resize);
      chart.dispose();
    };
  }, [rows]);

  if (loading) {
    return <div style={{ height: 280, display: "grid", placeItems: "center" }}><SpinLoading /></div>;
  }
  if (!rows.length) {
    return <div style={{ height: 120, display: "grid", placeItems: "center", color: "#8792a8" }}>暂无K线数据</div>;
  }
  return <div ref={chartRef} style={{ width: "100%", height: 280 }} />;
}

export function MarketPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const queryDate = new URLSearchParams(location.search).get("trade_date");
  const refreshKey = new URLSearchParams(location.search).get("refresh");
  const [tradeDate, setTradeDate] = useState<string>(queryDate || "");
  const [pickerVisible, setPickerVisible] = useState(false);
  const [tab, setTab] = useState("overview");
  const [data, setData] = useState<MarketSummary | null>(null);
  const [review, setReview] = useState<any>(null);
  const [hotStocks, setHotStocks] = useState<any[]>([]);
  const [hotSectors, setHotSectors] = useState<any[]>([]);
  const [limitRows, setLimitRows] = useState<any[]>([]);
  const [limitLadderRows, setLimitLadderRows] = useState<any[]>([]);
  const [limitTotal, setLimitTotal] = useState(0);
  const [limitConcept, setLimitConcept] = useState("");
  const [limitLadder, setLimitLadder] = useState<number | null>(null);
  const [includeSt, setIncludeSt] = useState(false);
  const [hotPlatform, setHotPlatform] = useState("");
  const [hotPlatformPickerVisible, setHotPlatformPickerVisible] = useState(false);
  const [watchCodes, setWatchCodes] = useState<Set<string>>(new Set());
  const [watchDraft, setWatchDraft] = useState<WatchDraft | null>(null);
  const [watchSubmitting, setWatchSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  function refreshWatchCodes() {
    return apiGet<any[]>("/h5/watch-pool")
      .then((items) => setWatchCodes(new Set((items || []).map((item: any) => item.stock_code))))
      .catch(() => {});
  }

  useEffect(() => {
    if (queryDate) return;
    apiGet<string[]>("/h5/market/trading-dates")
      .then((dates) => {
        const latestDate = (dates || []).slice().sort().reverse()[0] || todayString();
        setTradeDate(latestDate);
        navigate(`/market?trade_date=${latestDate}`, { replace: true });
      })
      .catch(() => {
        const fallbackDate = todayString();
        setTradeDate(fallbackDate);
        navigate(`/market?trade_date=${fallbackDate}`, { replace: true });
      });
  }, [navigate, queryDate]);

  useEffect(() => {
    if (!tradeDate) return;
    setLoading(true);
    setError("");

    refreshWatchCodes();

    apiGet<MarketSummary>(`/h5/market/overview?trade_date=${tradeDate}`)
      .then((summary) => setData(summary))
      .catch(() => {
        setData(null);
        setError("市场数据加载失败，请稍后重试");
      });

    apiGet<any>(`/market/review?trade_date=${tradeDate}`)
      .then((row) => setReview(row))
      .catch(() => setReview(null));

    apiGet<any>(`/h5/market/hot-stocks?trade_date=${tradeDate}&page_size=50${hotPlatform ? `&platform=${hotPlatform}` : ""}`)
      .then((hot) => setHotStocks(hot.list || hot || []))
      .catch(() => setHotStocks([]));

    apiGet<any>(`/h5/market/hot-boards?trade_date=${tradeDate}&page_size=5`)
      .then((boards) => setHotSectors((boards.list || boards || []).map((row: any) => ({
        name: row.plate_name || row.board_name,
        count: row.limit_up_count || row.raw_score || 0,
        changePct: row.change_pct,
        reason: row.up_reason || row.reason || "",
      }))))
      .catch(() => setHotSectors([]));

    apiGet<any>(`/h5/market/limit-ups?trade_date=${tradeDate}&page_size=500`)
      .then((limitList) => {
        const rows = limitList.list || limitList || [];
        setLimitRows(rows);
        setLimitLadderRows(limitList.limit_up_ladder || []);
        setLimitTotal(limitList.total || rows.length || 0);
      })
      .catch(() => {
        setLimitRows([]);
        setLimitLadderRows([]);
        setLimitTotal(0);
      })
      .finally(() => setLoading(false));
  }, [tradeDate, refreshKey, hotPlatform]);

  useEffect(() => {
    const nextDate = new URLSearchParams(location.search).get("trade_date");
    if (nextDate && nextDate !== tradeDate) {
      setTradeDate(nextDate);
    }
  }, [location.search, tradeDate]);

  function changeTradeDate(nextDate: string) {
    setTradeDate(nextDate);
    navigate(`/market?trade_date=${nextDate}`);
  }

  const amountText = data ? `${(data.total_amount / 10000).toFixed(2)}万亿` : "-";
  const totalBreadth = data ? Math.max((data.up_count || 0) + (data.down_count || 0) + (data.flat_count || 0), 1) : 1;
  const upRatio = data ? Math.round(((data.up_count || 0) / totalBreadth) * 100) : 0;
  const marketInfoSections = [
    { title: "今日机会", tag: "财联社", rows: data?.today_chances || [] },
    { title: "今日风口", tag: "财联社", rows: data?.today_tuyeres || [] },
    { title: "话题热榜", tag: "同花顺", rows: data?.topic_list || [] },
  ];

  const filteredLimitRows = useMemo(() => {
    let rows = limitRows;
    if (!includeSt) rows = rows.filter((row) => !(row.stock_name || "").includes("ST"));
    if (limitConcept) rows = rows.filter((row) => (row.concept || row.plate_name || "未分类") === limitConcept);
    if (limitLadder != null) rows = rows.filter((row) => limitHeight(row) === limitLadder);
    return rows;
  }, [limitRows, limitConcept, limitLadder, includeSt]);

  const preLadderRows = useMemo(() => {
    let rows = limitRows;
    if (!includeSt) rows = rows.filter((row) => !(row.stock_name || "").includes("ST"));
    if (limitConcept) rows = rows.filter((row) => (row.concept || row.plate_name || "未分类") === limitConcept);
    return rows;
  }, [limitRows, includeSt, limitConcept]);

  const { ladderHeights, ladderCounts } = useMemo(() => {
    if (includeSt && !limitConcept && limitLadderRows.length) {
      const heights = limitLadderRows.map((row) => row.height).filter(Boolean).sort((a, b) => Number(b) - Number(a));
      const counts: Record<number, number> = {};
      limitLadderRows.forEach((row) => {
        counts[row.height] = row.count || 0;
      });
      return { ladderHeights: heights, ladderCounts: counts };
    }
    const heights = [...new Set(preLadderRows.map((row) => limitHeight(row)))]
      .sort((a, b) => Number(b) - Number(a));
    const counts: Record<number, number> = {};
    heights.forEach((height) => {
      counts[height] = preLadderRows.filter((row) => limitHeight(row) === height).length;
    });
    return { ladderHeights: heights, ladderCounts: counts };
  }, [preLadderRows, includeSt, limitConcept, limitLadderRows]);

  const conceptButtons = useMemo(() => {
    const rows = includeSt ? limitRows : limitRows.filter((row) => !(row.stock_name || "").includes("ST"));
    const counts: Record<string, number> = {};
    rows.forEach((row) => {
      const name = row.concept || row.plate_name || "未分类";
      counts[name] = (counts[name] || 0) + 1;
    });
    return Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 15);
  }, [limitRows, includeSt]);

  function showMarketInfoDetail(title: string, item: any) {
    const stocks = item.stocks || [];
    Dialog.alert({
      title,
      content: (
        <div style={{ textAlign: "left", color: "#53627c", lineHeight: 1.65 }}>
          <strong style={{ color: "#18223d" }}>{item.subject_name || item.title}</strong>
          {item.title && item.subject_name ? <p>{item.title}</p> : null}
          {item.driver ? <p>{item.driver}</p> : null}
          {item.description ? <p>{item.description}</p> : null}
          {item.hot_value != null ? <p>热度：{item.hot_value}</p> : null}
          {item.attention_num != null ? <p>关注度：{item.attention_num}</p> : null}
          {stocks.length ? (
            <p>
              关联个股：
              {stocks.map((stock: any) => `${stock.stock_name || stock.name}${stock.change_pct != null ? ` ${formatPct(stock.change_pct)}` : ""}`).join(" / ")}
            </p>
          ) : null}
          <p style={{ marginTop: 10 }}>仅作为市场资讯辅助，请结合个人交易规则确认。</p>
        </div>
      ),
      confirmText: "知道了",
    });
  }

  function showLimitUpDetail(item: any) {
    Dialog.alert({
      title: item.stock_name || item.stock_code,
      content: (
        <div style={{ width: "min(86vw, 520px)", textAlign: "left", color: "#53627c", lineHeight: 1.65 }}>
          <LimitUpKlineChart stockCode={item.stock_code} />
          <p><strong>股票：</strong><StockLink stockName={item.stock_name} stockCode={item.stock_code} showCode /></p>
          <p><strong>所属板块：</strong>{item.concept || item.plate_name || "未分类"}</p>
          <p><strong>涨停时间：</strong>{item.limit_time || "-"}</p>
          <p><strong>连板：</strong>{limitHeight(item)} 板</p>
          {item.change_pct != null ? <p><strong>涨幅：</strong>{formatPct(item.change_pct)}</p> : null}
          {item.last_price != null ? <p><strong>最新价：</strong>{item.last_price}</p> : null}
          {item.reason_tags || item.limit_type ? <p><strong>标签：</strong>{item.reason_tags || item.limit_type}</p> : null}
          <p><strong>涨停原因：</strong>{item.limit_reason || "暂无原因"}</p>
          <p style={{ marginTop: 10 }}>K线来自财联社公开行情接口，仅作为涨停结果观察辅助，请结合个人交易规则确认。</p>
        </div>
      ),
      confirmText: "知道了",
    });
  }

  function addWatchFromMarket(item: any, sourceType: "hot_stock" | "limit_up") {
    setWatchDraft(buildWatchDraft(item, sourceType));
  }

  async function submitWatchDraft() {
    if (!watchDraft) return;
    if (!watchDraft.trading_system || !watchDraft.entry_reason.trim() || !watchDraft.key_observe_price || !watchDraft.invalid_condition.trim()) {
      Toast.show({ content: "请补全交易系统、入选理由、关键观察价和失效条件" });
      return;
    }
    setWatchSubmitting(true);
    try {
      await apiPost("/h5/watch-pool", {
        stock_code: watchDraft.stock_code,
        stock_name: watchDraft.stock_name,
        sector_name: watchDraft.sector_name,
        labels: watchDraft.source_type === "limit_up" ? ["relay"] : ["popularity"],
        source_type: watchDraft.source_type,
        entry_source: watchDraft.source_type,
        source_platform: watchDraft.source_platform,
        source_rank: watchDraft.source_rank,
        source_score: watchDraft.source_score,
        source_reason: watchDraft.source_reason,
        trading_system: watchDraft.trading_system,
        entry_reason: watchDraft.entry_reason,
        reason: watchDraft.entry_reason,
        key_observe_price: Number(watchDraft.key_observe_price),
        invalid_condition: watchDraft.invalid_condition,
        risk_tags: watchDraft.risk_tags,
        user_remark: watchDraft.user_remark,
      });
      Toast.show({ content: "已加入自选观察" });
      const code = watchDraft.stock_code;
      setWatchDraft(null);
      await refreshWatchCodes();
      setWatchCodes((prev) => new Set(prev).add(code));
    } catch {
      Toast.show({ content: "添加自选失败，请检查填写信息" });
    } finally {
      setWatchSubmitting(false);
    }
  }

  return (
    <PageShell
      title="市场"
      dateText={tradeDate}
      onDateClick={() => setPickerVisible(true)}
      onPrevDate={() => changeTradeDate(shiftTradeDate(tradeDate, -1))}
      onNextDate={() => changeTradeDate(shiftTradeDate(tradeDate, 1))}
      segments={[
        { key: "overview", label: "大盘", onClick: () => setTab("overview") },
        { key: "hot", label: "热榜", onClick: () => setTab("hot") },
        { key: "limit", label: "涨停榜", onClick: () => setTab("limit") },
      ]}
      activeSegment={tab}
    >
      <DatePicker
        title="选择日期"
        visible={pickerVisible}
        precision="day"
        value={stringToDate(tradeDate || todayString())}
        max={new Date()}
        onClose={() => setPickerVisible(false)}
        onConfirm={(value) => changeTradeDate(dateToString(value))}
      />

      {loading && <SpinLoading />}
      {error && <ErrorBlock description={error} />}
      {data && (
        <>
          {tab === "overview" && (
            <article className="feature-card">
              <div className="metric-grid">
                <div className="metric-tile">
                  <span>成交量</span>
                  <strong>{amountText}</strong>
                </div>
                <div className="metric-tile">
                  <span>上涨率</span>
                  <strong>{upRatio}%</strong>
                </div>
                <div className="metric-tile">
                  <span>涨停 / 跌停</span>
                  <strong>{data.limit_up_count} / {data.limit_down_count}</strong>
                </div>
                <div className="metric-tile">
                  <span>最高连板</span>
                  <strong>{data.max_continue_board}</strong>
                </div>
              </div>
              <div className="metric-tile" style={{ background: "linear-gradient(135deg, #f1f4ff 0%, #e8eeff 50%, #ffffff 100%)" }}>
                <span>上证指数</span>
                <strong>
                  {data.sh_index ?? "-"}
                  <span style={{ fontSize: 16, fontWeight: 400, marginLeft: 6, color: pctColor(data.sh_index_change_pct ?? data.index_change_pct) }}>
                    {formatPct(data.sh_index_change_pct ?? data.index_change_pct)}
                    {formatPx(data.sh_index_change_px)}
                  </span>
                </strong>
                <div style={{ fontSize: 12, color: "#7687a4", marginTop: 2 }}>
                  深成指 {data.sz_index ?? "-"}
                  <span style={{ color: pctColor(data.sz_index_change_pct), marginLeft: 4 }}>
                    {formatPct(data.sz_index_change_pct)}
                    {formatPx(data.sz_index_change_px)}
                  </span>
                  <span style={{ margin: "0 6px" }}>/</span>
                  创业板指 {data.cyb_index ?? "-"}
                  <span style={{ color: pctColor(data.cyb_index_change_pct), marginLeft: 4 }}>
                    {formatPct(data.cyb_index_change_pct)}
                    {formatPx(data.cyb_index_change_px)}
                  </span>
                </div>
                {data.market_comment && (
                  <div style={{ fontSize: 12, color: "#64748b", marginTop: 6, lineHeight: 1.5 }}>{data.market_comment}</div>
                )}
              </div>
              <div style={{ display: "grid", gap: 10, marginTop: 12 }}>
                {marketInfoSections.map((section) => (
                  <div key={section.title} className="metric-tile" style={{ padding: 14 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                      <strong style={{ fontSize: 16 }}>{section.title}</strong>
                      <span className="soft-tag">{section.tag}</span>
                    </div>
                    {section.rows.length ? (
                      <div style={{ display: "grid", gap: 8 }}>
                        {section.rows.slice(0, section.title === "话题热榜" ? 5 : 3).map((item: any, index: number) => (
                          <button
                            key={`${section.title}-${item.subject_id || item.topic_code || index}`}
                            type="button"
                            onClick={() => showMarketInfoDetail(section.title, item)}
                            style={{ border: 0, borderRadius: 14, padding: "10px 12px", textAlign: "left", background: "#f6f8ff", color: "#1d2948" }}
                          >
                            <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                              <strong style={{ fontSize: 14 }}>{item.subject_name || item.title}</strong>
                              {(item.hot_value != null || item.attention_num != null) && (
                                <span style={{ color: "#64748b", fontSize: 12, whiteSpace: "nowrap" }}>
                                  {item.hot_value != null ? item.hot_value : item.attention_num}
                                </span>
                              )}
                            </div>
                            <p style={{ margin: "4px 0 0", color: "#73809a", fontSize: 12 }}>
                              {item.title || item.driver || item.description || "点击查看详情"}
                            </p>
                          </button>
                        ))}
                      </div>
                    ) : (
                      <div className="empty-panel" style={{ minHeight: 72 }}>暂无{section.title}数据</div>
                    )}
                  </div>
                ))}
              </div>
              <p className="card-note">市场页仅展示客观原始数据，不作为交易建议。仅作为交易辅助，请结合个人交易规则确认。</p>
              {review ? (
                <div className="review-note-panel">
                  <strong>复盘信息</strong>
                  <p>{review.review_text || "暂无复盘摘要"}</p>
                </div>
              ) : null}
            </article>
          )}

          {tab === "hot" && (
            <>
            <article className="feature-card">
              <div className="card-head">
                <div className="card-headline">
                  <span className="icon-badge">热</span>
                  <h2>热榜</h2>
                </div>
                <span className="soft-tag" style={{ cursor: "pointer" }} onClick={() => setHotPlatformPickerVisible(true)}>
                  {hotPlatform ? `${hotPlatform} Top10` : "平台原始榜单"} ▾
                </span>
              </div>
              {hotStocks.length ? (
                <div className="stack-list">
                  {hotStocks.map((item) => (
                    <div key={`${item.stock_code}-${item.platform || "all"}`} className="row-card row-card-action">
                      <div>
                        <strong>
                          <StockLink stockName={item.stock_name} stockCode={item.stock_code} info={item} />
                        </strong>
                        <p>原始分数：{item.raw_score ?? "-"} / 排名：#{item.platform_rank ?? "-"}</p>
                        <p>{item.platform || "-"} · {item.board_name || "未分类"}</p>
                      </div>
                      {watchCodes.has(item.stock_code) ? (
                        <span style={{ fontSize: 12, color: "#00b578", lineHeight: 1, fontWeight: 700 }}>已自选</span>
                      ) : (
                        <span style={{ fontSize: 22, color: "#4b63ee", cursor: "pointer", lineHeight: 1, fontWeight: 300 }} onClick={(event) => { event.stopPropagation(); addWatchFromMarket(item, "hot_stock"); }}>+</span>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="empty-panel">当前日期暂无热榜数据</div>
              )}
            </article>
            {!hotPlatform && hotSectors.length > 0 && (
              <article className="feature-card compact-card">
                <div className="card-head">
                  <div className="card-headline"><span className="icon-badge">板</span><h2>热榜板块</h2></div>
                  <span className="soft-tag">涨停板块 Top5</span>
                </div>
                <div className="stack-list">
                  {hotSectors.map((s, idx) => (
                    <div key={s.name} className="row-card" style={{ padding: "10px 12px", alignItems: "flex-start" }}>
                      <span style={{ fontSize: 16, fontWeight: 800, color: idx < 3 ? "#e34d59" : "#4b63ee", minWidth: 20 }}>{idx + 1}</span>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <strong style={{ fontSize: 14 }}>{s.name}</strong>
                        <p style={{ margin: "1px 0", fontSize: 12, color: "#888" }}>
                          涨停 {s.count} 只
                          {s.changePct != null ? ` · ${formatPct(s.changePct)}` : ""}
                        </p>
                        {s.reason && <p style={{ margin: "2px 0 0", fontSize: 12, color: "#e34d59", lineHeight: 1.5 }}>{s.reason}</p>}
                      </div>
                    </div>
                  ))}
                </div>
              </article>
            )}
            </>
          )}

          {tab === "limit" && (
            <article className="feature-card">
              <div className="card-head">
                <div className="card-headline">
                  <span className="icon-badge">{limitConcept || limitLadder ? filteredLimitRows.length : (includeSt ? limitTotal : limitTotal - limitRows.filter((row) => (row.stock_name || "").includes("ST")).length)}</span>
                  <h2>涨停榜</h2>
                </div>
                <button
                  type="button"
                  onClick={() => setIncludeSt(!includeSt)}
                  style={{
                    padding: "4px 10px",
                    border: `1px solid ${includeSt ? "#e34d59" : "#ddd"}`,
                    borderRadius: 12,
                    fontSize: 11,
                    fontWeight: 700,
                    background: includeSt ? "#fff4f4" : "#fff",
                    color: includeSt ? "#e34d59" : "#999",
                  }}
                >
                  {includeSt ? "含ST" : "不含ST"}
                </button>
              </div>
              <div style={{ display: "flex", gap: 4, overflowX: "auto", paddingBottom: 4, marginBottom: 4, flexWrap: "wrap" }}>
                <button type="button" onClick={() => setLimitConcept("")} style={{ flex: "0 0 auto", padding: "4px 10px", border: 0, borderRadius: 12, fontSize: 12, fontWeight: 600, background: !limitConcept ? "linear-gradient(135deg, #5570ff, #4052d2)" : "#f4f6fb", color: !limitConcept ? "#fff" : "#64748b" }}>全部</button>
                {conceptButtons.map(([name, count]) => (
                  <button key={name} type="button" onClick={() => setLimitConcept(limitConcept === name ? "" : name)} style={{ flex: "0 0 auto", padding: "4px 10px", border: 0, borderRadius: 12, fontSize: 12, fontWeight: 600, background: limitConcept === name ? "linear-gradient(135deg, #5570ff, #4052d2)" : "#f4f6fb", color: limitConcept === name ? "#fff" : "#64748b" }}>{name} {count}</button>
                ))}
              </div>
              <div style={{ display: "flex", gap: 6, overflowX: "auto", paddingBottom: 4, marginBottom: 8 }}>
                <button type="button" onClick={() => setLimitLadder(null)} style={{ flex: "0 0 auto", padding: "6px 12px", border: 0, borderRadius: 14, fontSize: 13, fontWeight: 700, background: limitLadder == null ? "linear-gradient(135deg, #5570ff, #4052d2)" : "#f4f6fb", color: limitLadder == null ? "#fff" : "#64748b" }}>全部</button>
                {ladderHeights.map((height) => (
                  <button key={String(height)} type="button" onClick={() => setLimitLadder(limitLadder === height ? null : height)} style={{ flex: "0 0 auto", padding: "6px 12px", border: 0, borderRadius: 14, fontSize: 13, fontWeight: 700, background: limitLadder === height ? "linear-gradient(135deg, #e34d59, #c0392b)" : "#f4f6fb", color: limitLadder === height ? "#fff" : "#e34d59" }}>{height}板 {ladderCounts[height]}</button>
                ))}
              </div>
              {filteredLimitRows.length ? (
                <div className="stack-list">
                  {filteredLimitRows.map((item) => (
                    <div key={item.stock_code} className="row-card row-card-action" style={{ padding: "10px 12px", cursor: "pointer" }} onClick={() => showLimitUpDetail(item)}>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <strong>
                          <span onClick={(event) => event.stopPropagation()}>
                            <StockLink stockName={item.stock_name} stockCode={item.stock_code} info={item} />
                          </span>
                          <span style={{ fontSize: 11, fontWeight: 400, color: "#999", marginLeft: 4 }}>{item.limit_time}</span>
                        </strong>
                        <p style={{ margin: "2px 0" }}>
                          {item.concept || item.plate_name || "未分类"}
                          {(item.reason_tags || item.limit_type) ? <span style={{ color: "#e34d59", marginLeft: 4 }}>{item.reason_tags || item.limit_type}</span> : null}
                        </p>
                        <p style={{ margin: 0, fontSize: 11, color: "#aaa" }}>
                          {limitHeight(item)}板
                          {item.change_pct != null ? ` / ${formatPct(item.change_pct)}` : ""}
                          {item.last_price != null ? ` / ${item.last_price}` : ""}
                          {item.turnover_rate != null ? ` / 换手${item.turnover_rate}%` : ""}
                        </p>
                      </div>
                      {watchCodes.has(item.stock_code) ? (
                        <span style={{ fontSize: 12, color: "#00b578", fontWeight: 700 }}>已自选</span>
                      ) : (
                        <span style={{ fontSize: 20, color: "#4b63ee", cursor: "pointer", fontWeight: 300 }} onClick={(event) => { event.stopPropagation(); addWatchFromMarket(item, "limit_up"); }}>+</span>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="empty-panel">该筛选条件下暂无涨停个股</div>
              )}
            </article>
          )}
        </>
      )}
      <Popup
        visible={!!watchDraft}
        onMaskClick={() => setWatchDraft(null)}
        bodyStyle={{ borderTopLeftRadius: 22, borderTopRightRadius: 22, padding: "18px 18px 22px", maxHeight: "86vh", overflowY: "auto" }}
      >
        {watchDraft && (
          <div style={{ display: "grid", gap: 14 }}>
            <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "flex-start" }}>
              <div>
                <div style={{ fontSize: 20, fontWeight: 800, color: "#15213d" }}>{watchDraft.stock_name}</div>
                <div style={{ marginTop: 4, color: "#72819b", fontSize: 13 }}>{watchDraft.stock_code}</div>
              </div>
              <span className="soft-tag">{watchDraft.source_type === "limit_up" ? "涨停榜" : "人气榜"}</span>
            </div>

            <div style={{ borderRadius: 16, background: "#f6f8ff", padding: 12, color: "#53627c", fontSize: 13, lineHeight: 1.6 }}>
              <div>来源平台：{watchDraft.source_platform || "-"}</div>
              <div>来源排名：{watchDraft.source_rank ?? "-"}</div>
              <div>来源原因：{watchDraft.source_reason || "-"}</div>
              <div>系统推荐：{tradingSystemLabel(recommendTradingSystem(watchDraft.raw_item, watchDraft.source_type))}</div>
            </div>

            <label style={{ display: "grid", gap: 8 }}>
              <span style={{ fontWeight: 700, color: "#1d2948" }}>用户确认交易系统</span>
              <Selector
                options={tradingSystemOptions}
                value={[watchDraft.trading_system]}
                onChange={(value) => setWatchDraft({ ...watchDraft, trading_system: value[0] as WatchDraft["trading_system"] })}
              />
            </label>

            <label style={{ display: "grid", gap: 8 }}>
              <span style={{ fontWeight: 700, color: "#1d2948" }}>入选理由</span>
              <TextArea
                value={watchDraft.entry_reason}
                autoSize={{ minRows: 2, maxRows: 4 }}
                placeholder="说明为什么把它加入观察池"
                onChange={(value) => setWatchDraft({ ...watchDraft, entry_reason: value })}
              />
            </label>

            <label style={{ display: "grid", gap: 8 }}>
              <span style={{ fontWeight: 700, color: "#1d2948" }}>关键观察价</span>
              <Input
                type="number"
                value={watchDraft.key_observe_price}
                placeholder="例如 12.35"
                onChange={(value) => setWatchDraft({ ...watchDraft, key_observe_price: value })}
              />
            </label>

            <label style={{ display: "grid", gap: 8 }}>
              <span style={{ fontWeight: 700, color: "#1d2948" }}>失效条件</span>
              <TextArea
                value={watchDraft.invalid_condition}
                autoSize={{ minRows: 2, maxRows: 4 }}
                placeholder="例如 跌破关键观察价且无法收回"
                onChange={(value) => setWatchDraft({ ...watchDraft, invalid_condition: value })}
              />
            </label>

            <label style={{ display: "grid", gap: 8 }}>
              <span style={{ fontWeight: 700, color: "#1d2948" }}>风险标签</span>
              <Selector
                multiple
                options={riskTagOptions}
                value={watchDraft.risk_tags}
                onChange={(value) => setWatchDraft({ ...watchDraft, risk_tags: value as string[] })}
              />
            </label>

            <label style={{ display: "grid", gap: 8 }}>
              <span style={{ fontWeight: 700, color: "#1d2948" }}>用户备注</span>
              <TextArea
                value={watchDraft.user_remark}
                autoSize={{ minRows: 2, maxRows: 4 }}
                placeholder="可记录个人观察计划"
                onChange={(value) => setWatchDraft({ ...watchDraft, user_remark: value })}
              />
            </label>

            <p style={{ margin: 0, color: "#7b879c", fontSize: 12, lineHeight: 1.6 }}>
              加入自选仅用于后续观察和信号提醒，仅作为交易辅助，请结合个人交易规则确认。
            </p>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
              <Button block onClick={() => setWatchDraft(null)}>取消</Button>
              <Button block color="primary" loading={watchSubmitting} onClick={submitWatchDraft}>提交</Button>
            </div>
          </div>
        )}
      </Popup>

      <Picker
        columns={[[
          { label: "三平台素数加权", value: "" },
          { label: "财联社 cls", value: "cls" },
          { label: "同花顺 ths", value: "ths" },
          { label: "淘股吧 tgb", value: "tgb" },
        ]]}
        visible={hotPlatformPickerVisible}
        title="选择热榜来源"
        onClose={() => setHotPlatformPickerVisible(false)}
        onConfirm={(value) => {
          setHotPlatform((value as string[])[0] || "");
          setHotPlatformPickerVisible(false);
        }}
      />
    </PageShell>
  );
}
