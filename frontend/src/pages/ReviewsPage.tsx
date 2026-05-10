import { useEffect, useMemo, useState } from "react";
import { Button, Dialog, ErrorBlock, Input, Picker, Popup, SpinLoading, TextArea, Toast } from "antd-mobile";
import { apiDelete, apiGet, apiPost, apiPut } from "../api/client";
import { PageShell } from "../components/PageShell";

type ReviewItem = {
  review_id: number; review_type: string; review_period: string;
  status: string; title: string; system_summary: string;
  user_summary: string; improvement_plan: string; assistant_note: string;
};

type PlanItem = {
  id: number; plan_date: string; today_position: string;
  operation_summary: string; execution_status: string;
  tomorrow_plan: string; created_at?: string;
};

const POSITION_OPTS = ["空仓", "轻仓", "半仓", "重仓", "满仓"];
const EXEC_OPTS = ["完全执行", "部分执行", "未执行"];

export function ReviewsPage() {
  const [tab, setTab] = useState("plan");
  const [weekly, setWeekly] = useState<ReviewItem[]>([]);
  const [monthly, setMonthly] = useState<ReviewItem[]>([]);
  const [todos, setTodos] = useState<ReviewItem[]>([]);
  const [plans, setPlans] = useState<PlanItem[]>([]);
  const [editing, setEditing] = useState<ReviewItem | null>(null);
  const [note, setNote] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // plan form
  const [planForm, setPlanForm] = useState<PlanItem | null>(null);
  const [planPicker, setPlanPicker] = useState("");

  async function load() {
    setLoading(true);
    try {
      const [weeklyItems, monthlyItems, todoItems, planItems] = await Promise.all([
        apiGet<ReviewItem[]>("/h5/reviews/weekly"),
        apiGet<ReviewItem[]>("/h5/reviews/monthly"),
        apiGet<ReviewItem[]>("/h5/reviews/todos"),
        apiGet<PlanItem[]>("/h5/plans"),
      ]);
      setWeekly(weeklyItems);
      setMonthly(monthlyItems);
      setTodos(todoItems);
      setPlans(planItems);
      setError("");
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  const stats = useMemo(
    () => ({
      pending: todos.length,
      completed: [...weekly, ...monthly].filter((item) => item.status === "completed").length,
    }),
    [monthly, todos.length, weekly]
  );

  async function saveReview() {
    if (!editing) return;
    await apiPut(`/h5/reviews/${editing.review_id}`, { user_summary: note, status: "editing" });
    Toast.show({ content: "复盘已保存" });
    setEditing(null);
    await load();
  }

  async function savePlan() {
    if (!planForm) return;
    const payload: any = {
      plan_date: planForm.plan_date || new Date().toISOString().slice(0, 10),
      today_position: planForm.today_position,
      operation_summary: planForm.operation_summary,
      execution_status: planForm.execution_status,
      tomorrow_plan: planForm.tomorrow_plan,
    };
    if (planForm.id) {
      await apiPut(`/h5/plans/${planForm.id}`, payload);
    } else {
      await apiPost("/h5/plans", payload);
    }
    Toast.show({ content: planForm.id ? "已更新" : "已创建" });
    setPlanForm(null);
    await load();
  }

  async function deletePlan(id: number) {
    await apiDelete(`/h5/plans/${id}`);
    Toast.show({ content: "已删除" });
    load();
  }

  return (
    <PageShell
      title="复盘"
      hideHero
      segments={[
        { key: "plan", label: "日计划", onClick: () => setTab("plan") },
        { key: "weekly", label: "周复盘", onClick: () => setTab("weekly") },
        { key: "monthly", label: "月总结", onClick: () => setTab("monthly") },
      ]}
      activeSegment={tab}
    >
      {loading && <SpinLoading />}
      {error && <ErrorBlock description="复盘数据加载失败" />}

      {(tab === "weekly" || tab === "monthly") && (
        <>
          <section className="summary-board">
            <article className="summary-card">
              <span>待填写</span>
              <strong>{stats.pending}</strong>
              <p>包含周复盘、月总结和单笔交易复盘</p>
            </article>
            <article className="summary-card">
              <span>已完成</span>
              <strong>{stats.completed}</strong>
              <p>历史复盘不因模板更新被覆盖</p>
            </article>
          </section>

          <article className="feature-card">
            <div className="card-head">
              <div className="card-headline">
                <span className="icon-badge">复</span>
                <h2>{tab === "weekly" ? "周复盘" : "月总结"}</h2>
              </div>
              <span className="soft-tag">{(tab === "weekly" ? weekly : monthly).length} 份</span>
            </div>

            {(tab === "weekly" ? weekly : monthly).length ? (
              <div className="stack-list">
                {(tab === "weekly" ? weekly : monthly).map((item) => (
                  <div key={item.review_id} className="row-card row-card-action">
                    <div>
                      <strong>{item.title || item.review_period}</strong>
                      <p>周期：{item.review_period}</p>
                      <p>状态：{item.status}</p>
                      <p>{item.system_summary || item.assistant_note}</p>
                    </div>
                    <Button size="mini" onClick={() => { setEditing(item); setNote(item.user_summary || ""); }}>填写</Button>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-panel">暂无{tab === "weekly" ? "周复盘" : "月总结"}记录</div>
            )}
          </article>
        </>
      )}

      {tab === "plan" && (
        <>
          <article className="feature-card compact-card">
            <div className="card-head">
              <div className="card-headline">
                <span className="icon-badge">日</span>
                <h2>日计划</h2>
              </div>
              <Button size="mini" color="primary" onClick={() => setPlanForm({
                id: 0, plan_date: new Date().toISOString().slice(0, 10),
                today_position: "", operation_summary: "",
                execution_status: "", tomorrow_plan: "",
              })}>+ 添加</Button>
            </div>

            {plans.length ? (
              <div className="stack-list">
                {plans.map((item) => (
                  <div key={item.id} className="row-card">
                    <div>
                      <strong>{item.plan_date}</strong>
                      <p>仓位：{item.today_position || "-"} | 执行：{item.execution_status || "-"}</p>
                      <p>操作：{item.operation_summary || "-"}</p>
                      <p>明日：{item.tomorrow_plan || "-"}</p>
                    </div>
                    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                      <Button size="mini" fill="outline" onClick={() => setPlanForm({ ...item })}>编辑</Button>
                      <Button size="mini" fill="none" style={{ color: "#999", fontSize: 11 }}
                        onClick={async () => {
                          const ok = await Dialog.confirm({ content: "确认删除日计划？" });
                          if (ok) deletePlan(item.id);
                        }}>删除</Button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-panel">暂无日计划</div>
            )}
          </article>
        </>
      )}

      {/* Review Popup */}
      <Popup visible={Boolean(editing)} onMaskClick={() => setEditing(null)}
        bodyStyle={{ borderTopLeftRadius: 24, borderTopRightRadius: 24, padding: 20 }}>
        <div className="sheet-panel">
          <div className="sheet-head">
            <h3>填写复盘</h3>
            <p>记录市场、交易、执行和改进动作。仅作为交易辅助。</p>
          </div>
          <TextArea value={note} onChange={setNote} rows={7} placeholder="写下本周期最重要的观察、问题和下次改进动作" />
          <Button block color="primary" onClick={saveReview}>保存复盘</Button>
        </div>
      </Popup>

      {/* Plan Form Popup */}
      <Popup visible={Boolean(planForm)} onMaskClick={() => setPlanForm(null)}
        bodyStyle={{ borderTopLeftRadius: 24, borderTopRightRadius: 24, padding: 20 }}>
        <div className="sheet-panel">
          <div className="sheet-head">
            <h3>{planForm?.id ? "编辑日计划" : "添加日计划"}</h3>
            <p>{planForm?.plan_date}</p>
          </div>

          <Input placeholder="日期" value={planForm?.plan_date || ""}
            onChange={(v) => setPlanForm((p) => p ? { ...p, plan_date: v } : null)} />

          <div style={{ padding: "10px 14px", borderRadius: 12, background: "#f4f6fb", cursor: "pointer" }}
            onClick={() => setPlanPicker("position")}>
            <span style={{ fontSize: 13, color: "#888" }}>今日仓位：</span>
            <strong style={{ fontSize: 14 }}>{planForm?.today_position || "点击选择"}</strong>
          </div>

          <div style={{ padding: "10px 14px", borderRadius: 12, background: "#f4f6fb", cursor: "pointer" }}
            onClick={() => setPlanPicker("execution")}>
            <span style={{ fontSize: 13, color: "#888" }}>执行情况：</span>
            <strong style={{ fontSize: 14 }}>{planForm?.execution_status || "点击选择"}</strong>
          </div>

          <TextArea value={planForm?.operation_summary || ""}
            onChange={(v) => setPlanForm((p) => p ? { ...p, operation_summary: v } : null)}
            rows={3} placeholder="操作小结" />

          <TextArea value={planForm?.tomorrow_plan || ""}
            onChange={(v) => setPlanForm((p) => p ? { ...p, tomorrow_plan: v } : null)}
            rows={3} placeholder="明日计划" />

          <div style={{ display: "flex", gap: 8 }}>
            <Button block fill="none" onClick={() => setPlanForm(null)}>取消</Button>
            <Button block color="primary" onClick={savePlan}>保存</Button>
          </div>
        </div>
      </Popup>

      {/* Pickers */}
      <Picker
        columns={[POSITION_OPTS.map((v) => ({ label: v, value: v }))]}
        visible={planPicker === "position"}
        title="今日仓位"
        onClose={() => setPlanPicker("")}
        onConfirm={(val) => {
          setPlanForm((p) => p ? { ...p, today_position: (val as string[])[0] } : null);
          setPlanPicker("");
        }}
      />
      <Picker
        columns={[EXEC_OPTS.map((v) => ({ label: v, value: v }))]}
        visible={planPicker === "execution"}
        title="按计划执行情况"
        onClose={() => setPlanPicker("")}
        onConfirm={(val) => {
          setPlanForm((p) => p ? { ...p, execution_status: (val as string[])[0] } : null);
          setPlanPicker("");
        }}
      />
    </PageShell>
  );
}
