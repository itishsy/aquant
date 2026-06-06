import { useEffect, useState } from "react";
import { Button, ErrorBlock, Input, Popup, SpinLoading, Toast } from "antd-mobile";
import { apiGet, apiPost, apiPut } from "../api/client";
import type { TradingParam, TradingRule, TradingRuleBinding, TradingSystem } from "./admin/types";
import { FormLabel, PlaceholderCard, StatCard, TableCard } from "./admin/components/common";
import { RuleLibraryPanel } from "./admin/panels/RuleLibraryPanel";
import { TaskPanel } from "./admin/panels/TaskPanel";
import { TradingSystemPanelEditor } from "./admin/panels/TradingSystemPanelEditor";

const SECTIONS = [
  { key: "dashboard", label: "工作台" },
  { key: "watch", label: "自选交易管理" },
  { key: "tradingSystems", label: "交易体系" },
  { key: "ruleLibrary", label: "规则库" },
  { key: "sources", label: "数据源管理" },
  { key: "tasks", label: "采集任务管理" },
  { key: "mappings", label: "字段映射管理" },
  { key: "strategies", label: "策略管理" },
  { key: "dictionaries", label: "字典管理" },
  { key: "reviewTemplates", label: "复盘模板管理" },
  { key: "notifications", label: "消息推送管理" },
  { key: "logs", label: "日志中心" },
  { key: "security", label: "账号与安全" },
];

