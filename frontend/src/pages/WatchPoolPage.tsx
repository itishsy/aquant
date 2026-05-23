import { useEffect, useMemo, useState } from "react";
import { Button, Dialog, ErrorBlock, Input, Popup, Selector, SpinLoading, TextArea, Toast } from "antd-mobile";
import { apiDelete, apiGet, apiPost, apiPut } from "../api/client";
import { PageShell } from "../components/PageShell";
import { StockLink, toXueqiuUrl } from "../components/StockLink";


const ASSISTANT_NOTE = "仅作为交易辅助，请结合个人交易规则确认。";

const tradingSystemOptions = [
  { label: "全部体系", value: "" },
  { label: "平台突破", value: "platform_breakout" },
  { label: "上涨趋势", value: "uptrend" },
  { label: "追涨接力", value: "relay" },
];

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

function XueqiuButton({ item }: { item: any }) {
  const url = toXueqiuUrl(item?.stock_code);
  if (!url) return null;
  return (
    <Button
      size="mini"
      fill="none"
      onClick={(event) => { event.stopPropagation(); window.open(url, "_blank"); }}
      style={{
        borderRadius: 999,
        padding: "2px 4px",
        fontSize: 10,
        fontWeight: 800,
        color: "#4052d2",
        border: 0,
        background: "transparent",
      }}
    >
      雪球
    </Button>
  );
}

