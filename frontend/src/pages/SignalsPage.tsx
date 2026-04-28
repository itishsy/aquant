import { useEffect, useState } from "react";
import { Button, Dialog, ErrorBlock, SpinLoading } from "antd-mobile";
import { apiGet, apiPost } from "../api/client";
import { PageShell } from "../components/PageShell";

export function SignalsPage() {
  const [items, setItems] = useState<any[]>([]);
  const [error, setError] = useState("");

  const load = () => apiGet<any[]>("/signals").then(setItems).catch((err) => setError(String(err)));

  useEffect(() => {
    load();
  }, []);

  return (
    <PageShell title="信号">
      <div className="toolbar-row">
        <Button
          color="primary"
          onClick={async () => {
            await apiPost("/signals/scan");
            load();
          }}
        >
          扫描信号
        </Button>
      </div>
      {!items.length && !error && <SpinLoading />}
      {error && <ErrorBlock description="信号加载失败" />}
      <div className="stack-list">
        {items.map((item) => (
          <article key={item.id} className="feature-card compact-card">
            <div className="card-head">
              <div className="card-headline">
                <span className="icon-badge">⚡</span>
                <h2>{item.signal_text}</h2>
              </div>
              <span className="score-badge">{item.signal_level}</span>
            </div>
            <p className="card-note">
              {item.stock_name} · {item.stock_code}
            </p>
            <p className="card-note">{item.trigger_reason}</p>
            <p className="card-note">风险提示：{item.risk_desc}</p>
            <div className="action-row wrap-row">
              <Button size="small" onClick={() => apiPost(`/signals/${item.id}/ignore`).then(load)}>
                忽略
              </Button>
              <Button size="small" onClick={() => apiPost(`/signals/${item.id}/false-positive`).then(load)}>
                标记误报
              </Button>
              <Button
                size="small"
                color="primary"
                onClick={async () => {
                  await Dialog.confirm({ content: "确认人工记录该笔交易？" });
                  await apiPost(`/signals/${item.id}/confirm-trade`, {
                    price: item.current_price,
                    quantity: 100,
                    position: 0.2,
                    stop_loss_price: item.stop_loss_price || item.current_price * 0.95,
                    target_price: item.current_price * 1.08,
                    trade_plan: "人工确认后的观察性交易计划",
                  });
                  load();
                }}
              >
                确认交易
              </Button>
            </div>
          </article>
        ))}
      </div>
    </PageShell>
  );
}