export function AdminPage() {
  const [active, setActive] = useState("dashboard");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [overview, setOverview] = useState<any>(null);
  const [tasks, setTasks] = useState<any[]>([]);
  const [dictionaries, setDictionaries] = useState<any[]>([]);
  const [logs, setLogs] = useState<any[]>([]);
  const [sources, setSources] = useState<any[]>([]);
  const [strategies, setStrategies] = useState<any[]>([]);
  const [templates, setTemplates] = useState<any[]>([]);
  const [tradingSystems, setTradingSystems] = useState<TradingSystem[]>([]);
  const [tradingRules, setTradingRules] = useState<TradingRule[]>([]);
  const [registeredExecutors, setRegisteredExecutors] = useState<string[]>([]);
  const [selectedSystemCode, setSelectedSystemCode] = useState("");
  const [selectedSystem, setSelectedSystem] = useState<TradingSystem | null>(null);
  const [tradingParams, setTradingParams] = useState<TradingParam[]>([]);
  const [tradingBindings, setTradingBindings] = useState<TradingRuleBinding[]>([]);
  const [tradingLoading, setTradingLoading] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  // Watch management
  const [watches, setWatches] = useState<any[]>([]);
  const [signals, setSignals] = useState<any[]>([]);
  const [trades, setTrades] = useState<any[]>([]);
  const [watchForm, setWatchForm] = useState({ code: "", name: "", system: "uptrend", observePrice: "", removePrice: "", invalidCond: "", reason: "后台手动添加" });
  const [signalForm, setSignalForm] = useState({ watchId: "", strategy: "manual_admin_signal", buyPoint: "b15_divergence", price: "", stopLoss: "", target: "", reason: "后台手动添加信号", confirmed: false });
  const [tradeForm, setTradeForm] = useState({ signalId: "", price: "", amount: "", position: "", stopLoss: "", target: "", reason: "后台手动确认交易" });
  const [watchSubmitting, setWatchSubmitting] = useState(false);
  const [signalSubmitting, setSignalSubmitting] = useState(false);
  const [tradeSubmitting, setTradeSubmitting] = useState(false);
  const [watchManageTab, setWatchManageTab] = useState<"watch" | "signal" | "trade">("watch");
  const [watchEditorOpen, setWatchEditorOpen] = useState(false);

  async function loadAll() {
    setLoading(true);
    try {
      const safeGet = async <T,>(path: string, fallback: T): Promise<T> => {
        try {
          return await apiGet<T>(path);
        } catch (err) {
          console.warn(`admin load failed: ${path}`, err);
          return fallback;
        }
      };
      const [ov, tk, dc, lg, src, st, tpl, wl, sg, tr, ts, rules, executors] = await Promise.all([
        safeGet<any>("/admin/dashboard/overview", {}),
        safeGet<any[]>("/admin/tasks", []),
        safeGet<any[]>("/admin/dictionaries", []),
        safeGet<any[]>("/admin/task-logs", []),
        safeGet<any[]>("/admin/data-sources", []),
        safeGet<any[]>("/admin/strategies", []),
        safeGet<any[]>("/admin/notification-templates", []),
        safeGet<any[]>("/admin/watch-pool", []),
        safeGet<any[]>("/admin/watch-signals", []),
        safeGet<any[]>("/admin/watch-trades", []),
        safeGet<TradingSystem[]>("/admin/trading-systems", []),
        safeGet<TradingRule[]>("/admin/trading-rules", []),
        safeGet<string[]>("/admin/trading-executors", []),
      ]);
      setOverview(ov || {});
      setTasks(tk || []);
      setDictionaries(dc || []);
      setLogs(lg || []);
      setSources(src || []);
      setStrategies(st || []);
      setTemplates(tpl || []);
      setWatches(wl || []);
      setSignals(sg || []);
      setTrades(tr || []);
      setTradingSystems(ts || []);
      setTradingRules(rules || []);
      setRegisteredExecutors(executors || []);
      if (!selectedSystemCode && ts?.length) {
        setSelectedSystemCode(ts[0].system_code);
      }
      setError("");
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadAll();
  }, []);

  useEffect(() => {
    if (!selectedSystemCode) return;
    let ignore = false;
    async function loadTradingSystem() {
      setTradingLoading(true);
      try {
        const [detail, params, bindings] = await Promise.all([
          apiGet<TradingSystem>(`/admin/trading-systems/${selectedSystemCode}`),
          apiGet<TradingParam[]>(`/admin/trading-systems/${selectedSystemCode}/params`),
          apiGet<TradingRuleBinding[]>(`/admin/trading-systems/${selectedSystemCode}/rules`),
        ]);
        if (!ignore) {
          setSelectedSystem(detail);
          setTradingParams(params || []);
          setTradingBindings(bindings || []);
        }
      } catch (err) {
        if (!ignore) {
          setSelectedSystem(null);
          setTradingParams([]);
          setTradingBindings([]);
          Toast.show({ content: String(err) || "交易体系加载失败" });
        }
      } finally {
        if (!ignore) {
          setTradingLoading(false);
        }
      }
    }
    loadTradingSystem();
    return () => {
      ignore = true;
    };
  }, [selectedSystemCode]);

  async function addWatch() {
    if (!watchForm.code || !watchForm.name) { Toast.show({ content: "请填写代码和名称" }); return; }
    if (!watchForm.observePrice || Number(watchForm.observePrice) <= 0) { Toast.show({ content: "请填写有效观察价" }); return; }
    if (!watchForm.invalidCond.trim()) { Toast.show({ content: "请填写失效条件" }); return; }
    if (watchForm.system !== "uptrend" && watchForm.removePrice && Number(watchForm.removePrice) <= 0) { Toast.show({ content: "自动剔除价必须大于0" }); return; }
    setWatchSubmitting(true);
    try {
      await apiPost("/admin/watch-pool", {
        stock_code: watchForm.code, stock_name: watchForm.name,
        trading_system: watchForm.system || "uptrend",
        entry_reason: watchForm.reason || "后台手动添加",
        key_observe_price: watchForm.observePrice ? Number(watchForm.observePrice) : undefined,
        auto_remove_price: watchForm.system === "uptrend" ? undefined : watchForm.removePrice ? Number(watchForm.removePrice) : undefined,
        invalid_condition: watchForm.invalidCond,
      });
      Toast.show({ content: "观察股已添加" });
      setWatchForm({ code: "", name: "", system: "uptrend", observePrice: "", removePrice: "", invalidCond: "", reason: "后台手动添加" });
      setWatchEditorOpen(false);
      loadAll();
    } catch (err) { Toast.show({ content: String(err) || "添加失败" }); }
    finally { setWatchSubmitting(false); }
  }

  async function addSignal() {
    const wid = parseInt(signalForm.watchId);
    if (!wid) { Toast.show({ content: "请输入Watch ID" }); return; }
    if (signalForm.price && Number(signalForm.price) <= 0) { Toast.show({ content: "触发价必须大于0" }); return; }
    if (signalForm.stopLoss && Number(signalForm.stopLoss) <= 0) { Toast.show({ content: "止损价必须大于0" }); return; }
    if (signalForm.target && Number(signalForm.target) <= 0) { Toast.show({ content: "目标价必须大于0" }); return; }
    setSignalSubmitting(true);
    try {
      await apiPost(`/admin/watch-pool/${wid}/signals`, {
        strategy_name: signalForm.strategy || "manual_admin_signal",
        buy_point_type: signalForm.buyPoint || "b15_divergence",
        trigger_price: signalForm.price ? Number(signalForm.price) : undefined,
        stop_loss_price: signalForm.stopLoss ? Number(signalForm.stopLoss) : undefined,
        target_price: signalForm.target ? Number(signalForm.target) : undefined,
        trigger_reason: signalForm.reason || "后台手动添加信号",
        buy_point_confirmed: signalForm.confirmed,
      });
      Toast.show({ content: "信号已添加" });
      setSignalForm({ watchId: "", strategy: "manual_admin_signal", buyPoint: "b15_divergence", price: "", stopLoss: "", target: "", reason: "后台手动添加信号", confirmed: false });
      setWatchEditorOpen(false);
      loadAll();
    } catch (err) { Toast.show({ content: String(err) || "添加失败" }); }
    finally { setSignalSubmitting(false); }
  }

  async function addTrade() {
    const sid = parseInt(tradeForm.signalId);
    if (!sid) { Toast.show({ content: "请输入Signal ID" }); return; }
    if (!tradeForm.price || Number(tradeForm.price) <= 0) { Toast.show({ content: "请填写有效买入价" }); return; }
    if (!tradeForm.amount || Number(tradeForm.amount) <= 0) { Toast.show({ content: "请填写有效数量" }); return; }
    if (tradeForm.position && Number(tradeForm.position) <= 0) { Toast.show({ content: "仓位必须大于0" }); return; }
    if (tradeForm.stopLoss && Number(tradeForm.stopLoss) <= 0) { Toast.show({ content: "止损价必须大于0" }); return; }
    if (tradeForm.target && Number(tradeForm.target) <= 0) { Toast.show({ content: "目标价必须大于0" }); return; }
    setTradeSubmitting(true);
    try {
      await apiPost(`/admin/watch-signals/${sid}/create-trade`, {
        buy_price: Number(tradeForm.price),
        amount: Number(tradeForm.amount),
        position_ratio: tradeForm.position ? Number(tradeForm.position) : undefined,
        stop_loss_price: tradeForm.stopLoss ? Number(tradeForm.stopLoss) : undefined,
        target_price: tradeForm.target ? Number(tradeForm.target) : undefined,
        buy_reason: tradeForm.reason || "后台手动确认交易",
      });
      Toast.show({ content: "交易已添加" });
      setTradeForm({ signalId: "", price: "", amount: "", position: "", stopLoss: "", target: "", reason: "后台手动确认交易" });
      setWatchEditorOpen(false);
      loadAll();
    } catch (err) { Toast.show({ content: String(err) || "添加失败" }); }
    finally { setTradeSubmitting(false); }
  }

  const activeLabel = SECTIONS.find((item) => item.key === active)?.label || "";

  return (
    <div style={{ minHeight: "100vh", background: "#f4f6fb" }}>
      <header style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "10px 14px", background: "linear-gradient(90deg, #1b2447, #334497)", color: "#fff", position: "sticky", top: 0, zIndex: 100 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <Button size="mini" fill="none" style={{ color: "#fff", padding: "2px 6px" }} onClick={() => setMenuOpen(!menuOpen)}>
            {menuOpen ? "✕" : "☰"}
          </Button>
          <strong style={{ fontSize: 15 }}>Aquant · {activeLabel}</strong>
        </div>
        <Button size="mini" color="primary" onClick={loadAll}>刷新</Button>
      </header>

      {menuOpen && (
        <nav style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 4, padding: "8px 12px", background: "#fff", borderBottom: "1px solid #e8ecf4" }}>
          {SECTIONS.map((item) => (
            <button
              key={item.key}
              onClick={() => { setActive(item.key); setMenuOpen(false); }}
              style={{
                border: 0, borderRadius: 10, padding: "9px 8px", textAlign: "center", fontSize: 12, fontWeight: 700,
                color: active === item.key ? "#fff" : "#344054",
                background: active === item.key ? "linear-gradient(135deg, #5570ff, #4052d2)" : "#f4f6fb",
              }}
            >
              {item.label}
            </button>
          ))}
        </nav>
      )}

      <div style={{ padding: 12 }}>

        <section style={{ display: "grid", gap: 14 }}>
          {loading && <div style={{ display: "grid", placeItems: "center", minHeight: 240 }}><SpinLoading /></div>}
          {!loading && error && <ErrorBlock title="后台加载失败" description={error} />}

          {!loading && !error && active === "dashboard" && (
            <>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 12 }}>
                <StatCard label="自选数量" value={overview?.watch_count ?? 0} />
                <StatCard label="信号数量" value={overview?.signal_count ?? 0} />
                <StatCard label="交易数量" value={overview?.trade_count ?? 0} />
                <StatCard label="任务数量" value={tasks.length} />
              </div>
              <PlaceholderCard label="工作台" />
            </>
          )}

          {!loading && !error && active === "watch" && (
            <>
              <div style={{ borderRadius: 14, background: "#fff", padding: 14, display: "grid", gap: 12 }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10, flexWrap: "wrap" }}>
                  <div>
                    <h3 style={{ margin: 0, color: "#1d2d50" }}>自选交易管理</h3>
                    <p style={{ margin: "4px 0 0", color: "#667085", fontSize: 12 }}>
                      观察股 {watches.length} / 信号 {signals.length} / 交易 {trades.length}
                    </p>
                  </div>
                  <Button size="small" color="primary" onClick={() => setWatchEditorOpen(true)}>
                    {watchManageTab === "watch" ? "添加观察股" : watchManageTab === "signal" ? "添加信号" : "添加交易"}
                  </Button>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 8 }}>
                  {[
                    ["watch", "观察股管理", watches.length],
                    ["signal", "信号管理", signals.length],
                    ["trade", "交易管理", trades.length],
                  ].map(([key, label, count]) => (
                    <button
                      key={String(key)}
                      onClick={() => setWatchManageTab(key as "watch" | "signal" | "trade")}
                      style={{
                        border: 0,
                        borderRadius: 12,
                        padding: "10px 8px",
                        background: watchManageTab === key ? "linear-gradient(135deg, #5570ff, #4052d2)" : "#f4f6fb",
                        color: watchManageTab === key ? "#fff" : "#344054",
                        fontSize: 13,
                        fontWeight: 800,
                        cursor: "pointer",
                      }}
                    >
                      {label}<span style={{ marginLeft: 4, opacity: 0.8 }}>{count}</span>
                    </button>
                  ))}
                </div>

                {watchManageTab === "watch" && (
                  <div style={{ display: "grid", gap: 8 }}>
                    {watches.length ? watches.map((w: any) => (
                      <div key={w.watch_id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10, padding: "10px 0", borderBottom: "1px solid #f0f0f0", fontSize: 12 }}>
                        <div style={{ minWidth: 0 }}>
                          <strong style={{ color: "#1d2d50", fontSize: 13 }}>[{w.watch_id}] {w.stock_name}</strong>
                          <span style={{ color: "#888", marginLeft: 4 }}>{w.stock_code}</span>
                          <div style={{ marginTop: 3, color: "#667085" }}>
                            {w.trading_system_name || w.trading_system_code || w.trading_system || "-"} / {w.status || "-"} / {w.system_stage || "-"}
                          </div>
                        </div>
                        <div style={{ display: "flex", gap: 4, flexShrink: 0, flexWrap: "wrap", justifyContent: "flex-end" }}>
                          <Button size="mini" fill="outline" onClick={async () => {
                            const ok = window.confirm(`确认将 ${w.stock_name} 标记为失效？`);
                            if (!ok) return;
                            await apiPost(`/admin/watch-pool/${w.watch_id}/invalid`, { invalid_reason: "后台标记失效" });
                            Toast.show({ content: "已标记失效" }); loadAll();
                          }}>失效</Button>
                          <Button size="mini" fill="outline" onClick={async () => {
                            const ok = window.confirm(`确认剔除 ${w.stock_name}？`);
                            if (!ok) return;
                            await apiPost(`/admin/watch-pool/${w.watch_id}/remove`, {});
                            Toast.show({ content: "已剔除" }); loadAll();
                          }}>剔除</Button>
                          <Button size="mini" color="danger" fill="outline" onClick={async () => {
                            const ok = window.confirm(`确认将 ${w.stock_name} 加入黑名单？`);
                            if (!ok) return;
                            await apiPost(`/admin/watch-pool/${w.watch_id}/blacklist`, { reason: "后台加入黑名单" });
                            Toast.show({ content: "已加入黑名单" }); loadAll();
                          }}>黑名单</Button>
                        </div>
                      </div>
                    )) : <div style={{ color: "#98a2b3", fontSize: 13, textAlign: "center", padding: 20 }}>暂无观察股</div>}
                  </div>
                )}

                {watchManageTab === "signal" && (
                  <div style={{ display: "grid", gap: 8 }}>
                    {signals.length ? signals.map((s: any) => (
                      <div key={s.signal_id} style={{ padding: "10px 0", borderBottom: "1px solid #f0f0f0", fontSize: 12 }}>
                        <strong style={{ color: "#1d2d50", fontSize: 13 }}>[{s.signal_id}] {s.stock_name}</strong>
                        <span style={{ color: "#888", marginLeft: 4 }}>{s.stock_code}</span>
                        <div style={{ marginTop: 3, color: "#667085" }}>
                          watch={s.watch_id} / {s.rule_name || s.buy_point_type || s.rule_code || "-"} / {s.signal_type || "-"} / {s.signal_status || "-"}
                        </div>
                      </div>
                    )) : <div style={{ color: "#98a2b3", fontSize: 13, textAlign: "center", padding: 20 }}>暂无信号</div>}
                  </div>
                )}

                {watchManageTab === "trade" && (
                  <div style={{ display: "grid", gap: 8 }}>
                    {trades.length ? trades.map((t: any) => (
                      <div key={t.trade_id} style={{ padding: "10px 0", borderBottom: "1px solid #f0f0f0", fontSize: 12 }}>
                        <strong style={{ color: "#1d2d50", fontSize: 13 }}>[{t.trade_id}] {t.stock_name}</strong>
                        <span style={{ color: "#888", marginLeft: 4 }}>{t.stock_code}</span>
                        <div style={{ marginTop: 3, color: "#667085" }}>
                          signal={t.signal_id || "-"} / {t.trade_status || "-"} / 买入 {t.total_buy_amount || "-"}@{t.first_buy_price || "-"}
                        </div>
                      </div>
                    )) : <div style={{ color: "#98a2b3", fontSize: 13, textAlign: "center", padding: 20 }}>暂无交易</div>}
                  </div>
                )}
              </div>

              <Popup
                visible={watchEditorOpen}
                onMaskClick={() => setWatchEditorOpen(false)}
                bodyStyle={{ borderTopLeftRadius: 18, borderTopRightRadius: 18, padding: 14, maxHeight: "82vh", overflowY: "auto" }}
              >
                <div style={{ display: "grid", gap: 12 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
                    <h3 style={{ margin: 0, color: "#1d2d50" }}>
                      {watchManageTab === "watch" ? "添加观察股" : watchManageTab === "signal" ? "添加信号" : "添加交易"}
                    </h3>
                    <Button size="mini" fill="none" onClick={() => setWatchEditorOpen(false)}>关闭</Button>
                  </div>

                  {watchManageTab === "watch" && (
                    <div style={{ display: "grid", gap: 8 }}>
                      <FormLabel text="股票代码" /><Input placeholder="603019.SH" value={watchForm.code} onChange={(v) => setWatchForm({...watchForm, code: v})} />
                      <FormLabel text="股票名称" /><Input placeholder="中科曙光" value={watchForm.name} onChange={(v) => setWatchForm({...watchForm, name: v})} />
                      <FormLabel text="交易体系" /><Input placeholder="uptrend" value={watchForm.system} onChange={(v) => setWatchForm({...watchForm, system: v})} />
                      <FormLabel text="观察价" /><Input placeholder="50" value={watchForm.observePrice} onChange={(v) => setWatchForm({...watchForm, observePrice: v})} />
                      {watchForm.system !== "uptrend" && <><FormLabel text="自动剔除价" /><Input placeholder="48" value={watchForm.removePrice} onChange={(v) => setWatchForm({...watchForm, removePrice: v})} /></>}
                      <FormLabel text="失效条件" /><Input placeholder="跌破观察位" value={watchForm.invalidCond} onChange={(v) => setWatchForm({...watchForm, invalidCond: v})} />
                      <FormLabel text="入选理由" /><Input placeholder="后台手动添加" value={watchForm.reason} onChange={(v) => setWatchForm({...watchForm, reason: v})} />
                      <Button block color="primary" size="small" loading={watchSubmitting} onClick={addWatch}>添加观察股</Button>
                    </div>
                  )}

                  {watchManageTab === "signal" && (
                    <div style={{ display: "grid", gap: 8 }}>
                      <FormLabel text="Watch ID" /><Input placeholder="1" value={signalForm.watchId} onChange={(v) => setSignalForm({...signalForm, watchId: v})} />
                      <FormLabel text="策略名称" /><Input placeholder="manual_admin_signal" value={signalForm.strategy} onChange={(v) => setSignalForm({...signalForm, strategy: v})} />
                      <FormLabel text="买点类型" /><Input placeholder="b15_divergence" value={signalForm.buyPoint} onChange={(v) => setSignalForm({...signalForm, buyPoint: v})} />
                      <FormLabel text="触发价" /><Input placeholder="50.5" value={signalForm.price} onChange={(v) => setSignalForm({...signalForm, price: v})} />
                      <FormLabel text="止损价" /><Input placeholder="48" value={signalForm.stopLoss} onChange={(v) => setSignalForm({...signalForm, stopLoss: v})} />
                      <FormLabel text="目标价" /><Input placeholder="55" value={signalForm.target} onChange={(v) => setSignalForm({...signalForm, target: v})} />
                      <FormLabel text="触发原因" /><Input placeholder="后台手动添加信号" value={signalForm.reason} onChange={(v) => setSignalForm({...signalForm, reason: v})} />
                      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                        <input type="checkbox" checked={signalForm.confirmed} onChange={(e) => setSignalForm({...signalForm, confirmed: e.target.checked})} />
                        <span style={{ fontSize: 12 }}>买点已确认</span>
                      </div>
                      <Button block color="primary" size="small" loading={signalSubmitting} onClick={addSignal}>添加信号</Button>
                    </div>
                  )}

                  {watchManageTab === "trade" && (
                    <div style={{ display: "grid", gap: 8 }}>
                      <FormLabel text="Signal ID" /><Input placeholder="1" value={tradeForm.signalId} onChange={(v) => setTradeForm({...tradeForm, signalId: v})} />
                      <FormLabel text="买入价" /><Input placeholder="50.5" value={tradeForm.price} onChange={(v) => setTradeForm({...tradeForm, price: v})} />
                      <FormLabel text="数量" /><Input placeholder="100" value={tradeForm.amount} onChange={(v) => setTradeForm({...tradeForm, amount: v})} />
                      <FormLabel text="仓位" /><Input placeholder="0.2" value={tradeForm.position} onChange={(v) => setTradeForm({...tradeForm, position: v})} />
                      <FormLabel text="止损价" /><Input placeholder="48" value={tradeForm.stopLoss} onChange={(v) => setTradeForm({...tradeForm, stopLoss: v})} />
                      <FormLabel text="目标价" /><Input placeholder="55" value={tradeForm.target} onChange={(v) => setTradeForm({...tradeForm, target: v})} />
                      <FormLabel text="买入理由" /><Input placeholder="后台手动确认交易" value={tradeForm.reason} onChange={(v) => setTradeForm({...tradeForm, reason: v})} />
                      <Button block color="primary" size="small" loading={tradeSubmitting} onClick={addTrade}>添加交易</Button>
                    </div>
                  )}
                </div>
              </Popup>
            </>
          )}

          {!loading && !error && active === "tradingSystems" && (
            <TradingSystemPanelEditor
              systems={tradingSystems}
              selectedCode={selectedSystemCode}
              selectedSystem={selectedSystem}
              params={tradingParams}
              bindings={tradingBindings}
              loading={tradingLoading}
              onSelect={setSelectedSystemCode}
              rules={tradingRules}
              executors={registeredExecutors}
              onSaved={loadAll}
              onSystemUpdated={(data) => {
                setSelectedSystem(data);
                setTradingSystems((prev) => {
                  const exists = prev.some((s) => s.system_code === data.system_code);
                  return exists
                    ? prev.map((s) => s.system_code === data.system_code ? data : s)
                    : [...prev, data];
                });
              }}
            />
          )}

          {!loading && !error && active === "ruleLibrary" && (
            <RuleLibraryPanel
              rules={tradingRules}
              executors={registeredExecutors}
              onSaved={loadAll}
            />
          )}

          {!loading && !error && active === "tasks" && (
            <TaskPanel tasks={tasks} onRun={async (task) => {
              await apiPost(`/admin/tasks/${task.task_id}/run`);
              Toast.show({ content: `已触发 ${task.task_name}` });
              loadAll();
            }} onSaveConfig={async (task, config) => {
              await apiPut(`/admin/tasks/${task.task_id}`, { config_json: config });
              Toast.show({ content: "任务配置已保存" });
              loadAll();
            }} />
          )}

          {!loading && !error && active === "tasks_legacy" && (
            <div style={{ display: "grid", gap: 10 }}>
              {tasks.map((task) => (
                <div key={task.task_id} style={{ background: "#fff", borderRadius: 14, padding: 14, display: "flex", justifyContent: "space-between", gap: 12 }}>
                  <div>
                    <strong>{task.task_name}</strong>
                    <p style={{ margin: "4px 0 0", color: "#667085" }}>{task.owner_module || "-"} · {task.enabled ? "enabled" : "disabled"}</p>
                  </div>
                  <Button size="mini" color="primary" onClick={async () => {
                    await apiPost(`/admin/tasks/${task.task_id}/run`);
                    Toast.show({ content: `已触发 ${task.task_name}` });
                    loadAll();
                  }}>手动执行</Button>
                </div>
              ))}
            </div>
          )}

          {!loading && !error && active === "dictionaries" && (
            <TableCard rows={dictionaries.map((item) => `${item.dict_type} / ${item.dict_value} / ${item.dict_label}`)} empty="暂无字典" />
          )}
          {!loading && !error && active === "sources" && <TableCard rows={sources.map((item) => `${item.source_name || item.source_code} / ${item.enabled ? "enabled" : "disabled"}`)} empty="暂无数据源" />}
          {!loading && !error && active === "strategies" && <TableCard rows={strategies.map((item) => `${item.strategy_name} / ${item.buy_point_type || "-"}`)} empty="暂无策略" />}
          {!loading && !error && active === "reviewTemplates" && <TableCard rows={templates.map((item) => `${item.template_name || item.push_type} / ${item.channel || item.review_type || "-"}`)} empty="暂无模板" />}
          {!loading && !error && active === "logs" && <TableCard rows={logs.map((item) => `${item.task_name} / ${item.run_status} / ${item.started_at || "-"}`)} empty="暂无日志" />}
          {!loading && !error && ["mappings", "notifications", "security"].includes(active) && <PlaceholderCard label={activeLabel} />}
        </section>
      </div>
    </div>
  );
}

