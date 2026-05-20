import { useEffect, useState } from "react";
import { Button, ErrorBlock, SpinLoading, Toast } from "antd-mobile";
import { apiGet, apiPost } from "../api/client";
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

  async function runTask(task: any) {
    setRunningTaskId(task.task_id);
    try {
      const res: any = await apiPost(`/h5/me/tasks/${task.task_id}/run`);
      Toast.show({ content: `${task.task_label || task.task_name}：${res.log?.run_status || "done"}` });
      load();
    } catch {
      Toast.show({ content: "任务执行失败" });
    } finally {
      setRunningTaskId(null);
    }
  }

  function fmtTime(iso?: string) {
    if (!iso) return "暂无";
    const d = new Date(iso + "Z");
    const pad = (n: number) => String(n).padStart(2, "0");
    return `${d.getMonth() + 1}/${d.getDate()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
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
              <div>
                <strong>市场数据采集</strong>
                <p>最近采集：{fmtTime(summary?.last_collect_time)}</p>
                <p style={{ fontSize: 11, color: "#aaa" }}>定时任务：每日 18:00 自动采集大盘/热榜/涨停数据</p>
              </div>
              <Button size="small" loading={collecting} onClick={doCollect}>
                立即采集
              </Button>
            </div>

            <div className="row-card" style={{ display: "grid", gap: 12 }}>
              <div>
                <strong>后台任务管理</strong>
                <p>
                  总数：{taskData?.summary?.total ?? 0} / 启用：{taskData?.summary?.enabled ?? 0} / 运行中：{taskData?.summary?.running ?? 0} / 异常：{taskData?.summary?.failed ?? 0}
                </p>
              </div>
              <div style={{ display: "grid", gap: 12 }}>
                {(taskData?.groups || []).map((group: any) => (
                  <div key={group.module} style={{ display: "grid", gap: 8 }}>
                    <div style={{ color: "#22375c", fontSize: 13, fontWeight: 800 }}>{group.label}</div>
                    {(group.tasks || []).map((task: any) => {
                      const log = task.latest_log || {};
                      const currentStatus = task.running ? "running" : log.run_status;
                      return (
                        <div key={task.task_id} style={{ borderRadius: 12, background: "#f7f9ff", padding: 10, display: "grid", gap: 7 }}>
                          <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "flex-start" }}>
                            <div style={{ minWidth: 0 }}>
                              <strong style={{ display: "block", color: "#17213b", fontSize: 14 }}>{task.task_label || task.task_name}</strong>
                              <p style={{ margin: "3px 0 0", color: "#7b879c", fontSize: 12 }}>
                                {task.enabled ? "已启用" : "已停用"} · 最近：{fmtTime(log.finished_at || log.started_at)}
                              </p>
                            </div>
                            <span style={{ color: statusColor(currentStatus), fontSize: 12, fontWeight: 800, whiteSpace: "nowrap" }}>{statusText(currentStatus)}</span>
                          </div>
                          <div style={{ display: "flex", justifyContent: "space-between", gap: 8, alignItems: "center" }}>
                            <p style={{ margin: 0, color: "#98a2b3", fontSize: 12 }}>影响行数：{log.affected_rows ?? 0}{log.error_message ? ` / ${log.error_message}` : ""}</p>
                            <Button size="mini" fill="outline" loading={runningTaskId === task.task_id} disabled={task.running} onClick={() => runTask(task)}>
                              执行
                            </Button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ))}
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
                <p>{backendEntry?.enabled ? `可进入：${backendEntry.entry_url}` : "当前未开放"}</p>
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
