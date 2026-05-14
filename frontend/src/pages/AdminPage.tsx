import { useEffect, useState } from "react";
import { Button, ErrorBlock, SpinLoading, Toast } from "antd-mobile";
import { apiGet, apiPost } from "../api/client";

const SECTIONS = [
  { key: "dashboard", label: "工作台" },
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

  async function loadAll() {
    setLoading(true);
    try {
      const [ov, tk, dc, lg, src, st, tpl] = await Promise.all([
        apiGet<any>("/admin/dashboard/overview"),
        apiGet<any[]>("/admin/tasks"),
        apiGet<any[]>("/admin/dictionaries"),
        apiGet<any[]>("/admin/task-logs"),
        apiGet<any[]>("/admin/data-sources"),
        apiGet<any[]>("/admin/strategies"),
        apiGet<any[]>("/admin/notification-templates"),
      ]);
      setOverview(ov || {});
      setTasks(tk || []);
      setDictionaries(dc || []);
      setLogs(lg || []);
      setSources(src || []);
      setStrategies(st || []);
      setTemplates(tpl || []);
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

  const activeLabel = SECTIONS.find((item) => item.key === active)?.label || "";

  return (
    <div style={{ minHeight: "100vh", background: "#f4f6fb" }}>
      <header style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px 18px", background: "linear-gradient(90deg, #1b2447, #334497)", color: "#fff", position: "sticky", top: 0, zIndex: 100 }}>
        <strong style={{ fontSize: 16 }}>Aquant 后台 · {activeLabel}</strong>
        <Button size="mini" color="primary" onClick={loadAll}>刷新</Button>
      </header>

      <div style={{ display: "grid", gridTemplateColumns: "220px 1fr", gap: 16, padding: 16 }}>
        <aside style={{ display: "grid", gap: 8, alignSelf: "start", position: "sticky", top: 64 }}>
          {SECTIONS.map((item) => (
            <button
              key={item.key}
              onClick={() => setActive(item.key)}
              style={{
                border: 0,
                borderRadius: 12,
                padding: "12px 14px",
                textAlign: "left",
                fontWeight: 700,
                color: active === item.key ? "#fff" : "#344054",
                background: active === item.key ? "linear-gradient(135deg, #5570ff, #4052d2)" : "#fff",
                cursor: "pointer",
              }}
            >
              {item.label}
            </button>
          ))}
        </aside>

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

          {!loading && !error && active === "tasks" && (
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
