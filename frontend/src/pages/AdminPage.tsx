import { useEffect, useState } from "react";
import { Button, ErrorBlock, Input, SpinLoading, Toast } from "antd-mobile";
import { apiGet, apiPost, apiPut } from "../api/client";

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

type TradingSystem = {
  system_id: number;
  system_code: string;
  system_name: string;
  description: string;
  lifecycle_desc: string;
  enabled: boolean;
  sort_order: number;
};

type TradingParam = {
  param_id: number;
  system_code: string;
  param_key: string;
  param_name: string;
  param_type: string;
  required: boolean;
  default_value?: string | null;
  description: string;
  sort_order: number;
  enabled: boolean;
};

type TradingRule = {
  rule_id: number;
  rule_code: string;
  rule_name: string;
  rule_type: string;
  timeframe: string;
  executor_key: string;
  description: string;
  enabled: boolean;
};

type TradingRuleBinding = {
  binding_id: number;
  system_code: string;
  rule_code: string;
  stage: string;
  required: boolean;
  logic_group: string;
  logic_operator: string;
  enabled: boolean;
  sort_order: number;
  config_json?: Record<string, unknown>;
  rule?: TradingRule | null;
};

function FormLabel({ text }: { text: string }) {
  return <div style={{ fontSize: 12, color: "#5b6d8a", fontWeight: 700, marginBottom: 2 }}>{text}</div>;
}

