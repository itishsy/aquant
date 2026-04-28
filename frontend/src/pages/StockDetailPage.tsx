import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { ErrorBlock, SpinLoading } from "antd-mobile";
import { apiGet } from "../api/client";
import { LineChart } from "../components/LineChart";
import { MiniBars } from "../components/MiniBars";
import { PageShell } from "../components/PageShell";

export function StockDetailPage() {
  const { stockCode = "603019.SH" } = useParams();
  const [daily, setDaily] = useState<any>(null);
  const [intraday, setIntraday] = useState<any>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([apiGet(`/stocks/${stockCode}/kline/daily`), apiGet(`/stocks/${stockCode}/kline/15m`)])
      .then(([dailyData, intradayData]) => {
        setDaily(dailyData);
        setIntraday(intradayData);
        setError("");
      })
      .catch((err) => setError(String(err)));
  }, [stockCode]);

  const dailyCloses = useMemo(() => daily?.items?.map((item: any) => item.close) || [], [daily]);
  const intradayCloses = useMemo(() => intraday?.items?.map((item: any) => item.close) || [], [intraday]);
  const intradayHist = useMemo(() => intraday?.macd?.hist?.map((item: number) => Math.abs(item)) || [], [intraday]);

  return (
    <PageShell title={`个股详情 ${stockCode}`}>
      {error && <ErrorBlock description="个股详情加载失败" />}
      {!daily && !error && <SpinLoading />}

      {daily && (
        <article className="feature-card compact-card">
          <div className="card-head">
            <div className="card-headline">
              <span className="icon-badge">▥</span>
              <h2>日 K 与趋势</h2>
            </div>
            <span className="soft-tag">日线</span>
          </div>
          <LineChart values={dailyCloses.slice(-30)} />
          <div className="metric-grid">
            <div className="metric-tile">
              <span>日线数量</span>
              <strong>{daily.items.length}</strong>
            </div>
            <div className="metric-tile">
              <span>MA20 最新值</span>
              <strong>{daily.ma20[daily.ma20.length - 1] ?? "-"}</strong>
            </div>
          </div>
          <a href={daily.xueqiu_link} target="_blank">
            跳转雪球
          </a>
        </article>
      )}

      {intraday && (
        <article className="feature-card compact-card">
          <div className="card-head">
            <div className="card-headline">
              <span className="icon-badge">≈</span>
              <h2>15 分钟 MACD</h2>
            </div>
            <span className="soft-tag">盘中</span>
          </div>
          <LineChart values={intradayCloses} stroke="#5d74ff" fill={false} />
          <MiniBars values={intradayHist.slice(-10)} />
          <div className="metric-grid">
            <div className="metric-tile">
              <span>15 分钟 K 数量</span>
              <strong>{intraday.items.length}</strong>
            </div>
            <div className="metric-tile">
              <span>最新 DIF / DEA</span>
              <strong>
                {intraday.macd.dif[intraday.macd.dif.length - 1]} / {intraday.macd.dea[intraday.macd.dea.length - 1]}
              </strong>
            </div>
          </div>
        </article>
      )}
    </PageShell>
  );
}
