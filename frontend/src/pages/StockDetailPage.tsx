import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { ErrorBlock, SpinLoading } from "antd-mobile";
import { apiGet } from "../api/client";
import { PageShell } from "../components/PageShell";
import { StockLink } from "../components/StockLink";

type StockBrief = {
  stock_code: string;
  stock_name: string;
  sector_name?: string;
  xueqiu_url: string;
};

export function StockDetailPage() {
  const { stockCode = "603019.SH" } = useParams();
  const [brief, setBrief] = useState<StockBrief | null>(null);
  const [latestSource, setLatestSource] = useState<any>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([
      apiGet<StockBrief>(`/common/stocks/${stockCode}/brief`),
      apiGet(`/h5/market/stocks/${stockCode}/latest-source`),
    ])
      .then(([briefData, sourceData]) => {
        setBrief(briefData);
        setLatestSource(sourceData);
        setError("");
      })
      .catch((err) => setError(String(err)));
  }, [stockCode]);

  return (
    <PageShell title={`个股详情 ${stockCode}`}>
      {error && <ErrorBlock description="个股详情加载失败" />}
      {!brief && !error && <SpinLoading />}

      {brief && (
        <article className="feature-card compact-card">
          <div className="card-head">
            <div className="card-headline">
              <span className="icon-badge">股</span>
              <h2>
                <StockLink stockName={brief.stock_name} stockCode={brief.stock_code} />
              </h2>
            </div>
            <span className="soft-tag">雪球查看 K 线</span>
          </div>
          <div className="metric-grid">
            <div className="metric-tile">
              <span>股票代码</span>
              <strong>{brief.stock_code}</strong>
            </div>
            <div className="metric-tile">
              <span>所属板块</span>
              <strong>{brief.sector_name || "-"}</strong>
            </div>
          </div>
          <p className="card-note">
            系统内 K 线仅用于后台计算、信号触发和复盘统计。查看图形走势请通过雪球链接打开。
          </p>
        </article>
      )}

      {latestSource && (
        <article className="feature-card compact-card">
          <div className="card-head">
            <div className="card-headline">
              <span className="icon-badge">源</span>
              <h2>来源摘要</h2>
            </div>
            <span className="soft-tag">原始数据</span>
          </div>
          <p>最近人气来源：{latestSource.latest_hot?.platform || "暂无"}</p>
          <p>最近涨停来源：{latestSource.latest_limit?.platform || "暂无"}</p>
          <p className="card-note">仅作为交易辅助，请结合个人交易规则确认。</p>
        </article>
      )}
    </PageShell>
  );
}
