import { useEffect, useState } from "react";
import { Button, ErrorBlock, Selector, SpinLoading, TextArea, Toast } from "antd-mobile";
import { useParams } from "react-router-dom";
import { apiGet, apiPatch, apiPost } from "../api/client";
import { PageShell } from "../components/PageShell";

export function TradeReviewDetailPage() {
  const { tradeId } = useParams();
  const [detail, setDetail] = useState<any>(null);
  const [tags, setTags] = useState<any[]>([]);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [note, setNote] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    if (!tradeId) return;
    setLoading(true);
    try {
      const [detailRes, tagRes] = await Promise.all([
        apiGet(`/v1/trades/${tradeId}/review-detail`),
        apiGet<any[]>("/v1/error-tags"),
      ]);
      setDetail(detailRes);
      setTags(tagRes);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  async function generate() {
    const response = await apiPost(`/v1/trades/${tradeId}/review-detail/generate`);
    setDetail(response);
  }

  async function save() {
    await apiPatch(`/v1/trades/${tradeId}/review-detail`, {
      user_answers: { note },
      improvement_action: note,
    });
    await apiPost(`/v1/trades/${tradeId}/review-detail/error-tags`, {
      tag_ids: selectedTags.map(Number),
    });
    Toast.show({ content: "复盘已保存" });
    load();
  }

  useEffect(() => {
    load();
  }, [tradeId]);

  return (
    <PageShell title="单笔复盘">
      {loading && <SpinLoading />}
      {error && <ErrorBlock description="单笔复盘加载失败" />}
      <article className="feature-card">
        <div className="card-head">
          <div className="card-headline">
            <span className="icon-badge">复</span>
            <h2>交易评分</h2>
          </div>
          <Button size="small" color="primary" onClick={generate}>
            生成复盘
          </Button>
        </div>
        {detail ? (
          <>
            <div className="metric-grid">
              <div className="metric-tile">
                <span>买点质量</span>
                <strong>{detail.entry_quality_score}</strong>
              </div>
              <div className="metric-tile">
                <span>卖点质量</span>
                <strong>{detail.exit_quality_score}</strong>
              </div>
              <div className="metric-tile">
                <span>最终盈亏</span>
                <strong>{Math.round((detail.final_pnl_ratio || 0) * 100)}%</strong>
              </div>
              <div className="metric-tile">
                <span>总评分</span>
                <strong>{detail.trade_score}</strong>
              </div>
            </div>
            <p className="card-note">计划执行：{detail.plan_execution_result}。仅作为交易辅助，请结合个人交易计划确认。</p>
          </>
        ) : (
          <div className="empty-panel">完成交易后可生成单笔复盘卡片</div>
        )}
      </article>

      <article className="feature-card compact-card">
        <div className="card-headline">
          <span className="icon-badge">错</span>
          <h2>错误标签与改进</h2>
        </div>
        <Selector
          multiple
          columns={3}
          value={selectedTags}
          onChange={setSelectedTags}
          options={tags.map((tag) => ({ label: tag.tag_name, value: String(tag.tag_id) }))}
        />
        <TextArea value={note} onChange={setNote} rows={5} placeholder="记录本次最大问题和下次改进动作" />
        <Button block color="primary" onClick={save}>
          保存复盘
        </Button>
      </article>
    </PageShell>
  );
}
