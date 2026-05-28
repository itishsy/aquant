import { useEffect, useState } from "react";
import { Button, ErrorBlock, Input, SpinLoading, Toast } from "antd-mobile";
import { apiGet, apiPost, apiPut } from "../api/client";
import { PageShell } from "../components/PageShell";

export function SettingsPage() {
  const [profile, setProfile] = useState<any>(null);
  const [todos, setTodos] = useState<any>(null);
  const [summary, setSummary] = useState<any>(null);
  const [backendEntry, setBackendEntry] = useState<any>(null);
  const [taskData, setTaskData] = useState<any>(null);
  const [taskLogs, setTaskLogs] = useState<any[]>([]);
  const [error, setError] = useState("");
  const [collecting, setCollecting] = useState(false);
  const [runningTaskId, setRunningTaskId] = useState<number | null>(null);
  const [notifyEmail, setNotifyEmail] = useState("");
  const [emailSaving, setEmailSaving] = useState(false);

  async function load() {
    try {
      const [profileData, todosData, summaryData, entryData, tasksData, logsData] = await Promise.all([
        apiGet("/h5/me/profile"),
        apiGet("/h5/me/todos"),
        apiGet("/h5/me/system-summary"),
        apiGet("/h5/me/backend-entry"),
        apiGet("/h5/me/tasks"),
        apiGet<any[]>("/h5/me/task-logs?limit=8"),
      ]);
      setProfile(profileData);
      setTodos(todosData);
      setSummary(summaryData);
      setBackendEntry(entryData);
      setTaskData(tasksData);
      setTaskLogs(logsData || []);
      apiGet<any>("/h5/me/notification-email").then((d) => setNotifyEmail(d.email || "")).catch(() => {});
      setError("");
    } catch (err) {
      setError(String(err));
    }
  }

  useEffect(() => { load(); }, []);

  async function doCollect() {
    setCollecting(true);
    try {
      const res: any = await apiPost("/h5/me/collect-market");
      Toast.show({ content: `采集完成 (${res.collect_time?.slice(11, 19) || "ok"})` });
      load();
    } catch {
      Toast.show({ content: "采集失败" });
    } finally {
      setCollecting(false);
    }
  }

  async function saveEmail() {
    setEmailSaving(true);
    try {
      await apiPut("/h5/me/notification-email", { email: notifyEmail.trim() });
      Toast.show({ content: "邮箱已保存" });
    } catch { Toast.show({ content: "保存失败" }); }
    finally { setEmailSaving(false); }
  }

  async function runGroup(group: any) {
    setRunningTaskId(group.module);
    const tasks = (group.tasks || []).filter((t: any) => t.enabled);
    let ok = 0; let fail = 0;
    for (const task of tasks) {
      try {
        await apiPost(`/h5/me/tasks/${task.task_id}/run`);
        ok++;
      } catch { fail++; }
    }
    Toast.show({ content: `${group.label}：完成 ${ok}${fail ? ` / 失败 ${fail}` : ""}` });
    setRunningTaskId(null);
    load();
  }

  function fmtTime(iso?: string) {
    if (!iso) return "暂无";
    const d = new Date(iso + "Z");
    const pad = (n: number) => String(n).padStart(2, "0");
    return `${d.getMonth() + 1}/${d.getDate()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
  }

  function fmtTaskRunDate(iso?: string) {
    if (!iso) return "未运行";
    const d = new Date(iso + "Z");
    const pad = (n: number) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  }

  function statusText(status?: string) {
    if (status === "success") return "成功";
    if (status === "failed") return "失败";
    if (status === "running") return "运行中";
    return "未运行";
  }

  function statusColor(status?: string) {
    if (status === "success") return "#00a870";
    if (status === "failed") return "#e34d59";
    if (status === "running") return "#4b63ee";
    return "#7b879c";
  }

  return (
    <PageShell title="我的" hideHero>
      {error && <ErrorBlock description="我的页面加载失败" />}
      {!profile && !error && <SpinLoading />}
      {profile && (
        <article className="feature-card">
          <div className="card-head">
            <div className="card-headline">
              <span className="icon-badge">我</span>
              <h2>{profile.nickname || "Aquant 用户"}</h2>
            </div>
            <span className="soft-tag">单用户</span>
          </div>

          <div className="stack-list">
            <div className="row-card">
              <div>
                <strong>待办提醒</strong>
                <p>待复盘：{todos?.pending_reviews ?? 0} / 未读消息：{todos?.unread_notifications ?? 0}</p>
              </div>
            </div>

            <div className="row-card">
              <div style={{ flex: 1 }}>
                <strong>邮件通知</strong>
                <p style={{ fontSize: 12, color: "#888", marginTop: 4 }}>接收买卖信号提醒</p>
                <Input
                  value={notifyEmail}
                  onChange={setNotifyEmail}
                  placeholder="输入接收提醒的邮箱"
                  style={{ marginTop: 6 }}
                />
              </div>
              <Button size="small" color="primary" loading={emailSaving} onClick={saveEmail}>
                保存
              </Button>
            </div>

            <div className="row-card" style={{ display: "grid", gap: 12, alignItems: "stretch", justifyContent: "stretch" }}>
              <div>
                <strong>后台任务管理</strong>
                <p>
                  总数：{taskData?.summary?.total ?? 0} / 启用：{taskData?.summary?.enabled ?? 0} / 运行中：{taskData?.summary?.running ?? 0} / 异常：{taskData?.summary?.failed ?? 0}
                </p>
              </div>
              <div style={{ display: "grid", gap: 12, width: "100%" }}>
                {(taskData?.groups || []).map((group: any) => {
                  const hasRunning = (group.tasks || []).some((t: any) => t.running);
                  return (
                  <div key={group.module} style={{ borderRadius: 14, background: "#f7f9ff", padding: 12, display: "grid", gap: 8, width: "100%" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <div>
                        <div style={{ color: "#22375c", fontSize: 14, fontWeight: 800 }}>{group.label}</div>
                        <p style={{ margin: "2px 0 0", color: "#7b879c", fontSize: 12 }}>
                          {(group.tasks || []).length} 个子任务 · 启用 {group.tasks?.filter((t: any) => t.enabled).length || 0}
                        </p>
                      </div>
                      <Button size="small" fill="outline"
                        loading={runningTaskId === group.module}
                        disabled={hasRunning || runningTaskId != null}
                        onClick={() => runGroup(group)}>
                        执行
                      </Button>
                    </div>
                    <div style={{ width: "100%", fontSize: 11, display: "grid", gridTemplateColumns: "minmax(0, 1.4fr) minmax(0, 1fr) minmax(0, 1fr) minmax(0, 0.7fr)", gap: 8, color: "#7b879c", fontWeight: 700, padding: "4px 0", borderBottom: "1px solid #e6eaf2" }}>
                      <span>任务</span>
                      <span>执行计划</span>
                      <span>最近一次执行时间</span>
                      <span style={{ textAlign: "right" }}>运行状态</span>
                    </div>
                    {(group.tasks || []).map((task: any) => {
                      const log = task.latest_log || {};
                      const currentStatus = task.running ? "running" : log.run_status;
                      const lastRunTime = fmtTaskRunDate(log.finished_at || log.started_at);
                      return (
                        <div key={task.task_id} style={{ width: "100%", fontSize: 12, display: "grid", gridTemplateColumns: "minmax(0, 1.4fr) minmax(0, 1fr) minmax(0, 1fr) minmax(0, 0.7fr)", gap: 8, alignItems: "center", padding: "6px 0", borderBottom: "1px solid #eee" }}>
                          <span style={{ color: "#334" }}>{task.task_label || task.task_name}</span>
                          <span style={{ color: "#667085", fontSize: 11 }}>{task.execution_plan || task.cron_expression || "手动执行"}</span>
                          <span style={{ color: "#667085", fontSize: 11 }}>{lastRunTime}</span>
                          <span style={{ color: statusColor(currentStatus), fontWeight: 700, fontSize: 11, textAlign: "right" }}>{statusText(currentStatus)}</span>
                        </div>
                      );
                    })}
                  </div>
                  );
                })}
              </div>
            </div>

            <div className="row-card" style={{ display: "grid", gap: 8 }}>
              <div>
                <strong>最近任务日志</strong>
                <p>自动任务和手动执行的最近记录。</p>
              </div>
              <div style={{ display: "grid", gap: 6 }}>
                {taskLogs.length ? taskLogs.map((log) => (
                  <div key={log.log_id} style={{ display: "flex", justifyContent: "space-between", gap: 10, fontSize: 12, color: "#667085" }}>
                    <span style={{ minWidth: 0 }}>{log.task_name}</span>
                    <span style={{ color: statusColor(log.run_status), fontWeight: 800, whiteSpace: "nowrap" }}>{statusText(log.run_status)} · {fmtTime(log.finished_at || log.started_at)}</span>
                  </div>
                )) : <p>暂无任务日志</p>}
              </div>
            </div>

            <div className="row-card">
              <div>
                <strong>系统状态</strong>
                <p>模式：{summary?.mode || "single-user"} / 自选数量：{summary?.watch_count ?? 0}</p>
              </div>
            </div>

            <div className="row-card">
              <div>
                <strong>个人偏好</strong>
                <p>偏好配置通过后台字典和我的模块维护，敏感配置不会返回前端。</p>
              </div>
            </div>

            <div className="row-card">
              <div>
                <strong>后台管理入口</strong>
                <p><a href="/admin" style={{ color: "#4b63ee", fontWeight: 700 }}>进入后台管理系统</a></p>
              </div>
            </div>

            <div className="row-card">
              <div>
                <strong>合规边界</strong>
                <p>系统只做行情、信号、记录和复盘辅助，不连接真实账户。仅作为交易辅助，请结合个人交易规则确认。</p>
              </div>
            </div>
          </div>
        </article>
      )}
    </PageShell>
  );
}