function PlaceholderCard({ label }: { label: string }) {
  return (
    <div style={{ padding: 20, borderRadius: 14, background: "#fff", textAlign: "center" }}>
      <p style={{ color: "#667085", fontSize: 14 }}>{label}已接入后台框架</p>
      <p style={{ color: "#98a2b3", fontSize: 12 }}>后台写操作应继续通过 /api/admin/** 接口并记录操作日志。</p>
    </div>
  );
}

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

  async function loadAll() {
    setLoading(true);
    try {
      const [ov, tk, dc, lg, src, st, tpl, wl, sg, tr, ts, rules, executors] = await Promise.all([
        apiGet<any>("/admin/dashboard/overview"),
        apiGet<any[]>("/admin/tasks"),
        apiGet<any[]>("/admin/dictionaries"),
        apiGet<any[]>("/admin/task-logs"),
        apiGet<any[]>("/admin/data-sources"),
        apiGet<any[]>("/admin/strategies"),
        apiGet<any[]>("/admin/notification-templates"),
        apiGet<any[]>("/admin/watch-pool"),
        apiGet<any[]>("/admin/watch-signals"),
        apiGet<any[]>("/admin/watch-trades"),
        apiGet<TradingSystem[]>("/admin/trading-systems"),
        apiGet<TradingRule[]>("/admin/trading-rules"),
        apiGet<string[]>("/admin/trading-executors"),
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
    if (watchForm.removePrice && Number(watchForm.removePrice) <= 0) { Toast.show({ content: "自动剔除价必须大于0" }); return; }
    setWatchSubmitting(true);
    try {
      await apiPost("/admin/watch-pool", {
        stock_code: watchForm.code, stock_name: watchForm.name,
        trading_system: watchForm.system || "uptrend",
        entry_reason: watchForm.reason || "后台手动添加",
        key_observe_price: watchForm.observePrice ? Number(watchForm.observePrice) : undefined,
        auto_remove_price: watchForm.removePrice ? Number(watchForm.removePrice) : undefined,
        invalid_condition: watchForm.invalidCond,
      });
      Toast.show({ content: "观察股已添加" });
      setWatchForm({ code: "", name: "", system: "uptrend", observePrice: "", removePrice: "", invalidCond: "", reason: "后台手动添加" });
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
            <div style={{ display: "grid", gap: 14 }}>
              {/* Watch Pool */}
              <div style={{ borderRadius: 14, background: "#fff", padding: 14 }}>
                <h3 style={{ margin: "0 0 10px" }}>观察股管理</h3>
                <div style={{ display: "grid", gap: 8, marginBottom: 10 }}>
                  <FormLabel text="股票代码" /><Input placeholder="603019.SH" value={watchForm.code} onChange={(v) => setWatchForm({...watchForm, code: v})} />
                  <FormLabel text="股票名称" /><Input placeholder="中科曙光" value={watchForm.name} onChange={(v) => setWatchForm({...watchForm, name: v})} />
                  <FormLabel text="交易体系" /><Input placeholder="uptrend" value={watchForm.system} onChange={(v) => setWatchForm({...watchForm, system: v})} />
                  <FormLabel text="观察价" /><Input placeholder="50" value={watchForm.observePrice} onChange={(v) => setWatchForm({...watchForm, observePrice: v})} />
                  <FormLabel text="自动剔除价" /><Input placeholder="48" value={watchForm.removePrice} onChange={(v) => setWatchForm({...watchForm, removePrice: v})} />
                  <FormLabel text="失效条件" /><Input placeholder="跌破观察位" value={watchForm.invalidCond} onChange={(v) => setWatchForm({...watchForm, invalidCond: v})} />
                  <FormLabel text="入选理由" /><Input placeholder="后台手动添加" value={watchForm.reason} onChange={(v) => setWatchForm({...watchForm, reason: v})} />
                  <Button block color="primary" size="small" loading={watchSubmitting} onClick={addWatch}>添加观察股</Button>
                </div>
                {watches.length ? watches.map((w: any) => (
                  <div key={w.watch_id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 0", borderBottom: "1px solid #f0f0f0", fontSize: 12 }}>
                    <div style={{ minWidth: 0 }}>
                      <strong>[{w.watch_id}] {w.stock_name}</strong>
                      <span style={{ color: "#888", marginLeft: 4 }}>{w.stock_code}</span>
                      <span style={{ color: "#4b63ee", marginLeft: 4 }}>{w.status}</span>
                    </div>
                    <div style={{ display: "flex", gap: 4 }}>
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
                )) : <div style={{ color: "#888", fontSize: 12 }}>暂无</div>}
              </div>

              {/* Signals */}
              <div style={{ borderRadius: 14, background: "#fff", padding: 14 }}>
                <h3 style={{ margin: "0 0 10px" }}>信号管理</h3>
                <div style={{ display: "grid", gap: 8, marginBottom: 10 }}>
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
                {signals.length ? signals.map((s: any) => (
                  <div key={s.signal_id} style={{ padding: "6px 0", borderBottom: "1px solid #f0f0f0", fontSize: 12 }}>
                    [{s.signal_id}] w={s.watch_id} {s.stock_name} {s.signal_type}/{s.signal_level} {s.signal_status}
                  </div>
                )) : <div style={{ color: "#888", fontSize: 12 }}>暂无</div>}
              </div>

              {/* Trades */}
              <div style={{ borderRadius: 14, background: "#fff", padding: 14 }}>
                <h3 style={{ margin: "0 0 10px" }}>交易管理</h3>
                <div style={{ display: "grid", gap: 8, marginBottom: 10 }}>
                  <FormLabel text="Signal ID" /><Input placeholder="1" value={tradeForm.signalId} onChange={(v) => setTradeForm({...tradeForm, signalId: v})} />
                  <FormLabel text="买入价" /><Input placeholder="50.5" value={tradeForm.price} onChange={(v) => setTradeForm({...tradeForm, price: v})} />
                  <FormLabel text="数量" /><Input placeholder="100" value={tradeForm.amount} onChange={(v) => setTradeForm({...tradeForm, amount: v})} />
                  <FormLabel text="仓位" /><Input placeholder="0.2" value={tradeForm.position} onChange={(v) => setTradeForm({...tradeForm, position: v})} />
                  <FormLabel text="止损价" /><Input placeholder="48" value={tradeForm.stopLoss} onChange={(v) => setTradeForm({...tradeForm, stopLoss: v})} />
                  <FormLabel text="目标价" /><Input placeholder="55" value={tradeForm.target} onChange={(v) => setTradeForm({...tradeForm, target: v})} />
                  <FormLabel text="买入理由" /><Input placeholder="后台手动确认交易" value={tradeForm.reason} onChange={(v) => setTradeForm({...tradeForm, reason: v})} />
                  <Button block color="primary" size="small" loading={tradeSubmitting} onClick={addTrade}>添加交易</Button>
                </div>
                {trades.length ? trades.map((t: any) => (
                  <div key={t.trade_id} style={{ padding: "6px 0", borderBottom: "1px solid #f0f0f0", fontSize: 12 }}>
                    [{t.trade_id}] s={t.signal_id} {t.stock_name} {t.trade_status} 买入{t.total_buy_amount}@{t.first_buy_price}
                  </div>
                )) : <div style={{ color: "#888", fontSize: 12 }}>暂无</div>}
              </div>
            </div>
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

function StatCard({ label, value }: { label: string; value: any }) {
  return (
    <div style={{ background: "#fff", borderRadius: 14, padding: 16 }}>
      <p style={{ margin: 0, color: "#667085", fontSize: 12 }}>{label}</p>
      <strong style={{ display: "block", marginTop: 8, fontSize: 26, color: "#1d2939" }}>{value}</strong>
    </div>
  );
}

function TableCard({ rows, empty }: { rows: string[]; empty: string }) {
  return (
    <div style={{ background: "#fff", borderRadius: 14, padding: 14, display: "grid", gap: 8 }}>
      {rows.length ? rows.map((row) => (
        <div key={row} style={{ padding: "9px 10px", borderRadius: 10, background: "#f8fafc", color: "#344054", fontSize: 13 }}>{row}</div>
      )) : <div style={{ color: "#98a2b3", textAlign: "center", padding: 20 }}>{empty}</div>}
    </div>
  );
}

const WATCH_MONITOR_TASKS = new Set(["scan_watch_rules", "scan_trade_rules", "prepare_watch_kline_data", "prepare_trade_kline_data", "auto_remove_watch_pool", "update_watch_prices"]);

function taskErrorText(value?: string | null) {
  if (!value) return "-";
  return value.length > 80 ? `${value.slice(0, 80)}...` : value;
}

function taskTimeText(value?: string | null) {
  if (!value) return "未运行";
  return String(value).replace("T", " ").slice(0, 19);
}

function taskConfigSummary(config?: Record<string, any>) {
  if (!config || !Object.keys(config).length) return "未配置";
  const parts = [
    config.interval_minutes ? `间隔 ${config.interval_minutes} 分钟` : "",
    config.run_window ? `窗口 ${config.run_window}` : "",
    Array.isArray(config.timeframes) && config.timeframes.length ? `周期 ${config.timeframes.join("/")}` : "",
    config.max_requests_per_run ? `请求上限 ${config.max_requests_per_run}` : "",
    config.max_stocks_per_run ? `股票上限 ${config.max_stocks_per_run}` : "",
    config.only_trade_day ? "仅交易日" : "",
  ].filter(Boolean);
  return parts.length ? parts.join(" · ") : JSON.stringify(config);
}

function TaskPanel({ tasks, onRun, onSaveConfig }: { tasks: any[]; onRun: (task: any) => void; onSaveConfig: (task: any, config: Record<string, any>) => void }) {
  const watchTasks = tasks.filter((task) => WATCH_MONITOR_TASKS.has(task.task_name));
  const otherTasks = tasks.filter((task) => !WATCH_MONITOR_TASKS.has(task.task_name));
  return (
    <div style={{ display: "grid", gap: 14 }}>
      <TaskGroup title="自选监控" tasks={watchTasks} onRun={onRun} onSaveConfig={onSaveConfig} />
      <TaskGroup title="其他任务" tasks={otherTasks} onRun={onRun} onSaveConfig={onSaveConfig} />
    </div>
  );
}

function TaskGroup({ title, tasks, onRun, onSaveConfig }: { title: string; tasks: any[]; onRun: (task: any) => void; onSaveConfig: (task: any, config: Record<string, any>) => void }) {
  return (
    <div style={{ background: "#fff", borderRadius: 14, padding: 14, display: "grid", gap: 10 }}>
      <h3 style={{ margin: 0, color: "#1d2d50" }}>{title}</h3>
      {tasks.length ? tasks.map((task) => (
        <div key={task.task_id} style={{ borderRadius: 10, background: "#f8fafc", padding: 12, display: "grid", gap: 8 }}>
          <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "flex-start" }}>
            <div>
              <strong style={{ color: "#1d2d50" }}>{task.task_name}</strong>
              <p style={{ margin: "4px 0 0", color: "#667085", fontSize: 12 }}>{task.owner_module || "-"} / {task.task_type || "-"} / {task.enabled ? "enabled" : "disabled"}</p>
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <Button size="mini" fill="outline" onClick={() => {
                const raw = window.prompt("编辑任务配置 JSON", JSON.stringify(task.config_json || {}, null, 2));
                if (raw == null) return;
                try {
                  onSaveConfig(task, JSON.parse(raw));
                } catch {
                  Toast.show({ content: "JSON 格式不正确" });
                }
              }}>编辑配置</Button>
              <Button size="mini" color="primary" onClick={() => onRun(task)}>手动执行</Button>
            </div>
          </div>
          <div style={{ fontSize: 12, color: "#667085" }}>执行计划：{taskConfigSummary(task.config_json)}</div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 8, fontSize: 12, color: "#344054" }}>
            <span>最近运行：{taskTimeText(task.latest_started_at)}</span>
            <span>状态：{task.latest_run_status || "-"}</span>
            <span>影响条数：{task.latest_affected_rows ?? "-"}</span>
            <span>错误：{taskErrorText(task.latest_error_message)}</span>
          </div>
        </div>
      )) : <div style={{ color: "#98a2b3", fontSize: 13 }}>暂无任务</div>}
    </div>
  );
}

