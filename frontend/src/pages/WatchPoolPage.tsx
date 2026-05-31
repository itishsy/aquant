import { useEffect, useMemo, useState } from "react";
import { Button, Dialog, ErrorBlock, Input, Popup, Selector, SpinLoading, TextArea, Toast } from "antd-mobile";
import { apiDelete, apiGet, apiPost, apiPut } from "../api/client";
import { PageShell } from "../components/PageShell";
import { StockLink, toXueqiuUrl } from "../components/StockLink";
import { KlineChart } from "../components/StockDetailPopup";


const ASSISTANT_NOTE = "仅作为交易辅助，请结合个人交易规则确认。";

const tradingSystemOptions = [
  { label: "全部体系", value: "" },
  { label: "平台突破", value: "platform_breakout" },
  { label: "上涨趋势", value: "uptrend" },
  { label: "涨停接力", value: "limit_relay" },
  { label: "追涨接力", value: "relay" },
  { label: "超跌反弹", value: "oversold_rebound" },
];

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

type DetailKind = "watch" | "signal" | "trade";
type DetailTarget = {
  kind: DetailKind;
  item: any;
} | null;

const lifecycleOptions = [
  { label: "全部状态", value: "" },
  { label: "观察中", value: "watching" },
  { label: "已出信号", value: "signal_generated" },
  { label: "等待买点", value: "waiting_buy_point" },
  { label: "买入待确认", value: "buy_pending_confirm" },
  { label: "交易中", value: "trading" },
  { label: "卖出待处理", value: "sell_signal_pending" },
  { label: "卖出延后", value: "sell_delayed" },
  { label: "待复盘", value: "pending_review" },
  { label: "已失效", value: "invalid" },
  { label: "黑名单", value: "blacklist" },
  { label: "已剔除", value: "removed" },
];

const signalTypeLabels: Record<string, string> = { buy: "买入观察信号", sell: "卖出观察提醒", risk: "风险提醒" };
const buyPointLabels: Record<string, string> = {
  b15_divergence: "B15 底背离买点",
  support_buy: "支撑买点",
  platform_breakout_confirm: "平台突破确认买点",
};
const riskTagLabels: Record<string, string> = {
  high_position: "高位",
  weak_seal: "封板弱",
  abnormal_volume: "放量异常",
  sector_weak: "板块转弱",
  break_support: "跌破支撑",
};
const emotionOptions = [
  { label: "冷静", value: "calm" },
  { label: "犹豫", value: "hesitant" },
  { label: "冲动", value: "impulsive" },
  { label: "害怕踏空", value: "fearful" },
];

function labelOf(options: { label: string; value: string }[], value?: string) {
  return options.find((item) => item.value === value)?.label || value || "-";
}

function formatMoney(value: unknown) {
  const num = Number(value);
  if (!Number.isFinite(num)) return "-";
  return num.toFixed(2);
}

function statusTone(status?: string) {
  if (["trading", "buy_pending_confirm", "sell_signal_pending"].includes(status || "")) return { color: "#e34d59", bg: "#fff1f1" };
  if (["observe_risk_pending", "observe_invalid_pending", "observe_remove_pending"].includes(status || "")) return { color: "#e37318", bg: "#fff7e8" };
  if (["invalid", "removed", "blacklist"].includes(status || "")) return { color: "#7b879c", bg: "#eef2f7" };
  if (["signal_generated", "waiting_buy_point"].includes(status || "")) return { color: "#4b63ee", bg: "#eef2ff" };
  return { color: "#00a870", bg: "#eefaf4" };
}

function MiniStat({ label, value, tone = "#22375c" }: { label: string; value: any; tone?: string }) {
  return (
    <div style={{ borderRadius: 18, background: "rgba(255,255,255,0.72)", padding: "11px 12px", boxShadow: "inset 0 0 0 1px rgba(226,232,240,0.65)" }}>
      <div style={{ color: "#7b879c", fontSize: 12, marginBottom: 4 }}>{label}</div>
      <strong style={{ color: tone, fontSize: 19, lineHeight: 1 }}>{value ?? "-"}</strong>
    </div>
  );
}

function StatusPill({ label, status }: { label: string; status?: string }) {
  const tone = statusTone(status);
  return (
    <span style={{ borderRadius: 999, background: tone.bg, color: tone.color, padding: "6px 10px", fontSize: 12, fontWeight: 800, whiteSpace: "nowrap" }}>
      {label}
    </span>
  );
}

function InfoLine({ label, value }: { label: string; value: any }) {
  if (value === undefined || value === null || value === "") return null;
  return (
    <div style={{ display: "grid", gap: 2 }}>
      <span style={{ color: "#98a2b3", fontSize: 11, fontWeight: 700 }}>{label}</span>
      <span style={{ color: "#32415f", fontSize: 13, lineHeight: 1.45 }}>{value}</span>
    </div>
  );
}

function nextAction(item: any) {
  if (item.next_action) return item.next_action;
  const status = item.status;
  if (!item.monitor_enabled || item.signal_enabled === false) return "监控关闭，等待手动开启";
  if (status === "watching") return "等待策略信号触发";
  if (status === "signal_generated") return "复核信号质量";
  if (status === "waiting_buy_point") return "等待买点确认";
  if (status === "buy_pending_confirm") return "人工确认是否记录交易";
  if (status === "trading") return "跟踪卖出、止损、风险提醒";
  if (status === "pending_review") return "填写单笔交易复盘";
  if (status === "invalid") return "归档或剔除";
  return "继续观察";
}

function coreParamText(item: any) {
  const params = item.system_params_json || {};
  const parts = [
    params.platform_upper_price != null ? `箱体上沿 ${params.platform_upper_price}` : "",
    params.platform_support_price != null ? `平台支撑 ${params.platform_support_price}` : "",
    params.key_observe_price != null ? `观察价 ${params.key_observe_price}` : "",
    params.auto_remove_price != null ? `剔除价 ${params.auto_remove_price}` : "",
  ].filter(Boolean);
  return parts.join(" / ");
}

function ruleListText(value: any) {
  const items = Array.isArray(value) ? value : [];
  return items.length
    ? items.map((item) => typeof item === "string" ? item : (item.display_name || item.rule_name || item.rule_code || "-")).join(" / ")
    : "-";
}

function signalRuleText(item: any) {
  return item.rule_display_name || item.rule_name || buyPointLabels[item.buy_point_type] || item.rule_code || item.buy_point_type || "-";
}

function tradingSystemText(item: any) {
  return item.trading_system_name || labelOf(tradingSystemOptions, item.trading_system_code || item.trading_system);
}

function shortError(value?: string | null) {
  if (!value) return "";
  return value.length > 48 ? `${value.slice(0, 48)}...` : value;
}

function notificationStatusText(item: any) {
  if (item.notification_sent) return "邮件已发送";
  if (item.notification_error) return `邮件发送失败：${shortError(item.notification_error)}`;
  return "邮件待发送或不需要提醒";
}

function signalStatusText(status?: string) {
  const labels: Record<string, string> = {
    buy_pending_confirm: "买点待确认",
    observe_risk_pending: "观察风险待确认",
    observe_invalid_pending: "观察失效待确认",
    observe_remove_pending: "观察剔除待确认",
    sell_signal_pending: "卖点待处理",
    stop_loss_pending: "止损待处理",
    confirmed_buy: "已确认买入",
    ignored: "已忽略",
    false_positive: "误报",
    invalid: "已失效",
    abandoned: "已放弃",
  };
  return labels[status || ""] || status || "-";
}

function rulePreviewConclusionText(preview: any) {
  if (!preview) return "";
  if (preview.would_generate_signal) return "满足买点条件，若正式扫描会生成买点信号";
  if (!preview.required_passed) return "必要条件未满足，暂不会生成信号";
  if (!preview.buy_signal_triggered) return "必要条件满足，但买点信号未触发";
  return "暂不会生成信号";
}

