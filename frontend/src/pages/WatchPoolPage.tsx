import { useEffect, useMemo, useState } from "react";
import { Button, ErrorBlock, Input, SpinLoading, Toast } from "antd-mobile";
import { apiDelete, apiGet, apiPost } from "../api/client";
import { PageShell } from "../components/PageShell";
import { StockLink } from "../components/StockLink";

export function WatchPoolPage() {
  const [tab, setTab] = useState("watch");
  const [items, setItems] = useState<any[]>([]);
  const [signals, setSignals] = useState<any[]>([]);
  const [trades, setTrades] = useState<any[]>([]);
  const [stockCode, setStockCode] = useState("603019.SH");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    try {
      const [watchItems, signalItems, tradeItems] = await Promise.all([
        apiGet<any[]>("/h5/watch-pool"),
        apiGet<any[]>("/h5/watch-signals/recent"),
        apiGet<any[]>("/h5/watch-trades/recent"),
      ]);
      setItems(watchItems);
      setSignals(signalItems);
      setTrades(tradeItems);
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
              <span>今日入选</span>
              <strong>{items.filter((item) => String(item.created_at || "").slice(0, 10) === new Date().toISOString().slice(0, 10)).length}</strong>
              <p>市场页只提供添加入口</p>
            </article>
          </section>

          <div className="action-row">
            <Input value={stockCode} onChange={setStockCode} placeholder="输入股票代码" />
            <Button
              color="primary"
              onClick={async () => {
                await apiPost("/h5/watch-pool", {
                  stock_code: stockCode,
                  reason: "用户手动加入观察池",
                  labels: ["手动"],
                  operation_strategies: ["趋势交易"],
                  buy_point_types: ["B15 底背离买点"],
                });
                Toast.show({ content: "已添加自选，仅作为交易辅助" });
                load();
              }}
            >
              添加
            </Button>
          </div>

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
        <div className="stack-list">
          <article className="feature-card compact-card">
            <div className="card-head">
              <div className="card-headline">
                <span className="icon-badge">S</span>
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
        </div>
      )}

      {tab === "trade" && (
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
      )}
    </PageShell>
  );
}