function TradingSystemPanel({
  systems,
  selectedCode,
  selectedSystem,
  params,
  bindings,
  loading,
  onSelect,
}: {
  systems: TradingSystem[];
  selectedCode: string;
  selectedSystem: TradingSystem | null;
  params: TradingParam[];
  bindings: TradingRuleBinding[];
  loading: boolean;
  onSelect: (code: string) => void;
}) {
  const observeBindings = bindings.filter((item) => item.stage === "observe");
  const tradingBindings = bindings.filter((item) => item.stage === "trading");
  const stopLossBindings = bindings.filter((item) => item.stage === "stop_loss");

  return (
    <div style={{ display: "grid", gridTemplateColumns: "minmax(180px, 260px) 1fr", gap: 14 }}>
      <div style={{ background: "#fff", borderRadius: 14, padding: 14, display: "grid", gap: 8, alignContent: "start" }}>
        <h3 style={{ margin: "0 0 4px", color: "#1d2d50" }}>交易体系列表</h3>
        {systems.length ? systems.map((system) => (
          <button
            key={system.system_code}
            onClick={() => onSelect(system.system_code)}
            style={{
              border: 0,
              borderRadius: 10,
              padding: "10px 12px",
              textAlign: "left",
              background: selectedCode === system.system_code ? "linear-gradient(135deg, #5570ff, #4052d2)" : "#f4f6fb",
              color: selectedCode === system.system_code ? "#fff" : "#344054",
              cursor: "pointer",
            }}
          >
            <strong style={{ display: "block", fontSize: 14 }}>{system.system_name}</strong>
            <span style={{ display: "block", marginTop: 4, fontSize: 12, opacity: 0.78 }}>{system.system_code}</span>
          </button>
        )) : <div style={{ color: "#98a2b3", fontSize: 13 }}>暂无交易体系</div>}
      </div>

      <div style={{ display: "grid", gap: 14 }}>
        {loading && <div style={{ display: "grid", placeItems: "center", minHeight: 120, background: "#fff", borderRadius: 14 }}><SpinLoading /></div>}

        {!loading && selectedSystem && (
          <>
            <div style={{ background: "#fff", borderRadius: 14, padding: 14 }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "flex-start" }}>
                <div>
                  <h3 style={{ margin: 0, color: "#1d2d50" }}>{selectedSystem.system_name}</h3>
                  <p style={{ margin: "6px 0 0", color: "#667085", fontSize: 13 }}>{selectedSystem.system_code}</p>
                </div>
                <span style={{ borderRadius: 999, padding: "4px 8px", background: selectedSystem.enabled ? "#ecfdf3" : "#f2f4f7", color: selectedSystem.enabled ? "#027a48" : "#667085", fontSize: 12, fontWeight: 700 }}>
                  {selectedSystem.enabled ? "启用" : "停用"}
                </span>
              </div>
              <p style={{ margin: "12px 0 0", color: "#344054", fontSize: 13 }}>{selectedSystem.description || "暂无描述"}</p>
              <p style={{ margin: "6px 0 0", color: "#667085", fontSize: 12 }}>生命周期：{selectedSystem.lifecycle_desc || "-"}</p>
            </div>

            <div style={{ background: "#fff", borderRadius: 14, padding: 14 }}>
              <h3 style={{ margin: "0 0 10px", color: "#1d2d50" }}>观察参数</h3>
              <div style={{ display: "grid", gap: 8 }}>
                {params.length ? params.map((param) => (
                  <ParamRow key={param.param_id} param={param} />
                )) : <div style={{ color: "#98a2b3", fontSize: 13 }}>暂无参数定义</div>}
              </div>
            </div>

            <RuleStageCard title="观察阶段规则" items={observeBindings} />
            <RuleStageCard title="交易阶段卖点规则" items={tradingBindings} />
            <RuleStageCard title="止损规则" items={stopLossBindings} />
          </>
        )}

        {!loading && !selectedSystem && (
          <div style={{ background: "#fff", borderRadius: 14, padding: 20, textAlign: "center", color: "#98a2b3" }}>
            请选择一个交易体系
          </div>
        )}
      </div>
    </div>
  );
}

