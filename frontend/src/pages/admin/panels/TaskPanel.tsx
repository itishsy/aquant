import { Button, Toast } from "antd-mobile";
import { taskConfigSummary, taskErrorText, taskTimeText } from "../utils";

export const WATCH_MONITOR_TASKS = new Set(["scan_watch_rules", "scan_trade_rules", "prepare_watch_kline_data", "prepare_trade_kline_data", "auto_remove_watch_pool", "update_watch_prices"]);

export function TaskPanel({ tasks, onRun, onSaveConfig }: { tasks: any[]; onRun: (task: any) => void; onSaveConfig: (task: any, config: Record<string, any>) => void }) {
  const watchTasks = tasks.filter((task) => WATCH_MONITOR_TASKS.has(task.task_name));
  const otherTasks = tasks.filter((task) => !WATCH_MONITOR_TASKS.has(task.task_name));
  return (
    <div style={{ display: "grid", gap: 14 }}>
      <TaskGroup title="自选监控" tasks={watchTasks} onRun={onRun} onSaveConfig={onSaveConfig} />
      <TaskGroup title="其他任务" tasks={otherTasks} onRun={onRun} onSaveConfig={onSaveConfig} />
    </div>
  );
}

export function TaskGroup({ title, tasks, onRun, onSaveConfig }: { title: string; tasks: any[]; onRun: (task: any) => void; onSaveConfig: (task: any, config: Record<string, any>) => void }) {
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

