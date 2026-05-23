import { useEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties } from "react";
import { Button, DatePicker, Dialog, ErrorBlock, Input, Picker, Popup, Selector, SpinLoading, TextArea, Toast } from "antd-mobile";
import * as echarts from "echarts";
import { useLocation, useNavigate } from "react-router-dom";
import { apiGet, apiPost } from "../api/client";
import { PageShell } from "../components/PageShell";
import { StockLink, toXueqiuUrl } from "../components/StockLink";
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
  entry_source_type: "hot_stock" | "limit_up";
  sector_name?: string;
  trading_system: string;
  system_params_json: Record<string, string>;
  entry_reason: string;
  key_observe_price: string;
  invalid_condition: string;
  risk_tags: string[];
  user_remark: string;
  raw_item: any;
};

type TradingSystemDefinition = {
  system_code: string;
  system_name: string;
  enabled: boolean;
};

type TradingSystemParamDefinition = {
  param_id: number;
  system_code: string;
  param_key: string;
  param_name: string;
  param_type: "number" | "text" | "select" | "boolean";
  required: boolean;
  default_value?: string | null;
  description?: string;
  sort_order: number;
};

type StockViewerState = {
  type: "hot_stock" | "limit_up";
  rows: any[];
  index: number;
};

const tradingSystemOptions = [
  { label: "平台突破", value: "platform_breakout" },
  { label: "上涨趋势", value: "uptrend" },
  { label: "涨停接力", value: "limit_relay" },
  { label: "超跌反弹", value: "oversold_rebound" },
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

function getStockPriceInfo(item: any) {
  const price = item?.price ?? item?.last_price ?? item?.trigger_price ?? item?.first_buy_price;
  const change = item?.change_pct;
  if (price != null && change != null) {
    return <span style={{ fontSize: 12, color: "#888", marginLeft: 4 }}>({price}, {change >= 0 ? "+" : ""}{change}%)</span>;
  }
  if (price != null) {
    return <span style={{ fontSize: 12, color: "#888", marginLeft: 4 }}>({price})</span>;
  }
  return <span style={{ fontSize: 12, color: "#888", marginLeft: 4 }}>{item?.stock_code}</span>;
}

function formatPx(value?: number | null) {
  if (value == null) return "";
  return ` ${value >= 0 ? "+" : ""}${value.toFixed(2)}`;
}

/** 排名对应素数权重，与后端 `MockProvider.PRIME_SCORES` 一致，用于跨平台综合得分。 */
const HOT_RANK_PRIMES: Record<number, number> = {
  1: 71,
  2: 67,
  3: 61,
  4: 59,
  5: 53,
  6: 47,
  7: 43,
  8: 41,
  9: 37,
  10: 31,
  11: 29,
  12: 23,
  13: 19,
  14: 17,
  15: 13,
  16: 11,
  17: 7,
  18: 5,
  19: 3,
  20: 2,
};

function hotRankPrimeScore(rank: number | null | undefined): number {
  if (rank == null || Number.isNaN(Number(rank))) return HOT_RANK_PRIMES[20];
  const r = Math.max(1, Math.min(20, Math.floor(Number(rank))));
  return HOT_RANK_PRIMES[r] ?? HOT_RANK_PRIMES[20];
}

const HOT_UI_PLATFORM_ORDER = ["cls", "ths", "tgb"] as const;

function normalizeHotListPlatformKey(platform: string): string {
  const key = `${platform || ""}`.trim();
  const map: Record<string, string> = {
    cls: "cls",
    ths: "ths",
    tgb: "tgb",
    财联社: "cls",
    同花顺: "ths",
    东方财富: "tgb",
    mock: "mock",
    platform_a: "cls",
    platform_b: "ths",
    platform_c: "tgb",
  };
  return map[key] || key;
}

function hotPlatformLabel(platform: string): string {
  return normalizeHotListPlatformKey(platform || "");
}

function formatHotCardAmount(item: { amount?: number | null; price?: number | null }): string {
  if (item.amount != null && !Number.isNaN(Number(item.amount))) return `${Number(item.amount).toFixed(2)}亿`;
  if (item.price != null && !Number.isNaN(Number(item.price))) return `${Number(item.price).toFixed(2)}元`;
  return "-";
}

type HotStockAgg = any;

function aggregateHotStocks(flat: any[]): HotStockAgg[] {
  if (!flat.length) return [];
  const byCode = new Map<string, any[]>();
  for (const row of flat) {
    const code = row.stock_code;
    if (!code) continue;
    const expanded =
      row.cls_rank || row.ths_rank || row.tgb_rank
        ? [
            row.cls_rank ? { ...row, platform: "cls", platform_rank: row.cls_rank, raw_score: hotRankPrimeScore(row.cls_rank), raw_reason: row.reason } : null,
            row.ths_rank ? { ...row, platform: "ths", platform_rank: row.ths_rank, raw_score: hotRankPrimeScore(row.ths_rank), raw_reason: row.reason } : null,
            row.tgb_rank ? { ...row, platform: "tgb", platform_rank: row.tgb_rank, raw_score: hotRankPrimeScore(row.tgb_rank), raw_reason: row.reason } : null,
          ].filter(Boolean)
        : [row];
    const list = byCode.get(code) || [];
    list.push(...expanded);
    byCode.set(code, list);
  }
  const out: HotStockAgg[] = [];
  for (const rows of byCode.values()) {
    const best = rows.reduce((a, b) => {
      const ar = a.platform_rank ?? 99;
      const br = b.platform_rank ?? 99;
      return ar <= br ? a : b;
    });
    const byNorm = new Map<string, any>();
    for (const r of rows) {
      const nk = normalizeHotListPlatformKey(r.platform);
      const prev = byNorm.get(nk);
      const rank = r.platform_rank ?? 99;
      if (!prev || (prev.platform_rank ?? 99) > rank) byNorm.set(nk, r);
    }
    const orderedKeys: string[] = [];
    for (const p of HOT_UI_PLATFORM_ORDER) {
      if (byNorm.has(p)) orderedKeys.push(p);
    }
    for (const k of [...byNorm.keys()].sort()) {
      if (!orderedKeys.includes(k)) orderedKeys.push(k);
    }
    let composite = 0;
    const parts: string[] = [];
    for (const k of orderedKeys) {
      const r = byNorm.get(k)!;
      const rawRank = r.platform_rank;
      const scoreRank = rawRank == null ? 20 : Math.max(1, Math.min(20, Math.floor(Number(rawRank))));
      composite += hotRankPrimeScore(scoreRank);
      parts.push(`${k}#${rawRank == null ? "-" : scoreRank}`);
    }
    const sector =
      rows.map((r) => r.sector_name || r.board_name).find((s) => s && String(s).trim()) || best.board_name || "";
    out.push({
      ...best,
      sector_name: sector,
      board_name: sector || best.board_name,
      composite_prime_score: composite,
      score: composite,
      platform_rank_line: parts.join(" "),
      hot_aggregate_rows: rows,
    });
  }
  return out;
}

function hotPlatformOptions(rows: any[]) {
  const seen = new Map<string, string>();
  for (const row of rows) {
    if (row.cls_rank) seen.set("cls", "cls");
    if (row.ths_rank) seen.set("ths", "ths");
    if (row.tgb_rank) seen.set("tgb", "tgb");
    const key = normalizeHotListPlatformKey(row.platform);
    if (!key || seen.has(key)) continue;
    seen.set(key, hotPlatformLabel(row.platform));
  }
  return [...seen.entries()]
    .map(([key, label]) => ({ key, label }))
    .sort((a, b) => {
      const ai = HOT_UI_PLATFORM_ORDER.indexOf(a.key as any);
      const bi = HOT_UI_PLATFORM_ORDER.indexOf(b.key as any);
      if (ai !== -1 || bi !== -1) return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
      return a.key.localeCompare(b.key);
    });
}

function sortHotComposite(rows: HotStockAgg[]): HotStockAgg[] {
  return [...rows].sort((a, b) => {
    const ds = (b.composite_prime_score || 0) - (a.composite_prime_score || 0);
    if (ds !== 0) return ds;
    const ar = a.platform_rank ?? 99;
    const br = b.platform_rank ?? 99;
    return ar - br;
  });
}

function filterAndSortHotByPlatform(rows: HotStockAgg[], platform: string): HotStockAgg[] {
  const want = normalizeHotListPlatformKey(platform);
  const filtered = rows.filter((row) => {
    const subs = row.hot_aggregate_rows || [row];
    return subs.some((r: any) => normalizeHotListPlatformKey(r.platform) === want);
  });
  return filtered.sort((a, b) => {
    const subsA = a.hot_aggregate_rows || [a];
    const subsB = b.hot_aggregate_rows || [b];
    const ra = subsA.find((r: any) => normalizeHotListPlatformKey(r.platform) === want)?.platform_rank ?? 999;
    const rb = subsB.find((r: any) => normalizeHotListPlatformKey(r.platform) === want)?.platform_rank ?? 999;
    return ra - rb;
  });
}

function pctColor(value?: number | null) {
  return value == null ? "#7687a4" : value >= 0 ? "#e34d59" : "#00b578";
}

function FieldTitle({ title, required, hint }: { title: string; required?: boolean; hint?: string }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "baseline" }}>
      <span style={{ color: "#18223d", fontWeight: 800, fontSize: 14 }}>
        {title}
        {required ? <span style={{ color: "#e34d59", marginLeft: 3 }}>*</span> : null}
      </span>
      {hint ? <span style={{ color: "#98a2b3", fontSize: 12, textAlign: "right" }}>{hint}</span> : null}
    </div>
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

