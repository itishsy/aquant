import { useEffect, useState } from "react";
import { Button, ErrorBlock, Input, Picker, SpinLoading, Toast } from "antd-mobile";
import { apiDelete, apiGet, apiPost, apiPut } from "../api/client";

const SECTIONS = [
  { key: "dashboard", label: "工作台" },
  { key: "watchpool", label: "自选池" },
  { key: "sources", label: "数据源" },
  { key: "tasks", label: "任务" },
  { key: "mappings", label: "字段映射" },
  { key: "strategies", label: "策略" },
  { key: "dictionaries", label: "字典" },
  { key: "reviewTemplates", label: "复盘模板" },
  { key: "notifications", label: "推送" },
  { key: "logs", label: "日志" },
  { key: "security", label: "安全" },
];

const STATUS_OPTIONS = [
  { label: "观察中 (watching)", value: "watching" },
  { label: "已触发 (triggered)", value: "triggered" },
  { label: "持仓中 (holding)", value: "holding" },
  { label: "不交易 (not_trade)", value: "not_trade" },
  { label: "已完成 (completed)", value: "completed" },
  { label: "已剔除 (removed)", value: "removed" },
  { label: "黑名单 (blacklist)", value: "blacklist" },
];

const LABEL_OPTS = ["人气", "接力", "趋势"];
const STRATEGY_OPTS = ["趋势交易", "加速接力", "平台突破"];
const BUY_POINT_OPTS = ["B15 底背离买点", "支撑买点", "平台突破确认买点"];

function statusLabel(v: string) {
  return STATUS_OPTIONS.find((s) => s.value === v)?.label || v;
}