function ParamRow({ param }: { param: TradingParam }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "minmax(120px, 180px) 1fr", gap: 10, padding: "10px 12px", borderRadius: 10, background: "#f8fafc" }}>
      <div>
        <strong style={{ display: "block", color: "#1d2d50", fontSize: 13 }}>{param.param_name}</strong>
        <span style={{ color: "#667085", fontSize: 12 }}>{param.param_key}</span>
      </div>
      <div style={{ display: "grid", gap: 4 }}>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          <SmallTag>{param.param_type}</SmallTag>
          <SmallTag>{param.required ? "必填" : "非必填"}</SmallTag>
          <SmallTag>{param.enabled ? "启用" : "停用"}</SmallTag>
        </div>
        <span style={{ color: "#667085", fontSize: 12 }}>{param.description || "-"}</span>
      </div>
    </div>
  );
}

function RuleStageCard({ title, items }: { title: string; items: TradingRuleBinding[] }) {
  return (
    <div style={{ background: "#fff", borderRadius: 14, padding: 14 }}>
      <h3 style={{ margin: "0 0 10px", color: "#1d2d50" }}>{title}</h3>
      <div style={{ display: "grid", gap: 8 }}>
        {items.length ? items.map((binding) => (
          <div key={binding.binding_id} style={{ padding: "10px 12px", borderRadius: 10, background: "#f8fafc" }}>
            <div style={{ display: "flex", justifyContent: "space-between", gap: 10, flexWrap: "wrap" }}>
              <strong style={{ color: "#1d2d50", fontSize: 13 }}>{binding.rule?.rule_name || binding.rule_code}</strong>
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                <SmallTag>{binding.logic_group || "-"}</SmallTag>
                <SmallTag>{binding.logic_operator}</SmallTag>
                <SmallTag>{binding.required ? "必需" : "可选"}</SmallTag>
              </div>
            </div>
            <div style={{ display: "grid", gap: 4, marginTop: 8, color: "#667085", fontSize: 12 }}>
              <span>规则编码：{binding.rule_code}</span>
              <span>类型/周期：{binding.rule?.rule_type || "-"} / {binding.rule?.timeframe || "-"}</span>
              <span>执行器键：{binding.rule?.executor_key || "-"}</span>
              <span>{binding.rule?.description || "暂无描述"}</span>
            </div>
          </div>
        )) : <div style={{ color: "#98a2b3", fontSize: 13 }}>暂无规则绑定</div>}
      </div>
    </div>
  );
}

function SmallTag({ children, tone = "primary" }: { children: string | number; tone?: "primary" | "muted" }) {
  const muted = tone === "muted";
  return (
    <span style={{ borderRadius: 999, padding: "2px 7px", background: muted ? "#eef0f3" : "#eef2ff", color: muted ? "#98a2b3" : "#4052d2", fontSize: 11, fontWeight: 700 }}>
      {children}
    </span>
  );
}

const RULE_TYPES = ["buy_signal", "sell_signal", "stop_loss", "filter", "confirm"];
const TIMEFRAMES = ["5m", "15m", "30m", "daily"];
const PARAM_TYPES = ["number", "text", "select", "boolean"];
const SYSTEM_STAGES = ["observe", "buy_confirm", "trading", "sell", "stop_loss"];
const LOGIC_OPERATORS = ["AND", "OR"];

