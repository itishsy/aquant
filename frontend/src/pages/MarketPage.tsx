import { useEffect, useState } from "react";
import { Button, DatePicker, ErrorBlock, SpinLoading } from "antd-mobile";
import { useLocation, useNavigate } from "react-router-dom";
import { apiGet, apiPost } from "../api/client";
import { PageShell } from "../components/PageShell";
import { StockLink } from "../components/StockLink";
import { dateToString, shiftTradeDate, stringToDate, todayString } from "../lib/tradeDates";

type MarketSummary = {
  source: string;
  total_amount: number;
  up_count: number;
  down_count: number;
  flat_count: number;
  limit_up_count: number;
  limit_down_count: number;
  max_continue_board: number;
  sh_index?: number;
  sz_index?: number;
  cyb_index?: number;
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
    apiGet<MarketSummary>(`/h5/market/overview?trade_date=${tradeDate}`)
      .then((summary) => { setData(summary); setError(""); })
      .catch(() => setData(null));

    apiGet<any>(`/market/review?trade_date=${tradeDate}`)
      .then((r) => setReview(r))
      .catch(() => setReview(null));

    apiGet<any>(`/h5/market/hot-stocks?trade_date=${tradeDate}&page_size=50`)
      .then((hot) => setHotStocks(hot.list || hot))
      .catch(() => setHotStocks([]));

    apiGet<any>(`/h5/market/limit-ups?trade_date=${tradeDate}&page_size=50`)
      .then((limitList) => setLimitRows(limitList.list || limitList))
      .catch(() => setLimitRows([]));

    apiGet<any>(`/limit-up/summary?trade_date=${tradeDate}`)
      .then((limit) => setLimitSummary(limit))
      .catch(() => setLimitSummary(null))
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

  const amountText = data ? `${(data.total_amount / 10000).toFixed(2)}万亿` : "-";
  const totalBreadth = data ? Math.max((data.up_count || 0) + (data.down_count || 0) + (data.flat_count || 0), 1) : 1;
  const upRatio = data ? Math.round(((data.up_count || 0) / totalBreadth) * 100) : 0;

  function addWatchFromMarket(item: any, sourceType: string) {
    apiPost("/h5/watch-pool", {
      stock_code: item.stock_code,
      stock_name: item.stock_name,
      sector_name: item.board_name || item.concept,
      labels: sourceType === "limit_up" ? ["接力"] : ["人气"],
      operation_strategies: sourceType === "limit_up" ? ["加速接力"] : ["趋势交易"],
      buy_point_types: ["B15 底背离买点"],
      source_type: sourceType,
      source_platform: item.platform,
      source_rank: item.platform_rank,
      source_score: item.raw_score,
      source_reason: item.raw_reason || item.limit_reason,
      reason: item.raw_reason || item.limit_reason || "市场页手动加入自选",
    }).catch(() => {
      setError("添加自选失败，请稍后重试");
    });
  }

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
                <span className="soft-tag">{data.source || "原始数据"}</span>
              </div>
              <div className="metric-grid">
                <div className="metric-tile">
                  <span>全市场成交额</span>
                  <strong>{amountText}</strong>
                </div>
                <div className="metric-tile">
                  <span>上涨率</span>
                  <strong>{upRatio}%</strong>
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
              <div className="metric-grid">
                <div className="metric-tile">
                  <span>上证指数</span>
                  <strong>{data.sh_index ?? "-"}</strong>
                </div>
                <div className="metric-tile">
                  <span>深成指</span>
                  <strong>{data.sz_index ?? "-"}</strong>
                </div>
                <div className="metric-tile">
                  <span>创业板指</span>
                  <strong>{data.cyb_index ?? "-"}</strong>
                </div>
              </div>
              <p className="card-note">市场页仅展示客观原始数据，不作为交易建议。仅作为交易辅助，请结合个人交易规则确认。</p>
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
                <span className="soft-tag">三平台素数加权</span>
              </div>
              {hotStocks.length ? (
                <div className="stack-list">
                  {hotStocks.slice(0, 10).map((item, idx) => (
                    <div key={item.stock_code} className="row-card">
                      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                        <span style={{ color: "#4b63ee", fontWeight: 800, fontSize: 20, minWidth: 24 }}>
                          {idx + 1}
                        </span>
                        <div>
                          <strong>
                            <StockLink stockName={item.stock_name} stockCode={item.stock_code} />
                          </strong>
                          <p>综合得分：{item.total_score} {item.cross_platform ? "多平台共振" : ""}</p>
                          <p>
                            {(item.platforms || []).map((p: any) => `${p.platform} #${p.rank}(${p.score})`).join("  ")}
                          </p>
                        </div>
                      </div>
                      <Button size="small" color="primary" fill="solid" onClick={() => addWatchFromMarket(item, "hot_stock")}>
                        + 自选
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
                <span className="soft-tag">按封板时间</span>
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
                            <p>{item.limit_reason || "暂无涨停原因"}</p>
                          </div>
                          <Button size="small" color="primary" fill="solid" onClick={() => addWatchFromMarket(item, "limit_up")}>
                            + 自选
                          </Button>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="empty-panel">当前日期暂无涨停明细</div>
                  )}
            </article>
          )}
        </>
      )}
    </PageShell>
  );
}
