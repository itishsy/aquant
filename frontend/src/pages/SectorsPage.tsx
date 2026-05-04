import { useEffect, useState } from "react";
import { ErrorBlock, SpinLoading } from "antd-mobile";
import { apiGet } from "../api/client";
import { PageShell } from "../components/PageShell";
import { StockLink } from "../components/StockLink";

export function SectorsPage() {
  const [items, setItems] = useState<any[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    const today = new Date().toISOString().slice(0, 10);
    apiGet<any[]>(`/sectors/top?trade_date=${today}`).then(setItems).catch((err) => setError(String(err)));
  }, []);

  return (
    <PageShell title="板块">
      {!items.length && !error && <SpinLoading />}
      {error && <ErrorBlock description="板块数据加载失败" />}
      <div className="stack-list">
        {items.map((item) => (
          <article key={item.id} className="feature-card compact-card">
            <div className="card-head">
              <div className="card-headline">
                <span className="icon-badge">◎</span>
                <h2>{item.sector_name}</h2>
              </div>
              <span className="score-badge">{Math.round(item.sector_score)}</span>
            </div>
            <p className="card-note">类型：{item.sector_type}</p>
            <p className="card-note">涨停数量：{item.limit_up_count}</p>
            <p className="card-note">
              龙头股：<StockLink stockName={item.leader_stock_name} stockCode={item.leader_stock_code} />
            </p>
            <p className="card-note">入榜原因：{item.reason}</p>
            <p className="card-note">风险提示：{item.risk_hint}</p>
          </article>
        ))}
      </div>
    </PageShell>
  );
}
