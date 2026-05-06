import { useEffect, useState } from "react";
import { Button, ErrorBlock, SpinLoading } from "antd-mobile";
import { apiGet, apiPost } from "../api/client";

const sections = [
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

export function AdminPage() {
  const [active, setActive] = useState("dashboard");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [overview, setOverview] = useState<any>(null);
  const [tasks, setTasks] = useState<any[]>([]);
  const [dictionaries, setDictionaries] = useState<any[]>([]);
  const [logs, setLogs] = useState<any[]>([]);

  async function load() {
    setLoading(true);
    setError("");
    try {
      const [overviewData, taskData, dictData, logData] = await Promise.all([
        apiGet<any>("/admin/dashboard/overview"),
        apiGet<any[]>("/admin/tasks"),
        apiGet<any[]>("/admin/dictionaries"),
        apiGet<any[]>("/admin/task-logs"),
      ]);
      setOverview(overviewData);
      setTasks(taskData || []);
      setDictionaries(dictData || []);
      setLogs(logData || []);
    } catch (err) {
      setError("后台管理数据加载失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function runFirstTask() {
    if (!tasks[0]?.task_id) return;
    await apiPost(`/admin/tasks/${tasks[0].task_id}/run`);
    await load();
  }

  return (
    <main className="admin-layout">
      <aside className="admin-sidebar">
        <h1>Aquant Admin</h1>
        <p>单用户后台管理</p>
        {sections.map((item) => (
          <button key={item.key} className={active === item.key ? "active" : ""} onClick={() => setActive(item.key)}>
            {item.label}
          </button>
        ))}
      </aside>
      <section className="admin-content">
        {loading && <SpinLoading />}
        {error && <ErrorBlock description={error} />}
        {!loading && !error && (
          <>
            <div className="admin-card">
              <span className="pill">后台管理</span>
              <h2>{sections.find((item) => item.key === active)?.label}</h2>
              <p>后台不进入 H5 底部导航；写操作保留操作日志，敏感配置应脱敏展示。</p>
            </div>

            {active === "dashboard" && (
              <div className="admin-grid">
                <div className="admin-card">
                  <strong>任务数</strong>
                  <b>{overview?.tasks ?? 0}</b>
                </div>
                <div className="admin-card">
                  <strong>数据源</strong>
                  <b>{overview?.data_sources ?? 0}</b>
                </div>
                <div className="admin-card">
                  <strong>字典项</strong>
                  <b>{overview?.dictionaries ?? 0}</b>
                </div>
              </div>
            )}

            {active === "tasks" && (
              <div className="admin-card">
                <div className="admin-row">
                  <h3>采集任务</h3>
                  <Button size="small" color="primary" onClick={runFirstTask}>
                    手动执行首个任务
                  </Button>
                </div>
                {tasks.map((task) => (
                  <p key={task.task_id}>
                    {task.task_name} / {task.task_type} / {task.enabled ? "启用" : "停用"}
                  </p>
                ))}
              </div>
            )}

            {active === "dictionaries" && (
              <div className="admin-card">
                <h3>字典管理</h3>
                {dictionaries.slice(0, 20).map((item) => (
                  <p key={item.dict_id}>
                    {item.dict_type}: {item.dict_label}
                  </p>
                ))}
              </div>
            )}

            {active === "logs" && (
              <div className="admin-card">
                <h3>日志中心</h3>
                {logs.length === 0 && <p>暂无任务日志</p>}
                {logs.map((item) => (
                  <p key={item.log_id}>
                    {item.task_name} / {item.run_status} / {item.error_message || "无错误"}
                  </p>
                ))}
              </div>
            )}

            {!["dashboard", "tasks", "dictionaries", "logs"].includes(active) && (
              <div className="admin-card">
                <h3>{sections.find((item) => item.key === active)?.label}</h3>
                <p>基础入口已就绪，可连接对应 `/api/admin/**` 配置接口继续扩展。</p>
              </div>
            )}
          </>
        )}
      </section>
    </main>
  );
}