function TradingSystemPanelEditor({
  systems,
  selectedCode,
  selectedSystem,
  params,
  bindings,
  loading,
  onSelect,
  rules,
  executors,
  onSaved,
}: {
  systems: TradingSystem[];
  selectedCode: string;
  selectedSystem: TradingSystem | null;
  params: TradingParam[];
  bindings: TradingRuleBinding[];
  loading: boolean;
  onSelect: (code: string) => void;
  rules: TradingRule[];
  executors: string[];
  onSaved: () => void;
}) {
  const registeredExecutors = new Set(executors);
  const [saving, setSaving] = useState(false);
  const [systemForm, setSystemForm] = useState<any>(null);
  const [ruleForm, setRuleForm] = useState<any>(blankRuleForm());
  const [paramForm, setParamForm] = useState<any>(blankParamForm());
  const [bindingForm, setBindingForm] = useState<any>(blankBindingForm(rules[0]?.rule_code || ""));

  useEffect(() => {
    if (selectedSystem) {
      setSystemForm({ ...selectedSystem });
    } else {
      setSystemForm(blankSystemForm());
    }
  }, [selectedSystem?.system_code]);

  useEffect(() => {
    setBindingForm((prev: any) => ({ ...prev, rule_code: prev.rule_code || rules[0]?.rule_code || "" }));
  }, [rules.length]);

  const selectedBindingRule = rules.find((item) => item.rule_code === bindingForm.rule_code);
  const ruleExecutorMissing = !!ruleForm.executor_key && !registeredExecutors.has(ruleForm.executor_key);
  const bindingExecutorMissing = !!selectedBindingRule?.executor_key && !registeredExecutors.has(selectedBindingRule.executor_key);

  async function saveWithToast(action: () => Promise<void>) {
    setSaving(true);
    try {
      await action();
      Toast.show({ content: "已保存" });
      await onSaved();
    } catch (err: any) {
      Toast.show({ content: err?.message || "保存失败" });
    } finally {
      setSaving(false);
    }
  }

  async function saveSystem() {
    if (!systemForm?.system_code || !systemForm?.system_name) {
      Toast.show({ content: "请填写体系编码和名称" });
      return;
    }
    await saveWithToast(async () => {
      const payload = normalizeSystemForm(systemForm);
      if (systemForm.system_id) {
        await apiPut(`/admin/trading-systems/${systemForm.system_code}`, payload);
      } else {
        await apiPost(`/admin/trading-systems`, payload);
        onSelect(systemForm.system_code);
      }
    });
  }

  async function saveRule() {
    if (!ruleForm.rule_code || !ruleForm.rule_name || !ruleForm.executor_key) {
      Toast.show({ content: "请填写规则编码、名称和执行器" });
      return;
    }
    await saveWithToast(async () => {
      const payload = normalizeRuleForm(ruleForm);
      if (ruleForm.rule_id) {
        await apiPut(`/admin/trading-rules/${ruleForm.rule_code}`, payload);
      } else {
        await apiPost(`/admin/trading-rules`, payload);
      }
      setRuleForm(blankRuleForm());
    });
  }

  async function saveParam() {
    if (!selectedCode) {
      Toast.show({ content: "请先选择交易体系" });
      return;
    }
    if (!paramForm.param_key || !paramForm.param_name) {
      Toast.show({ content: "请填写参数编码和名称" });
      return;
    }
    await saveWithToast(async () => {
      const payload = normalizeParamForm(paramForm);
      if (paramForm.param_id) {
        await apiPut(`/admin/trading-params/${paramForm.param_id}`, payload);
      } else {
        await apiPost(`/admin/trading-systems/${selectedCode}/params`, payload);
      }
      setParamForm(blankParamForm());
    });
  }

  async function saveBinding() {
    if (!selectedCode) {
      Toast.show({ content: "请先选择交易体系" });
      return;
    }
    if (!bindingForm.rule_code || !bindingForm.stage) {
      Toast.show({ content: "请选择规则和阶段" });
      return;
    }
    await saveWithToast(async () => {
      const payload = normalizeBindingForm(bindingForm);
      if (bindingForm.binding_id) {
        await apiPut(`/admin/trading-rule-bindings/${bindingForm.binding_id}`, payload);
      } else {
        await apiPost(`/admin/trading-systems/${selectedCode}/rules`, payload);
      }
      setBindingForm(blankBindingForm(rules[0]?.rule_code || ""));
    });
  }

  return (
    <section style={{ display: "grid", gap: 14 }}>
      <div style={{ background: "#fff", borderRadius: 14, padding: 14, display: "grid", gap: 10 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
          <h3 style={{ margin: 0, color: "#1d2d50" }}>交易体系管理</h3>
          <Button size="mini" onClick={() => { setSystemForm(blankSystemForm()); onSelect(""); }}>新增</Button>
        </div>
        <div style={{ display: "flex", gap: 8, overflowX: "auto", paddingBottom: 2 }}>
          {systems.length ? systems.map((system) => (
            <button
              key={system.system_code}
              onClick={() => onSelect(system.system_code)}
              style={{
                border: 0,
                borderRadius: 999,
                padding: "10px 16px",
                textAlign: "left",
                background: selectedCode === system.system_code ? "linear-gradient(135deg, #5570ff, #4052d2)" : "#f4f6fb",
                color: selectedCode === system.system_code ? "#fff" : "#344054",
                cursor: "pointer",
                minWidth: 150,
                flex: "0 0 auto",
              }}
            >
              <strong style={{ display: "block", fontSize: 14, lineHeight: 1.2, whiteSpace: "nowrap" }}>{system.system_name}</strong>
              <span style={{ display: "block", marginTop: 4, fontSize: 12, opacity: 0.78, whiteSpace: "nowrap" }}>{system.system_code}</span>
            </button>
          )) : <div style={{ color: "#98a2b3", fontSize: 13 }}>暂无交易体系</div>}
        </div>
      </div>

      <div style={{ display: "grid", gap: 14 }}>
        {loading && <div style={{ display: "grid", placeItems: "center", minHeight: 120, background: "#fff", borderRadius: 14 }}><SpinLoading /></div>}

        {!loading && (
          <>
            <EditCard title={systemForm?.system_id ? "编辑交易体系" : "新增交易体系"}>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 10 }}>
                <TextField label="体系编码" value={systemForm?.system_code || ""} disabled={!!systemForm?.system_id} onChange={(v) => setSystemForm({ ...systemForm, system_code: v })} />
                <TextField label="体系名称" value={systemForm?.system_name || ""} onChange={(v) => setSystemForm({ ...systemForm, system_name: v })} />
                <TextField label="描述" value={systemForm?.description || ""} onChange={(v) => setSystemForm({ ...systemForm, description: v })} />
                <TextField label="生命周期说明" value={systemForm?.lifecycle_desc || ""} onChange={(v) => setSystemForm({ ...systemForm, lifecycle_desc: v })} />
                <TextField label="排序" value={String(systemForm?.sort_order ?? 0)} onChange={(v) => setSystemForm({ ...systemForm, sort_order: v })} />
                <CheckField label="启用" checked={!!systemForm?.enabled} onChange={(v) => setSystemForm({ ...systemForm, enabled: v })} />
              </div>
              <Button color="primary" size="small" loading={saving} onClick={saveSystem}>保存体系</Button>
            </EditCard>

            {selectedCode && selectedSystem && (
              <>
                <EditCard title="参数定义">
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 10 }}>
                    <TextField label="参数编码" value={paramForm.param_key} disabled={!!paramForm.param_id} onChange={(v) => setParamForm({ ...paramForm, param_key: v })} />
                    <TextField label="参数名称" value={paramForm.param_name} onChange={(v) => setParamForm({ ...paramForm, param_name: v })} />
                    <SelectField label="类型" value={paramForm.param_type} options={PARAM_TYPES} onChange={(v) => setParamForm({ ...paramForm, param_type: v })} />
                    <TextField label="默认值" value={paramForm.default_value || ""} onChange={(v) => setParamForm({ ...paramForm, default_value: v })} />
                    <TextField label="排序" value={String(paramForm.sort_order ?? 0)} onChange={(v) => setParamForm({ ...paramForm, sort_order: v })} />
                    <CheckField label="必填" checked={!!paramForm.required} onChange={(v) => setParamForm({ ...paramForm, required: v })} />
                    <CheckField label="启用" checked={!!paramForm.enabled} onChange={(v) => setParamForm({ ...paramForm, enabled: v })} />
                    <TextField label="说明" value={paramForm.description || ""} onChange={(v) => setParamForm({ ...paramForm, description: v })} />
                  </div>
                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                    <Button color="primary" size="small" loading={saving} onClick={saveParam}>保存参数</Button>
                    <Button size="small" onClick={() => setParamForm(blankParamForm())}>新增参数</Button>
                  </div>
                  <SimpleRows
                    empty="暂无参数定义"
                    rows={params.map((param) => ({
                      key: String(param.param_id),
                      title: `${param.param_name} / ${param.param_key}`,
                      desc: `${param.param_type} / ${param.required ? "必填" : "非必填"} / 排序 ${param.sort_order}`,
                      enabled: param.enabled,
                      onEdit: () => setParamForm({ ...param }),
                    }))}
                  />
                </EditCard>

                <EditCard title="体系规则绑定">
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 10 }}>
                    <SelectField label="规则" value={bindingForm.rule_code} options={rules.map((rule) => rule.rule_code)} onChange={(v) => setBindingForm({ ...bindingForm, rule_code: v })} />
                    <SelectField label="阶段" value={bindingForm.stage} options={SYSTEM_STAGES} onChange={(v) => setBindingForm({ ...bindingForm, stage: v })} />
                    <TextField label="logic_group" value={bindingForm.logic_group || ""} onChange={(v) => setBindingForm({ ...bindingForm, logic_group: v })} />
                    <SelectField label="logic_operator" value={bindingForm.logic_operator} options={LOGIC_OPERATORS} onChange={(v) => setBindingForm({ ...bindingForm, logic_operator: v })} />
                    <TextField label="排序" value={String(bindingForm.sort_order ?? 0)} onChange={(v) => setBindingForm({ ...bindingForm, sort_order: v })} />
                    <CheckField label="required" checked={!!bindingForm.required} onChange={(v) => setBindingForm({ ...bindingForm, required: v })} />
                    <CheckField label="启用" checked={!!bindingForm.enabled} onChange={(v) => setBindingForm({ ...bindingForm, enabled: v })} />
                  </div>
                  {bindingExecutorMissing && <WarningText />}
                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                    <Button color="primary" size="small" loading={saving} onClick={saveBinding}>保存绑定</Button>
                    <Button size="small" onClick={() => setBindingForm(blankBindingForm(rules[0]?.rule_code || ""))}>新增绑定</Button>
                  </div>
                  <SimpleRows
                    empty="暂无规则绑定"
                    rows={bindings.map((binding) => ({
                      key: String(binding.binding_id),
                      title: `${binding.rule?.rule_name || binding.rule_code} / ${binding.stage}`,
                      desc: `${binding.logic_group || "-"} ${binding.logic_operator} / ${binding.required ? "必需" : "可选"} / ${binding.rule?.executor_key || "-"}`,
                      enabled: binding.enabled,
                      warning: !!binding.rule?.executor_key && !registeredExecutors.has(binding.rule.executor_key),
                      onEdit: () => setBindingForm({ ...binding }),
                    }))}
                  />
                </EditCard>
              </>
            )}

          </>
        )}
      </div>
    </section>
  );
}

