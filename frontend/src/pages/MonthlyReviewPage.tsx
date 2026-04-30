import { useEffect, useState } from "react";
import { Button, ErrorBlock, SpinLoading } from "antd-mobile";
import { apiGet, apiPost } from "../api/client";
import { PageShell } from "../components/PageShell";

function currentMonth() {
  return new Date().toISOString().slice(0, 7);
}

export function MonthlyReviewPage() {
  const [month, setMonth] = useState(currentMonth());
  const [review, setReview] = useState<any>(null);
  const [score, setScore] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      const [reviewRes, scoreRes] = await Promise.all([
        apiGet(`/v1/reviews/monthly?month=${month}`),
        apiGet(`/v1/trading-score/monthly?month=${month}`),
      ]);
      setReview(reviewRes);
      setScore(scoreRes);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  async function generate() {
    setLoading(true);
    try {
      const response = await apiPost("/v1/reviews/monthly/generate", { month });
      setReview(response);
      await load();
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <PageShell title="月度总结" dateText={month}>
      {loading && <SpinLoading />}
      {error && <ErrorBlock description="月度总结加载失败" />}
      <article className="feature-card">
        <div className="card-head">
          <div className="card-headline">
            <span className="icon-badge">月</span>
            <h2>交易能力评分</h2>
          </div>
          <Button size="small" color="primary" onClick={generate}>
            生成总结
          </Button>
        </div>
        {review ? (
          <>
            <section className="summary-board">
              <article className="summary-card">
                <span>月度盈亏</span>
                <strong>{review.monthly_pnl}</strong>
                <p>已记录交易汇总</p>
              </article>
              <article className="summary-card">
                <span>交易次数</span>
                <strong>{review.total_trades}</strong>
                <p>本月总交易数</p>
              </article>
              <article className="summary-card">
                <span>胜率</span>
                <strong>{Math.round((review.win_rate || 0) * 100)}%</strong>
                <p>完成交易胜率</p>
              </article>
              <article className="summary-card">
                <span>纪律评分</span>
                <strong>{review.discipline_score}</strong>
                <p>仅作为交易辅助</p>
              </article>
            </section>
            <div className="review-note-panel">
              <strong>能力评分</strong>
              <p>总分：{score?.total_score ?? review.ability_score?.total_score ?? "-"}</p>
              <p>下月目标：{review.next_month_goals?.goal || "减少计划外交易，强化复盘完成率。"}</p>
            </div>
          </>
        ) : (
          <div className="empty-panel">暂无月度总结，可点击生成</div>
        )}
      </article>
    </PageShell>
  );
}