export function WatchPoolPage() {
  const [tab, setTab] = useState("watch");
  const [items, setItems] = useState<any[]>([]);
  const [signals, setSignals] = useState<any[]>([]);
  const [trades, setTrades] = useState<any[]>([]);
  const [executions, setExecutions] = useState<any[] | null>(null);
  const [executionTrade, setExecutionTrade] = useState<any | null>(null);
  const [watchSummary, setWatchSummary] = useState<any>({});
  const [signalSummary, setSignalSummary] = useState<any>({});
  const [tradeSummary, setTradeSummary] = useState<any>({});
  const [tradingSystem, setTradingSystem] = useState("");
  const [lifecycleStatus, setLifecycleStatus] = useState("");
  const [editing, setEditing] = useState<any | null>(null);
  const [tradingSystems, setTradingSystems] = useState<TradingSystemDefinition[]>([]);
  const [editSystemParams, setEditSystemParams] = useState<TradingSystemParamDefinition[]>([]);
  const [buyForm, setBuyForm] = useState<any | null>(null);
  const [sellForm, setSellForm] = useState<any | null>(null);
  const [detailTarget, setDetailTarget] = useState<DetailTarget>(null);
  const [watchDetail, setWatchDetail] = useState<any>(null);
  const [watchDetailTab, setWatchDetailTab] = useState<"detail" | "kline">("detail");
  const [watchDetailKline, setWatchDetailKline] = useState<any[]>([]);
  const [watchDetailKlineLoading, setWatchDetailKlineLoading] = useState(false);
  const [rulePreview, setRulePreview] = useState<any | null>(null);
  const [rulePreviewLoading, setRulePreviewLoading] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (tradingSystem) params.set("trading_system", tradingSystem);
      if (lifecycleStatus) params.set("status", lifecycleStatus);
      const watchPath = `/h5/watch-pool${params.toString() ? `?${params.toString()}` : ""}`;
      const [watchItems, signalItems, tradeItems, watchSum, signalSum, tradeSum] = await Promise.all([
        apiGet<any[]>(watchPath),
        apiGet<any[]>("/h5/watch-signals/recent"),
        apiGet<any[]>("/h5/watch-trades/recent"),
        apiGet<any>("/h5/watch-pool/summary"),
        apiGet<any>("/h5/watch-signals/summary"),
        apiGet<any>("/h5/watch-trades/summary"),
      ]);
      setItems(watchItems || []);
      setSignals(signalItems || []);
      setTrades(tradeItems || []);
      setWatchSummary(watchSum || {});
      setSignalSummary(signalSum || {});
      setTradeSummary(tradeSum || {});
      setError("");
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [tradingSystem, lifecycleStatus]);

  useEffect(() => {
    apiGet<TradingSystemDefinition[]>("/h5/trading-systems")
      .then((rows) => setTradingSystems(rows || []))
      .catch(() => setTradingSystems([]));
  }, []);

  useEffect(() => {
    const systemCode = editing?.trading_system_code || editing?.trading_system;
    if (!systemCode) {
      setEditSystemParams([]);
      return;
    }
    apiGet<TradingSystemParamDefinition[]>(`/h5/trading-systems/${systemCode}/params`)
      .then((rows) => setEditSystemParams(rows || []))
      .catch(() => setEditSystemParams([]));
  }, [editing?.trading_system_code, editing?.trading_system]);

  useEffect(() => {
    const code = detailTarget?.item?.stock_code || watchDetail?.stock_code;
    if (!(detailTarget || watchDetail) || watchDetailTab !== "kline" || !code) return;
    setWatchDetailKlineLoading(true);
    apiGet<any[]>(`/h5/market/stocks/${encodeURIComponent(code)}/kline-daily?limit=100`)
      .then((rows) => setWatchDetailKline(rows || []))
      .catch(() => setWatchDetailKline([]))
      .finally(() => setWatchDetailKlineLoading(false));
  }, [detailTarget?.item?.stock_code, watchDetail?.stock_code, watchDetailTab]);

  const buySignals = useMemo(() => signals.filter((item) => item.signal_type === "buy"), [signals]);
  const riskSignals = useMemo(() => signals.filter((item) => item.signal_type !== "buy"), [signals]);
  const pendingTradeSignals = useMemo(
    () => signals.filter((item) => item.related_trade_id && ["sell_signal_pending", "stop_loss_pending"].includes(item.signal_status)),
    [signals]
  );
  const watchingItems = useMemo(() => items.filter((i) => i.status === "watching" || i.status === "观察中"), [items]);
  const todayStr = new Date().toISOString().slice(0, 10);
  const todayNew = useMemo(() => items.filter((item) => String(item.created_at || "").slice(0, 10) === todayStr).length, [items, todayStr]);
  const todaySignals = useMemo(() => signals.filter((s) => (s.trigger_date || "").slice(0, 10) === todayStr).length, [signals, todayStr]);
  const detailItem = detailTarget?.item || watchDetail;
  const activeDetailKind: DetailKind = detailTarget?.kind || "watch";

  function closeDetail() {
    setDetailTarget(null);
    setWatchDetail(null);
    setEditing(null);
    setRulePreview(null);
    setWatchDetailKline([]);
    setWatchDetailTab("detail");
  }

  function detailPrice(item: any) {
    return item?.latest_price ?? item?.last_price ?? item?.trigger_price ?? item?.average_buy_price ?? item?.first_buy_price ?? item?.entry_price;
  }

  function detailChangePct(item: any) {
    return item?.change_pct ?? item?.pct_chg ?? item?.change_percent;
  }

  function detailStatus(item: any, kind: DetailKind) {
    if (kind === "signal") return signalStatusText(item?.signal_status);
    if (kind === "trade") return item?.trade_status || "-";
    if (item?.monitor_enabled === false || item?.signal_enabled === false) return "监控暂停";
    return labelOf(lifecycleOptions, item?.status);
  }

  function detailStage(item: any, kind: DetailKind) {
    if (kind === "signal") return signalTypeLabels[item?.signal_type] || item?.signal_type || "-";
    if (kind === "trade") return `阶段 ${item?.current_stage || "trading"}`;
    return `阶段 ${item?.system_stage || "observe"}`;
  }

  function renderDetailTags(item: any, kind: DetailKind) {
    return (
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
        <StatusPill label={tradingSystemText(item)} status={kind === "trade" ? "trading" : item?.status || item?.signal_status} />
        <StatusPill label={detailStatus(item, kind)} status={item?.status || item?.signal_status || item?.trade_status} />
        <StatusPill label={detailStage(item, kind)} status={kind === "signal" ? item?.signal_status : item?.system_stage || item?.current_stage} />
      </div>
    );
  }


  function signalKindText(item: any) {
    if (item?.rule_type === "stop_loss" || item?.signal_status === "stop_loss_pending") return "止损";
    if (item?.signal_type === "buy") return "买点";
    if (item?.signal_type === "sell") return "卖点";
    if (["invalid_signal", "remove_signal"].includes(item?.rule_type) || String(item?.signal_status || "").includes("invalid")) return "风险/失效";
    if (item?.signal_type === "risk") return "风险";
    return signalTypeLabels[item?.signal_type] || item?.signal_type || "-";
  }

  function signalSnapshot(item: any) {
    const snapshot = item?.snapshot_json || item?.raw_snapshot || {};
    if (typeof snapshot === "string") {
      try { return JSON.parse(snapshot); } catch { return {}; }
    }
    return snapshot || {};
  }

  function boolText(value: any) {
    if (value === true) return "是";
    if (value === false) return "否";
    return value;
  }

  function klineCountText(snapshot: any) {
    const barCount = snapshot.bar_count ?? snapshot.freshness?.bar_count;
    const requiredBars = snapshot.required_bars ?? snapshot.freshness?.required_bars;
    if (barCount == null && requiredBars == null) return undefined;
    return String(barCount ?? "-") + " / " + String(requiredBars ?? "-");
  }


  function latestPendingTradeSignal(trade: any) {
    const candidates = signals
      .filter((signal) => signal.related_trade_id === trade.trade_id && ["sell_signal_pending", "stop_loss_pending"].includes(signal.signal_status))
      .sort((a, b) => String(b.trigger_time || b.trigger_date || "").localeCompare(String(a.trigger_time || a.trigger_date || "")));
    return candidates[0];
  }

  function tradeNextAction(item: any, pendingSignal?: any) {
    if (pendingSignal?.signal_status === "stop_loss_pending") return "出现止损提醒，请人工确认是否退出";
    if (pendingSignal?.signal_status === "sell_signal_pending") return "出现卖点提醒，请人工确认是否卖出或继续持有";
    if (["open", "holding"].includes(item?.trade_status)) return "继续按卖点/止损规则监控，等待人工确认";
    if (item?.trade_status === "closed") return "交易已结束，等待复盘";
    return item?.next_action || "查看交易状态并按计划处理";
  }

  function tradeSignalText(signal?: any) {
    if (!signal) return "暂无待处理信号";
    return [signalKindText(signal), signalRuleText(signal), signalStatusText(signal.signal_status), signal.trigger_price ?? "-"].join(" / ");
  }

  function emotionText(value?: string) {
    return emotionOptions.find((item) => item.value === value)?.label || value;
  }

  function renderDetailBody(item: any, kind: DetailKind) {
    if (kind === "signal") {
      const snapshot = signalSnapshot(item);
      const latestKlineTime = snapshot.latest_kline_time ?? snapshot.freshness?.latest_kline_time;
      const expectedLatestTime = snapshot.expected_latest_time ?? snapshot.freshness?.expected_latest_time;
      return (
        <>
          <div style={{ borderRadius: 16, background: "#f7f9ff", padding: 12, display: "grid", gap: 10 }}>
            <div style={{ color: "#22375c", fontSize: 14, fontWeight: 900 }}>信号判断</div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 8 }}>
              <Field label="信号类型" value={signalKindText(item)} />
              <Field label="信号状态" value={signalStatusText(item.signal_status)} />
              <Field label="触发规则" value={signalRuleText(item)} />
              <Field label="规则周期" value={item.rule_timeframe || item.timeframe || snapshot.timeframe} />
              <Field label="触发价" value={item.trigger_price} />
              <Field label="触发时间" value={item.trigger_time || item.trigger_date} />
              <Field label="邮件提醒" value={notificationStatusText(item)} />
            </div>
          </div>

          <div style={{ borderRadius: 16, background: "#f7f9ff", padding: 12, display: "grid", gap: 10 }}>
            <div style={{ color: "#22375c", fontSize: 14, fontWeight: 900 }}>触发依据</div>
            <InfoLine label="触发原因" value={item.trigger_reason || snapshot.reason || ASSISTANT_NOTE} />
            <InfoLine label="风险说明" value={item.risk_desc || snapshot.risk_desc} />
            {item.stop_loss_price != null && <InfoLine label="止损价" value={item.stop_loss_price} />}
            {item.target_price != null && <InfoLine label="目标价" value={item.target_price} />}
          </div>

          <div style={{ borderRadius: 16, background: "#f7f9ff", padding: 12, display: "grid", gap: 10 }}>
            <div style={{ color: "#22375c", fontSize: 14, fontWeight: 900 }}>数据新鲜度</div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 8 }}>
              <Field label="data_status" value={snapshot.data_status || "未记录"} />
              <Field label="latest_kline_time" value={latestKlineTime || "未记录"} />
              <Field label="expected_latest_time" value={expectedLatestTime || "未记录"} />
              <Field label="bar_count / required_bars" value={klineCountText(snapshot) || "未记录"} />
              <Field label="quote_update_time" value={snapshot.quote_update_time || "未记录"} />
              <Field label="quote_is_fresh" value={boolText(snapshot.quote_is_fresh) ?? "未记录"} />
            </div>
          </div>

          <p style={{ margin: 0, color: "#8a94a8", fontSize: 12, lineHeight: 1.55 }}>{ASSISTANT_NOTE}</p>
        </>
      );
    }

    if (kind === "trade") {
      const pendingSignal = latestPendingTradeSignal(item);
      const params = item.system_params_json || {};
      const paramText = [
        params.platform_upper_price != null ? "箱体上沿 " + params.platform_upper_price : "",
        params.platform_support_price != null ? "平台支撑位 " + params.platform_support_price : "",
        params.key_observe_price != null ? "关键观察价 " + params.key_observe_price : "",
        params.auto_remove_price != null ? "自动剔除价 " + params.auto_remove_price : "",
      ].filter(Boolean).join(" / ");
      return (
        <>
          <div style={{ borderRadius: 16, background: "#f7f9ff", padding: 12, display: "grid", gap: 10 }}>
            <div style={{ color: "#22375c", fontSize: 14, fontWeight: 900 }}>当前交易</div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 8 }}>
              <Field label="交易状态" value={item.trade_status} />
              <Field label="当前阶段" value={item.current_stage || "trading"} />
              <Field label="买入均价" value={item.average_buy_price ?? item.first_buy_price} />
              <Field label="剩余数量" value={item.remaining_amount} />
              <Field label="仓位" value={item.position_ratio != null ? formatMoney(Number(item.position_ratio) * 100) + "%" : undefined} />
              <Field label="浮动盈亏金额" value={formatMoney(item.pnl_amount)} />
              <Field label="浮动盈亏比例" value={item.pnl_ratio != null ? formatMoney(Number(item.pnl_ratio) * 100) + "%" : undefined} />
              <Field label="止损价" value={item.stop_loss_price} />
              <Field label="目标价" value={item.target_price} />
              <Field label="下一步动作" value={tradeNextAction(item, pendingSignal)} />
            </div>
          </div>

          <div style={{ borderRadius: 16, background: "#f7f9ff", padding: 12, display: "grid", gap: 10 }}>
            <div style={{ color: "#22375c", fontSize: 14, fontWeight: 900 }}>规则监控</div>
            <InfoLine label="进入交易的规则" value={item.entry_rule_display_name || item.entry_rule_name || item.entry_rule_code} />
            <InfoLine label="当前监控卖点规则" value={ruleListText(item.active_sell_rules || item.active_sell_rule_codes_json)} />
            <InfoLine label="当前监控止损规则" value={ruleListText(item.active_stop_rules || item.active_stop_rule_codes_json)} />
            <InfoLine label="最新待处理卖点/止损信号" value={tradeSignalText(pendingSignal)} />
          </div>

          <div style={{ borderRadius: 16, background: "#f7f9ff", padding: 12, display: "grid", gap: 10 }}>
            <div style={{ color: "#22375c", fontSize: 14, fontWeight: 900 }}>交易计划</div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(96px, 1fr))", gap: 8 }}>
              <Field label="首次买入时间" value={String(item.first_buy_time || item.created_at || "").slice(0, 16)} />
              <Field label="情绪状态" value={emotionText(item.emotion_state)} />
            </div>
            <InfoLine label="买入理由" value={item.buy_reason} />
            <InfoLine label="交易计划" value={item.trade_plan} />
            <InfoLine label="关联观察参数" value={paramText} />
          </div>
        </>
      );
    }

    const params = item.system_params_json || {};
    const riskText = (item.risk_tags || []).map((tag: string) => riskTagLabels[tag] || tag).join(" / ");
    return (
      <>
        <div style={{ borderRadius: 16, background: "#f7f9ff", padding: 12, display: "grid", gap: 10 }}>
          <div style={{ color: "#22375c", fontSize: 14, fontWeight: 900 }}>当前观察</div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 8 }}>
            <Field label="当前状态" value={detailStatus(item, "watch")} />
            <Field label="当前阶段" value={item.system_stage || "observe"} />
            <Field label="下一步动作" value={nextAction(item)} />
          </div>
        </div>

        <div style={{ borderRadius: 16, background: "#f7f9ff", padding: 12, display: "grid", gap: 10 }}>
          <div style={{ color: "#22375c", fontSize: 14, fontWeight: 900 }}>核心观察参数</div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 8 }}>
            <Field label="箱体上沿" value={params.platform_upper_price} />
            <Field label="平台支撑位" value={params.platform_support_price} />
            <Field label="关键观察价" value={params.key_observe_price ?? item.key_observe_price} />
            <Field label="自动剔除价" value={params.auto_remove_price ?? item.auto_remove_price} />
          </div>
        </div>

        <div style={{ borderRadius: 16, background: "#f7f9ff", padding: 12, display: "grid", gap: 10 }}>
          <div style={{ color: "#22375c", fontSize: 14, fontWeight: 900 }}>观察依据</div>
          <InfoLine label="失效条件" value={params.invalid_condition || item.invalid_condition} />
          <InfoLine label="入选理由" value={item.entry_reason} />
          <InfoLine label="风险标签" value={riskText} />
          <InfoLine label="用户备注" value={item.user_remark || item.remark} />
        </div>

        <div style={{ borderRadius: 16, background: "#f7f9ff", padding: 12, display: "grid", gap: 10 }}>
          <div style={{ color: "#22375c", fontSize: 14, fontWeight: 900 }}>补充信息</div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(96px, 1fr))", gap: 8 }}>
            <Field label="入选时间" value={String(item.created_at || "").slice(0, 10)} />
            <Field label="入选来源" value={item.entry_source || "手动"} />
            <Field label="板块" value={item.sector_name} />
          </div>
        </div>

        <p style={{ margin: 0, fontSize: 11, color: "#aaa" }}>{ASSISTANT_NOTE}</p>
      </>
    );

  }

  function Field({ label, value }: { label: string; value?: any }) {
  if (value == null || value === "" || value === "-") return null;
  return (
    <div style={{ minWidth: 0, borderRadius: 12, background: "#f7f9ff", padding: "8px 10px", fontSize: 13 }}>
      <div style={{ color: "#8a94a8", fontSize: 11, fontWeight: 800, marginBottom: 3 }}>{label}</div>
      <div style={{ color: "#263653", fontWeight: 700, wordBreak: "break-word", lineHeight: 1.45 }}>{value}</div>
    </div>
  );
}

  function openDetail(kind: DetailKind, item: any) {
    setDetailTarget({ kind, item });
    setWatchDetail(item);
    setEditing(null);
    setRulePreview(null);
    setWatchDetailTab("detail");
    setWatchDetailKline([]);
  }

  function openWatchDetail(item: any) {
    openDetail("watch", item);
  }

  const availableTradingSystemOptions = useMemo(() => {
    if (!tradingSystems.length) return tradingSystemOptions.filter((item) => item.value);
    return tradingSystems.map((item) => ({ label: item.system_name, value: item.system_code }));
  }, [tradingSystems]);

  function normalizeEditParams(item: any) {
    const params = { ...(item.system_params_json || {}) };
    if (params.key_observe_price == null && item.key_observe_price != null) params.key_observe_price = item.key_observe_price;
    if (params.auto_remove_price == null && item.auto_remove_price != null) params.auto_remove_price = item.auto_remove_price;
    if (params.invalid_condition == null && item.invalid_condition) params.invalid_condition = item.invalid_condition;
    return Object.fromEntries(Object.entries(params).map(([key, value]) => [key, value == null ? "" : String(value)]));
  }

  function updateEditParam(paramKey: string, value: string) {
    if (!editing) return;
    const nextParams = { ...(editing.system_params_json || {}), [paramKey]: value };
    setEditing({
      ...editing,
      system_params_json: nextParams,
      key_observe_price: paramKey === "key_observe_price" ? value : editing.key_observe_price,
      auto_remove_price: paramKey === "auto_remove_price" ? value : editing.auto_remove_price,
      invalid_condition: paramKey === "invalid_condition" ? value : editing.invalid_condition,
    });
  }

  function changeEditSystem(systemCode: string) {
    if (!editing) return;
    const nextParams: Record<string, string> = {};
    if (editing.key_observe_price) nextParams.key_observe_price = editing.key_observe_price;
    if (editing.auto_remove_price) nextParams.auto_remove_price = editing.auto_remove_price;
    if (editing.invalid_condition) nextParams.invalid_condition = editing.invalid_condition;
    setEditing({
      ...editing,
      trading_system: systemCode,
      trading_system_code: systemCode,
      system_params_json: nextParams,
    });
  }

  function renderEditParam(param: TradingSystemParamDefinition) {
    const value = String(editing?.system_params_json?.[param.param_key] ?? "");
    const label = `${param.param_name}${param.required ? " *" : ""}`;
    return (
      <div key={param.param_key} style={{ display: "grid", gap: 4 }}>
        <span style={{ color: "#5b6d8a", fontSize: 12, fontWeight: 700 }}>{label}</span>
        {param.param_type === "text" ? (
          <TextArea value={value} rows={2} placeholder={param.description || param.param_name} onChange={(next) => updateEditParam(param.param_key, next)} />
        ) : param.param_type === "boolean" ? (
          <Selector
            options={[{ label: "是", value: "true" }, { label: "否", value: "false" }]}
            value={[value || "false"]}
            onChange={(next) => updateEditParam(param.param_key, String(next[0] || "false"))}
          />
        ) : (
          <Input type={param.param_type === "number" ? "number" : "text"} value={value} placeholder={param.description || param.param_name} onChange={(next) => updateEditParam(param.param_key, next)} />
        )}
      </div>
    );
  }

  function buildEditSystemParams() {
    const raw = editing?.system_params_json || {};
    const booleanKeys = new Set(editSystemParams.filter((param) => param.param_type === "boolean").map((param) => param.param_key));
    return Object.fromEntries(Object.entries(raw).map(([key, value]) => [
      key,
      booleanKeys.has(key) ? value === true || value === "true" : value,
    ]));
  }

  function openEdit(item: any) {
    const systemCode = item.trading_system_code || item.trading_system || "platform_breakout";
    const params = normalizeEditParams(item);
    setEditing({
      watch_id: item.watch_id,
      stock_name: item.stock_name,
      stock_code: item.stock_code,
      trading_system: systemCode,
      trading_system_code: systemCode,
      system_params_json: params,
      entry_reason: item.entry_reason || item.reason || "",
      key_observe_price: params.key_observe_price || "",
      auto_remove_price: params.auto_remove_price || "",
      invalid_condition: params.invalid_condition || item.invalid_condition || "",
      risk_tags: item.risk_tags || [],
      user_remark: item.user_remark || item.remark || "",
      adjust_reason: "",
    });
  }

  function openBuyForm(signal: any) {
    setBuyForm({
      signal_id: signal.signal_id,
      stock_name: signal.stock_name,
      stock_code: signal.stock_code,
      buy_price: signal.trigger_price != null ? String(signal.trigger_price) : "",
      amount: "",
      position_ratio: "",
      stop_loss_price: signal.stop_loss_price != null ? String(signal.stop_loss_price) : "",
      target_price: signal.target_price != null ? String(signal.target_price) : "",
      buy_reason: signal.trigger_reason || "",
      trade_plan: "",
      emotion_state: "calm",
    });
  }

  function openSellForm(trade: any) {
    setSellForm({
      trade_id: trade.trade_id,
      stock_name: trade.stock_name,
      stock_code: trade.stock_code,
      remaining_amount: trade.remaining_amount || 0,
      sell_price: "",
      sell_reason: "manual_full_exit",
      execution_comment: "",
    });
  }

  async function saveEdit() {
    if (!editing?.adjust_reason?.trim()) {
      Toast.show({ content: "请填写调整原因" });
      return;
    }
    try {
      const missingParam = editSystemParams.find((param) => param.required && !String(editing.system_params_json?.[param.param_key] ?? "").trim());
      if (missingParam) {
        Toast.show({ content: `请填写${missingParam.param_name}` });
        return;
      }
      const keyObservePrice = editing.system_params_json?.key_observe_price || editing.key_observe_price;
      const autoRemovePrice = editing.system_params_json?.auto_remove_price || editing.auto_remove_price;
      const invalidCondition = editing.system_params_json?.invalid_condition || editing.invalid_condition;
      const systemParams = buildEditSystemParams();
      const updated = await apiPut<any>(`/h5/watch-pool/${editing.watch_id}`, {
        trading_system_code: editing.trading_system_code || editing.trading_system,
        trading_system: editing.trading_system,
        system_params_json: systemParams,
        entry_reason: editing.entry_reason,
        key_observe_price: keyObservePrice && String(keyObservePrice).trim() ? Number(keyObservePrice) : null,
        auto_remove_price: autoRemovePrice && String(autoRemovePrice).trim() ? Number(autoRemovePrice) : null,
        invalid_condition: invalidCondition,
        risk_tags: editing.risk_tags,
        user_remark: editing.user_remark,
        adjust_reason: editing.adjust_reason,
      });
      Toast.show({ content: "观察参数已调整" });
      setEditing(null);
      setWatchDetail(updated);
      setDetailTarget({ kind: "watch", item: updated });
      setItems((prev) => prev.map((item) => item.watch_id === updated.watch_id ? updated : item));
    } catch (err: any) {
      Toast.show({ content: err?.message || "保存失败，请重试" });
    }
  }

  async function confirmBuy() {
    if (!buyForm?.stop_loss_price) {
      Toast.show({ content: "止损价必填" });
      return;
    }
    await apiPost(`/h5/watch-signals/${buyForm.signal_id}/confirm-buy`, {
      buy_price: Number(buyForm.buy_price),
      amount: Number(buyForm.amount),
      position_ratio: buyForm.position_ratio ? Number(buyForm.position_ratio) : undefined,
      stop_loss_price: Number(buyForm.stop_loss_price),
      target_price: buyForm.target_price ? Number(buyForm.target_price) : undefined,
      buy_reason: buyForm.buy_reason,
      trade_plan: buyForm.trade_plan,
      emotion_state: buyForm.emotion_state,
      buy_point_confirmed: true,
    });
    Toast.show({ content: "已记录人工确认买入" });
    setBuyForm(null);
    load();
  }

  async function confirmFullSell() {
    if (!sellForm?.sell_price) {
      Toast.show({ content: "请填写卖出价" });
      return;
    }
    await apiPost(`/h5/watch-trades/${sellForm.trade_id}/confirm-sell`, {
      sell_price: Number(sellForm.sell_price),
      amount: Number(sellForm.remaining_amount),
      execution_type: "sell",
      execution_reason: `${sellForm.sell_reason}${sellForm.execution_comment ? `：${sellForm.execution_comment}` : ""}`,
      is_full_exit: true,
    });
    Toast.show({ content: "已记录全部卖出，请进入复盘" });
    setSellForm(null);
    load();
  }

  async function showExecutions(trade: any) {
    setExecutionTrade(trade);
    setExecutions(null);
    const rows = await apiGet<any[]>(`/h5/watch-trades/${trade.trade_id}/executions`);
    setExecutions(rows || []);
  }

  async function abandonSignal(signal: any) {
    const confirmed = await Dialog.confirm({ content: `放弃 ${signal.stock_name} 本次机会？`, confirmText: "放弃本次机会", cancelText: "取消" });
    if (!confirmed) return;
    await apiPost(`/h5/watch-signals/${signal.signal_id}/abandon`, { reason: "用户放弃本次机会" });
    Toast.show({ content: "已放弃本次机会" });
    load();
  }

  async function markInvalid(item: any) {
    const confirmed = await Dialog.confirm({ content: `确认将 ${item.stock_name} 标记为失效？`, confirmText: "标记失效", cancelText: "取消" });
    if (!confirmed) return;
    await apiPost(`/h5/watch-pool/${item.watch_id}/invalid`, { invalid_reason: "用户标记失效" });
    Toast.show({ content: "已标记失效" });
    load();
  }

  async function removeWatch(item: any) {
    const confirmed = await Dialog.confirm({ content: `确认剔除 ${item.stock_name}？该观察记录会从观察表物理删除，不再保留。`, confirmText: "确认剔除", cancelText: "取消" });
    if (!confirmed) return;
    await apiDelete(`/h5/watch-pool/${item.watch_id}/hard-delete`);
    Toast.show({ content: "已剔除" });
    setItems((prev) => prev.filter((row) => row.watch_id !== item.watch_id));
    setWatchDetail(null);
    setDetailTarget(null);
    setEditing(null);
    load();
  }

  async function blacklistWatch(item: any) {
    const confirmed = await Dialog.confirm({ content: `确认将 ${item.stock_name} 加入黑名单？后续重新加入需要明确确认风险。`, confirmText: "加入黑名单", cancelText: "取消" });
    if (!confirmed) return;
    await apiPost(`/h5/watch-pool/${item.watch_id}/blacklist`, { reason: "用户加入黑名单" });
    Toast.show({ content: "已加入黑名单" });
    load();
  }

  async function toggleMonitor(item: any) {
    const enabled = item.monitor_enabled !== false && item.signal_enabled !== false;
    await apiPost(`/h5/watch-pool/${item.watch_id}/monitor/${enabled ? "disable" : "enable"}`, { reason: enabled ? "用户关闭监控" : "用户开启监控" });
    Toast.show({ content: enabled ? "已关闭监控" : "已开启监控" });
    load();
  }

  async function editWatchFromStock(item: any) {
    if (!item?.watch_id) {
      Toast.show({ content: "该股票暂无可编辑观察记录" });
      return;
    }
    try {
      const watch = item.key_observe_price !== undefined && item.invalid_condition !== undefined
        ? item
        : await apiGet<any>(`/h5/watch-pool/${item.watch_id}`);
      setWatchDetail(watch);
      setDetailTarget({ kind: "watch", item: watch });
      setRulePreview(null);
      openEdit(watch);
    } catch {
      Toast.show({ content: "获取观察记录失败" });
    }
  }

  function renderSignalCard(item: any) {
    const canConfirmBuy = item.signal_status === "buy_pending_confirm";
    return (
      <div key={item.signal_id} className="row-card" style={{ display: "grid", gap: 10, cursor: "pointer" }} onClick={() => openDetail("signal", item)}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 10 }}>
          <div>
            <strong><StockLink stockName={item.stock_name} stockCode={item.stock_code} info={item} onEdit={editWatchFromStock} onOpenDetail={() => openDetail("signal", item)} /></strong>
            <p style={{ marginTop: 4 }}>{tradingSystemText(item)} / {signalTypeLabels[item.signal_type] || item.signal_type}</p>
          </div>
        </div>
        <div style={{ display: "grid", gap: 4, color: "#64748b", fontSize: 13, lineHeight: 1.55 }}>
          <p>买点类型：{buyPointLabels[item.buy_point_type] || item.buy_point_type || "-"}</p>
          <p>触发价格：{item.trigger_price ?? "-"}</p>
          <p>买点确认：{item.buy_point_confirmed ? "已确认" : "待确认"} / 状态：{signalStatusText(item.signal_status)}</p>
          <p>止损位：{item.stop_loss_price ?? "-"}</p>
          <p>目标价：{item.target_price ?? "-"}</p>
          <p>风险说明：{item.risk_desc || "-"}</p>
          <p>{item.trigger_reason || ASSISTANT_NOTE}</p>
          <p style={{ color: "#8a94a8" }}>{ASSISTANT_NOTE}</p>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {canConfirmBuy && <Button size="mini" color="primary" onClick={(event) => { event.stopPropagation(); openBuyForm(item); }}>确认买入</Button>}
          <Button size="mini" fill="outline" onClick={(event) => { event.stopPropagation(); abandonSignal(item); }}>放弃本次机会</Button>
        </div>
      </div>
    );
  }

  function renderTradeCard(item: any) {
    const isOpen = ["open", "holding"].includes(item.trade_status);
    return (
      <div key={item.trade_id} className="row-card" style={{ display: "grid", gap: 10, cursor: "pointer" }} onClick={() => openDetail("trade", item)}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 10 }}>
          <div>
            <strong><StockLink stockName={item.stock_name} stockCode={item.stock_code} info={item} onEdit={editWatchFromStock} onOpenDetail={() => openDetail("trade", item)} /></strong>
            <p style={{ marginTop: 4 }}>{labelOf(tradingSystemOptions, item.trading_system)} / {item.trade_status || "-"}</p>
          </div>
        </div>
        <div style={{ display: "grid", gap: 4, color: "#64748b", fontSize: 13, lineHeight: 1.55 }}>
          <p>买入价：{item.average_buy_price ?? item.first_buy_price ?? "-"}</p>
          <p>剩余数量：{item.remaining_amount ?? "-"}</p>
          <p>止损价：{item.stop_loss_price ?? "-"}</p>
          <p>目标价：{item.target_price ?? "-"}</p>
          <p>盈亏：{formatMoney(item.pnl_amount)} / {formatMoney((Number(item.pnl_ratio) || 0) * 100)}%</p>
          <p>状态：{item.trade_status || "-"}</p>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <Button size="mini" fill="outline" onClick={(event) => { event.stopPropagation(); showExecutions(item); }}>查看执行流水</Button>
          {isOpen && <Button size="mini" color="danger" fill="outline" onClick={(event) => { event.stopPropagation(); openSellForm(item); }}>确认全部卖出</Button>}
        </div>
      </div>
    );
  }

  function renderSignalCardV2(item: any) {
    const canConfirmBuy = item.signal_status === "buy_pending_confirm";
    const isRisk = item.signal_type !== "buy";
    return (
      <div key={item.signal_id} style={{ borderRadius: 22, background: "#fff", padding: 14, boxShadow: "0 10px 28px rgba(31,43,77,0.07)", display: "grid", gap: 12, cursor: "pointer" }} onClick={() => openDetail("signal", item)}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "flex-start" }}>
          <div style={{ minWidth: 0 }}>
            <strong style={{ display: "block", fontSize: 17, color: "#17213b" }}>
              <StockLink stockName={item.stock_name} stockCode={item.stock_code} info={item} onEdit={editWatchFromStock} onOpenDetail={() => openDetail("signal", item)} />
            </strong>
            <div style={{ marginTop: 6, display: "flex", gap: 6, flexWrap: "wrap" }}>
              <StatusPill label={signalTypeLabels[item.signal_type] || item.signal_type} status={isRisk ? "sell_signal_pending" : item.signal_status} />
              <StatusPill label={tradingSystemText(item)} status="signal_generated" />
            </div>
          </div>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
          <MiniStat label="触发价" value={item.trigger_price ?? "-"} />
          <MiniStat label="止损位" value={item.stop_loss_price ?? "-"} tone="#e34d59" />
          <MiniStat label="目标价" value={item.target_price ?? "-"} tone="#4b63ee" />
        </div>
        <div style={{ borderRadius: 18, background: "#f7f9ff", padding: 12, display: "grid", gap: 9 }}>
          <InfoLine label="触发规则" value={signalRuleText(item)} />
          <InfoLine label="买点类型" value={buyPointLabels[item.buy_point_type] || item.buy_point_type || "-"} />
          <InfoLine label="确认状态" value={`${item.buy_point_confirmed ? "已确认" : "待确认"} / ${signalStatusText(item.signal_status)}`} />
          <InfoLine label="触发原因" value={item.trigger_reason || ASSISTANT_NOTE} />
          <InfoLine label="风险说明" value={item.risk_desc || "-"} />
          <p style={{ margin: 0, color: "#8a94a8", fontSize: 12, lineHeight: 1.55 }}>{ASSISTANT_NOTE}</p>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: canConfirmBuy ? "1.1fr 1fr" : "1fr", gap: 8 }}>
          {canConfirmBuy && <Button block color="primary" onClick={(event) => { event.stopPropagation(); openBuyForm(item); }} style={{ borderRadius: 14, fontWeight: 800 }}>确认买入</Button>}
          <Button block fill="outline" onClick={(event) => { event.stopPropagation(); abandonSignal(item); }} style={{ borderRadius: 14 }}>放弃本次机会</Button>
        </div>
      </div>
    );
  }

  function renderTradeCardV2(item: any) {
    const isOpen = ["open", "holding"].includes(item.trade_status);
    const pnl = Number(item.pnl_amount) || 0;
    return (
      <div key={item.trade_id} style={{ borderRadius: 22, background: "#fff", padding: 14, boxShadow: "0 10px 28px rgba(31,43,77,0.07)", display: "grid", gap: 12, cursor: "pointer" }} onClick={() => openDetail("trade", item)}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "flex-start" }}>
          <div style={{ minWidth: 0 }}>
            <strong style={{ display: "block", fontSize: 17, color: "#17213b" }}>
              <StockLink stockName={item.stock_name} stockCode={item.stock_code} info={item} onEdit={editWatchFromStock} onOpenDetail={() => openDetail("trade", item)} />
            </strong>
            <div style={{ marginTop: 6, display: "flex", gap: 6, flexWrap: "wrap" }}>
              <StatusPill label={tradingSystemText(item)} status="trading" />
              <StatusPill label={item.trade_status || "-"} status={item.trade_status} />
              <StatusPill label={`阶段 ${item.current_stage || "trading"}`} status="trading" />
            </div>
          </div>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
          <MiniStat label="买入均价" value={item.average_buy_price ?? item.first_buy_price ?? "-"} />
          <MiniStat label="剩余数量" value={item.remaining_amount ?? "-"} />
          <MiniStat label="盈亏率" value={`${formatMoney((Number(item.pnl_ratio) || 0) * 100)}%`} tone={pnl >= 0 ? "#e34d59" : "#00a870"} />
        </div>
        <div style={{ borderRadius: 18, background: "#f7f9ff", padding: 12, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          <InfoLine label="止损价" value={item.stop_loss_price ?? "-"} />
          <InfoLine label="目标价" value={item.target_price ?? "-"} />
        </div>
          <InfoLine label="进入规则" value={item.entry_rule_code || item.buy_point_type || "-"} />
          <InfoLine label="交易体系" value={labelOf(tradingSystemOptions, item.trading_system_code || item.trading_system)} />
          <InfoLine label="卖点规则" value={ruleListText(item.active_sell_rule_codes_json)} />
          <InfoLine label="止损规则" value={ruleListText(item.active_stop_rule_codes_json)} />
          <InfoLine label="进入规则" value={item.entry_rule_display_name || item.entry_rule_name || item.entry_rule_code || item.buy_point_type || "-"} />
          <InfoLine label="交易体系" value={tradingSystemText(item)} />
          <InfoLine label="卖点规则" value={ruleListText(item.active_sell_rules || item.active_sell_rule_codes_json)} />
          <InfoLine label="止损规则" value={ruleListText(item.active_stop_rules || item.active_stop_rule_codes_json)} />
        <div style={{ display: "grid", gridTemplateColumns: isOpen ? "1fr 1fr" : "1fr", gap: 8 }}>
          <Button block fill="outline" onClick={(event) => { event.stopPropagation(); showExecutions(item); }} style={{ borderRadius: 14 }}>执行流水</Button>
          {isOpen && <Button block color="danger" fill="outline" onClick={(event) => { event.stopPropagation(); openSellForm(item); }} style={{ borderRadius: 14 }}>确认全部卖出</Button>}
        </div>
      </div>
    );
  }

  async function previewWatchRules(item: any) {
    if (!item?.watch_id) return;
    setRulePreviewLoading(true);
    try {
      const data = await apiPost<any>(`/h5/watch-pool/${item.watch_id}/rule-preview`);
      setRulePreview(data);
    } catch (err: any) {
      Toast.show({ content: err?.message || "规则试算失败" });
    } finally {
      setRulePreviewLoading(false);
    }
  }

  function renderSignalCardV3(item: any) {
    return (
      <div key={item.signal_id} style={{ borderRadius: 22, background: "#fff", padding: 14, boxShadow: "0 10px 28px rgba(31,43,77,0.07)", display: "grid", gap: 10, cursor: "pointer" }} onClick={() => openDetail("signal", item)}>
        <div style={{ minWidth: 0 }}>
          <strong style={{ display: "block", fontSize: 17, color: "#17213b" }}>
            <StockLink stockName={item.stock_name} stockCode={item.stock_code} info={item} onEdit={editWatchFromStock} onOpenDetail={() => openDetail("signal", item)} />
          </strong>
          <div style={{ marginTop: 7, display: "flex", gap: 6, flexWrap: "wrap" }}>
            <StatusPill label={signalKindText(item)} status={item.signal_status} />
            <StatusPill label={signalStatusText(item.signal_status)} status={item.signal_status} />
          </div>
        </div>
        <div style={{ borderRadius: 18, background: "#f7f9ff", padding: 12, display: "grid", gap: 8 }}>
          <InfoLine label="触发规则" value={signalRuleText(item)} />
          <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 8 }}>
            <Field label="触发价" value={item.trigger_price} />
            <Field label="触发时间" value={String(item.trigger_time || item.trigger_date || "").slice(0, 16)} />
          </div>
        </div>
      </div>
    );
  }

  function renderTradeCardV3(item: any) {
    const pnlRatio = item.pnl_ratio != null ? formatMoney(Number(item.pnl_ratio) * 100) + "%" : undefined;
    return (
      <div key={item.trade_id} style={{ borderRadius: 22, background: "#fff", padding: 14, boxShadow: "0 10px 28px rgba(31,43,77,0.07)", display: "grid", gap: 10, cursor: "pointer" }} onClick={() => openDetail("trade", item)}>
        <div style={{ minWidth: 0 }}>
          <strong style={{ display: "block", fontSize: 17, color: "#17213b" }}>
            <StockLink stockName={item.stock_name} stockCode={item.stock_code} info={item} onEdit={editWatchFromStock} onOpenDetail={() => openDetail("trade", item)} />
          </strong>
          <div style={{ marginTop: 7, display: "flex", gap: 6, flexWrap: "wrap" }}>
            <StatusPill label={item.trade_status || "-"} status={item.trade_status} />
            <StatusPill label={pnlRatio ? "盈亏 " + pnlRatio : "盈亏 -"} status={Number(item.pnl_ratio || 0) >= 0 ? "sell_signal_pending" : "watching"} />
          </div>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 8 }}>
          <MiniStat label="买入均价" value={item.average_buy_price ?? item.first_buy_price ?? "-"} />
          <MiniStat label="止损价" value={item.stop_loss_price ?? "-"} tone="#e34d59" />
          <MiniStat label="目标价" value={item.target_price ?? "-"} tone="#4b63ee" />
        </div>
      </div>
    );
  }

  function renderWatchCard(item: any) {
    const status = item.status;
    return (
      <div key={item.watch_id} style={{ borderRadius: 22, background: "#fff", padding: 14, boxShadow: "0 10px 28px rgba(31,43,77,0.07)", display: "grid", gap: 10, cursor: "pointer" }} onClick={() => openDetail("watch", item)}>
        <div style={{ minWidth: 0 }}>
          <strong style={{ display: "block", fontSize: 17, color: "#17213b" }}>
            <StockLink stockName={item.stock_name} stockCode={item.stock_code} info={item} onEdit={editWatchFromStock} onOpenDetail={openWatchDetail} />
          </strong>
          <div style={{ marginTop: 7, display: "flex", gap: 6, flexWrap: "wrap" }}>
            <StatusPill label={tradingSystemText(item)} status="signal_generated" />
            <StatusPill label={labelOf(lifecycleOptions, status)} status={status} />
            <StatusPill label={"阶段 " + (item.system_stage || "observe")} status={status} />
          </div>
        </div>
        {coreParamText(item) && <div style={{ color: "#64748b", fontSize: 12, lineHeight: 1.5 }}>{coreParamText(item)}</div>}
        <div style={{ borderRadius: 16, background: "#f7f9ff", padding: "10px 12px", color: "#4052d2", fontSize: 12, lineHeight: 1.5, fontWeight: 700 }}>
          {nextAction(item)}
        </div>
      </div>
    );
  }

  return (
    <PageShell
      title="自选"
      hideHero
      segments={[
        { key: "watch", label: "观察", onClick: () => setTab("watch") },
        { key: "signal", label: "信号", onClick: () => setTab("signal") },
        { key: "trade", label: "交易", onClick: () => setTab("trade") },
      ]}
      activeSegment={tab}
    >
      {loading && <SpinLoading />}
      {error && <ErrorBlock description="自选页加载失败" />}

      {tab === "watch" && (
        <article className="feature-card">
          <div className="card-head">
            <div className="card-headline"><span className="icon-badge">{watchingItems.length}</span><h2>观察</h2></div>
            <span className="soft-tag">今日新增 {todayNew} / 观察中 {watchingItems.length}</span>
          </div>
          {watchingItems.length ? (
            <div className="stack-list">
              {watchingItems.map(renderWatchCard)}
            </div>
          ) : <div className="empty-panel">暂无观察中的自选股</div>}
        </article>
      )}

      {tab === "signal" && (
        <article className="feature-card">
          <div className="card-head">
            <div className="card-headline"><span className="icon-badge">{todaySignals}</span><h2>信号</h2></div>
            <span className="soft-tag">今日 {todaySignals} / 总数 {signalSummary.total ?? signals.length}</span>
          </div>
          <div className="stack-list">
            {buySignals.map(renderSignalCardV3)}
            {riskSignals.map(renderSignalCardV3)}
            {!buySignals.length && !riskSignals.length && <div className="empty-panel">暂无信号</div>}
          </div>
        </article>
      )}

      {tab === "trade" && (
        <article className="feature-card">
          <div className="card-head">
            <div className="card-headline"><span className="icon-badge">{tradeSummary.open ?? 0}</span><h2>交易</h2></div>
            <span className="soft-tag">持仓 {tradeSummary.open ?? 0} / 总数 {tradeSummary.total ?? trades.length}</span>
          </div>
          {pendingTradeSignals.length ? (
            <div style={{ display: "grid", gap: 10, marginBottom: 12 }}>
              <div style={{ color: "#e34d59", fontWeight: 800, fontSize: 13 }}>卖点/止损提醒</div>
              {pendingTradeSignals.map(renderSignalCardV2)}
            </div>
          ) : null}
          {trades.length ? <div className="stack-list">{trades.map(renderTradeCardV3)}</div> : <div className="empty-panel">暂无交易记录</div>}
        </article>
      )}


      <Popup visible={Boolean(buyForm)} onMaskClick={() => setBuyForm(null)} bodyStyle={{ borderTopLeftRadius: 22, borderTopRightRadius: 22, padding: 18, maxHeight: "86vh", overflowY: "auto" }}>
        {buyForm && (
          <div style={{ display: "grid", gap: 12 }}>
            <div><h3 style={{ margin: 0 }}>确认买入</h3><p style={{ margin: "4px 0 0", color: "#72819b" }}>{buyForm.stock_name} {buyForm.stock_code}</p></div>
            <Input type="number" value={buyForm.buy_price} placeholder="买入价" onChange={(value) => setBuyForm({ ...buyForm, buy_price: value })} />
            <Input type="number" value={buyForm.amount} placeholder="数量" onChange={(value) => setBuyForm({ ...buyForm, amount: value })} />
            <Input type="number" value={buyForm.position_ratio} placeholder="仓位，例如 0.2" onChange={(value) => setBuyForm({ ...buyForm, position_ratio: value })} />
            <Input type="number" value={buyForm.stop_loss_price} placeholder="止损价（必填）" onChange={(value) => setBuyForm({ ...buyForm, stop_loss_price: value })} />
            <Input type="number" value={buyForm.target_price} placeholder="目标价" onChange={(value) => setBuyForm({ ...buyForm, target_price: value })} />
            <TextArea value={buyForm.buy_reason} rows={3} placeholder="买入理由" onChange={(value) => setBuyForm({ ...buyForm, buy_reason: value })} />
            <TextArea value={buyForm.trade_plan} rows={3} placeholder="交易计划" onChange={(value) => setBuyForm({ ...buyForm, trade_plan: value })} />
            <Selector options={emotionOptions} value={[buyForm.emotion_state]} onChange={(value) => setBuyForm({ ...buyForm, emotion_state: value[0] })} />
            <p style={{ margin: 0, color: "#8a94a8", fontSize: 12 }}>{ASSISTANT_NOTE}</p>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}><Button block onClick={() => setBuyForm(null)}>取消</Button><Button block color="primary" onClick={confirmBuy}>确认</Button></div>
          </div>
        )}
      </Popup>

      <Popup visible={Boolean(detailItem)} onMaskClick={closeDetail} bodyStyle={{ borderTopLeftRadius: 22, borderTopRightRadius: 22, padding: "12px max(14px, env(safe-area-inset-right)) calc(16px + env(safe-area-inset-bottom)) max(14px, env(safe-area-inset-left))", maxHeight: "88vh", overflowY: "auto" }}>
        {detailItem && !(activeDetailKind === "watch" && editing && editing.watch_id === detailItem.watch_id) && (
          <div style={{ display: "grid", gap: 14 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}>
              <div style={{ minWidth: 0 }}>
                <h3 style={{ margin: 0, fontSize: 18, color: "#17213b" }}>{detailItem.stock_name}</h3>
                <div style={{ marginTop: 4, display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center", color: "#667085", fontSize: 12 }}>
                  <span>{detailItem.stock_code}</span>
                  {detailPrice(detailItem) != null && <strong style={{ color: "#17213b" }}>{detailPrice(detailItem)}</strong>}
                  {detailChangePct(detailItem) != null && (
                    <span style={{ color: Number(detailChangePct(detailItem)) >= 0 ? "#e34d59" : "#00a870", fontWeight: 800 }}>
                      {Number(detailChangePct(detailItem)).toFixed(2)}%
                    </span>
                  )}
                </div>
              </div>
              {toXueqiuUrl(detailItem.stock_code) && (
                <Button
                  size="mini"
                  fill="outline"
                  onClick={() => window.open(toXueqiuUrl(detailItem.stock_code), "_blank")}
                  style={{ borderRadius: 999, minWidth: 36, height: 32, padding: "0 9px", fontWeight: 900 }}
                  title="雪球"
                >
                  ↗
                </Button>
              )}
            </div>

            {renderDetailTags(detailItem, activeDetailKind)}

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
              {[
                { key: "detail" as const, label: "详情" },
                { key: "kline" as const, label: "日K线" },
              ].map((item) => (
                <button
                  key={item.key}
                  type="button"
                  onClick={() => setWatchDetailTab(item.key)}
                  style={{
                    border: 0,
                    borderRadius: 14,
                    padding: "9px 0",
                    fontSize: 13,
                    fontWeight: 800,
                    background: watchDetailTab === item.key ? "linear-gradient(135deg, #5570ff, #4052d2)" : "#eef2f8",
                    color: watchDetailTab === item.key ? "#fff" : "#64748b",
                  }}
                >
                  {item.label}
                </button>
              ))}
            </div>

            {watchDetailTab === "detail" ? (
              <>
                {renderDetailBody(detailItem, activeDetailKind)}
                {activeDetailKind === "watch" && rulePreview && (
                  <div style={{ borderRadius: 12, background: rulePreview.would_generate_signal ? "#fff1f1" : "#f7f9ff", padding: 12, display: "grid", gap: 8 }}>
                    <strong style={{ color: rulePreview.would_generate_signal ? "#e34d59" : "#22375c", fontSize: 14 }}>规则试算：{rulePreviewConclusionText(rulePreview)}</strong>
                    {(rulePreview.rules || []).map((rule: any) => (
                      <div key={rule.rule_code} style={{ borderRadius: 10, background: "#fff", padding: 10, display: "grid", gap: 4 }}>
                        <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                          <strong style={{ color: "#17213b", fontSize: 13 }}>{rule.rule_display_name || rule.rule_name || rule.rule_code}</strong>
                          <span style={{ color: rule.triggered ? "#00a870" : "#e34d59", fontSize: 12, fontWeight: 800 }}>{rule.triggered ? "满足" : "未满足"}</span>
                        </div>
                        <div style={{ color: "#667085", fontSize: 12 }}>{rule.rule_type} / {rule.timeframe} / {rule.required ? "必需" : "可选"} / {rule.logic_group || "-"}</div>
                        <div style={{ color: "#475467", fontSize: 12 }}>{rule.reason || "暂无原因"}</div>
                      </div>
                    ))}
                  </div>
                )}
              </>
            ) : (
              <div style={{ borderRadius: 18, background: "#fff", boxShadow: "0 12px 36px rgba(31,43,77,0.08)", overflow: "hidden" }}>
                <div style={{ padding: "12px 14px 0", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <strong style={{ color: "#18223d", fontSize: 16 }}>日K线</strong>
                  <span style={{ color: "#8a94a8", fontSize: 12 }}>{detailItem.stock_code}</span>
                </div>
                <KlineChart data={watchDetailKline} loading={watchDetailKlineLoading} />
              </div>
            )}

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(112px, 1fr))", gap: 8 }}>
              {activeDetailKind === "watch" && (
                <>
                  <Button block fill="outline" size="small" onClick={() => openEdit(detailItem)}>编辑参数</Button>
                  <Button block fill="outline" size="small" loading={rulePreviewLoading} onClick={() => previewWatchRules(detailItem)}>试算</Button>
                  <Button block fill="outline" size="small" onClick={() => toggleMonitor(detailItem)}>{detailItem.monitor_enabled !== false && detailItem.signal_enabled !== false ? "关闭监控" : "开启监控"}</Button>
                  <Button block fill="outline" size="small" onClick={() => markInvalid(detailItem)}>标记失效</Button>
                  <Button block fill="outline" size="small" onClick={() => removeWatch(detailItem)}>剔除</Button>
                  <Button block color="danger" fill="outline" size="small" onClick={() => blacklistWatch(detailItem)}>加入黑名单</Button>
                </>
              )}
              {activeDetailKind === "signal" && (
                <>
                  {detailItem.signal_type === "buy" && (
                    <>
                      {detailItem.signal_status === "buy_pending_confirm" && <Button block color="primary" size="small" onClick={() => openBuyForm(detailItem)}>确认买入</Button>}
                      <Button block fill="outline" size="small" onClick={() => abandonSignal(detailItem)}>放弃本次机会</Button>
                    </>
                  )}
                  {detailItem.signal_type === "risk" && (
                    <div style={{ gridColumn: "1 / -1", borderRadius: 14, background: "#fff8e8", color: "#8a5a00", padding: "10px 12px", fontSize: 12, lineHeight: 1.5 }}>
                      风险/失效信号仅提示人工处理，当前不会自动剔除或自动交易。
                    </div>
                  )}
                  {detailItem.signal_type === "sell" && (
                    <div style={{ gridColumn: "1 / -1", borderRadius: 14, background: "#fff1f1", color: "#b42318", padding: "10px 12px", fontSize: 12, lineHeight: 1.5 }}>
                      卖点/止损信号待人工处理，卖出动作继续通过交易确认流程完成。
                    </div>
                  )}
                </>
              )}
              {activeDetailKind === "trade" && (
                <>
                  <Button block fill="outline" size="small" onClick={() => showExecutions(detailItem)}>执行流水</Button>
                  {["open", "holding"].includes(detailItem.trade_status) && <Button block color="danger" fill="outline" size="small" onClick={() => openSellForm(detailItem)}>确认卖出</Button>}
                </>
              )}
              <Button block fill="outline" size="small" onClick={closeDetail}>关闭</Button>
            </div>
          </div>
        )}

        {watchDetail && (editing && editing.watch_id === watchDetail.watch_id) && editing && (
          <div style={{ display: "grid", gap: 14 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <h3 style={{ margin: 0, fontSize: 17 }}>调整观察参数</h3>
                <p style={{ margin: "2px 0 0", color: "#888", fontSize: 13 }}>{editing.stock_name} {editing.stock_code}</p>
              </div>
            </div>

            <div style={{ borderRadius: 12, background: "#f7f9ff", padding: 12, display: "grid", gap: 10 }}>
              <div style={{ color: "#5b6d8a", fontSize: 12, fontWeight: 700 }}>交易体系</div>
              <Selector options={availableTradingSystemOptions} value={[editing.trading_system_code || editing.trading_system]} onChange={(value) => changeEditSystem(String(value[0] || ""))} />
            </div>

            <div style={{ borderRadius: 12, background: "#f7f9ff", padding: 12, display: "grid", gap: 10 }}>
              <div style={{ color: "#5b6d8a", fontSize: 12, fontWeight: 700 }}>交易体系参数</div>
              {editSystemParams.length ? editSystemParams.map((param) => renderEditParam(param)) : (
                <div style={{ color: "#98a2b3", fontSize: 12 }}>当前体系暂无参数定义</div>
              )}
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
              <div style={{ display: "grid", gap: 4 }}>
                <span style={{ color: "#5b6d8a", fontSize: 12, fontWeight: 700 }}>关键观察价</span>
                <Input type="number" value={editing.key_observe_price} placeholder="12.00" onChange={(value) => updateEditParam("key_observe_price", value)} />
              </div>
              <div style={{ display: "grid", gap: 4 }}>
                <span style={{ color: "#5b6d8a", fontSize: 12, fontWeight: 700 }}>自动剔除价</span>
                <Input type="number" value={editing.auto_remove_price} placeholder="跌破后软剔除" onChange={(value) => updateEditParam("auto_remove_price", value)} />
              </div>
            </div>

            <div style={{ display: "grid", gap: 10 }}>
              <div style={{ display: "grid", gap: 4 }}>
                <span style={{ color: "#5b6d8a", fontSize: 12, fontWeight: 700 }}>入选理由</span>
                <TextArea value={editing.entry_reason} rows={2} placeholder="为什么值得进入观察池" onChange={(value) => setEditing({ ...editing, entry_reason: value })} />
              </div>
              <div style={{ display: "grid", gap: 4 }}>
                <span style={{ color: "#5b6d8a", fontSize: 12, fontWeight: 700 }}>失效条件</span>
                <TextArea value={editing.invalid_condition} rows={2} placeholder="什么情况下不再观察" onChange={(value) => updateEditParam("invalid_condition", value)} />
              </div>
            </div>

            <div style={{ borderRadius: 12, background: "#f7f9ff", padding: 12, display: "grid", gap: 8 }}>
              <div style={{ display: "grid", gap: 4 }}>
                <span style={{ color: "#5b6d8a", fontSize: 12, fontWeight: 700 }}>风险标签</span>
                <Selector multiple options={Object.entries(riskTagLabels).map(([value, label]) => ({ value, label }))} value={editing.risk_tags} onChange={(value) => setEditing({ ...editing, risk_tags: value as string[] })} />
              </div>
              <div style={{ display: "grid", gap: 4 }}>
                <span style={{ color: "#5b6d8a", fontSize: 12, fontWeight: 700 }}>用户备注</span>
                <TextArea value={editing.user_remark} rows={2} placeholder="记录观察要点或提醒" onChange={(value) => setEditing({ ...editing, user_remark: value })} />
              </div>
            </div>

            <div style={{ borderRadius: 12, background: "#fff8e8", padding: "10px 12px" }}>
              <div style={{ display: "grid", gap: 4 }}>
                <span style={{ color: "#c0392b", fontSize: 12, fontWeight: 700 }}>本次调整原因 *</span>
                <TextArea value={editing.adjust_reason} rows={2} placeholder="必填，说明为什么调整参数" onChange={(value) => setEditing({ ...editing, adjust_reason: value })} />
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
              <Button block onClick={() => setEditing(null)}>取消</Button>
              <Button block color="primary" onClick={saveEdit}>保存</Button>
            </div>
            <Button block color="danger" fill="outline" onClick={() => removeWatch(editing)} size="small">剔除</Button>
          </div>
        )}
      </Popup>
      <Popup visible={Boolean(sellForm)} onMaskClick={() => setSellForm(null)} bodyStyle={{ borderTopLeftRadius: 22, borderTopRightRadius: 22, padding: 18, maxHeight: "86vh", overflowY: "auto" }}>
        {sellForm && (
          <div style={{ display: "grid", gap: 12 }}>
            <div><h3 style={{ margin: 0 }}>确认全部卖出</h3><p style={{ margin: "4px 0 0", color: "#72819b" }}>{sellForm.stock_name} {sellForm.stock_code}</p></div>
            <Input type="number" value={sellForm.sell_price} placeholder="卖出价" onChange={(value) => setSellForm({ ...sellForm, sell_price: value })} />
            <Input value={String(sellForm.remaining_amount)} disabled placeholder="全部卖出数量" />
            <Input value={sellForm.sell_reason} placeholder="卖出原因" onChange={(value) => setSellForm({ ...sellForm, sell_reason: value })} />
            <TextArea value={sellForm.execution_comment} rows={3} placeholder="执行说明" onChange={(value) => setSellForm({ ...sellForm, execution_comment: value })} />
            <p style={{ margin: 0, color: "#8a94a8", fontSize: 12 }}>全部卖出后会进入复盘流程。{ASSISTANT_NOTE}</p>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}><Button block onClick={() => setSellForm(null)}>取消</Button><Button block color="danger" onClick={confirmFullSell}>确认全部卖出</Button></div>
          </div>
        )}
      </Popup>

      <Popup visible={Boolean(executionTrade)} onMaskClick={() => { setExecutionTrade(null); setExecutions(null); }} bodyStyle={{ borderTopLeftRadius: 22, borderTopRightRadius: 22, padding: 18, maxHeight: "86vh", overflowY: "auto" }}>
        {executionTrade && (
          <div style={{ display: "grid", gap: 12 }}>
            <div><h3 style={{ margin: 0 }}>执行流水</h3><p style={{ margin: "4px 0 0", color: "#72819b" }}>{executionTrade.stock_name} {executionTrade.stock_code}</p></div>
            {executions == null ? <SpinLoading /> : executions.length ? (
              <div className="stack-list">
                {executions.map((item) => (
                  <div key={item.execution_id} className="row-card" style={{ display: "grid", gap: 4 }}>
                    <strong>{item.execution_type} / {item.execution_price} / {item.execution_amount}</strong>
                    <p>时间：{item.execution_time || "-"}</p>
                    <p>说明：{item.execution_reason || "-"}</p>
                    <p>盈亏：{formatMoney(item.pnl_amount)} / {formatMoney((Number(item.pnl_ratio) || 0) * 100)}%</p>
                  </div>
                ))}
              </div>
            ) : <div className="empty-panel">暂无执行流水</div>}
          </div>
        )}
      </Popup>
    </PageShell>
  );
}
