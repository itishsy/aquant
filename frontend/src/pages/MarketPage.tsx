import { useEffect, useMemo, useState } from "react";
import { Button, DatePicker, Dialog, ErrorBlock, Picker, SpinLoading, Toast } from "antd-mobile";
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
  market_comment?: string;
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
  const [limitTotal, setLimitTotal] = useState(0);
  const [limitSummary, setLimitSummary] = useState<any>(null);
  const [limitConcept, setLimitConcept] = useState("");
  const [conceptPickerVisible, setConceptPickerVisible] = useState(false);
  const [hotPlatform, setHotPlatform] = useState("");
  const [hotPlatformPickerVisible, setHotPlatformPickerVisible] = useState(false);
  const [watchCodes, setWatchCodes] = useState<Set<string>>(new Set());
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    apiGet<any[]>("/h5/watch-pool").then((items) => {
      setWatchCodes(new Set((items || []).map((w: any) => w.stock_code)));
    }).catch(() => {});

    apiGet<MarketSummary>(`/h5/market/overview?trade_date=${tradeDate}`)
      .then((summary) => { setData(summary); setError(""); })
      .catch(() => setData(null));

    apiGet<any>(`/market/review?trade_date=${tradeDate}`)
      .then((r) => setReview(r))
      .catch(() => setReview(null));

    apiGet<any>(`/h5/market/hot-stocks?trade_date=${tradeDate}&page_size=50${hotPlatform ? `&platform=${hotPlatform}` : ""}`)
      .then((hot) => setHotStocks(hot.list || hot))
      .catch(() => setHotStocks([]));

    apiGet<any>(`/h5/market/limit-ups?trade_date=${tradeDate}&page_size=200`)
      .then((limitList) => {
        setLimitRows(limitList.list || limitList);
        setLimitTotal(limitList.total || (limitList.list ? limitList.list.length : (Array.isArray(limitList) ? limitList.length : 0)));
      })
      .catch(() => { setLimitRows([]); setLimitTotal(0); });

    apiGet<any>(`/limit-up/summary?trade_date=${tradeDate}`)
      .then((limit) => setLimitSummary(limit))
      .catch(() => setLimitSummary(null))
      .finally(() => setLoading(false));
  }, [tradeDate, refreshKey, hotPlatform]);

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

  // Concept filter for limit ups
  const conceptOptions = useMemo(() => {
    const counts: Record<string, number> = {};
    limitRows.forEach((r) => {
      const name = r.concept || "未分类";
      counts[name] = (counts[name] || 0) + 1;
    });
    return [{ label: "全部涨停", value: "" }].concat(
      Object.entries(counts)
        .sort((a, b) => b[1] - a[1])
        .map(([name, cnt]) => ({ label: `${name} (${cnt})`, value: name }))
    );
  }, [limitRows]);

  const filteredLimitRows = useMemo(() => {
    if (!limitConcept) return limitRows;
    return limitRows.filter((r) => (r.concept || "未分类") === limitConcept);
  }, [limitRows, limitConcept]);

  async function addWatchFromMarket(item: any, sourceType: string) {
    const confirmed = await Dialog.confirm({
      content: `添加 ${item.stock_name} 到自选观察池？`,
      confirmText: "确认添加",
      cancelText: "取消",
    });
    if (!confirmed) return;
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
    })
      .then(() => {
        Toast.show({ content: "已添加自选" });
        setWatchCodes((prev) => new Set(prev).add(item.stock_code));
      })
      .catch(() => setError("添加自选失败"));
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
              <div className="metric-grid">
                <div className="metric-tile">
                  <span>成交量</span>
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
              <div className="metric-tile" style={{ background: "linear-gradient(135deg, #f1f4ff 0%, #e8eeff 50%, #ffffff 100%)" }}>
                <span>上证指数</span>
                <strong>
                  {data.sh_index ?? "-"}
                  {data.index_change_pct != null && (
                    <span style={{ fontSize: 16, fontWeight: 400, marginLeft: 6, color: data.index_change_pct >= 0 ? "#e34d59" : "#00b578" }}>
                      {data.index_change_pct >= 0 ? "+" : ""}{data.index_change_pct}%
                    </span>
                  )}
                </strong>
                <div style={{ fontSize: 12, color: "#7687a4", marginTop: 2 }}>
                  深成指 {data.sz_index ?? "-"} · 创业板指 {data.cyb_index ?? "-"}
                </div>
              </div>
              {data.market_comment && (
                <div className="review-note-panel">
                  <strong>每日收评</strong>
                  <p>{data.market_comment}</p>
                </div>
              )}
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
                <span className="soft-tag" style={{ cursor: "pointer" }} onClick={() => setHotPlatformPickerVisible(true)}>
                  {hotPlatform ? `${hotPlatform} Top10` : "三平台素数加权"} ▾
                </span>
              </div>
              {hotStocks.length ? (
                <div className="stack-list">
                  {hotStocks.slice(0, 10).map((item) => (
                    <div key={item.stock_code} className="row-card">
                      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                        <span style={{ color: "#4b63ee", fontWeight: 800, fontSize: 16, minWidth: 32, textAlign: "center" }}>
                          {item.total_score ?? item.raw_score ?? "-"}
                        </span>
                        <div>
                          <strong>
                            <StockLink stockName={item.stock_name} stockCode={item.stock_code} info={item} />
                          </strong>
                          {hotPlatform ? (
                            <>
                              <p>原始分数：{item.raw_score ?? "-"} / 排名：#{item.platform_rank ?? "-"}</p>
                              <p>{item.board_name || "未分类"}</p>
                            </>
                          ) : (
                            <>
                              <p>综合得分：{item.total_score} {item.cross_platform ? "多平台共振" : ""}</p>
                              <p>
                                {(item.platforms || []).map((p: any) => `${p.platform} #${p.rank}(${p.score})`).join("  ")}
                              </p>
                            </>
                          )}
                        </div>
                      </div>
                      {watchCodes.has(item.stock_code) ? (
                        <span style={{ fontSize: 18, color: "#00b578", lineHeight: 1 }}>✓</span>
                      ) : (
                        <span style={{ fontSize: 22, color: "#4b63ee", cursor: "pointer", lineHeight: 1, fontWeight: 300 }}
                          onClick={(e) => { e.stopPropagation(); addWatchFromMarket(item, "hot_stock"); }}>+</span>
                      )}
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
                  <span className="icon-badge">{limitConcept ? filteredLimitRows.length : limitTotal}</span>
                  <h2>涨停榜</h2>
                </div>
                <span className="soft-tag" style={{ cursor: "pointer" }} onClick={() => setConceptPickerVisible(true)}>
                  {limitConcept || "全部板块"} ▾
                </span>
              </div>
              {filteredLimitRows.length ? (
                    <div className="stack-list">
                      {filteredLimitRows.slice(0, 20).map((item) => (
                        <div key={item.stock_code} className="row-card row-card-action">
                          <div>
                            <strong>
                              <StockLink stockName={item.stock_name} stockCode={item.stock_code} info={item} />
                              <span style={{ fontSize: 11, fontWeight: 400, color: "#999", marginLeft: 4 }}>
                                {item.limit_time}
                              </span>
                            </strong>
                            <p>
                              {item.concept || "未分类"}
                              {item.limit_reason ? <span style={{ color: "#e34d59", marginLeft: 4 }}>{item.limit_reason}</span> : null}
                            </p>
                            <p>
                              封板：{item.limit_time} / 连板：{item.board_count} / 换手：{item.turnover_rate}%
                            </p>
                          </div>
                          {watchCodes.has(item.stock_code) ? (
                            <span style={{ fontSize: 18, color: "#00b578", lineHeight: 1 }}>✓</span>
                          ) : (
                            <span style={{ fontSize: 22, color: "#4b63ee", cursor: "pointer", lineHeight: 1, fontWeight: 300 }}
                              onClick={(e) => { e.stopPropagation(); addWatchFromMarket(item, "limit_up"); }}>+</span>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="empty-panel">该板块暂无涨停明细</div>
                  )}
            </article>
          )}
        </>
      )}
      <Picker
        columns={[[
          { label: "三平台素数加权", value: "" },
          { label: "财联社 cls", value: "cls" },
          { label: "同花顺 ths", value: "ths" },
          { label: "淘股吧 tgb", value: "tgb" },
        ]]}
        visible={hotPlatformPickerVisible}
        title="选择热榜来源"
        onClose={() => setHotPlatformPickerVisible(false)}
        onConfirm={(val) => {
          setHotPlatform((val as string[])[0] || "");
          setHotPlatformPickerVisible(false);
        }}
      />

      <Picker
        columns={[conceptOptions]}
        visible={conceptPickerVisible}
        title="选择涨停板块"
        onClose={() => setConceptPickerVisible(false)}
        onConfirm={(val) => {
          setLimitConcept((val as string[])[0] || "");
          setConceptPickerVisible(false);
        }}
      />
    </PageShell>
  );
}