function limitHeight(row: any) {
  return row.ladder_height || row.board_count || 1;
}

function recommendTradingSystem(item: any, sourceType: "hot_stock" | "limit_up"): WatchDraft["trading_system"] {
  const reason = `${item.raw_reason || ""} ${item.limit_reason || ""} ${item.reason || ""}`;
  if (reason.includes("突破") || reason.toLowerCase().includes("breakout")) return "platform_breakout";
  if (sourceType === "limit_up") return "limit_relay";
  return "uptrend";
}

function tradingSystemLabel(value: string, systems: TradingSystemDefinition[] = []) {
  return systems.find((item) => item.system_code === value)?.system_name || tradingSystemOptions.find((item) => item.value === value)?.label || value;
}

function buildWatchDraft(item: any, sourceType: "hot_stock" | "limit_up"): WatchDraft {
  const sourceReason = item.raw_reason || item.limit_reason || item.reason || item.up_reason || "";
  const tradingSystem = recommendTradingSystem(item, sourceType);
  const price = item.last_price ?? item.price ?? item.trigger_price ?? "";
  const systemParams = {
    key_observe_price: price ? String(price) : "",
    invalid_condition: sourceType === "limit_up" ? "涨停结构走弱或跌破关键观察价" : "跌破关键观察价或人气逻辑失效",
  };
  return {
    stock_code: item.stock_code,
    stock_name: item.stock_name,
    entry_source_type: sourceType,
    sector_name: item.sector_name || item.board_name || item.concept || item.plate_name,
    trading_system: tradingSystem,
    system_params_json: systemParams,
    entry_reason: sourceReason || (sourceType === "limit_up" ? "涨停榜手动加入观察" : "人气榜手动加入观察"),
    key_observe_price: systemParams.key_observe_price,
    invalid_condition: systemParams.invalid_condition,
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
    const closes = rows.map((row) => Number(row.close || 0));
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
        { type: "category", data: dates, boundaryGap: true, axisLabel: { fontSize: 10, interval: Math.max(1, Math.floor(rows.length / 6)) } },
        { type: "category", data: dates, gridIndex: 1, axisLabel: { show: false } },
        { type: "category", data: dates, gridIndex: 2, axisLabel: { fontSize: 10, interval: Math.max(1, Math.floor(rows.length / 6)) } },
      ],
      yAxis: [
        { type: "value", scale: true, axisLabel: { fontSize: 10 } },
        { type: "value", gridIndex: 1, axisLabel: { fontSize: 10 } },
        { type: "value", gridIndex: 2, scale: true, axisLabel: { fontSize: 10 } },
      ],
      dataZoom: [{ type: "inside", xAxisIndex: [0, 1, 2] }],
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
        {
          name: "MACD",
          type: "bar",
          data: macd.hist,
          xAxisIndex: 2,
          yAxisIndex: 2,
          itemStyle: { color: (params: any) => (params.data >= 0 ? "#e34d59" : "#00b578") },
        },
        {
          name: "DIF",
          type: "line",
          data: macd.dif,
          xAxisIndex: 2,
          yAxisIndex: 2,
          symbol: "none",
          lineStyle: { width: 1, color: "#4b63ee" },
        },
        {
          name: "DEA",
          type: "line",
          data: macd.dea,
          xAxisIndex: 2,
          yAxisIndex: 2,
          symbol: "none",
          lineStyle: { width: 1, color: "#f59e0b" },
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
    return <div style={{ height: 350, display: "grid", placeItems: "center" }}><SpinLoading /></div>;
  }
  if (!rows.length) {
    return <div style={{ height: 120, display: "grid", placeItems: "center", color: "#8792a8" }}>暂无K线数据</div>;
  }
  return <div ref={chartRef} style={{ width: "100%", height: 350 }} />;
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
  const [hotStocksRaw, setHotStocksRaw] = useState<any[]>([]);
  const [hotSectors, setHotSectors] = useState<any[]>([]);
  const [limitRows, setLimitRows] = useState<any[]>([]);
  const [limitLadderRows, setLimitLadderRows] = useState<any[]>([]);
  const [limitTotal, setLimitTotal] = useState(0);
  const [limitConcept, setLimitConcept] = useState("");
  const [limitLadder, setLimitLadder] = useState<number | null>(null);
  const [includeSt, setIncludeSt] = useState(false);
  const [hotPlatform, setHotPlatform] = useState("");
  const [watchCodes, setWatchCodes] = useState<Set<string>>(new Set());
  const [watchDraft, setWatchDraft] = useState<WatchDraft | null>(null);
  const [tradingSystems, setTradingSystems] = useState<TradingSystemDefinition[]>([]);
  const [systemParams, setSystemParams] = useState<TradingSystemParamDefinition[]>([]);
  const [watchSubmitting, setWatchSubmitting] = useState(false);
  const [stockViewer, setStockViewer] = useState<StockViewerState | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  function refreshWatchCodes() {
    return apiGet<any[]>("/h5/watch-pool")
      .then((items) => setWatchCodes(new Set((items || []).map((item: any) => item.stock_code))))
      .catch(() => {});
  }

  useEffect(() => {
    if (queryDate) { setTradeDate(queryDate); return; }
    apiGet<TradingSystemDefinition[]>("/h5/trading-systems")
      .then((rows) => setTradingSystems(rows || []))
      .catch(() => setTradingSystems([]));
    apiGet<string[]>("/h5/market/trading-dates")
      .then((dates) => {
        const latestDate = (dates || []).slice().sort().reverse()[0] || todayString();
        setTradeDate(latestDate);
      })
      .catch(() => {
        setTradeDate(todayString());
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!watchDraft?.trading_system) {
      setSystemParams([]);
      return;
    }
    apiGet<TradingSystemParamDefinition[]>(`/h5/trading-systems/${watchDraft.trading_system}/params`)
      .then((rows) => setSystemParams(rows || []))
      .catch(() => setSystemParams([]));
  }, [watchDraft?.trading_system]);

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
  }, [tradeDate, refreshKey]);

  useEffect(() => {
    if (!tradeDate) return;
    apiGet<any>(`/h5/market/hot-stocks?trade_date=${tradeDate}&page_size=1000`)
      .then((hot) => setHotStocksRaw(hot.list || hot || []))
      .catch(() => setHotStocksRaw([]));
  }, [tradeDate]);

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

  const hotAggregated = useMemo(() => aggregateHotStocks(hotStocksRaw), [hotStocksRaw]);
  const hotPlatforms = useMemo(() => hotPlatformOptions(hotStocksRaw), [hotStocksRaw]);

  const hotDisplayRows = useMemo(() => {
    if (!hotAggregated.length) return [];
    if (!hotPlatform) return sortHotComposite(hotAggregated).slice(0, 10);
    return filterAndSortHotByPlatform(hotAggregated, hotPlatform).slice(0, 10);
  }, [hotAggregated, hotPlatform]);

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
    const entries = Object.entries(counts).sort((a, b) => b[1] - a[1]);
    // Only show concepts with more than 2 stocks, and exclude "其他"/"未分类"
    const filtered = entries.filter(([n, count]) => count > 2 && n !== "其他" && n !== "未分类");
    return filtered.slice(0, 15);
  }, [limitRows, includeSt]);

  const conceptDescription = useMemo(() => {
    if (!limitConcept) return "";
    const sector = hotSectors.find((s) => s.name === limitConcept);
    return sector?.reason || "";
  }, [hotSectors, limitConcept]);

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

  function openStockViewer(type: StockViewerState["type"], rows: any[], index = 0) {
    const validRows = rows.filter((row) => row?.stock_code);
    if (!validRows.length) return;
    setStockViewer({ type, rows: validRows, index: Math.min(Math.max(index, 0), validRows.length - 1) });
  }

  function changeStockViewerIndex(delta: number) {
    setStockViewer((viewer) => {
      if (!viewer) return viewer;
      const nextIndex = Math.min(Math.max(viewer.index + delta, 0), viewer.rows.length - 1);
      return { ...viewer, index: nextIndex };
    });
  }

  const availableTradingSystemOptions = useMemo(() => {
    if (!tradingSystems.length) return tradingSystemOptions;
    return tradingSystems.map((item) => ({ label: item.system_name, value: item.system_code }));
  }, [tradingSystems]);

  function updateWatchParam(paramKey: string, value: string) {
    if (!watchDraft) return;
    const nextParams = { ...watchDraft.system_params_json, [paramKey]: value };
    setWatchDraft({
      ...watchDraft,
      system_params_json: nextParams,
      key_observe_price: paramKey === "key_observe_price" ? value : watchDraft.key_observe_price,
      invalid_condition: paramKey === "invalid_condition" ? value : watchDraft.invalid_condition,
    });
  }

  function changeWatchSystem(systemCode: string) {
    if (!watchDraft) return;
    const nextParams = {
      key_observe_price: watchDraft.key_observe_price,
      invalid_condition: watchDraft.invalid_condition,
    };
    setWatchDraft({
      ...watchDraft,
      trading_system: systemCode,
      system_params_json: nextParams,
    });
  }

  function addWatchFromMarket(item: any, sourceType: "hot_stock" | "limit_up") {
    setWatchDraft(buildWatchDraft(item, sourceType));
  }

  async function submitWatchDraft() {
    if (!watchDraft) return;
    const missingParam = systemParams.find((param) => param.required && !String(watchDraft.system_params_json[param.param_key] ?? "").trim());
    if (!watchDraft.trading_system || !watchDraft.entry_reason.trim() || missingParam) {
      Toast.show({ content: missingParam ? `请填写${missingParam.param_name}` : "请补全交易体系和入选理由" });
      return;
    }
    const keyObservePrice = watchDraft.system_params_json.key_observe_price || watchDraft.key_observe_price;
    const invalidCondition = watchDraft.system_params_json.invalid_condition || watchDraft.invalid_condition;
    setWatchSubmitting(true);
    try {
      await apiPost("/h5/watch-pool", {
        stock_code: watchDraft.stock_code,
        stock_name: watchDraft.stock_name,
        sector_name: watchDraft.sector_name,
        labels: watchDraft.entry_source_type === "limit_up" ? ["relay"] : ["popularity"],
        entry_source: watchDraft.entry_source_type === "limit_up" ? "limit_up" : "hot_stock",
        trading_system_code: watchDraft.trading_system,
        trading_system: watchDraft.trading_system,
        system_params_json: watchDraft.system_params_json,
        system_stage: "observe",
        entry_reason: watchDraft.entry_reason,
        reason: watchDraft.entry_reason,
        key_observe_price: keyObservePrice ? Number(keyObservePrice) : undefined,
        invalid_condition: invalidCondition,
        risk_tags: watchDraft.risk_tags,
        user_remark: watchDraft.user_remark,
      });
      const code = watchDraft.stock_code;
      setWatchDraft(null);
      setWatchCodes((prev) => new Set(prev).add(code));
      Toast.show({ content: "已加入自选观察" });
    } catch {
      Toast.show({ content: "添加自选失败，请检查填写信息" });
    } finally {
      setWatchSubmitting(false);
    }
  }

  const viewerItem = stockViewer ? stockViewer.rows[stockViewer.index] : null;
  const viewerReason = viewerItem
    ? stockViewer?.type === "limit_up"
      ? viewerItem.limit_reason || viewerItem.reason || viewerItem.raw_reason || "暂无入榜原因"
      : viewerItem.hot_reason || viewerItem.raw_reason || viewerItem.reason || viewerItem.up_reason || "暂无入榜原因"
    : "";
  const viewerXueqiuUrl = viewerItem ? toXueqiuUrl(viewerItem.stock_code) : "";

  return (
    <PageShell
      title="市场"
      dateText={tradeDate}
      onDateClick={() => setPickerVisible(true)}
      onPrevDate={() => changeTradeDate(shiftTradeDate(tradeDate, -1))}
      onNextDate={() => changeTradeDate(shiftTradeDate(tradeDate, 1))}
      segments={[
        { key: "overview", label: "大盘", onClick: () => setTab("overview") },
        { key: "hot", label: "人气榜", onClick: () => setTab("hot") },
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
                <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                  <button
                    type="button"
                    onClick={() => setHotPlatform("")}
                    style={{
                      padding: "4px 10px",
                      border: `1px solid ${!hotPlatform ? "#5570ff" : "#ddd"}`,
                      borderRadius: 12,
                      fontSize: 11,
                      fontWeight: 700,
                      background: !hotPlatform ? "#eef2ff" : "#fff",
                      color: !hotPlatform ? "#5570ff" : "#999",
                    }}
                  >
                    综合
                  </button>
                  {hotPlatforms.map((p) => (
                    <button key={p.key} type="button" onClick={() => setHotPlatform(hotPlatform === p.key ? "" : p.key)}
                    style={{
                      padding: "4px 10px",
                      border: `1px solid ${hotPlatform === p.key ? "#5570ff" : "#ddd"}`,
                      borderRadius: 12,
                      fontSize: 11,
                      fontWeight: 700,
                      background: hotPlatform === p.key ? "#eef2ff" : "#fff",
                      color: hotPlatform === p.key ? "#5570ff" : "#999",
                    }}>{p.label}</button>
                  ))}
                  <span style={{ alignSelf: "center", color: "#98a2b3", fontSize: 11, fontWeight: 700 }}>
                    {hotStocksRaw.length}条 / {hotPlatforms.length}平台
                  </span>
                </div>
                <div style={{ display: "flex", gap: 6, marginLeft: "auto" }}>
                {hotDisplayRows.length ? (
                  <button
                  type="button"
                  onClick={() => openStockViewer("hot_stock", hotDisplayRows, 0)}
                  style={{
                    padding: "4px 10px",
                    border: "1px solid #ddd",
                    borderRadius: 12,
                    fontSize: 11,
                    fontWeight: 700,
                    background: "#fff",
                    color: "#999",
                  }}
                > K线
                </button>
                ) : null}
                </div>
              </div>
              {hotStocksRaw.length ? (
                <div className="stack-list">
                  {hotDisplayRows.map((item, index) => (
                    <div key={item.stock_code} className="row-card row-card-action" onClick={() => openStockViewer("hot_stock", hotDisplayRows, index)} style={{ cursor: "pointer" }}>
                      <div style={{ minWidth: 0, flex: 1 }}>
                        <strong style={{ display: "block", lineHeight: 1.45 }}>
                          {item.stock_name}{getStockPriceInfo(item)}
                        </strong>
                        <p style={{ margin: "6px 0 0", color: "#73809a", fontSize: 12, lineHeight: 1.5 }}>
                          {item.composite_prime_score} {item.platform_rank_line}
                        </p>
                        <p style={{ margin: "4px 0 0", color: "#73809a", fontSize: 12, lineHeight: 1.5 }}>
                          {item.sector_name || item.board_name || "未分类"}
                        </p>
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
            </>
          )}

          {tab === "limit" && (
            <article className="feature-card">
                <div className="card-head">
                  <div className="card-headline">
                    <span className="icon-badge">{includeSt ? limitTotal : limitTotal - limitRows.filter((row) => (row.stock_name || "").includes("ST")).length}</span>
                  </div>
                  <div style={{ display: "flex", gap: 6 }}>
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
                    <button
                      type="button"
                      onClick={() => openStockViewer("limit_up", filteredLimitRows, 0)}
                      style={{
                        padding: "4px 10px",
                        border: "1px solid #ddd",
                        borderRadius: 12,
                        fontSize: 11,
                        fontWeight: 700,
                        background: "#fff",
                        color: "#999",
                      }}
                    > 查看全部
                    </button>
                  </div>
                </div>
              <div style={{ display: "flex", gap: 4, overflowX: "auto", paddingBottom: 4, flexWrap: "wrap" }}>
                {conceptButtons.map(([name, count]) => (
                  <button key={name} type="button" onClick={() => setLimitConcept(limitConcept === name ? "" : name)} style={{ flex: "0 0 auto", padding: "4px 10px", border: 0, borderRadius: 12, fontSize: 12, fontWeight: 600, background: limitConcept === name ? "linear-gradient(135deg, #5570ff, #4052d2)" : "#f4f6fb", color: limitConcept === name ? "#fff" : "#64748b" }}>{name} {count}</button>
                ))}
              </div>
              {conceptDescription && (
                <div style={{ padding: "6px 10px", borderRadius: 10, background: "#fff4f4", fontSize: 12, color: "#c0392b", lineHeight: 1.5, marginBottom: 4 }}>{conceptDescription}</div>
              )}
              {!limitConcept && (
              <div style={{ display: "flex", gap: 6, overflowX: "auto", paddingBottom: 4, marginBottom: 8 }}>
                {ladderHeights.map((height) => ( 
                  height < 2 ? null : (
                    <button key={String(height)} type="button" onClick={() => setLimitLadder(limitLadder === height ? null : height)} style={{ flex: "0 0 auto", padding: "6px 12px", border: 0, borderRadius: 14, fontSize: 13, fontWeight: 700, background: limitLadder === height ? "linear-gradient(135deg, #e34d59, #c0392b)" : "#f4f6fb", color: limitLadder === height ? "#fff" : "#e34d59" }}>{height}板 {ladderCounts[height]}</button>
                  )
                ))}
              </div>
              )}
              {filteredLimitRows.length ? (
                <div className="stack-list">
                  {filteredLimitRows.map((item, index) => (
                    <div key={item.stock_code} className="row-card row-card-action" style={{ padding: "10px 12px", cursor: "pointer" }} onClick={() => openStockViewer("limit_up", filteredLimitRows, index)}>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <strong>
                          {item.stock_name}{getStockPriceInfo(item)}
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
        visible={!!stockViewer}
        onMaskClick={() => setStockViewer(null)}
        bodyStyle={{
          borderTopLeftRadius: 28,
          borderTopRightRadius: 28,
          padding: 0,
          height: "82vh",
          overflow: "hidden",
          background: "linear-gradient(180deg, #f7f9ff 0%, #ffffff 38%)",
        }}
      >
        {stockViewer && viewerItem ? (
          <div style={{ display: "flex", flexDirection: "column", height: "82vh" }}>
            <div style={{ padding: "6px 14px 4px" }}>
              <div style={{ width: 32, height: 4, borderRadius: 999, background: "#d9dfef", margin: "0 auto 8px" }} />
              <div style={{ display: "flex", justifyContent: "space-between", gap: 8, alignItems: "center" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <strong style={{ fontSize: 18, color: "#141d36" }}>{viewerItem.stock_name || viewerItem.stock_code}</strong>
                  <span style={{ color: "#8892a8", fontSize: 12 }}>
                    {viewerItem.sector_name || viewerItem.board_name || viewerItem.concept || viewerItem.plate_name || viewerItem.assoc_plate || ""}
                  </span>
                </div>
                <span style={{ color: "#8a94a8", fontSize: 12 }}>{stockViewer.index + 1} / {stockViewer.rows.length}</span>
              </div>
            </div>

            <div style={{ overflowY: "auto", padding: "0 18px 92px", WebkitOverflowScrolling: "touch" }}>
              <div style={{ borderRadius: 24, background: "#fff", boxShadow: "0 12px 36px rgba(31, 43, 77, 0.08)", overflow: "hidden" }}>
                <div style={{ padding: "12px 14px 0", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <strong style={{ color: "#18223d", fontSize: 16 }}>日K线</strong>
                  <span style={{ color: "#8a94a8", fontSize: 12 }}>日K线</span>
                </div>
                <LimitUpKlineChart stockCode={viewerItem.stock_code} />
              </div>

              <div style={{ marginTop: 12, borderRadius: 22, background: "#fff", padding: 14, boxShadow: "0 10px 30px rgba(31, 43, 77, 0.07)" }}>
                  <div style={{ borderRadius: 12, background: "#fff4f4", padding: "10px 12px", lineHeight: 1.6 }}>
                    <span style={{ fontSize: 11, color: "#c0392b", fontWeight: 700 }}>
                      {stockViewer.type === "limit_up" ? "涨停原因" : "入榜原因"}
                    </span>
                    <div style={{ fontSize: 14, color: "#c0392b", marginTop: 4, wordBreak: "break-word" }}>{viewerReason}</div>
                  </div>
              </div>
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
              <div style={{ display: "grid", gridTemplateColumns: "0.82fr 0.82fr 1fr 0.92fr", gap: 8 }}>
                <Button block disabled={stockViewer.index === 0} onClick={() => changeStockViewerIndex(-1)} style={{ borderRadius: 14 }}>上一个</Button>
                <Button block disabled={stockViewer.index >= stockViewer.rows.length - 1} onClick={() => changeStockViewerIndex(1)} style={{ borderRadius: 14 }}>下一个</Button>
                {watchCodes.has(viewerItem.stock_code) ? (
                  <Button block disabled style={{ borderRadius: 14 }}>已观察</Button>
                ) : (
                  <Button block color="primary" onClick={() => { addWatchFromMarket(viewerItem, stockViewer.type); }} style={{ borderRadius: 14, fontWeight: 800 }}>+观察</Button>
                )}
                <Button block fill="outline" onClick={() => { if (viewerXueqiuUrl) window.open(viewerXueqiuUrl, "_blank"); }} style={{ borderRadius: 14 }}>雪球</Button>
              </div>
            </div>
          </div>
        ) : null}
      </Popup>

      <Popup
        visible={!!watchDraft}
        onMaskClick={() => setWatchDraft(null)}
        bodyStyle={{
          borderTopLeftRadius: 28,
          borderTopRightRadius: 28,
          padding: 0,
          maxHeight: "92vh",
          overflow: "hidden",
          background: "linear-gradient(180deg, #f7f9ff 0%, #ffffff 34%)",
        }}
      >
        {watchDraft && (
          <div style={{ display: "flex", flexDirection: "column", maxHeight: "92vh" }}>
            <div style={{ padding: "10px 18px 8px" }}>
              <div style={{ width: 42, height: 5, borderRadius: 999, background: "#d9dfef", margin: "0 auto 12px" }} />
              <div style={{ display: "flex", justifyContent: "space-between", gap: 14, alignItems: "flex-start" }}>
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontSize: 22, fontWeight: 900, color: "#141d36", letterSpacing: "-0.02em" }}>{watchDraft.stock_name}</div>
                  <div style={{ marginTop: 5, color: "#6b7894", fontSize: 13 }}>{watchDraft.stock_code}</div>
                </div>
                <span
                  style={{
                    flexShrink: 0,
                    borderRadius: 999,
                    padding: "8px 12px",
                    fontSize: 12,
                    fontWeight: 800,
                    color: "#4257d8",
                    background: "#eef2ff",
                  }}
                >
                  {watchDraft.entry_source_type === "limit_up" ? "涨停榜来源" : "人气榜来源"}
                </span>
              </div>
            </div>

            <div style={{ overflowY: "auto", padding: "0 18px 14px", WebkitOverflowScrolling: "touch" }}>
              <div
                style={{
                  borderRadius: 22,
                  background: "linear-gradient(135deg, #1d2948 0%, #4d63ed 100%)",
                  padding: 15,
                  color: "#fff",
                  boxShadow: "0 14px 34px rgba(66, 87, 216, 0.24)",
                }}
              >
                <div style={{ display: "grid", gap: 10, fontSize: 12, opacity: 0.9 }}>
                  <div>
                    <div style={{ opacity: 0.68 }}>来源</div>
                    <strong style={{ display: "block", marginTop: 3, fontSize: 14 }}>{watchDraft.entry_source_type === "limit_up" ? "涨停榜" : "人气榜"}</strong>
                  </div>
                  <div>
                    <div style={{ opacity: 0.68 }}>系统推荐</div>
                    <strong style={{ display: "block", marginTop: 3, fontSize: 15 }}>{tradingSystemLabel(recommendTradingSystem(watchDraft.raw_item, watchDraft.entry_source_type), tradingSystems)}</strong>
                  </div>
                </div>
                <div style={{ marginTop: 12, borderTop: "1px solid rgba(255,255,255,0.18)", paddingTop: 10, fontSize: 13, lineHeight: 1.55 }}>
                  {watchDraft.entry_reason || "暂无来源原因"}
                </div>
              </div>

              <section style={{ marginTop: 14, display: "grid", gap: 12 }}>
                <div style={{ borderRadius: 22, background: "#fff", padding: 14, boxShadow: "0 10px 30px rgba(31, 43, 77, 0.07)" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 10 }}>
                    <strong style={{ color: "#18223d", fontSize: 16 }}>交易系统</strong>
                    <span style={{ color: "#8a94a8", fontSize: 12 }}>请选择一种观察框架</span>
                  </div>
                  <Selector
                    columns={3}
                    options={availableTradingSystemOptions}
                    value={[watchDraft.trading_system]}
                    onChange={(value) => changeWatchSystem(value[0] as string)}
                  />
                </div>

                <div style={{ borderRadius: 22, background: "#fff", padding: 14, boxShadow: "0 10px 30px rgba(31, 43, 77, 0.07)", display: "grid", gap: 12 }}>
                  <FieldTitle title="入选理由" required hint="为什么值得进入观察池" />
                  <TextArea
                    value={watchDraft.entry_reason}
                    autoSize={{ minRows: 2, maxRows: 4 }}
                    placeholder="例如：热榜持续靠前，板块有承接，等待低风险买点"
                    onChange={(value) => setWatchDraft({ ...watchDraft, entry_reason: value })}
                    style={{ "--font-size": "14px", "--color": "#1d2948", background: "#f7f9ff", borderRadius: 14, padding: 10 } as CSSProperties}
                  />

                  <div style={{ display: "grid", gap: 10 }}>
                    {systemParams.length ? systemParams.map((param) => (
                      <div key={param.param_key} style={{ display: "grid", gap: 8 }}>
                        <FieldTitle title={param.param_name} required={param.required} hint={param.description} />
                        {param.param_type === "text" ? (
                          <TextArea
                            value={watchDraft.system_params_json[param.param_key] || ""}
                            autoSize={{ minRows: 2, maxRows: 4 }}
                            placeholder={param.param_name}
                            onChange={(value) => updateWatchParam(param.param_key, value)}
                            style={{ "--font-size": "14px", "--color": "#1d2948", background: "#f7f9ff", borderRadius: 14, padding: 10 } as CSSProperties}
                          />
                        ) : (
                          <Input
                            type={param.param_type === "number" ? "number" : "text"}
                            value={watchDraft.system_params_json[param.param_key] || ""}
                            placeholder={param.param_name}
                            onChange={(value) => updateWatchParam(param.param_key, value)}
                            style={{ "--font-size": "15px", "--color": "#1d2948", background: "#f7f9ff", borderRadius: 14, padding: "10px 12px" } as CSSProperties}
                          />
                        )}
                      </div>
                    )) : (
                      <div style={{ color: "#8a94a8", fontSize: 13 }}>该交易体系暂无参数定义。</div>
                    )}
                  </div>
                </div>

                <div style={{ borderRadius: 22, background: "#fff", padding: 14, boxShadow: "0 10px 30px rgba(31, 43, 77, 0.07)" }}>
                  <FieldTitle title="风险标签" hint="可多选，帮助后续复盘" />
                  <div style={{ marginTop: 10 }}>
                    <Selector
                      multiple
                      columns={3}
                      options={riskTagOptions}
                      value={watchDraft.risk_tags}
                      onChange={(value) => setWatchDraft({ ...watchDraft, risk_tags: value as string[] })}
                    />
                  </div>
                </div>

                <div style={{ borderRadius: 22, background: "#fff", padding: 14, boxShadow: "0 10px 30px rgba(31, 43, 77, 0.07)", display: "grid", gap: 10 }}>
                  <FieldTitle title="用户备注" hint="可选" />
                  <TextArea
                    value={watchDraft.user_remark}
                    autoSize={{ minRows: 2, maxRows: 4 }}
                    placeholder="记录你的观察计划、情绪提醒或复盘线索"
                    onChange={(value) => setWatchDraft({ ...watchDraft, user_remark: value })}
                    style={{ "--font-size": "14px", "--color": "#1d2948", background: "#f7f9ff", borderRadius: 14, padding: 10 } as CSSProperties}
                  />
                </div>

                <div style={{ borderRadius: 18, padding: "12px 14px", background: "#fff8e8", color: "#8a641f", fontSize: 12, lineHeight: 1.6 }}>
                  加入自选仅用于后续观察和信号提醒，仅作为交易辅助，请结合个人交易规则确认。
                </div>
              </section>
            </div>

            <div
              style={{
                padding: "12px 18px calc(12px + env(safe-area-inset-bottom))",
                background: "rgba(255,255,255,0.92)",
                borderTop: "1px solid rgba(226,232,240,0.9)",
                boxShadow: "0 -10px 28px rgba(31,43,77,0.08)",
                backdropFilter: "blur(14px)",
              }}
            >
              <div style={{ display: "grid", gridTemplateColumns: "0.9fr 1.4fr", gap: 10 }}>
                <Button block style={{ borderRadius: 16 }} onClick={() => setWatchDraft(null)}>取消</Button>
                <Button block color="primary" loading={watchSubmitting} onClick={submitWatchDraft} style={{ borderRadius: 16, fontWeight: 800 }}>
                  加入自选观察
                </Button>
              </div>
            </div>
          </div>
        )}
      </Popup>

    </PageShell>
  );
}

