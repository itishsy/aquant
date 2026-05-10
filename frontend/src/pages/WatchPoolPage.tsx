import { useEffect, useMemo, useState } from "react";
import { Button, Dialog, ErrorBlock, SpinLoading, Toast } from "antd-mobile";
import { apiDelete, apiGet, apiPut } from "../api/client";
import { PageShell } from "../components/PageShell";
import { StockLink } from "../components/StockLink";

export function WatchPoolPage() {
  const [tab, setTab] = useState("trade");
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
  const watchingItems = useMemo(() => items.filter((item) => item.pool_status === "watching" || item.pool_status === "观察中"), [items]);
  const holdingItems = useMemo(() => items.filter((item) => item.pool_status === "holding" || item.pool_status === "持仓中"), [items]);
  const completedItems = useMemo(() => items.filter((item) => item.pool_status === "completed" || item.pool_status === "已完成"), [items]);
  const todayStr = new Date().toISOString().slice(0, 10);
  const todayNew = useMemo(() => watchingItems.filter((item) => String(item.created_at || "").slice(0, 10) === todayStr).length, [watchingItems, todayStr]);
  const todaySignals = useMemo(() => signals.filter((s) => (s.trigger_date || "").slice(0, 10) === todayStr).length, [signals, todayStr]);
  const totalPnl = useMemo(
    () => trades.reduce((sum, t) => sum + (Number(t.pnl_amount) || 0), 0),
    [trades]
  );

  return (
    <PageShell
      title="自选"
      hideHero
      segments={[
        { key: "trade", label: "交易", onClick: () => setTab("trade") },
        { key: "signal", label: "信号", onClick: () => setTab("signal") },
        { key: "watch", label: "观察", onClick: () => setTab("watch") },
      ]}
      activeSegment={tab}
    >
      {loading && <SpinLoading />}
      {error && <ErrorBlock description="自选页加载失败" />}

      {tab === "watch" && (
        <article className="feature-card">
          <div className="card-head">
            <div className="card-headline">
              <span className="icon-badge">{todayNew}</span>
              <h2>观察</h2>
            </div>
            <span className="soft-tag">今日新增 {todayNew} / 总数 {watchingItems.length}</span>
          </div>

          {watchingItems.length ? (
            <div className="stack-list">
              {watchingItems.map((item) => (
                <div key={item.watch_id} className="row-card row-card-action">
                  <div>
                    <strong>
                      <StockLink stockName={item.stock_name} stockCode={item.stock_code} info={item} />
                    </strong>
                    <p>状态：{item.pool_status}</p>
                    <p>来源：{item.source_platform || "手动"} {item.source_rank ? `#${item.source_rank}` : ""}</p>
                    <p>原因：{item.source_reason || item.reason || "用户手动关注"}</p>
                    <p>标签：{(item.labels || []).join(" / ") || "暂无标签"}</p>
                  </div>
                  <Button
                    size="mini"
                    fill="outline"
                    style={{ fontSize: 12, color: "#999", borderColor: "#ccc" }}
                    onClick={async () => {
                      const confirmed = await Dialog.confirm({
                        content: `确认剔除 ${item.stock_name}？`,
                        confirmText: "确认剔除",
                        cancelText: "取消",
                      });
                      if (confirmed) {
                        await apiDelete(`/h5/watch-pool/${item.watch_id}`);
                        load();
                      }
                    }}
                  >
                    剔除
                  </Button>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-panel">暂无自选数据</div>
          )}
        </article>
      )}

      {tab === "signal" && (
        <article className="feature-card">
          <div className="card-head">
            <div className="card-headline">
              <span className="icon-badge">{todaySignals}</span>
              <h2>信号</h2>
            </div>
            <span className="soft-tag">今日 {todaySignals} / 总数 {signalSummary.total ?? signals.length}</span>
          </div>
          <div className="stack-list">
            {buySignals.map((item) => (
              <div key={item.signal_id} className="row-card">
                <div>
                  <strong><StockLink stockName={item.stock_name} stockCode={item.stock_code} info={item} /></strong>
                  <p>{item.trigger_reason}</p>
                </div>
                <span className="score-badge">{item.signal_level}</span>
              </div>
            ))}
            {riskSignals.map((item) => (
              <div key={item.signal_id} className="row-card">
                <div>
                  <strong><StockLink stockName={item.stock_name} stockCode={item.stock_code} info={item} /></strong>
                  <p>{item.risk_desc || item.trigger_reason}</p>
                </div>
                <span className="score-badge">{item.signal_level}</span>
              </div>
            ))}
            {!buySignals.length && !riskSignals.length && (
              <div className="empty-panel">暂无信号</div>
            )}
          </div>
        </article>
      )}

      {tab === "trade" && (
        <article className="feature-card">
          <div className="card-head">
            <div className="card-headline">
              <span className="icon-badge">{holdingItems.length}</span>
              <h2>交易</h2>
            </div>
            <span className="soft-tag">持仓中 {holdingItems.length} / 总数 {holdingItems.length + completedItems.length}</span>
          </div>
          {holdingItems.length ? (
            <div className="stack-list">
              {holdingItems.map((item) => (
                <div key={item.watch_id} className="row-card">
                  <div>
                    <strong>
                      <StockLink stockName={item.stock_name} stockCode={item.stock_code} info={item} />
                    </strong>
                    <p>标签：{(item.labels || []).join(" / ") || "-"}</p>
                    <p>策略：{(item.operation_strategies || []).join(",")}</p>
                    {item.reason && <p>理由：{item.reason}</p>}
                  </div>
                  <Button size="mini" color="danger" fill="outline"
                    onClick={async () => {
                      const confirmed = await Dialog.confirm({ content: `确认 ${item.stock_name} 卖出清仓？`, confirmText: "确认", cancelText: "取消" });
                      if (!confirmed) return;
                      await apiPut(`/h5/watch-pool/${item.watch_id}`, { pool_status: "completed" });
                      Toast.show({ content: "已标记完成" });
                      load();
                    }}>卖出</Button>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-panel">暂无持仓</div>
          )}
        </article>
      )}
    </PageShell>
  );
}