function nextAction(item: any) {
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
  const [buyForm, setBuyForm] = useState<any | null>(null);
  const [sellForm, setSellForm] = useState<any | null>(null);
  const [watchDetail, setWatchDetail] = useState<any>(null);
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

  const buySignals = useMemo(() => signals.filter((item) => item.signal_type === "buy"), [signals]);
  const riskSignals = useMemo(() => signals.filter((item) => item.signal_type !== "buy"), [signals]);
  const watchingItems = useMemo(() => items.filter((i) => i.status === "watching" || i.status === "观察中"), [items]);
  const todayStr = new Date().toISOString().slice(0, 10);
  const todayNew = useMemo(() => items.filter((item) => String(item.created_at || "").slice(0, 10) === todayStr).length, [items, todayStr]);
  const todaySignals = useMemo(() => signals.filter((s) => (s.trigger_date || "").slice(0, 10) === todayStr).length, [signals, todayStr]);

  function Field({ label, value }: { label: string; value?: any }) {
  if (value == null || value === "" || value === "-") return null;
  return (
    <div style={{ fontSize: 13 }}>
      <span style={{ color: "#888" }}>{label}</span>
      <span style={{ color: "#334", marginLeft: 4 }}>{value}</span>
    </div>
  );
}

  function openEdit(item: any) {
    setEditing({
      watch_id: item.watch_id,
      stock_name: item.stock_name,
      stock_code: item.stock_code,
      trading_system: item.trading_system || "uptrend",
      entry_reason: item.entry_reason || item.reason || "",
      key_observe_price: item.key_observe_price != null ? String(item.key_observe_price) : "",
      auto_remove_price: item.auto_remove_price != null ? String(item.auto_remove_price) : "",
      invalid_condition: item.invalid_condition || "",
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
      const updated = await apiPut<any>(`/h5/watch-pool/${editing.watch_id}`, {
        trading_system: editing.trading_system,
        entry_reason: editing.entry_reason,
        key_observe_price: editing.key_observe_price && editing.key_observe_price.trim() ? Number(editing.key_observe_price) : null,
        auto_remove_price: editing.auto_remove_price && editing.auto_remove_price.trim() ? Number(editing.auto_remove_price) : null,
        invalid_condition: editing.invalid_condition,
        risk_tags: editing.risk_tags,
        user_remark: editing.user_remark,
        adjust_reason: editing.adjust_reason,
      });
      Toast.show({ content: "观察参数已调整" });
      setEditing(null);
      setWatchDetail(updated);
      setItems((prev) => prev.map((item) => item.watch_id === updated.watch_id ? updated : item));
    } catch {
      Toast.show({ content: "保存失败，请重试" });
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
      openEdit(watch);
    } catch {
      Toast.show({ content: "获取观察记录失败" });
    }
  }

  function renderSignalCard(item: any) {
    const canConfirmBuy = item.signal_status === "buy_pending_confirm";
    return (
      <div key={item.signal_id} className="row-card" style={{ display: "grid", gap: 10 }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 10 }}>
          <div>
            <strong><StockLink stockName={item.stock_name} stockCode={item.stock_code} info={item} onEdit={editWatchFromStock} /></strong>
            <p style={{ marginTop: 4 }}>{labelOf(tradingSystemOptions, item.trading_system)} / {signalTypeLabels[item.signal_type] || item.signal_type}</p>
          </div>
          <XueqiuButton item={item} />
        </div>
        <div style={{ display: "grid", gap: 4, color: "#64748b", fontSize: 13, lineHeight: 1.55 }}>
          <p>买点类型：{buyPointLabels[item.buy_point_type] || item.buy_point_type || "-"}</p>
          <p>触发价格：{item.trigger_price ?? "-"}</p>
          <p>买点确认：{item.buy_point_confirmed ? "已确认" : "待确认"} / 状态：{item.signal_status || "-"}</p>
          <p>止损位：{item.stop_loss_price ?? "-"}</p>
          <p>目标价：{item.target_price ?? "-"}</p>
          <p>风险说明：{item.risk_desc || "-"}</p>
          <p>{item.trigger_reason || ASSISTANT_NOTE}</p>
          <p style={{ color: "#8a94a8" }}>{ASSISTANT_NOTE}</p>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {canConfirmBuy && <Button size="mini" color="primary" onClick={() => openBuyForm(item)}>确认买入</Button>}
          <Button size="mini" fill="outline" onClick={() => abandonSignal(item)}>放弃本次机会</Button>
        </div>
      </div>
    );
  }

  function renderTradeCard(item: any) {
    const isOpen = ["open", "holding"].includes(item.trade_status);
    return (
      <div key={item.trade_id} className="row-card" style={{ display: "grid", gap: 10 }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 10 }}>
          <div>
            <strong><StockLink stockName={item.stock_name} stockCode={item.stock_code} info={item} onEdit={editWatchFromStock} /></strong>
            <p style={{ marginTop: 4 }}>{labelOf(tradingSystemOptions, item.trading_system)} / {item.trade_status || "-"}</p>
          </div>
          <XueqiuButton item={item} />
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
          <Button size="mini" fill="outline" onClick={() => showExecutions(item)}>查看执行流水</Button>
          {isOpen && <Button size="mini" color="danger" fill="outline" onClick={() => openSellForm(item)}>确认全部卖出</Button>}
        </div>
      </div>
    );
  }

  function renderSignalCardV2(item: any) {
    const canConfirmBuy = item.signal_status === "buy_pending_confirm";
    const isRisk = item.signal_type !== "buy";
    return (
      <div key={item.signal_id} style={{ borderRadius: 22, background: "#fff", padding: 14, boxShadow: "0 10px 28px rgba(31,43,77,0.07)", display: "grid", gap: 12 }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "flex-start" }}>
          <div style={{ minWidth: 0 }}>
            <strong style={{ display: "block", fontSize: 17, color: "#17213b" }}>
              <StockLink stockName={item.stock_name} stockCode={item.stock_code} info={item} onEdit={editWatchFromStock} />
            </strong>
            <div style={{ marginTop: 6, display: "flex", gap: 6, flexWrap: "wrap" }}>
              <StatusPill label={signalTypeLabels[item.signal_type] || item.signal_type} status={isRisk ? "sell_signal_pending" : item.signal_status} />
              <StatusPill label={labelOf(tradingSystemOptions, item.trading_system)} status="signal_generated" />
            </div>
          </div>
          <XueqiuButton item={item} />
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
          <MiniStat label="触发价" value={item.trigger_price ?? "-"} />
          <MiniStat label="止损位" value={item.stop_loss_price ?? "-"} tone="#e34d59" />
          <MiniStat label="目标价" value={item.target_price ?? "-"} tone="#4b63ee" />
        </div>
        <div style={{ borderRadius: 18, background: "#f7f9ff", padding: 12, display: "grid", gap: 9 }}>
          <InfoLine label="买点类型" value={buyPointLabels[item.buy_point_type] || item.buy_point_type || "-"} />
          <InfoLine label="确认状态" value={`${item.buy_point_confirmed ? "已确认" : "待确认"} / ${item.signal_status || "-"}`} />
          <InfoLine label="触发原因" value={item.trigger_reason || ASSISTANT_NOTE} />
          <InfoLine label="风险说明" value={item.risk_desc || "-"} />
          <p style={{ margin: 0, color: "#8a94a8", fontSize: 12, lineHeight: 1.55 }}>{ASSISTANT_NOTE}</p>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: canConfirmBuy ? "1.1fr 1fr" : "1fr", gap: 8 }}>
          {canConfirmBuy && <Button block color="primary" onClick={() => openBuyForm(item)} style={{ borderRadius: 14, fontWeight: 800 }}>确认买入</Button>}
          <Button block fill="outline" onClick={() => abandonSignal(item)} style={{ borderRadius: 14 }}>放弃本次机会</Button>
        </div>
      </div>
    );
  }

  function renderTradeCardV2(item: any) {
    const isOpen = ["open", "holding"].includes(item.trade_status);
    const pnl = Number(item.pnl_amount) || 0;
    return (
      <div key={item.trade_id} style={{ borderRadius: 22, background: "#fff", padding: 14, boxShadow: "0 10px 28px rgba(31,43,77,0.07)", display: "grid", gap: 12 }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "flex-start" }}>
          <div style={{ minWidth: 0 }}>
            <strong style={{ display: "block", fontSize: 17, color: "#17213b" }}>
              <StockLink stockName={item.stock_name} stockCode={item.stock_code} info={item} onEdit={editWatchFromStock} />
            </strong>
            <div style={{ marginTop: 6, display: "flex", gap: 6, flexWrap: "wrap" }}>
              <StatusPill label={labelOf(tradingSystemOptions, item.trading_system)} status="trading" />
              <StatusPill label={item.trade_status || "-"} status={item.trade_status} />
            </div>
          </div>
          <XueqiuButton item={item} />
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
        <div style={{ display: "grid", gridTemplateColumns: isOpen ? "1fr 1fr" : "1fr", gap: 8 }}>
          <Button block fill="outline" onClick={() => showExecutions(item)} style={{ borderRadius: 14 }}>执行流水</Button>
          {isOpen && <Button block color="danger" fill="outline" onClick={() => openSellForm(item)} style={{ borderRadius: 14 }}>确认全部卖出</Button>}
        </div>
      </div>
    );
  }

  function renderWatchCard(item: any) {
    const status = item.status;
    const monitorOff = item.monitor_enabled === false || item.signal_enabled === false;
    const source = `${item.entry_source || item || item || "manual"}${item ? ` #${item}` : ""}`;
    const riskText = (item.risk_tags || []).map((tag: string) => riskTagLabels[tag] || tag).join(" / ") || "暂无";
    return (
      <div key={item.watch_id} style={{ borderRadius: 24, background: "#fff", padding: 15, boxShadow: "0 12px 30px rgba(31,43,77,0.07)", display: "grid", gap: 12 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}>
          <div style={{ minWidth: 0 }}>
            <strong style={{ display: "block", fontSize: 18, color: "#17213b" }}>
              <StockLink stockName={item.stock_name} stockCode={item.stock_code} info={item} onEdit={editWatchFromStock} />
            </strong>
            <div style={{ marginTop: 7, display: "flex", gap: 6, flexWrap: "wrap" }}>
              <StatusPill label={labelOf(tradingSystemOptions, item.trading_system)} status="signal_generated" />
              <StatusPill label={labelOf(lifecycleOptions, status)} status={status} />
            </div>
          </div>
          <StatusPill label={monitorOff ? "监控关闭" : "监控中"} status={monitorOff ? "invalid" : "watching"} />
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
          <MiniStat label="观察价" value={item.key_observe_price ?? "-"} tone="#4b63ee" />
          <MiniStat label="来源" value={source} />
        </div>
        <div style={{ borderRadius: 18, background: "#f7f9ff", padding: 12, display: "grid", gap: 10 }}>
          <InfoLine label="入选理由" value={item.entry_reason || item.reason || item || "用户手动关注"} />
          <InfoLine label="失效条件" value={item.invalid_condition || "-"} />
          <InfoLine label="风险标签" value={riskText} />
          <InfoLine label="下一步" value={nextAction(item)} />
          {item.user_remark ? <InfoLine label="备注" value={item.user_remark} /> : null}
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
          <Button block fill="outline" onClick={() => { setWatchDetail(item); openEdit(item); }} style={{ borderRadius: 14 }}>调整</Button>
          <Button block fill="outline" onClick={() => toggleMonitor(item)} style={{ borderRadius: 14 }}>{monitorOff ? "开启监控" : "关闭监控"}</Button>
          <Button block fill="outline" onClick={() => markInvalid(item)} style={{ borderRadius: 14 }}>失效</Button>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
          <Button block fill="outline" onClick={() => removeWatch(item)} style={{ borderRadius: 14 }}>剔除</Button>
          <Button block color="danger" fill="outline" onClick={() => blacklistWatch(item)} style={{ borderRadius: 14 }}>黑名单</Button>
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
              {watchingItems.map((item) => (
                <div key={item.watch_id} className="row-card" style={{ padding: "10px 12px", cursor: "pointer" }}
                  onClick={() => setWatchDetail(item)}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <strong style={{ fontSize: 15 }}><StockLink stockName={item.stock_name} stockCode={item.stock_code} info={item} onEdit={editWatchFromStock} /></strong>
                    <p style={{ margin: "3px 0 0", fontSize: 12, color: "#888" }}>
                      {item.sector_name || "未分类"} · {String(item.created_at || "").slice(0, 10) || "-"}
                    </p>
                  </div>
                  <XueqiuButton item={item} />
                </div>
              ))}
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
            {buySignals.map(renderSignalCardV2)}
            {riskSignals.map(renderSignalCardV2)}
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
          {trades.length ? <div className="stack-list">{trades.map(renderTradeCardV2)}</div> : <div className="empty-panel">暂无交易记录</div>}
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

      <Popup visible={Boolean(watchDetail)} onMaskClick={() => { setWatchDetail(null); setEditing(null); }} bodyStyle={{ borderTopLeftRadius: 22, borderTopRightRadius: 22, padding: 18, maxHeight: "86vh", overflowY: "auto" }}>
        {watchDetail && !(editing && editing.watch_id === watchDetail.watch_id) && (
          <div style={{ display: "grid", gap: 14 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div>
                <h3 style={{ margin: 0, fontSize: 18 }}>{watchDetail.stock_name}</h3>
                <p style={{ margin: "2px 0 0", color: "#888", fontSize: 13 }}>{watchDetail.stock_code}</p>
              </div>
              <span style={{
                borderRadius: 999, padding: "4px 10px", fontSize: 11, fontWeight: 700,
                background: watchDetail.monitor_enabled !== false ? "#eefaf4" : "#fef3f2",
                color: watchDetail.monitor_enabled !== false ? "#00a870" : "#e34d59",
              }}>{watchDetail.monitor_enabled !== false ? "监控中" : "已暂停"}</span>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "6px 16px" }}>
              <Field label="板块" value={watchDetail.sector_name} />
              <Field label="标签" value={(watchDetail.labels || []).join(" / ")} />
              <Field label="交易体系" value={watchDetail.trading_system} />
              <Field label="入选来源" value={watchDetail.entry_source || "手动"} />
              <Field label="入选时间" value={String(watchDetail.created_at || "").slice(0, 10)} />
              <Field label="操作策略" value={(watchDetail.operation_strategies || []).join(",")} />
              <Field label="买点类型" value={(watchDetail.buy_point_types || []).join(",")} />
              {watchDetail.entry_price != null && <Field label="入选价" value={watchDetail.entry_price} />}
              {watchDetail.key_observe_price != null && <Field label="关键观察价" value={`${watchDetail.key_observe_price}`} />}
              {watchDetail.auto_remove_price != null && <Field label="自动剔除价" value={`${watchDetail.auto_remove_price}`} />}
            </div>

            {(watchDetail.entry_reason || watchDetail.invalid_condition || watchDetail.user_remark || watchDetail.remark) && (
              <div style={{ borderRadius: 12, background: "#f7f9ff", padding: 12, display: "grid", gap: 6 }}>
                {watchDetail.entry_reason && <div style={{ fontSize: 13 }}><span style={{ color: "#888" }}>入选理由：</span><span style={{ color: "#334" }}>{watchDetail.entry_reason}</span></div>}
                {watchDetail.invalid_condition && <div style={{ fontSize: 13 }}><span style={{ color: "#888" }}>失效条件：</span><span style={{ color: "#334" }}>{watchDetail.invalid_condition}</span></div>}
                {watchDetail.user_remark && <div style={{ fontSize: 13 }}><span style={{ color: "#888" }}>用户备注：</span><span style={{ color: "#334" }}>{watchDetail.user_remark}</span></div>}
                {watchDetail.remark && <div style={{ fontSize: 13 }}><span style={{ color: "#888" }}>备注：</span><span style={{ color: "#334" }}>{watchDetail.remark}</span></div>}
              </div>
            )}

            <p style={{ margin: 0, fontSize: 11, color: "#aaa" }}>仅作为交易辅助，请结合个人交易规则确认。</p>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
              <Button block fill="outline" size="small" onClick={() => openEdit(watchDetail)}>编辑</Button>
              <Button block fill="none" size="small" style={{ fontSize: 12 }} onClick={() => {
                const code = (watchDetail.stock_code || "").trim().toUpperCase();
                const marketPrefix = code.match(/^(SH|SZ|BJ)\d{6}$/);
                const marketSuffix = code.match(/^(\d{6})\.(SH|SZ|BJ)$/);
                const xq = marketPrefix ? code : (marketSuffix ? `${marketSuffix[2]}${marketSuffix[1]}` : code);
                window.open(`https://xueqiu.com/S/${xq}`, "_blank");
              }}>雪球</Button>
              <Button block fill="outline" size="small" onClick={() => { setWatchDetail(null); setEditing(null); }}>关闭</Button>
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
              <Selector options={tradingSystemOptions.filter((item) => item.value)} value={[editing.trading_system]} onChange={(value) => setEditing({ ...editing, trading_system: value[0] })} />
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
              <div style={{ display: "grid", gap: 4 }}>
                <span style={{ color: "#5b6d8a", fontSize: 12, fontWeight: 700 }}>关键观察价</span>
                <Input type="number" value={editing.key_observe_price} placeholder="12.00" onChange={(value) => setEditing({ ...editing, key_observe_price: value })} />
              </div>
              <div style={{ display: "grid", gap: 4 }}>
                <span style={{ color: "#5b6d8a", fontSize: 12, fontWeight: 700 }}>自动剔除价</span>
                <Input type="number" value={editing.auto_remove_price} placeholder="跌破后软剔除" onChange={(value) => setEditing({ ...editing, auto_remove_price: value })} />
              </div>
            </div>

            <div style={{ display: "grid", gap: 10 }}>
              <div style={{ display: "grid", gap: 4 }}>
                <span style={{ color: "#5b6d8a", fontSize: 12, fontWeight: 700 }}>入选理由</span>
                <TextArea value={editing.entry_reason} rows={2} placeholder="为什么值得进入观察池" onChange={(value) => setEditing({ ...editing, entry_reason: value })} />
              </div>
              <div style={{ display: "grid", gap: 4 }}>
                <span style={{ color: "#5b6d8a", fontSize: 12, fontWeight: 700 }}>失效条件</span>
                <TextArea value={editing.invalid_condition} rows={2} placeholder="什么情况下不再观察" onChange={(value) => setEditing({ ...editing, invalid_condition: value })} />
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
