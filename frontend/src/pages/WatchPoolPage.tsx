import { useEffect, useMemo, useState } from "react";
import { Button, ErrorBlock, Input, SpinLoading } from "antd-mobile";
import { apiDelete, apiGet, apiPost } from "../api/client";
import { PageShell } from "../components/PageShell";

export function WatchPoolPage() {
  const [tab, setTab] = useState("watch");
  const [items, setItems] = useState<any[]>([]);
  const [signals, setSignals] = useState<any[]>([]);
  const [stockCode, setStockCode] = useState("603019.SH");
  const [error, setError] = useState("");

  const load = async () => {
    try {
      const [watchItems, signalItems] = await Promise.all([apiGet<any[]>("/watch-pool"), apiGet<any[]>("/signals")]);
      setItems(watchItems);
      setSignals(signalItems);
      setError("");
    } catch (err) {
      setError(String(err));
    }
  };

  useEffect(() => {
    load();
  }, []);

  const buySignals = useMemo(() => signals.filter((item) => item.signal_type === "buy"), [signals]);
  const riskSignals = useMemo(() => signals.filter((item) => item.signal_type !== "buy"), [signals]);

  return (
    <PageShell
      title="自选"
      hideHero
      segments={[
        { key: "watch", label: "自选", onClick: () => setTab("watch") },
        { key: "signal", label: "信号", onClick: () => setTab("signal") },
      ]}
      activeSegment={tab}
    >
      {!items.length && !error && <SpinLoading />}
      {error && <ErrorBlock description="自选页加载失败" />}

      {tab === "watch" && (
        <article className="feature-card">
          <div className="card-head">
            <div className="card-headline">
              <span className="icon-badge">★</span>
              <h2>自选</h2>
            </div>
            <span className="soft-tag">观察池</span>
          </div>

          <div className="action-row">
            <Input value={stockCode} onChange={setStockCode} placeholder="输入股票代码" />
            <Button
              color="primary"
              onClick={async () => {
                await apiPost("/watch-pool", {
                  stock_code: stockCode,
                  reason: "手动加入观察池",
                  labels: ["manual"],
                  strategy_type: "manual",
                });
                load();
              }}
            >
              添加
            </Button>
          </div>

          {items.length ? (
            <div className="stack-list">
              {items.map((item) => (
                <div key={item.id} className="row-card row-card-action">
                  <div>
                    <strong>
                      {item.stock_name} {item.stock_code}
                    </strong>
                    <p>入池原因：{item.reason}</p>
                    <p>标签：{(item.labels || []).join(" / ") || "暂无标签"}</p>
                    <p>最新信号：{item.last_signal_type || "暂无信号"}</p>
                  </div>
                  <div className="card-actions">
                    <a
                      className="text-link"
                      href={`https://xueqiu.com/S/${item.stock_code.split(".")[1]}${item.stock_code.split(".")[0]}`}
                      target="_blank"
                    >
                      雪球
                    </a>
                    <Button
                      size="mini"
                      onClick={async () => {
                        await apiDelete(`/watch-pool/${item.stock_code}`);
                        load();
                      }}
                    >
                      删除
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
                <span className="icon-badge">⚡</span>
                <h2>买入观察信号</h2>
              </div>
              <span className="soft-tag">{buySignals.length} 条</span>
            </div>
            {buySignals.length ? (
              <div className="stack-list">
                {buySignals.map((item) => (
                  <div key={item.id} className="row-card">
                    <div>
                      <strong>{item.stock_name}</strong>
                      <p>{item.stock_code}</p>
                      <p>{item.trigger_reason}</p>
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
                <h2>风险 / 卖出信号</h2>
              </div>
              <span className="soft-tag">{riskSignals.length} 条</span>
            </div>
            {riskSignals.length ? (
              <div className="stack-list">
                {riskSignals.map((item) => (
                  <div key={item.id} className="row-card">
                    <div>
                      <strong>{item.stock_name}</strong>
                      <p>{item.stock_code}</p>
                      <p>{item.risk_desc}</p>
                    </div>
                    <span className="score-badge">{item.signal_level}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-panel">暂无风险信号数据</div>
            )}
          </article>
        </div>
      )}
    </PageShell>
  );
}