function blankSystemForm() {
  return { system_code: "", system_name: "", description: "", lifecycle_desc: "", enabled: true, sort_order: 0 };
}

function blankRuleForm() {
  return { rule_code: "", rule_name: "", rule_type: "buy_signal", timeframe: "15m", executor_key: "", description: "", enabled: true };
}

function blankParamForm() {
  return { param_key: "", param_name: "", param_type: "number", required: false, default_value: "", description: "", sort_order: 0, enabled: true };
}

function blankBindingForm(ruleCode: string) {
  return { rule_code: ruleCode, stage: "observe", required: false, logic_group: "", logic_operator: "AND", enabled: true, sort_order: 0 };
}

function normalizeSystemForm(form: any) {
  return { ...form, system_code: String(form.system_code || "").trim(), system_name: String(form.system_name || "").trim(), sort_order: Number(form.sort_order || 0), enabled: !!form.enabled };
}

function normalizeRuleForm(form: any) {
  return { ...form, rule_code: String(form.rule_code || "").trim(), rule_name: String(form.rule_name || "").trim(), executor_key: String(form.executor_key || "").trim(), enabled: !!form.enabled };
}

function normalizeParamForm(form: any) {
  return { ...form, param_key: String(form.param_key || "").trim(), param_name: String(form.param_name || "").trim(), sort_order: Number(form.sort_order || 0), required: !!form.required, enabled: !!form.enabled };
}

function normalizeBindingForm(form: any) {
  return { ...form, sort_order: Number(form.sort_order || 0), required: !!form.required, enabled: !!form.enabled };
}

function EditCard({ title, children }: { title: string; children: any }) {
  return (
    <div style={{ background: "#fff", borderRadius: 14, padding: 14, display: "grid", gap: 12 }}>
      <h3 style={{ margin: 0, color: "#1d2d50" }}>{title}</h3>
      {children}
    </div>
  );
}

