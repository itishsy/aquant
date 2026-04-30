import { useEffect, useMemo, useState } from "react";
import { Button, ErrorBlock, Form, Input, Popup, SpinLoading, TextArea, Toast } from "antd-mobile";
import { apiGet, apiPost } from "../api/client";
import { PageShell } from "../components/PageShell";

type WeeklyReview = {
  week_start: string;
  week_end: string;
  metrics: {
    total_trades: number;
    win_rate: number;
    profit_loss_ratio: number;
    total_pnl: number;
    max_drawdown: number;
    signal_success_rate: number;
  };
  system_summary: string;
  user_notes: string;
};

type DailyPlan = {
  id: number;
  plan_date: string;
  title: string;
  focus: string;
  risk_rule: string;
  note: string;
  created_at: string;
};

function getWeekRange() {
  const end = new Date();
  const start = new Date(end);
  start.setDate(end.getDate() - 6);
  return {
    weekStart: start.toISOString().slice(0, 10),
    weekEnd: end.toISOString().slice(0, 10),
  };
}

export function ReviewsPage() {
  const [{ weekStart, weekEnd }] = useState(getWeekRange);
  const [tab, setTab] = useState("daily");
  const [review, setReview] = useState<WeeklyReview | null>(null);
  const [dailyPlans, setDailyPlans] = useState<DailyPlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [planPopupOpen, setPlanPopupOpen] = useState(false);
  const [notePopupOpen, setNotePopupOpen] = useState(false);
  const [planTitle, setPlanTitle] = useState("");
  const [planFocus, setPlanFocus] = useState("");
  const [planRiskRule, setPlanRiskRule] = useState("");
  const [planNote, setPlanNote] = useState("");
  const [weeklyNote, setWeeklyNote] = useState("");
  const [submittingPlan, setSubmittingPlan] = useState(false);
  const [savingNote, setSavingNote] = useState(false);

  async function load() {
    setLoading(true);
    setError("");
    try {
      const [reviewResponse, plansResponse] = await Promise.all([
        apiGet<WeeklyReview>(`/reviews/weekly?week_start=${weekStart}&week_end=${weekEnd}`),
        apiGet<DailyPlan[]>(`/reviews/daily-plans?start_date=${weekStart}&end_date=${weekEnd}`),
      ]);
      setReview(reviewResponse);
      setWeeklyNote(reviewResponse.user_notes || "");
      setDailyPlans(plansResponse);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const summary = useMemo(
    () => ({
      count: dailyPlans.length,
      latest: dailyPlans[0]?.plan_date || "暂无",
    }),
    [dailyPlans]
  );

  async function savePlan() {
    if (!planTitle.trim()) {
      Toast.show({ content: "请先填写计划标题" });
      return;
    }
    setSubmittingPlan(true);
    try {
      await apiPost<DailyPlan>("/reviews/daily-plans", {
        plan_date: new Date().toISOString().slice(0, 10),
        title: planTitle.trim(),
        focus: planFocus.trim(),
        risk_rule: planRiskRule.trim(),
        note: planNote.trim(),
      });
      setPlanPopupOpen(false);
      setPlanTitle("");
      setPlanFocus("");
      setPlanRiskRule("");
      setPlanNote("");
      await load();
      Toast.show({ content: "已保存每日计划" });
    } catch (err) {
      Toast.show({ content: `保存失败：${String(err)}` });
    } finally {
      setSubmittingPlan(false);
    }
  }

  async function saveWeeklyNote() {
    setSavingNote(true);
    try {
      const updated = await apiPost<WeeklyReview>("/reviews/weekly/note", {
        week_start: weekStart,
        week_end: weekEnd,
        user_notes: weeklyNote,
      });
      setReview(updated);
      setWeeklyNote(updated.user_notes || "");
      setNotePopupOpen(false);
      Toast.show({ content: "已保存复盘心得" });
    } catch (err) {
      Toast.show({ content: `保存失败：${String(err)}` });
    } finally {
      setSavingNote(false);
    }
  }

  const metrics = review?.metrics;

  return (
    <PageShell
      title="复盘"
      hideHero
      segments={[
        { key: "daily", label: "每日计划", onClick: () => setTab("daily") },
        { key: "weekly", label: "周复盘", onClick: () => setTab("weekly") },
        { key: "monthly", label: "月总结", onClick: () => setTab("monthly") },
      ]}
      activeSegment={tab}
    >
      {loading && <SpinLoading />}
      {error && <ErrorBlock description="复盘数据加载失败" />}

      {review && metrics ? (
        <>
          <section className="summary-board">
            <article className="summary-card">
              <span>周交易数</span>
              <strong>{metrics.total_trades}</strong>
              <p>本周完成交易总数</p>
            </article>
            <article className="summary-card">
              <span>胜率</span>
              <strong>{metrics.win_rate}</strong>
              <p>已完成交易胜率</p>
            </article>
            <article className="summary-card">
              <span>盈亏比</span>
              <strong>{metrics.profit_loss_ratio}</strong>
              <p>盈利与亏损对比</p>
            </article>
            <article className="summary-card">
              <span>计划记录数</span>
              <strong>{summary.count}</strong>
              <p>最近计划日期：{summary.latest}</p>
            </article>
          </section>

          <article className="feature-card">
            <div className="card-head">
              <div className="card-headline">
                <span className="icon-badge">复</span>
                <h2>{tab === "daily" ? "每日计划" : tab === "weekly" ? "周复盘" : "月总结"}</h2>
              </div>
              {tab === "daily" ? (
                <Button size="small" color="primary" onClick={() => setPlanPopupOpen(true)}>
                  新建计划
                </Button>
              ) : (
                <Button size="small" color="primary" onClick={() => setNotePopupOpen(true)}>
                  编辑心得
                </Button>
              )}
            </div>

            {tab === "daily" ? (
              <>
                <p className="card-note">记录当天关注方向、风险条件和执行提醒，方便盘后复盘对照。</p>
                {dailyPlans.length ? (
                  <div className="stack-list">
                    {dailyPlans.map((plan) => (
                      <div key={plan.id} className="row-card row-card-action">
                        <div>
                          <strong>{plan.title}</strong>
                          <p>计划日期：{plan.plan_date}</p>
                          <p>关注方向：{plan.focus || "未填写"}</p>
                          <p>风控条件：{plan.risk_rule || "未填写"}</p>
                          <p>补充备注：{plan.note || "未填写"}</p>
                        </div>
                        <span className="soft-tag">{plan.plan_date}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="empty-panel">暂无历史计划</div>
                )}
              </>
            ) : null}

            {tab === "weekly" ? (
              <>
                <div className="metric-grid">
                  <div className="metric-tile">
                    <span>总交易数</span>
                    <strong>{metrics.total_trades}</strong>
                  </div>
                  <div className="metric-tile">
                    <span>总盈亏</span>
                    <strong>{metrics.total_pnl}</strong>
                  </div>
                  <div className="metric-tile">
                    <span>最大回撤</span>
                    <strong>{metrics.max_drawdown}</strong>
                  </div>
                  <div className="metric-tile">
                    <span>信号表现</span>
                    <strong>{metrics.signal_success_rate}</strong>
                  </div>
                </div>
                <div className="review-note-panel">
                  <strong>系统总结</strong>
                  <p>{review.system_summary}</p>
                  <strong>复盘心得</strong>
                  <p>{review.user_notes || "暂无复盘心得，点击右上角编辑心得。"}</p>
                </div>
              </>
            ) : null}

            {tab === "monthly" ? (
              <div className="review-note-panel">
                <strong>月度总结</strong>
                <p>当前先保留摘要区和编辑入口，下一步可以继续补月度统计、题材命中率和执行偏差分布。</p>
                <p>当前心得：{review.user_notes || "暂无记录"}</p>
              </div>
            ) : null}
          </article>
        </>
      ) : null}

      <Popup
        visible={planPopupOpen}
        onMaskClick={() => setPlanPopupOpen(false)}
        bodyStyle={{ borderTopLeftRadius: 24, borderTopRightRadius: 24, padding: 20 }}
      >
        <div className="sheet-panel">
          <div className="sheet-head">
            <h3>新建每日计划</h3>
            <p>围绕市场环境、主线方向和执行纪律做简要记录。</p>
          </div>
          <Form
            footer={
              <Button block color="primary" loading={submittingPlan} onClick={savePlan}>
                保存计划
              </Button>
            }
          >
            <Form.Item label="计划标题">
              <Input value={planTitle} onChange={setPlanTitle} placeholder="例如：4月26日盘前计划" />
            </Form.Item>
            <Form.Item label="关注方向">
              <Input value={planFocus} onChange={setPlanFocus} placeholder="例如：算力修复、机器人轮动" />
            </Form.Item>
            <Form.Item label="风控条件">
              <Input value={planRiskRule} onChange={setPlanRiskRule} placeholder="例如：市场转弱不追高，只做观察" />
            </Form.Item>
            <Form.Item label="补充备注">
              <TextArea value={planNote} onChange={setPlanNote} rows={4} placeholder="补充仓位、观察名单和失效条件" />
            </Form.Item>
          </Form>
        </div>
      </Popup>

      <Popup
        visible={notePopupOpen}
        onMaskClick={() => setNotePopupOpen(false)}
        bodyStyle={{ borderTopLeftRadius: 24, borderTopRightRadius: 24, padding: 20 }}
      >
        <div className="sheet-panel">
          <div className="sheet-head">
            <h3>{tab === "weekly" ? "编辑周复盘心得" : "编辑月总结心得"}</h3>
            <p>记录市场判断、执行偏差和下周改进方向，仅作为交易辅助。</p>
          </div>
          <Form
            footer={
              <Button block color="primary" loading={savingNote} onClick={saveWeeklyNote}>
                保存心得
              </Button>
            }
          >
            <Form.Item label="复盘心得">
              <TextArea
                value={weeklyNote}
                onChange={setWeeklyNote}
                rows={6}
                placeholder="例如：本周市场修复但分化明显，计划内交易质量高于临盘追价交易。"
              />
            </Form.Item>
          </Form>
        </div>
      </Popup>
    </PageShell>
  );
}
