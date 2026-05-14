import { useEffect, useMemo, useState } from "react";
import { Button, Dialog, ErrorBlock, Input, Popup, Selector, SpinLoading, TextArea, Toast } from "antd-mobile";
import { apiDelete, apiGet, apiPost, apiPut } from "../api/client";
import { PageShell } from "../components/PageShell";
import { StockLink } from "../components/StockLink";

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

function nextAction(item: any) {
  const status = item.lifecycle_status || item.pool_status;
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
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (tradingSystem) params.set("trading_system", tradingSystem);
      if (lifecycleStatus) params.set("lifecycle_status", lifecycleStatus);
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
  const todayStr = new Date().toISOString().slice(0, 10);
  const todayNew = useMemo(() => items.filter((item) => String(item.created_at || "").slice(0, 10) === todayStr).length, [items, todayStr]);
  const todaySignals = useMemo(() => signals.filter((s) => (s.trigger_date || "").slice(0, 10) === todayStr).length, [signals, todayStr]);

  function openEdit(item: any) {
    setEditing({
      watch_id: item.watch_id,
      stock_name: item.stock_name,
      stock_code: item.stock_code,
      trading_system: item.trading_system || "uptrend",
      entry_reason: item.entry_reason || item.reason || "",
      key_observe_price: item.key_observe_price != null ? String(item.key_observe_price) : "",
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
    await apiPut(`/h5/watch-pool/${editing.watch_id}`, {
      trading_system: editing.trading_system,
      entry_reason: editing.entry_reason,
      key_observe_price: Number(editing.key_observe_price),
      invalid_condition: editing.invalid_condition,
      risk_tags: editing.risk_tags,
      user_remark: editing.user_remark,
      adjust_reason: editing.adjust_reason,
    });
    Toast.show({ content: "观察参数已调整" });
    setEditing(null);
    load();
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
    const confirmed = await Dialog.confirm({ content: `确认剔除 ${item.stock_name}？历史记录会保留。`, confirmText: "确认剔除", cancelText: "取消" });
    if (!confirmed) return;
    await apiDelete(`/h5/watch-pool/${item.watch_id}`);
    Toast.show({ content: "已剔除" });
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

  function renderSignalCard(item: any) {
    const canConfirmBuy = item.signal_status === "buy_pending_confirm";
    return (
      <div key={item.signal_id} className="row-card" style={{ display: "grid", gap: 10 }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 10 }}>
          <div>
            <strong><StockLink stockName={item.stock_name} stockCode={item.stock_code} info={item} /></strong>
            <p style={{ marginTop: 4 }}>{labelOf(tradingSystemOptions, item.trading_system)} / {signalTypeLabels[item.signal_type] || item.signal_type}</p>
          </div>
          <span className="score-badge">{item.signal_level}</span>
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
            <strong><StockLink stockName={item.stock_name} stockCode={item.stock_code} info={item} /></strong>
            <p style={{ marginTop: 4 }}>{labelOf(tradingSystemOptions, item.trading_system)} / {item.trade_status || "-"}</p>
          </div>
          <span className="score-badge">{formatMoney(item.pnl_amount)}</span>
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
            <div className="card-headline"><span className="icon-badge">{todayNew}</span><h2>观察</h2></div>
            <span className="soft-tag">今日新增 {todayNew} / 当前 {items.length} / 总览 {watchSummary.watching ?? "-"}</span>
          </div>
          <div style={{ display: "grid", gap: 10, marginBottom: 14 }}>
            <Selector options={tradingSystemOptions} value={[tradingSystem]} onChange={(value) => setTradingSystem((value[0] as string) || "")} />
            <Selector options={lifecycleOptions} value={[lifecycleStatus]} onChange={(value) => setLifecycleStatus((value[0] as string) || "")} />
          </div>
          {items.length ? (
            <div className="stack-list">
              {items.map((item) => (
                <div key={item.watch_id} className="row-card" style={{ display: "grid", gap: 10 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", gap: 10 }}>
                    <div>
                      <strong><StockLink stockName={item.stock_name} stockCode={item.stock_code} info={item} /></strong>
                      <p style={{ marginTop: 4 }}>{labelOf(tradingSystemOptions, item.trading_system)} / {labelOf(lifecycleOptions, item.lifecycle_status || item.pool_status)}</p>
                    </div>
                    <span className="soft-tag">{item.monitor_enabled === false || item.signal_enabled === false ? "监控关闭" : "监控中"}</span>
                  </div>
                  <div style={{ display: "grid", gap: 4, color: "#64748b", fontSize: 13, lineHeight: 1.55 }}>
                    <p>入选来源：{item.entry_source || item.source_type || item.source_platform || "manual"} {item.source_rank ? `#${item.source_rank}` : ""}</p>
                    <p>入选理由：{item.entry_reason || item.reason || item.source_reason || "用户手动关注"}</p>
                    <p>关键观察价：{item.key_observe_price ?? "-"}</p>
                    <p>失效条件：{item.invalid_condition || "-"}</p>
                    <p>风险标签：{(item.risk_tags || []).map((tag: string) => riskTagLabels[tag] || tag).join(" / ") || "-"}</p>
                    <p>下一步动作：{nextAction(item)}</p>
                    {item.user_remark ? <p>备注：{item.user_remark}</p> : null}
                  </div>
                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                    <Button size="mini" fill="outline" onClick={() => openEdit(item)}>调整观察参数</Button>
                    <Button size="mini" fill="outline" onClick={() => markInvalid(item)}>标记失效</Button>
                    <Button size="mini" fill="outline" onClick={() => toggleMonitor(item)}>{item.monitor_enabled === false || item.signal_enabled === false ? "开启监控" : "关闭监控"}</Button>
                    <Button size="mini" fill="outline" onClick={() => removeWatch(item)}>剔除</Button>
                    <Button size="mini" color="danger" fill="outline" onClick={() => blacklistWatch(item)}>黑名单</Button>
                  </div>
                </div>
              ))}
            </div>
          ) : <div className="empty-panel">暂无符合筛选条件的自选股</div>}
        </article>
      )}

      {tab === "signal" && (
        <article className="feature-card">
          <div className="card-head">
            <div className="card-headline"><span className="icon-badge">{todaySignals}</span><h2>信号</h2></div>
            <span className="soft-tag">今日 {todaySignals} / 总数 {signalSummary.total ?? signals.length}</span>
          </div>
          <div className="stack-list">
            {buySignals.map(renderSignalCard)}
            {riskSignals.map(renderSignalCard)}
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
          {trades.length ? <div className="stack-list">{trades.map(renderTradeCard)}</div> : <div className="empty-panel">暂无交易记录</div>}
        </article>
      )}

      <Popup visible={Boolean(editing)} onMaskClick={() => setEditing(null)} bodyStyle={{ borderTopLeftRadius: 22, borderTopRightRadius: 22, padding: 18, maxHeight: "86vh", overflowY: "auto" }}>
        {editing && (
          <div style={{ display: "grid", gap: 12 }}>
            <div><h3 style={{ margin: 0 }}>调整观察参数</h3><p style={{ margin: "4px 0 0", color: "#72819b" }}>{editing.stock_name} {editing.stock_code}</p></div>
            <Selector options={tradingSystemOptions.filter((item) => item.value)} value={[editing.trading_system]} onChange={(value) => setEditing({ ...editing, trading_system: value[0] })} />
            <TextArea value={editing.entry_reason} rows={3} placeholder="入选理由" onChange={(value) => setEditing({ ...editing, entry_reason: value })} />
            <Input type="number" value={editing.key_observe_price} placeholder="关键观察价" onChange={(value) => setEditing({ ...editing, key_observe_price: value })} />
            <TextArea value={editing.invalid_condition} rows={3} placeholder="失效条件" onChange={(value) => setEditing({ ...editing, invalid_condition: value })} />
            <Selector multiple options={Object.entries(riskTagLabels).map(([value, label]) => ({ value, label }))} value={editing.risk_tags} onChange={(value) => setEditing({ ...editing, risk_tags: value as string[] })} />
            <TextArea value={editing.user_remark} rows={3} placeholder="用户备注" onChange={(value) => setEditing({ ...editing, user_remark: value })} />
            <TextArea value={editing.adjust_reason} rows={2} placeholder="本次调整原因，必填" onChange={(value) => setEditing({ ...editing, adjust_reason: value })} />
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}><Button block onClick={() => setEditing(null)}>取消</Button><Button block color="primary" onClick={saveEdit}>保存</Button></div>
          </div>
        )}
      </Popup>

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