function PlaceholderCard({ label }: { label: string }) {
  return (
    <div style={{ padding: 20, borderRadius: 14, background: "#fff", textAlign: "center" }}>
      <p style={{ color: "#888", fontSize: 14 }}>{label}模块已就绪</p>
      <p style={{ color: "#aaa", fontSize: 12 }}>可连接对应 /api/admin/** 配置接口继续扩展</p>
    </div>
  );
}

export function AdminPage() {
  const [active, setActive] = useState("dashboard");
  const [menuOpen, setMenuOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [overview, setOverview] = useState<any>(null);
  const [tasks, setTasks] = useState<any[]>([]);
  const [dictionaries, setDictionaries] = useState<any[]>([]);
  const [logs, setLogs] = useState<any[]>([]);
  const [sources, setSources] = useState<any[]>([]);
  const [strategies, setStrategies] = useState<any[]>([]);
  const [templates, setTemplates] = useState<any[]>([]);

  const [watches, setWatches] = useState<any[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [form, setForm] = useState({ stock_code: "", stock_name: "", sector_name: "", reason: "", source_type: "manual", labels: [] as string[], operation_strategies: [] as string[], buy_point_types: [] as string[] });
  const [pickerKey, setPickerKey] = useState("");
  const [pickerVisible, setPickerVisible] = useState(false);

  async function loadAll() {
    setLoading(true);
    try {
      const [ov, tk, dc, lg, src, st, tpl, wa] = await Promise.all([
        apiGet<any>("/admin/dashboard/overview"),
        apiGet<any[]>("/admin/tasks"),
        apiGet<any[]>("/admin/dictionaries"),
        apiGet<any[]>("/admin/task-logs"),
        apiGet<any[]>("/admin/data-sources"),
        apiGet<any[]>("/admin/strategies"),
        apiGet<any[]>("/admin/notification-templates"),
        apiGet<any[]>("/h5/watch-pool"),
      ]);
      setOverview(ov); setTasks(tk || []); setDictionaries(dc || []);
      setLogs(lg || []); setSources(src || []); setStrategies(st || []);
      setTemplates(tpl || []); setWatches(wa || []);
      setError("");
    } catch { setError("加载失败"); }
    finally { setLoading(false); }
  }

  useEffect(() => { loadAll(); }, []);

  function resetForm() {
    setForm({ stock_code: "", stock_name: "", sector_name: "", reason: "", source_type: "manual", labels: [], operation_strategies: [], buy_point_types: [] });
    setEditId(null); setShowForm(true);
  }

  function editWatch(item: any) {
    setForm({
      stock_code: item.stock_code || "", stock_name: item.stock_name || "",
      sector_name: item.sector_name || "", reason: item.reason || "",
      source_type: item.source_type || "manual",
      labels: item.labels || [], operation_strategies: item.operation_strategies || [],
      buy_point_types: item.buy_point_types || [],
    });
    setEditId(item.watch_id); setShowForm(true);
  }

  async function saveWatch() {
    if (!form.stock_code.trim() || !form.stock_name.trim()) { Toast.show({ content: "请填写股票代码和名称" }); return; }
    const payload: any = { ...form, stock_code: form.stock_code.trim().toUpperCase(), stock_name: form.stock_name.trim() };
    if (!payload.labels.length) payload.labels = ["手动"];
    if (!payload.operation_strategies.length) payload.operation_strategies = ["趋势交易"];
    if (!payload.buy_point_types.length) payload.buy_point_types = ["B15 底背离买点"];
    try {
      if (editId) { await apiPut(`/h5/watch-pool/${editId}`, payload); }
      else { await apiPost("/h5/watch-pool", payload); }
      Toast.show({ content: editId ? "已更新" : "已添加" });
      setShowForm(false); loadAll();
    } catch { Toast.show({ content: "保存失败" }); }
  }

  async function updateStatus(watchId: number, pool_status: string) {
    await apiPut(`/h5/watch-pool/${watchId}`, { pool_status });
    Toast.show({ content: "状态已更新" }); loadAll();
  }

  async function removeWatch(watchId: number) {
    await apiDelete(`/h5/watch-pool/${watchId}`);
    Toast.show({ content: "已剔除" }); loadAll();
  }

  async function restoreWatch(watchId: number) {
    await apiPost(`/h5/watch-pool/${watchId}/restore`);
    Toast.show({ content: "已恢复" }); loadAll();
  }

  const activeLabel = SECTIONS.find((s) => s.key === active)?.label || "";

  return (
    <div style={{ minHeight: "100vh", background: "#f4f6fb" }}>
      <header style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "10px 14px", background: "linear-gradient(90deg, #1b2447, #334497)", color: "#fff", position: "sticky", top: 0, zIndex: 100 }}>
        <strong style={{ fontSize: 16 }}>Aquant · {activeLabel}</strong>
        <Button size="mini" fill="none" style={{ color: "#fff" }} onClick={() => setMenuOpen(!menuOpen)}>
          {menuOpen ? "✕" : "☰"} 菜单
        </Button>
      </header>

      {menuOpen && (
        <nav style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 4, padding: "8px 14px", background: "#fff", borderBottom: "1px solid #e8ecf4" }}>
          {SECTIONS.map((s) => (
            <button
              key={s.key}
              onClick={() => { setActive(s.key); setMenuOpen(false); }}
              style={{ padding: "9px 10px", border: "none", borderRadius: 10, textAlign: "center", fontSize: 13, background: active === s.key ? "linear-gradient(135deg, #5570ff, #4052d2)" : "#f4f6fb", color: active === s.key ? "#fff" : "#334", fontWeight: active === s.key ? 700 : 400 }}
            >
              {s.label}
            </button>
          ))}
        </nav>
      )}

      <section style={{ padding: "10px 14px 80px" }}>
        {loading && <SpinLoading />}
        {error && <ErrorBlock description={error} />}
        {!loading && !error && (
          <>
            {/* ====== Dashboard ====== */}
            {active === "dashboard" && (
              <div style={{ display: "grid", gap: 10 }}>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 8 }}>
                  {[{ label: "任务", val: overview?.tasks ?? 0 }, { label: "数据源", val: overview?.data_sources ?? 0 }, { label: "字典", val: overview?.dictionaries ?? 0 }].map((m) => (
                    <div key={m.label} style={{ padding: 14, borderRadius: 14, background: "#fff", textAlign: "center" }}>
                      <div style={{ fontSize: 11, color: "#888" }}>{m.label}</div>
                      <div style={{ fontSize: 26, fontWeight: 800, color: "#4052d2" }}>{m.val}</div>
                    </div>
                  ))}
                </div>
                <div style={{ padding: 14, borderRadius: 14, background: "#fff" }}>
                  <strong>自选统计</strong>
                  <p style={{ margin: 4, fontSize: 13, color: "#666" }}>
                    总数 {watches.length} / 观察中 {watches.filter((w) => w.pool_status === "watching").length} / 持仓 {watches.filter((w) => w.pool_status === "holding").length}
                  </p>
                </div>
                <div style={{ padding: 14, borderRadius: 14, background: "#fff" }}>
                  <strong>任务状态</strong>
                  <p style={{ margin: 4, fontSize: 13, color: "#666" }}>
                    总 {overview?.tasks ?? 0} / 运行中 {tasks.filter((t) => t.running).length}
                  </p>
                </div>
                <div style={{ padding: 14, borderRadius: 14, background: "#fff" }}>
                  <strong>最近错误</strong>
                  {logs.filter((l) => l.run_status === "failed").slice(0, 3).map((l) => (
                    <p key={l.log_id} style={{ margin: 2, fontSize: 12, color: "#e34d59" }}>{l.task_name}: {l.error_message?.slice(0, 50)}</p>
                  ))}
                  {!logs.filter((l) => l.run_status === "failed").length && <p style={{ fontSize: 12, color: "#888" }}>无异常</p>}
                </div>
              </div>
            )}

            {/* ====== Watch Pool ====== */}
            {active === "watchpool" && (
              <div style={{ display: "grid", gap: 10 }}>
                {!showForm && <Button block color="primary" onClick={resetForm}>+ 添加自选</Button>}
                {showForm && (
                  <div style={{ display: "grid", gap: 8, padding: 14, borderRadius: 14, background: "#fff" }}>
                    <strong style={{ fontSize: 15 }}>{editId ? "编辑自选" : "添加自选"}</strong>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                      <Input placeholder="股票代码" value={form.stock_code} onChange={(v) => setForm({ ...form, stock_code: v })} />
                      <Input placeholder="股票名称" value={form.stock_name} onChange={(v) => setForm({ ...form, stock_name: v })} />
                    </div>
                    <Input placeholder="所属板块" value={form.sector_name} onChange={(v) => setForm({ ...form, sector_name: v })} />
                    <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                      <Button size="mini" fill="outline" onClick={() => { setPickerKey("labels"); setPickerVisible(true); }}>
                        标签：{form.labels.length ? form.labels.join(",") : "-"}
                      </Button>
                      <Button size="mini" fill="outline" onClick={() => { setPickerKey("strategies"); setPickerVisible(true); }}>
                        策略：{form.operation_strategies.length ? form.operation_strategies.join(",") : "-"}
                      </Button>
                      <Button size="mini" fill="outline" onClick={() => { setPickerKey("buy_points"); setPickerVisible(true); }}>
                        买点：{form.buy_point_types.length ? form.buy_point_types.join(",") : "-"}
                      </Button>
                    </div>
                    <Input placeholder="入选理由" value={form.reason} onChange={(v) => setForm({ ...form, reason: v })} />
                    <div style={{ display: "flex", gap: 8 }}>
                      <Button block color="primary" onClick={saveWatch}>{editId ? "保存" : "确认添加"}</Button>
                      <Button block fill="none" onClick={() => setShowForm(false)}>取消</Button>
                    </div>
                  </div>
                )}
                {!showForm && watches.map((item) => (
                  <div key={item.watch_id} style={{ padding: 12, borderRadius: 14, background: "#fff" }}>
                    <strong style={{ fontSize: 15 }}>{item.stock_name} ({item.stock_code})</strong>
                    <div style={{ fontSize: 12, color: "#888", margin: "3px 0" }}>
                      状态：<span style={{ color: "#4b63ee", fontWeight: 700 }}>{statusLabel(item.pool_status)}</span>
                      {" | "}标签：{(item.labels || []).join(",") || "-"}
                    </div>
                    <div style={{ fontSize: 12, color: "#888" }}>
                      策略：{(item.operation_strategies || []).join(",")} | 买点：{(item.buy_point_types || []).join(",")}
                    </div>
                    {item.reason && <div style={{ fontSize: 12, color: "#aaa", marginTop: 2 }}>理由：{item.reason}</div>}
                    <div style={{ display: "flex", gap: 4, marginTop: 6, flexWrap: "wrap" }}>
                      <Button size="mini" onClick={() => editWatch(item)}>编辑</Button>
                      <Button size="mini" fill="outline" onClick={() => { setPickerKey(`status_${item.watch_id}`); setPickerVisible(true); }}>状态</Button>
                      {item.pool_status === "removed" || item.pool_status === "已剔除" ? (
                        <Button size="mini" color="primary" onClick={() => restoreWatch(item.watch_id)}>恢复</Button>
                      ) : (
                        <Button size="mini" color="danger" onClick={() => removeWatch(item.watch_id)}>剔除</Button>
                      )}
                    </div>
                  </div>
                ))}
                {!watches.length && <div style={{ textAlign: "center", padding: 40, color: "#888" }}>暂无自选股</div>}
              </div>
            )}

            {/* ====== Data Sources ====== */}
            {active === "sources" && (
              <div style={{ display: "grid", gap: 8 }}>
                {sources.map((s) => (
                  <div key={s.source_id} style={{ padding: 12, borderRadius: 14, background: "#fff" }}>
                    <strong style={{ fontSize: 14 }}>{s.source_name}</strong>
                    <p style={{ margin: 2, fontSize: 12, color: "#888" }}>{s.source_type} / {s.platform || "-"} / {s.enabled ? "启用" : "停用"}</p>
                    <p style={{ margin: 2, fontSize: 11, color: "#aaa" }}>{s.base_url || "无"}</p>
                  </div>
                ))}
                {!sources.length && <PlaceholderCard label="数据源" />}
              </div>
            )}

            {/* ====== Tasks ====== */}
            {active === "tasks" && (
              <div style={{ display: "grid", gap: 8 }}>
                {tasks.map((t) => (
                  <div key={t.task_id} style={{ padding: 12, borderRadius: 14, background: "#fff" }}>
                    <strong style={{ fontSize: 14 }}>{t.task_name}</strong>
                    <p style={{ margin: 2, fontSize: 12, color: "#888" }}>{t.task_type} / {t.enabled ? "启用" : "停用"} / {t.running ? "运行中" : "空闲"}</p>
                    <Button size="mini" color="primary" onClick={async () => { await apiPost(`/admin/tasks/${t.task_id}/run`); Toast.show({ content: `已触发 ${t.task_name}` }); loadAll(); }}>手动执行</Button>
                  </div>
                ))}
              </div>
            )}

            {/* ====== Field Mappings ====== */}
            {active === "mappings" && <PlaceholderCard label="字段映射" />}

            {/* ====== Strategies ====== */}
            {active === "strategies" && (
              <div style={{ display: "grid", gap: 8 }}>
                {strategies.map((s) => (
                  <div key={s.strategy_id} style={{ padding: 12, borderRadius: 14, background: "#fff" }}>
                    <strong style={{ fontSize: 14 }}>{s.strategy_name}</strong>
                    <p style={{ margin: 2, fontSize: 12, color: "#888" }}>{s.strategy_type} / {s.enabled ? "启用" : "停用"}</p>
                  </div>
                ))}
                {!strategies.length && <PlaceholderCard label="策略" />}
              </div>
            )}

            {/* ====== Dictionaries ====== */}
            {active === "dictionaries" && (
              <div style={{ display: "grid", gap: 6 }}>
                {dictionaries.slice(0, 40).map((d) => (
                  <div key={d.dict_id} style={{ padding: 10, borderRadius: 12, background: "#fff", fontSize: 12 }}>
                    <span style={{ color: "#4b63ee", fontWeight: 700 }}>{d.dict_type}</span>: {d.dict_label} = {d.dict_value}
                  </div>
                ))}
              </div>
            )}

            {/* ====== Review Templates ====== */}
            {active === "reviewTemplates" && <PlaceholderCard label="复盘模板" />}

            {/* ====== Notification Templates ====== */}
            {active === "notifications" && (
              <div style={{ display: "grid", gap: 8 }}>
                {templates.map((t) => (
                  <div key={t.template_id} style={{ padding: 12, borderRadius: 14, background: "#fff" }}>
                    <strong style={{ fontSize: 14 }}>{t.push_type}</strong>
                    <p style={{ margin: 2, fontSize: 12, color: "#888" }}>渠道：{t.channel} / {t.enabled ? "启用" : "停用"}</p>
                  </div>
                ))}
                {!templates.length && <PlaceholderCard label="推送" />}
              </div>
            )}

            {/* ====== Logs ====== */}
            {active === "logs" && (
              <div style={{ display: "grid", gap: 8 }}>
                {logs.length === 0 && <div style={{ textAlign: "center", padding: 40, color: "#888" }}>暂无日志</div>}
                {logs.map((l) => (
                  <div key={l.log_id} style={{ padding: 10, borderRadius: 12, background: "#fff", fontSize: 12 }}>
                    <strong>{l.task_name}</strong>
                    <span style={{ marginLeft: 8, color: l.run_status === "success" ? "#00b578" : "#e34d59" }}>{l.run_status}</span>
                    {l.error_message && <p style={{ margin: "2px 0 0", color: "#888" }}>{l.error_message.slice(0, 80)}</p>}
                  </div>
                ))}
              </div>
            )}

            {/* ====== Security ====== */}
            {active === "security" && (
              <div style={{ padding: 14, borderRadius: 14, background: "#fff" }}>
                <strong style={{ fontSize: 15 }}>账号与安全</strong>
                <p style={{ fontSize: 13, color: "#888" }}>单管理员模式</p>
                <p style={{ fontSize: 13, color: "#888" }}>数据库连接：***</p>
                <p style={{ fontSize: 13, color: "#888" }}>Redis：***</p>
                <p style={{ fontSize: 13, color: "#888" }}>数据源授权信息已脱敏</p>
                <p className="card-note" style={{ marginTop: 8 }}>敏感配置不返回前端，所有后台写操作记录到 config_operation_log</p>
              </div>
            )}
          </>
        )}
      </section>

      <Picker
        columns={[(pickerKey === "labels" ? LABEL_OPTS : pickerKey === "strategies" ? STRATEGY_OPTS : BUY_POINT_OPTS).map((v) => ({ label: v, value: v }))]}
        visible={pickerVisible && pickerKey !== "" && !pickerKey.startsWith("status_")}
        onClose={() => setPickerVisible(false)}
        onConfirm={(val) => {
          const vals = val as string[];
          if (pickerKey === "labels") setForm({ ...form, labels: vals });
          else if (pickerKey === "strategies") setForm({ ...form, operation_strategies: vals });
          else if (pickerKey === "buy_points") setForm({ ...form, buy_point_types: vals });
          setPickerVisible(false);
        }}
      />

      <Picker
        columns={[STATUS_OPTIONS]}
        visible={pickerVisible && pickerKey.startsWith("status_")}
        title="选择状态"
        onClose={() => setPickerVisible(false)}
        onConfirm={(val) => {
          const watchId = parseInt(pickerKey.replace("status_", ""), 10);
          const newStatus = (val as string[])[0];
          if (watchId && newStatus) { updateStatus(watchId, newStatus); }
          setPickerVisible(false);
        }}
      />
    </div>
  );
}
