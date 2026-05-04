import { useEffect, useState } from "react";
import { Button, DatePicker, ErrorBlock, SpinLoading } from "antd-mobile";
import { useLocation, useNavigate } from "react-router-dom";
import { apiGet } from "../api/client";
import { PageShell } from "../components/PageShell";
import { StockLink } from "../components/StockLink";
import { dateToString, shiftTradeDate, stringToDate, todayString } from "../lib/tradeDates";

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
  const location = useLocation();
  const navigate = useNavigate();
  const searchParams = new URLSearchParams(location.search);
  const queryDate = searchParams.get("trade_date");
  const refreshKey = searchParams.get("refresh");
  const [tradeDate, setTradeDate] = useState<string>(queryDate || todayString());
  const [pickerVisible, setPickerVisible] = useState(false);
  const [tab, setTab] = useState("overview");
  const [data, setData] = useState<MarketSummary | null>(null);
  const [review, setReview] = useState<any>(null);
  const [hotStocks, setHotStocks] = useState<any[]>([]);
  const [limitRows, setLimitRows] = useState<any[]>([]);
  const [limitSummary, setLimitSummary] = useState<any>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      apiGet<MarketSummary>(`/market/daily?trade_date=${tradeDate}`),
      apiGet<any>(`/market/review?trade_date=${tradeDate}`),
      apiGet<any[]>(`/hot-stocks/top?trade_date=${tradeDate}`),
      apiGet<any[]>(`/limit-up/list?trade_date=${tradeDate}`),
      apiGet<any>(`/limit-up/summary?trade_date=${tradeDate}`),
    ])
      .then(([summary, reviewData, hot, limitList, limit]) => {
        setData(summary);
        setReview(reviewData);
        setHotStocks(hot);
        setLimitRows(limitList);
        setLimitSummary(limit);
        setError("");
      })
      .catch((err) => {
        setData(null);
        setError(String(err));
      })
      .finally(() => setLoading(false));
  }, [tradeDate, refreshKey]);

  useEffect(() => {
    const nextDate = new URLSearchParams(location.search).get("trade_date");
    if (nextDate && nextDate !== tradeDate) {
      setTradeDate(nextDate);
    }
  }, [location.search, tradeDate]);

  function changeTradeDate(nextDate: string) {
    setTradeDate(nextDate);
    navigate(`/market?trade_date=${nextDate}`);
  }

  const heatBars = data
    ? [
        { label: "温度", value: data.market_score, color: "var(--accent)" },
        { label: "上涨率", value: Math.round(data.up_ratio * 100), color: "var(--accent-soft)" },
      ]
    : [];

  const amountText = data ? `${(data.total_amount / 10000).toFixed(2)}万亿` : "-";

  return (
    <PageShell
      title="市场"
      dateText={tradeDate}
      onDateClick={() => setPickerVisible(true)}
      onPrevDate={() => changeTradeDate(shiftTradeDate(tradeDate, -1))}
      onNextDate={() => changeTradeDate(shiftTradeDate(tradeDate, 1))}
      segments={[
        { key: "overview", label: "大盘", onClick: () => setTab("overview") },
        { key: "hot", label: "热榜", onClick: () => setTab("hot") },
        { key: "limit", label: "涨停榜", onClick: () => setTab("limit") },
      ]}
      activeSegment={tab}
    >
      <DatePicker
        title="选择日期"
        visible={pickerVisible}
        precision="day"
        value={stringToDate(tradeDate)}
        max={new Date()}
        onClose={() => setPickerVisible(false)}
        onConfirm={(value) => changeTradeDate(dateToString(value))}
      />

      {loading && <SpinLoading />}
      {error && <ErrorBlock description="市场数据加载失败，请稍后重试" />}
      {data && (
        <>
          {tab === "overview" && (
            <article className="feature-card">
              <div className="card-head">
                <div className="card-headline">
                  <span className="icon-badge">市</span>
                  <h2>大盘</h2>
                </div>
                <span className="soft-tag">{data.market_status}</span>
              </div>
              <div className="metric-grid">
                <div className="metric-tile">
                  <span>全市场成交额</span>
                  <strong>{amountText}</strong>
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
              {review ? (
                <div className="review-note-panel">
                  <strong>复盘信息</strong>
                  <p>{review.review_text || "暂无复盘摘要"}</p>
                  {review.topic?.length ? (
                    <>
                      <strong>热门话题</strong>
                      <p>{review.topic.slice(0, 3).map((item: any) => item.title).join(" / ")}</p>
                    </>
                  ) : null}
                  {review.subject?.length ? (
                    <>
                      <strong>热门板块</strong>
                      <p>{review.subject.slice(0, 3).map((item: any) => item.name).join(" / ")}</p>
                    </>
                  ) : null}
                </div>
              ) : null}
            </article>
          )}

          {tab === "hot" && (
            <article className="feature-card">
              <div className="card-head">
                <div className="card-headline">
                  <span className="icon-badge">热</span>
                  <h2>热榜</h2>
                </div>
                <span className="soft-tag">{tradeDate}</span>
              </div>
              {hotStocks.length ? (
                <div className="stack-list">
                  {hotStocks.slice(0, 10).map((item) => (
                    <div key={item.stock_code} className="row-card">
                      <div>
                        <strong>
                          <StockLink stockName={item.stock_name} stockCode={item.stock_code} />
                        </strong>
                        <p>得分：{item.total_score}</p>
                        <p>
                          {item.sector_name}
                        </p>
                        <p>
                          平台：{Object.entries(item.platform_ranks || {})
                            .map(([platform, rank]) => `${platform}#${rank}`)
                            .join(" / ")}
                        </p>
                      </div>
                      <Button size="small" color="primary" fill="solid" onClick={() => {}}>
                        加自选
                      </Button>
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
                  <span className="icon-badge">停</span>
                  <h2>涨停榜</h2>
                </div>
                <span className="soft-tag">统计</span>
              </div>
              {limitSummary ? (
                <>
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
                  </div>
                  {limitRows.length ? (
                    <div className="stack-list">
                      {limitRows.slice(0, 20).map((item) => (
                        <div key={item.stock_code} className="row-card row-card-action">
                          <div>
                            <strong>
                              <StockLink stockName={item.stock_name} stockCode={item.stock_code} />
                            </strong>
                            <p>
                              {item.concept || "未分类"} / {item.limit_type}
                            </p>
                            <p>
                              封板：{item.limit_time} / 连板：{item.board_count} / 换手：{item.turnover_rate}%
                            </p>
                            <p>{item.reason || "暂无涨停原因"}</p>
                          </div>
                          <span className="score-badge">{item.board_count}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="empty-panel">当前日期暂无涨停明细</div>
                  )}
                </>
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