function TextField({ label, value, disabled, onChange }: { label: string; value: string; disabled?: boolean; onChange: (value: string) => void }) {
  return (
    <label style={{ display: "grid", gap: 4 }}>
      <FormLabel text={label} />
      <Input value={value} disabled={disabled} onChange={onChange} style={{ "--background": "#f8fafc", "--border-radius": "8px", "--padding-left": "10px" } as any} />
    </label>
  );
}

function SelectField({ label, value, options, onChange }: { label: string; value: string; options: string[]; onChange: (value: string) => void }) {
  return (
    <label style={{ display: "grid", gap: 4 }}>
      <FormLabel text={label} />
      <select value={value} onChange={(event) => onChange(event.target.value)} style={{ height: 34, border: "1px solid #e4e7ec", borderRadius: 8, background: "#f8fafc", color: "#344054", padding: "0 8px" }}>
        {options.map((option) => <option key={option} value={option}>{option}</option>)}
      </select>
    </label>
  );
}

function CheckField({ label, checked, onChange }: { label: string; checked: boolean; onChange: (value: boolean) => void }) {
  return (
    <label style={{ display: "flex", alignItems: "center", gap: 8, minHeight: 52, color: "#344054", fontSize: 13, fontWeight: 700 }}>
      <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} />
      {label}
    </label>
  );
}

function WarningText() {
  return <div style={{ borderRadius: 8, background: "#fff7ed", color: "#b54708", padding: "8px 10px", fontSize: 12, fontWeight: 700 }}>该规则暂无执行器，不能参与自动监控</div>;
}

function SimpleRows({ rows, empty }: { rows: { key: string; title: string; desc: string; enabled: boolean; warning?: boolean; onEdit: () => void }[]; empty: string }) {
  const sortedRows = [...rows].sort((a, b) => Number(b.enabled) - Number(a.enabled));
  return (
    <div style={{ display: "grid", gap: 8 }}>
      {sortedRows.length ? sortedRows.map((row) => (
        <div key={row.key} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10, padding: "9px 10px", borderRadius: 10, background: row.enabled ? "#f8fafc" : "#f2f4f7", opacity: row.enabled ? 1 : 0.72 }}>
          <div style={{ display: "grid", gap: 4, minWidth: 0 }}>
            <strong style={{ color: row.enabled ? "#1d2d50" : "#667085", fontSize: 13 }}>{row.title}</strong>
            <span style={{ color: row.enabled ? "#667085" : "#98a2b3", fontSize: 12 }}>{row.desc}</span>
            {row.warning && <span style={{ color: "#b54708", fontSize: 12 }}>该规则暂无执行器，不能参与自动监控</span>}
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <SmallTag tone={row.enabled ? "primary" : "muted"}>{row.enabled ? "启用" : "停用"}</SmallTag>
            <Button size="mini" onClick={row.onEdit}>编辑</Button>
          </div>
        </div>
      )) : <div style={{ color: "#98a2b3", fontSize: 13 }}>{empty}</div>}
    </div>
  );
}

