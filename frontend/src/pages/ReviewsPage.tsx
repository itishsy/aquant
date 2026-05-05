import { useEffect, useMemo, useState } from "react";
import { Button, ErrorBlock, Popup, SpinLoading, TextArea, Toast } from "antd-mobile";
import { apiGet, apiPut } from "../api/client";
import { PageShell } from "../components/PageShell";

type ReviewItem = {
  review_id: number;
  review_type: string;
  review_period: string;
  status: string;
  title: string;
  system_summary: string;
  user_summary: string;
  improvement_plan: string;
  assistant_note: string;
};

export function ReviewsPage() {
  const [tab, setTab] = useState("weekly");
  const [weekly, setWeekly] = useState<ReviewItem[]>([]);
  const [monthly, setMonthly] = useState<ReviewItem[]>([]);
  const [todos, setTodos] = useState<ReviewItem[]>([]);
  const [editing, setEditing] = useState<ReviewItem | null>(null);
  const [note, setNote] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    try {
      const [weeklyItems, monthlyItems, todoItems] = await Promise.all([
        apiGet<ReviewItem[]>("/h5/reviews/weekly"),
        apiGet<ReviewItem[]>("/h5/reviews/monthly"),
        apiGet<ReviewItem[]>("/h5/reviews/todos"),
      ]);
      setWeekly(weeklyItems);
      setMonthly(monthlyItems);
      setTodos(todoItems);
      setError("");
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const activeItems = tab === "weekly" ? weekly : monthly;
  const stats = useMemo(
    () => ({
      pending: todos.length,
      completed: [...weekly, ...monthly].filter((item) => item.status === "completed").length,
    }),
    [monthly, todos.length, weekly]
  );

  async function saveReview() {
    if (!editing) return;
    await apiPut(`/h5/reviews/${editing.review_id}`, {
      user_summary: note,
      status: "editing",
    });
    Toast.show({ content: "复盘已保存，仅作为交易辅助" });
    setEditing(null);
    await load();
  }

  return (
    <PageShell
      title="复盘"
      hideHero
      segments={[
        { key: "weekly", label: "周复盘", onClick: () => setTab("weekly") },
        { key: "monthly", label: "月复盘", onClick: () => setTab("monthly") },
      ]}
      activeSegment={tab}
    >
      {loading && <SpinLoading />}
      {error && <ErrorBlock description="复盘数据加载失败" />}

      <section className="summary-board">
        <article className="summary-card">
          <span>待填写</span>
          <strong>{stats.pending}</strong>
          <p>包含周复盘、月复盘和单笔交易复盘</p>
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
            <h2>{tab === "weekly" ? "周复盘" : "月复盘"}</h2>
          </div>
          <span className="soft-tag">{activeItems.length} 份</span>
        </div>

        {activeItems.length ? (
          <div className="stack-list">
            {activeItems.map((item) => (
              <div key={item.review_id} className="row-card row-card-action">
                <div>
                  <strong>{item.title || item.review_period}</strong>
                  <p>周期：{item.review_period}</p>
                  <p>状态：{item.status}</p>
                  <p>{item.system_summary || item.assistant_note}</p>
                </div>
                <Button
                  size="mini"
                  onClick={() => {
                    setEditing(item);
                    setNote(item.user_summary || "");
                  }}
                >
                  填写
                </Button>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-panel">暂无{tab === "weekly" ? "周复盘" : "月复盘"}记录</div>
        )}
      </article>

      <Popup
        visible={Boolean(editing)}
        onMaskClick={() => setEditing(null)}
        bodyStyle={{ borderTopLeftRadius: 24, borderTopRightRadius: 24, padding: 20 }}
      >
        <div className="sheet-panel">
          <div className="sheet-head">
            <h3>填写复盘</h3>
            <p>记录市场、交易、执行和改进动作。仅作为交易辅助，请结合个人交易规则确认。</p>
          </div>
          <TextArea value={note} onChange={setNote} rows={7} placeholder="写下本周期最重要的观察、问题和下次改进动作" />
          <Button block color="primary" onClick={saveReview}>
            保存复盘
          </Button>
        </div>
      </Popup>
    </PageShell>
  );
}
