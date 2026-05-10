import { useEffect, useMemo, useState } from "react";
import { DatePicker, Dialog, ErrorBlock, Picker, SpinLoading, Toast } from "antd-mobile";
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
  index_change_pct?: number;
  sh_index_change_pct?: number;
  sh_index_change_px?: number;
  sz_index_change_pct?: number;
  sz_index_change_px?: number;
  cyb_index_change_pct?: number;
  cyb_index_change_px?: number;
  today_chances?: any[];
  today_tuyeres?: any[];
  topic_list?: any[];
  limit_up_ladder?: any[];
};

export function MarketPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const searchParams = new URLSearchParams(location.search);
  const queryDate = searchParams.get("trade_date");
  const refreshKey = searchParams.get("refresh");
  const [tradeDate, setTradeDate] = useState<string>(queryDate || "");
  const [pickerVisible, setPickerVisible] = useState(false);
  const [tab, setTab] = useState("overview");
  const [data, setData] = useState<MarketSummary | null>(null);
  const [review, setReview] = useState<any>(null);
  const [hotStocks, setHotStocks] = useState<any[]>([]);
  const [limitRows, setLimitRows] = useState<any[]>([]);
  const [limitTotal, setLimitTotal] = useState(0);
  const [limitConcept, setLimitConcept] = useState("");
  const [conceptPickerVisible, setConceptPickerVisible] = useState(false);
  const [hotPlatform, setHotPlatform] = useState("");
  const [hotPlatformPickerVisible, setHotPlatformPickerVisible] = useState(false);
  const [watchCodes, setWatchCodes] = useState<Set<string>>(new Set());
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (queryDate) return;

    apiGet<string[]>("/h5/market/trading-dates")
      .then((dates) => {
        const latestDate = (dates || []).slice().sort().reverse()[0];
        const nextDate = latestDate || todayString();
        setTradeDate(nextDate);
        navigate(`/market?trade_date=${nextDate}`, { replace: true });
      })
      .catch(() => {
        const fallbackDate = todayString();
        setTradeDate(fallbackDate);
        navigate(`/market?trade_date=${fallbackDate}`, { replace: true });
      });
  }, [navigate, queryDate]);

  useEffect(() => {
    if (!tradeDate) return;

    setLoading(true);
    setError("");
    apiGet<any[]>("/h5/watch-pool")
      .then((items) => setWatchCodes(new Set((items || []).map((w: any) => w.stock_code))))
      .catch(() => {});

    apiGet<MarketSummary>(`/h5/market/overview?trade_date=${tradeDate}`)
      .then((summary) => setData(summary))
      .catch(() => {
        setData(null);
        setError("市场数据加载失败，请稍后重试");
      });

    apiGet<any>(`/market/review?trade_date=${tradeDate}`)
      .then((r) => setReview(r))
      .catch(() => setReview(null));

    apiGet<any>(`/h5/market/hot-stocks?trade_date=${tradeDate}&page_size=50${hotPlatform ? `&platform=${hotPlatform}` : ""}`)
      .then((hot) => setHotStocks(hot.list || hot))
      .catch(() => setHotStocks([]));

    apiGet<any>(`/h5/market/limit-ups?trade_date=${tradeDate}&page_size=500`)
      .then((limitList) => {
        const rows = limitList.list || limitList || [];
        setLimitRows(rows);
        setLimitTotal(limitList.total || rows.length || 0);
      })
      .catch(() => {
        setLimitRows([]);
        setLimitTotal(0);
      });

    apiGet<any>(`/limit-up/summary?trade_date=${tradeDate}`)
      .catch(() => null)
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
  const formatPct = (value?: number | null) => {
    if (value == null) return "";
    return `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;
  };
  const formatPx = (value?: number | null) => {
    if (value == null) return "";
    return ` ${value >= 0 ? "+" : ""}${value.toFixed(2)}`;
  };
  const pctColor = (value?: number | null) => value == null ? "#7687a4" : value >= 0 ? "#e34d59" : "#00b578";
  const marketInfoSections = [
    { title: "今日机会", tag: "财联社", rows: data?.today_chances || [] },
    { title: "今日风口", tag: "财联社", rows: data?.today_tuyeres || [] },
    { title: "话题热榜", tag: "同花顺", rows: data?.topic_list || [] },
  ];

  const conceptOptions = useMemo(() => {
    const counts: Record<string, number> = {};
    limitRows.forEach((r) => {
      const name = r.concept || r.plate_name || "未分类";
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
    return limitRows.filter((r) => (r.concept || r.plate_name || "未分类") === limitConcept);
  }, [limitRows, limitConcept]);

  function showMarketInfoDetail(title: string, item: any) {
    const stocks = item.stocks || [];
    Dialog.alert({
      title,
      content: (
        <div style={{ textAlign: "left", color: "#53627c", lineHeight: 1.65 }}>
          <strong style={{ color: "#18223d" }}>{item.subject_name || item.title}</strong>
          {item.title && item.subject_name ? <p>{item.title}</p> : null}
          {item.driver ? <p>{item.driver}</p> : null}
          {item.description ? <p>{item.description}</p> : null}
          {item.hot_value != null ? <p>热度：{item.hot_value}</p> : null}
          {item.attention_num != null ? <p>关注度：{item.attention_num}</p> : null}
          {stocks.length ? (
            <p>
              关联个股：
              {stocks.map((stock: any) => `${stock.stock_name || stock.name}${stock.change_pct != null ? ` ${formatPct(stock.change_pct)}` : ""}`).join(" / ")}
            </p>
          ) : null}
          <p style={{ marginTop: 10 }}>仅作为市场资讯辅助，请结合个人交易规则确认。</p>
        </div>
      ),
      confirmText: "知道了",
    });
  }

  function showLimitLadderDetail(item: any) {
    Dialog.alert({
      title: `${item.height}板梯队`,
      content: (
        <div style={{ textAlign: "left", color: "#53627c", lineHeight: 1.65 }}>
          <p>共 {item.count || 0} 只股票。</p>
          <div style={{ display: "grid", gap: 6 }}>
            {(item.stocks || []).map((stock: any) => (
              <div key={`${item.height}-${stock.stock_code}`} style={{ padding: "8px 10px", borderRadius: 12, background: "#f6f8ff" }}>
                <StockLink stockName={stock.stock_name} stockCode={stock.stock_code} showCode />
              </div>
            ))}
          </div>
          <p style={{ marginTop: 10 }}>涨停梯队仅展示客观涨停结构，作为市场观察辅助。</p>
        </div>
      ),
      confirmText: "知道了",
    });
  }

  function showLimitUpDetail(item: any) {
    Dialog.alert({
      title: item.stock_name || item.stock_code,
      content: (
        <div style={{ textAlign: "left", color: "#53627c", lineHeight: 1.65 }}>
          <p><strong>股票：</strong><StockLink stockName={item.stock_name} stockCode={item.stock_code} showCode /></p>
          <p><strong>所属板块：</strong>{item.concept || item.plate_name || "未分类"}</p>
          <p><strong>涨停时间：</strong>{item.limit_time || "-"}</p>
          <p><strong>连板：</strong>{item.board_count || item.ladder_height || 1} 板</p>
          {item.ladder_height ? <p><strong>梯队：</strong>{item.ladder_height} 板梯队</p> : null}
          {item.change_pct != null ? <p><strong>涨幅：</strong>{formatPct(item.change_pct)}</p> : null}
          {item.last_price != null ? <p><strong>最新价：</strong>{item.last_price}</p> : null}
          {item.reason_tags || item.limit_type ? <p><strong>标签：</strong>{item.reason_tags || item.limit_type}</p> : null}
          <p><strong>涨停原因：</strong>{item.limit_reason || "暂无原因"}</p>
          <p style={{ marginTop: 10 }}>仅作为涨停结果观察辅助，请结合个人交易规则确认。</p>
        </div>
      ),
      confirmText: "知道了",
    });
  }

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
      sector_name: item.board_name || item.concept || item.plate_name,
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
        value={stringToDate(tradeDate || todayString())}
        max={new Date()}
        onClose={() => setPickerVisible(false)}
        onConfirm={(value) => changeTradeDate(dateToString(value))}
      />

      {loading && <SpinLoading />}
      {error && <ErrorBlock description={error} />}
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
                  <span style={{ fontSize: 16, fontWeight: 400, marginLeft: 6, color: pctColor(data.sh_index_change_pct ?? data.index_change_pct) }}>
                    {formatPct(data.sh_index_change_pct ?? data.index_change_pct)}
                    {formatPx(data.sh_index_change_px)}
                  </span>
                </strong>
                <div style={{ fontSize: 12, color: "#7687a4", marginTop: 2 }}>
                  深成指 {data.sz_index ?? "-"}
                  <span style={{ color: pctColor(data.sz_index_change_pct), marginLeft: 4 }}>
                    {formatPct(data.sz_index_change_pct)}
                    {formatPx(data.sz_index_change_px)}
                  </span>
                  <span style={{ margin: "0 6px" }}>/</span>
                  创业板指 {data.cyb_index ?? "-"}
                  <span style={{ color: pctColor(data.cyb_index_change_pct), marginLeft: 4 }}>
                    {formatPct(data.cyb_index_change_pct)}
                    {formatPx(data.cyb_index_change_px)}
                  </span>
                </div>
              </div>
              <div style={{ display: "grid", gap: 10, marginTop: 12 }}>
                {marketInfoSections.map((section) => (
                  <div key={section.title} className="metric-tile" style={{ padding: 14 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                      <strong style={{ fontSize: 16 }}>{section.title}</strong>
                      <span className="soft-tag">{section.tag}</span>
                    </div>
                    {section.rows.length ? (
                      <div style={{ display: "grid", gap: 8 }}>
                        {section.rows.slice(0, section.title === "话题热榜" ? 5 : 3).map((item: any, index: number) => (
                          <button
                            key={`${section.title}-${item.subject_id || item.topic_code || index}`}
                            type="button"
                            onClick={() => showMarketInfoDetail(section.title, item)}
                            style={{
                              border: 0,
                              borderRadius: 14,
                              padding: "10px 12px",
                              textAlign: "left",
                              background: "#f6f8ff",
                              color: "#1d2948",
                            }}
                          >
                            <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                              <strong style={{ fontSize: 14 }}>{item.subject_name || item.title}</strong>
                              {(item.hot_value != null || item.attention_num != null) && (
                                <span style={{ color: "#64748b", fontSize: 12, whiteSpace: "nowrap" }}>
                                  {item.hot_value != null ? item.hot_value : item.attention_num}
                                </span>
                              )}
                            </div>
                            <p style={{ margin: "4px 0 0", color: "#73809a", fontSize: 12 }}>
                              {item.title || item.driver || item.description || "点击查看详情"}
                            </p>
                          </button>
                        ))}
                      </div>
                    ) : (
                      <div className="empty-panel" style={{ minHeight: 72 }}>暂无{section.title}数据</div>
                    )}
                  </div>
                ))}
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
                  {hotStocks.map((item) => (
                    <div key={`${item.stock_code}-${item.platform || "all"}`} className="row-card row-card-action">
                      <div>
                        <strong>
                          <span onClick={(event) => event.stopPropagation()}>
                            <StockLink stockName={item.stock_name} stockCode={item.stock_code} info={item} />
                          </span>
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
                      {watchCodes.has(item.stock_code) ? (
                        <span style={{ fontSize: 18, color: "#00b578", lineHeight: 1 }}>✓</span>
                      ) : (
                        <span
                          style={{ fontSize: 22, color: "#4b63ee", cursor: "pointer", lineHeight: 1, fontWeight: 300 }}
                          onClick={(e) => { e.stopPropagation(); addWatchFromMarket(item, "hot_stock"); }}
                        >
                          +
                        </span>
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
              {(data.limit_up_ladder || []).length ? (
                <div style={{ display: "grid", gap: 10, marginBottom: 14 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <strong style={{ fontSize: 16 }}>涨停梯度</strong>
                    <span className="soft-tag">连板结构</span>
                  </div>
                  <div style={{ display: "flex", gap: 10, overflowX: "auto", paddingBottom: 2 }}>
                    {(data.limit_up_ladder || []).map((item: any) => (
                      <button
                        key={item.height}
                        type="button"
                        onClick={() => showLimitLadderDetail(item)}
                        style={{
                          minWidth: 130,
                          border: 0,
                          borderRadius: 18,
                          padding: "12px 14px",
                          textAlign: "left",
                          background: "linear-gradient(135deg, #fff4f4 0%, #eef3ff 100%)",
                          color: "#1d2948",
                        }}
                      >
                        <div style={{ fontSize: 22, fontWeight: 900, color: "#e34d59" }}>{item.height}板</div>
                        <div style={{ fontSize: 13, color: "#64748b", marginTop: 2 }}>{item.count || 0} 只</div>
                        <div style={{ fontSize: 12, color: "#73809a", marginTop: 6, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                          {(item.stocks || []).slice(0, 2).map((stock: any) => stock.stock_name).join(" / ") || "点击查看"}
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              ) : null}
              {filteredLimitRows.length ? (
                <div className="stack-list">
                  {filteredLimitRows.map((item) => (
                    <div
                      key={item.stock_code}
                      className="row-card row-card-action"
                      style={{ cursor: "pointer" }}
                      onClick={() => showLimitUpDetail(item)}
                    >
                      <div>
                        <strong>
                          <StockLink stockName={item.stock_name} stockCode={item.stock_code} info={item} />
                          <span style={{ fontSize: 11, fontWeight: 400, color: "#999", marginLeft: 4 }}>
                            {item.limit_time}
                          </span>
                        </strong>
                        <p>
                          {item.concept || item.plate_name || "未分类"}
                          {(item.reason_tags || item.limit_type) ? (
                            <span style={{ color: "#e34d59", marginLeft: 4 }}>{item.reason_tags || item.limit_type}</span>
                          ) : null}
                        </p>
                        <p>
                          涨停 {item.limit_time || "-"} / 连板 {item.board_count || item.ladder_height || 1}
                          {item.ladder_height ? ` / ${item.ladder_height}板梯队` : ""}
                        </p>
                      </div>
                      {watchCodes.has(item.stock_code) ? (
                        <span style={{ fontSize: 18, color: "#00b578", lineHeight: 1 }}>✓</span>
                      ) : (
                        <span
                          style={{ fontSize: 22, color: "#4b63ee", cursor: "pointer", lineHeight: 1, fontWeight: 300 }}
                          onClick={(e) => { e.stopPropagation(); addWatchFromMarket(item, "limit_up"); }}
                        >
                          +
                        </span>
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
