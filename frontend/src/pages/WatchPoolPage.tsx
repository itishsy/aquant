import { useEffect, useMemo, useState } from "react";
import { Button, ErrorBlock, SpinLoading } from "antd-mobile";
import { apiDelete, apiGet } from "../api/client";
import { PageShell } from "../components/PageShell";
import { StockLink } from "../components/StockLink";

export function WatchPoolPage() {
  const [tab, setTab] = useState("watch");
  const [items, setItems] = useState<any[]>([]);
  const [signals, setSignals] = useState<any[]>([]);
  const [trades, setTrades] = useState<any[]>([]);
  const [watchSummary, setWatchSummary] = useState<any>({});
  const [signalSummary, setSignalSummary] = useState<any>({});
  const [tradeSummary, setTradeSummary] = useState<any>({});
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    try {
      const [watchItems, signalItems, tradeItems, watchSum, signalSum, tradeSum] = await Promise.all([
        apiGet<any[]>("/h5/watch-pool"),
        apiGet<any[]>("/h5/watch-signals/recent"),
        apiGet<any[]>("/h5/watch-trades/recent"),
        apiGet<any>("/h5/watch-pool/summary"),
        apiGet<any>("/h5/watch-signals/summary"),
        apiGet<any>("/h5/watch-trades/summary"),
      ]);
      setItems(watchItems);
      setSignals(signalItems);
      setTrades(tradeItems);
      setWatchSummary(watchSum);
      setSignalSummary(signalSum);
      setTradeSummary(tradeSum);
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

  const buySignals = useMemo(() => signals.filter((item) => item.signal_type === "buy"), [signals]);
  const riskSignals = useMemo(() => signals.filter((item) => item.signal_type !== "buy"), [signals]);
  const monitoringCount = items.filter((item) => item.monitor_enabled).length;
  const pendingSignals = signals.filter(
    (s) => s.signal_status === "pending" || s.signal_status === "未处理"
  ).length;
  const totalPnl = useMemo(
    () => trades.reduce((sum, t) => sum + (Number(t.pnl_amount) || 0), 0),
    [trades]
  );

  return (
    <PageShell
      title="自选"
      hideHero
      segments={[
        { key: "watch", label: "观察", onClick: () => setTab("watch") },
        { key: "signal", label: "信号", onClick: () => setTab("signal") },
        { key: "trade", label: "交易", onClick: () => setTab("trade") },
      ]}
      activeSegment={tab}
    >
      {loading && <SpinLoading />}
      {error && <ErrorBlock description="自选页加载失败" />}

      {tab === "watch" && (
        <article className="feature-card">
          <div className="card-head">
            <div className="card-headline">
              <span className="icon-badge">*</span>
              <h2>观察池</h2>
            </div>
            <span className="soft-tag">监控中 {monitoringCount}</span>
          </div>

          <section className="summary-board">
            <article className="summary-card">
              <span>总入选</span>
              <strong>{items.length}</strong>
              <p>全部由用户手动加入</p>
            </article>
            <article className="summary-card">
              <span>观察中</span>
              <strong>{watchSummary.watching ?? "-"}</strong>
              <p>状态：watching</p>
            </article>
            <article className="summary-card">
              <span>已触发</span>
              <strong>{watchSummary.triggered ?? "-"}</strong>
              <p>触发买入信号</p>
            </article>
            <article className="summary-card">
              <span>已剔除</span>
              <strong>{watchSummary.removed ?? "-"}</strong>
              <p>不再关注</p>
            </article>
          </section>

          {items.length ? (
            <div className="stack-list">
              {items.map((item) => (
                <div key={item.watch_id} className="row-card row-card-action">
                  <div>
                    <strong>
                      <StockLink stockName={item.stock_name} stockCode={item.stock_code} />
                    </strong>
                    <p>状态：{item.pool_status}</p>
                    <p>来源：{item.source_platform || "手动"} {item.source_rank ? `#${item.source_rank}` : ""}</p>
                    <p>原因：{item.source_reason || item.reason || "用户手动关注"}</p>
                    <p>标签：{(item.labels || []).join(" / ") || "暂无标签"}</p>
                  </div>
                  <div className="card-actions">
                    <StockLink className="text-link" stockName="雪球" stockCode={item.stock_code} showCode={false} />
                    <Button
                      size="mini"
                      onClick={async () => {
                        await apiDelete(`/h5/watch-pool/${item.watch_id}`);
                        load();
                      }}
                    >
                      剔除
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-panel">暂无自选数据</div>
          )}
        </article>
      )}

      {tab === "signal" && (
        <>
          <article className="feature-card compact-card">
            <div className="card-head">
              <div className="card-headline">
                <span className="icon-badge">S</span>
                <h2>信号汇总</h2>
              </div>
            </div>
            <section className="summary-board">
              <article className="summary-card">
                <span>总信号</span>
                <strong>{signalSummary.total ?? signals.length}</strong>
                <p>全部信号统计</p>
              </article>
              <article className="summary-card">
                <span>买入信号</span>
                <strong>{signalSummary.buy ?? buySignals.length}</strong>
                <p>需人工确认</p>
              </article>
              <article className="summary-card">
                <span>风险/卖出</span>
                <strong>{signalSummary.sell_or_risk ?? riskSignals.length}</strong>
                <p>风险提醒</p>
              </article>
              <article className="summary-card">
                <span>待处理</span>
                <strong>{pendingSignals}</strong>
                <p>状态：pending</p>
              </article>
            </section>
            <p className="card-note">{signalSummary.assistant_note || "仅作为交易辅助，请结合个人交易规则确认。"}</p>
          </article>

          <article className="feature-card compact-card">
            <div className="card-head">
              <div className="card-headline">
                <span className="icon-badge">B</span>
                <h2>买入观察信号</h2>
              </div>
              <span className="soft-tag">{buySignals.length} 条</span>
            </div>
            {buySignals.length ? (
              <div className="stack-list">
                {buySignals.map((item) => (
                  <div key={item.signal_id} className="row-card">
                    <div>
                      <strong>
                        <StockLink stockName={item.stock_name} stockCode={item.stock_code} />
                      </strong>
                      <p>{item.trigger_reason}</p>
                      <p>{item.assistant_note}</p>
                    </div>
                    <span className="score-badge">{item.signal_level}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-panel">暂无买入观察信号</div>
            )}
          </article>

          <article className="feature-card compact-card">
            <div className="card-head">
              <div className="card-headline">
                <span className="icon-badge">!</span>
                <h2>风险 / 卖出提醒</h2>
              </div>
              <span className="soft-tag">{riskSignals.length} 条</span>
            </div>
            {riskSignals.length ? (
              <div className="stack-list">
                {riskSignals.map((item) => (
                  <div key={item.signal_id} className="row-card">
                    <div>
                      <strong>
                        <StockLink stockName={item.stock_name} stockCode={item.stock_code} />
                      </strong>
                      <p>{item.risk_desc || item.trigger_reason}</p>
                      <p>{item.assistant_note}</p>
                    </div>
                    <span className="score-badge">{item.signal_level}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-panel">暂无风险提醒</div>
            )}
          </article>
        </>
      )}

      {tab === "trade" && (
        <>
          <article className="feature-card compact-card">
            <div className="card-head">
              <div className="card-headline">
                <span className="icon-badge">$</span>
                <h2>交易汇总</h2>
              </div>
            </div>
            <section className="summary-board">
              <article className="summary-card">
                <span>总交易</span>
                <strong>{tradeSummary.total ?? trades.length}</strong>
                <p>全部交易记录</p>
              </article>
              <article className="summary-card">
                <span>持仓中</span>
                <strong>{tradeSummary.open ?? trades.filter((t) => t.trade_status === "open" || t.trade_status === "holding").length}</strong>
                <p>状态：open / holding</p>
              </article>
              <article className="summary-card">
                <span>已完成</span>
                <strong>{tradeSummary.completed ?? trades.filter((t) => t.trade_status === "completed").length}</strong>
                <p>状态：completed</p>
              </article>
              <article className="summary-card">
                <span>总盈亏</span>
                <strong style={{ color: totalPnl >= 0 ? "#e34d59" : "#00b578" }}>
                  {totalPnl >= 0 ? "+" : ""}{totalPnl.toFixed(2)}
                </strong>
                <p>盈亏合计</p>
              </article>
            </section>
            <p className="card-note">仅作为交易辅助，请结合个人交易规则确认。</p>
          </article>

          <article className="feature-card compact-card">
            <div className="card-head">
              <div className="card-headline">
                <span className="icon-badge">记</span>
                <h2>交易记录</h2>
              </div>
              <span className="soft-tag">{trades.length} 条</span>
            </div>
            {trades.length ? (
              <div className="stack-list">
                {trades.map((item) => (
                  <div key={item.trade_id} className="row-card">
                    <div>
                      <strong>
                        <StockLink stockName={item.stock_name} stockCode={item.stock_code} />
                      </strong>
                      <p>状态：{item.trade_status}</p>
                      <p>剩余：{item.remaining_amount}，盈亏：{item.pnl_amount}</p>
                      <p>{item.assistant_note}</p>
                    </div>
                    <span className="soft-tag">人工确认</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-panel">暂无交易记录</div>
            )}
          </article>
        </>
      )}
    </PageShell>
  );
}