function RuleLibraryPanel({ rules, executors, onSaved }: { rules: any[]; executors: string[]; onSaved: () => void }) {
  const [form, setForm] = useState({ rule_code: "", rule_name: "", rule_type: "buy_signal", timeframe: "15m", executor_key: "", description: "", enabled: true, config_json: {} as any });
  const [editing, setEditing] = useState<any>(null);
  const [submitting, setSubmitting] = useState(false);
  const [filter, setFilter] = useState({ keyword: "", rule_type: "", enabled: "" });
  const [showForm, setShowForm] = useState(false);

  const registered = new Set(executors);
  const filtered = rules.filter((r) => {
    if (filter.enabled === "enabled" && !r.enabled) return false;
    if (filter.enabled === "disabled" && r.enabled) return false;
    if (filter.rule_type && r.rule_type !== filter.rule_type) return false;
    if (filter.keyword) {
      const kw = filter.keyword.toLowerCase();
      return (r.rule_name || "").includes(kw) || (r.rule_code || "").includes(kw) || (r.executor_key || "").includes(kw);
    }
    return true;
  });

  const RULE_TYPE_LABELS: Record<string, string> = { buy_signal: "买点信号", sell_signal: "卖点信号", stop_loss: "止损信号", filter: "过滤条件", confirm: "确认条件", observe_risk: "观察风险", invalid_signal: "观察失效", remove_signal: "自动剔除" };

  function resetForm() { setForm({ rule_code: "", rule_name: "", rule_type: "buy_signal", timeframe: "15m", executor_key: "", description: "", enabled: true, config_json: {} }); setEditing(null); setShowForm(true); }
  function editRule(r: any) { setForm({ rule_code: r.rule_code, rule_name: r.rule_name, rule_type: r.rule_type, timeframe: r.timeframe, executor_key: r.executor_key, description: r.description || "", enabled: r.enabled, config_json: r.config_json || {} }); setEditing(r); setShowForm(true); }

  async function save() {
    if (!form.rule_code || !form.rule_name || !form.executor_key) { Toast.show({ content: "请填写规则编码、名称和执行器键" }); return; }
    setSubmitting(true);
    try {
      if (editing) {
        await apiPut(`/admin/trading-rules/${editing.rule_code}`, form);
      } else {
        await apiPost("/admin/trading-rules", form);
      }
      Toast.show({ content: "规则已保存" }); setShowForm(false); onSaved();
    } catch { Toast.show({ content: "保存失败" }); }
    finally { setSubmitting(false); }
  }

  return (
    <div style={{ display: "grid", gap: 12 }}>
      <div style={{ borderRadius: 14, background: "#fff", padding: 14 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
          <h3 style={{ margin: 0, fontSize: 15 }}>规则库 ({filtered.length}/{rules.length})</h3>
          <Button size="mini" color="primary" onClick={resetForm}>+ 新增</Button>
        </div>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 10 }}>
          <input placeholder="搜索" value={filter.keyword} onChange={(e) => setFilter({ ...filter, keyword: e.target.value })} style={{ flex: 1, minWidth: 80, padding: "6px 10px", borderRadius: 10, border: "1px solid #ddd", fontSize: 12 }} />
          <select value={filter.rule_type} onChange={(e) => setFilter({ ...filter, rule_type: e.target.value })} style={{ padding: "6px 8px", borderRadius: 10, border: "1px solid #ddd", fontSize: 12 }}>
            <option value="">全部类型</option>
            {Object.entries(RULE_TYPE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
          <select value={filter.enabled} onChange={(e) => setFilter({ ...filter, enabled: e.target.value })} style={{ padding: "6px 8px", borderRadius: 10, border: "1px solid #ddd", fontSize: 12 }}>
            <option value="">全部状态</option><option value="enabled">已启用</option><option value="disabled">已停用</option>
          </select>
        </div>
        {filtered.map((r) => (
          <div key={r.rule_code} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 0", borderBottom: "1px solid #f0f0f0", fontSize: 12 }}>
            <div style={{ minWidth: 0 }}>
              <strong style={{ fontSize: 13 }}>{r.rule_name}</strong>
              <span style={{ color: "#888", marginLeft: 6 }}>{r.rule_code}</span>
              <div style={{ color: "#888", marginTop: 2 }}>
                <span style={{ display: "inline-block", padding: "2px 6px", borderRadius: 6, background: "#eef2ff", color: "#4b63ee", fontSize: 11, fontWeight: 700 }}>{RULE_TYPE_LABELS[r.rule_type] || r.rule_type}</span>
                <span style={{ marginLeft: 4 }}>{r.timeframe} · {r.executor_key}</span>
                {!registered.has(r.executor_key) && <span style={{ color: "#b54708", marginLeft: 4 }}>【无执行器】</span>}
              </div>
            </div>
            <Button size="mini" fill="outline" onClick={() => editRule(r)}>编辑</Button>
          </div>
        ))}
      </div>
      {showForm && (
        <div style={{ borderRadius: 14, background: "#fff", padding: 14, display: "grid", gap: 8 }}>
          <h3 style={{ margin: 0, fontSize: 14 }}>{editing ? "编辑规则" : "新增规则"}</h3>
          <div><div style={{ color: "#5b6d8a", fontSize: 11, fontWeight: 700, marginBottom: 2 }}>rule_code</div><input value={form.rule_code} onChange={(e) => setForm({ ...form, rule_code: e.target.value })} disabled={!!editing} style={{ width: "100%", padding: "6px 10px", borderRadius: 10, border: "1px solid #ddd", fontSize: 12 }} /></div>
          <div><div style={{ color: "#5b6d8a", fontSize: 11, fontWeight: 700, marginBottom: 2 }}>rule_name</div><input value={form.rule_name} onChange={(e) => setForm({ ...form, rule_name: e.target.value })} style={{ width: "100%", padding: "6px 10px", borderRadius: 10, border: "1px solid #ddd", fontSize: 12 }} /></div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
            <div><div style={{ color: "#5b6d8a", fontSize: 11, fontWeight: 700, marginBottom: 2 }}>rule_type</div><select value={form.rule_type} onChange={(e) => setForm({ ...form, rule_type: e.target.value })} style={{ width: "100%", padding: "6px 8px", borderRadius: 10, border: "1px solid #ddd", fontSize: 12 }}>{Object.entries(RULE_TYPE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></div>
            <div><div style={{ color: "#5b6d8a", fontSize: 11, fontWeight: 700, marginBottom: 2 }}>timeframe</div><select value={form.timeframe} onChange={(e) => setForm({ ...form, timeframe: e.target.value })} style={{ width: "100%", padding: "6px 8px", borderRadius: 10, border: "1px solid #ddd", fontSize: 12 }}><option value="5m">5m</option><option value="15m">15m</option><option value="30m">30m</option><option value="daily">daily</option></select></div>
          </div>
          <div><div style={{ color: "#5b6d8a", fontSize: 11, fontWeight: 700, marginBottom: 2 }}>executor_key</div>
            <select value={form.executor_key} onChange={(e) => setForm({ ...form, executor_key: e.target.value })} style={{ width: "100%", padding: "6px 8px", borderRadius: 10, border: "1px solid #ddd", fontSize: 12 }}>
              <option value="">选择执行器</option>
              {executors.map((ex: string) => <option key={ex} value={ex}>{ex}</option>)}
            </select></div>
          <div><div style={{ color: "#5b6d8a", fontSize: 11, fontWeight: 700, marginBottom: 2 }}>description</div><textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} rows={2} style={{ width: "100%", padding: "6px 10px", borderRadius: 10, border: "1px solid #ddd", fontSize: 12 }} /></div>
          <div style={{ borderRadius: 12, background: "#f8fafc", padding: 10 }}>
            <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 4 }}>高级配置 JSON</div>
            <textarea
              value={JSON.stringify(form.config_json || {}, null, 2)}
              onChange={(e) => { try { setForm({ ...form, config_json: JSON.parse(e.target.value) }); } catch {} }}
              rows={4}
              style={{ width: "100%", padding: "6px 10px", borderRadius: 10, border: "1px solid #ddd", fontSize: 11, fontFamily: "monospace" }}
            />
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <Button block color="primary" size="small" loading={submitting} onClick={save}>保存</Button>
            <Button block fill="none" size="small" onClick={() => setShowForm(false)}>取消</Button>
          </div>
        </div>
      )}
    </div>
  );
}
