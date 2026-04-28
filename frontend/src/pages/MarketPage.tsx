import { useEffect, useState } from "react";
import { ErrorBlock, SpinLoading } from "antd-mobile";
import { apiGet } from "../api/client";
import { PageShell } from "../components/PageShell";
import { TRADE_DATES, shiftTradeDate } from "../lib/tradeDates";

type MarketSummary = {
  market_score: number;
  market_status: string;
  market_comment: string;
  total_amount: number;
  up_ratio: number;
  limit_up_count: number;
  limit_down_count: number;
  max_continue_board: number;
};

export function MarketPage() {
  const [tradeDate, setTradeDate] = useState<string>(TRADE_DATES[TRADE_DATES.length - 1]);
  const [tab, setTab] = useState("overview");
  const [data, setData] = useState<MarketSummary | null>(null);
  const [hotStocks, setHotStocks] = useState<any[]>([]);
  const [limitSummary, setLimitSummary] = useState<any>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([
      apiGet<MarketSummary>(`/market/daily?trade_date=${tradeDate}`),
      apiGet<any[]>(`/hot-stocks/top?trade_date=${tradeDate}`),
      apiGet<any>(`/limit-up/summary?trade_date=${tradeDate}`),
    ])
      .then(([summary, hot, limit]) => {
        setData(summary);
        setHotStocks(hot);
        setLimitSummary(limit);
        setError("");
      })
      .catch((err) => setError(String(err)));
  }, [tradeDate]);

  const heatBars = data
    ? [
        { label: "温度", value: data.market_score, color: "var(--accent)" },
        { label: "上涨率", value: Math.round(data.up_ratio * 100), color: "var(--accent-soft)" },
        { label: "涨停", value: Math.min(data.limit_up_count, 100), color: "var(--accent-calm)" },
        { label: "连板", value: Math.min(data.max_continue_board * 20, 100), color: "var(--accent-deep)" },
      ]
    : [];

  return (
    <PageShell
      title="市场"
      dateText={tradeDate}
      onPrevDate={() => setTradeDate((current) => shiftTradeDate(current, -1))}
      onNextDate={() => setTradeDate((current) => shiftTradeDate(current, 1))}
      segments={[
        { key: "overview", label: "大盘", onClick: () => setTab("overview") },
        { key: "hot", label: "热榜", onClick: () => setTab("hot") },
        { key: "limit", label: "涨停榜", onClick: () => setTab("limit") },
      ]}
      activeSegment={tab}
    >
      {!data && !error && <SpinLoading />}
      {error && <ErrorBlock description="市场数据加载失败，请稍后重试" />}
      {data && (
        <>
          {tab === "overview" && (
            <article className="feature-card">
              <div className="card-head">
                <div className="card-headline">
                  <span className="icon-badge">▣</span>
                  <h2>大盘</h2>
                </div>
                <span className="soft-tag">{data.market_status}</span>
              </div>
              <div className="metric-grid">
                <div className="metric-tile metric-hero">
                  <span>市场温度</span>
                  <strong>{data.market_score}</strong>
                  <em>{data.market_status}</em>
                </div>
                <div className="metric-tile">
                  <span>全市场成交额</span>
                  <strong>{data.total_amount}</strong>
                </div>
                <div className="metric-tile">
                  <span>上涨率</span>
                  <strong>{Math.round(data.up_ratio * 100)}%</strong>
                </div>
                <div className="metric-tile">
                  <span>涨停 / 跌停</span>
                  <strong>
                    {data.limit_up_count} / {data.limit_down_count}
                  </strong>
                </div>
                <div className="metric-tile">
                  <span>最高连板</span>
                  <strong>{data.max_continue_board}</strong>
                </div>
              </div>
              <div className="trend-panel">
                {heatBars.map((bar) => (
                  <div key={bar.label} className="trend-row">
                    <span>{bar.label}</span>
                    <div className="trend-track">
                      <div className="trend-fill" style={{ width: `${bar.value}%`, background: bar.color }} />
                    </div>
                    <strong>{bar.value}</strong>
                  </div>
                ))}
              </div>
              <p className="card-note">{data.market_comment}</p>
            </article>
          )}

          {tab === "hot" && (
            <article className="feature-card">
              <div className="card-head">
                <div className="card-headline">
                  <span className="icon-badge">◉</span>
                  <h2>热榜</h2>
                </div>
                <span className="soft-tag">{tradeDate}</span>
              </div>
              {hotStocks.length ? (
                <div className="stack-list">
                  {hotStocks.slice(0, 10).map((item, index) => (
                    <div key={item.stock_code} className="row-card">
                      <div>
                        <strong>
                          {index + 1}. {item.stock_name}
                        </strong>
                        <p>
                          {item.stock_code} · {item.sector_name}
                        </p>
                      </div>
                      <span className="score-badge">{item.total_score}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="empty-panel">当前日期暂无热榜数据</div>
              )}
            </article>
          )}

          {tab === "limit" && (
            <article className="feature-card">
              <div className="card-head">
                <div className="card-headline">
                  <span className="icon-badge">▲</span>
                  <h2>涨停榜</h2>
                </div>
                <span className="soft-tag">统计</span>
              </div>
              {limitSummary ? (
                <div className="metric-grid">
                  <div className="metric-tile">
                    <span>涨停家数</span>
                    <strong>{limitSummary.count}</strong>
                  </div>
                  <div className="metric-tile">
                    <span>最高连板</span>
                    <strong>{limitSummary.max_continue_board}</strong>
                  </div>
                  <div className="metric-tile">
                    <span>首板数量</span>
                    <strong>{limitSummary.first_board_count}</strong>
                  </div>
                  <div className="metric-tile">
                    <span>连板数量</span>
                    <strong>{limitSummary.continue_board_count}</strong>
                  </div>
                  <div className="metric-tile">
                    <span>炸板率</span>
                    <strong>{Math.round(limitSummary.broken_limit_rate * 100)}%</strong>
                  </div>
                </div>
              ) : (
                <div className="empty-panel">当前日期暂无涨停数据</div>
              )}
            </article>
          )}
        </>
      )}
    </PageShell>
  );
}
