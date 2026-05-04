import { useEffect, useMemo, useState } from "react";
import { Button, ErrorBlock, Form, Input, Popup, Selector, SpinLoading, TextArea, Toast } from "antd-mobile";
import { apiGet, apiPost } from "../api/client";
import { PageShell } from "../components/PageShell";
import { StockLink } from "../components/StockLink";
import { shiftTradeDate, todayString } from "../lib/tradeDates";

type TradeRecord = {
  id: number;
  stock_code: string;
  stock_name: string;
  buy_price: number;
  quantity: number;
  position_ratio: number;
  stop_loss_price: number | null;
  target_price: number | null;
  trade_plan: string;
  status: string;
  sell_price: number | null;
  sell_quantity: number | null;
  sell_reason: string | null;
  realized_pnl: number | null;
  created_at: string;
};

export function TradesPage() {
  const [tradeDate, setTradeDate] = useState<string>(todayString());
  const [tab, setTab] = useState("open");
  const [items, setItems] = useState<TradeRecord[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [sellTarget, setSellTarget] = useState<TradeRecord | null>(null);
  const [sellPrice, setSellPrice] = useState("");
  const [sellReason, setSellReason] = useState("按计划止盈，人工记录卖出，仅作为交易辅助");
  const [sellTag, setSellTag] = useState<string[]>(["止盈"]);

  async function load() {
    setLoading(true);
    setError("");
    try {
      const response = await apiGet<TradeRecord[]>("/trades");
      setItems(response);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const filtered = useMemo(
    () =>
      items.filter((item) => {
        const matchTab = tab === "open" ? item.status === "open" : item.status !== "open";
        const matchDate = String(item.created_at || "").slice(0, 10) <= tradeDate;
        return matchTab && matchDate;
      }),
    [items, tab, tradeDate]
  );

  const summary = useMemo(() => {
    const openPositions = filtered.filter((item) => item.status === "open");
    const pnlValues = filtered.map((item) => item.realized_pnl || 0);
    return {
      count: filtered.length,
      openCount: openPositions.length,
      totalPnl: pnlValues.reduce((acc, value) => acc + value, 0),
      avgPosition:
        openPositions.length > 0
          ? Math.round(
              (openPositions.reduce((acc, item) => acc + (item.position_ratio || 0), 0) / openPositions.length) * 100
            )
          : 0,
    };
  }, [filtered]);

  async function submitSell() {
    if (!sellTarget) return;
    try {
      await apiPost(`/trades/${sellTarget.id}/sell`, {
        price: Number(sellPrice || sellTarget.buy_price),
        quantity: sellTarget.quantity,
        reason: `${sellTag.join(" / ")}：${sellReason}`,
      });
      setSellTarget(null);
      setSellPrice("");
      setSellReason("按计划止盈，人工记录卖出，仅作为交易辅助");
      setSellTag(["止盈"]);
      await load();
      Toast.show({ content: "已保存卖出记录" });
    } catch (err) {
      Toast.show({ content: `保存失败：${String(err)}` });
    }
  }

  return (
    <PageShell
      title="交易记录"
      dateText={tradeDate}
      onPrevDate={() => setTradeDate((current) => shiftTradeDate(current, -1))}
      onNextDate={() => setTradeDate((current) => shiftTradeDate(current, 1))}
      segments={[
        { key: "open", label: "持仓中", onClick: () => setTab("open") },
        { key: "closed", label: "已完成", onClick: () => setTab("closed") },
      ]}
      activeSegment={tab}
    >
      {loading && <SpinLoading />}
      {error && <ErrorBlock description="交易记录加载失败" />}

      <section className="summary-board">
        <article className="summary-card">
          <span>记录数</span>
          <strong>{summary.count}</strong>
          <p>当前筛选下的交易总数</p>
        </article>
        <article className="summary-card">
          <span>持仓中</span>
          <strong>{summary.openCount}</strong>
          <p>仍在跟踪的仓位</p>
        </article>
        <article className="summary-card">
          <span>总盈亏</span>
          <strong>{summary.totalPnl}</strong>
          <p>已实现盈亏汇总</p>
        </article>
        <article className="summary-card">
          <span>平均仓位</span>
          <strong>{summary.avgPosition}%</strong>
          <p>当前持仓平均占比</p>
        </article>
      </section>

      {filtered.length ? (
        <div className="stack-list">
          {filtered.map((item) => (
            <article key={item.id} className="feature-card compact-card">
              <div className="card-head">
                <div className="card-headline">
                  <span className="icon-badge">交</span>
                  <h2>
                    <StockLink stockName={item.stock_name} stockCode={item.stock_code} />
                  </h2>
                </div>
                <span className="soft-tag">{item.status === "open" ? "持仓中" : "已完成"}</span>
              </div>

              <div className="metric-grid slim-grid">
                <div className="metric-tile">
                  <span>买入价</span>
                  <strong>{item.buy_price}</strong>
                </div>
                <div className="metric-tile">
                  <span>数量</span>
                  <strong>{item.quantity}</strong>
                </div>
                <div className="metric-tile">
                  <span>盈亏</span>
                  <strong>{item.realized_pnl ?? "未结算"}</strong>
                </div>
              </div>

              <div className="detail-grid">
                <div>
                  <span>仓位</span>
                  <strong>{Math.round((item.position_ratio || 0) * 100)}%</strong>
                </div>
                <div>
                  <span>止损价</span>
                  <strong>{item.stop_loss_price ?? "-"}</strong>
                </div>
                <div>
                  <span>目标价</span>
                  <strong>{item.target_price ?? "-"}</strong>
                </div>
              </div>

              <p className="card-note">计划：{item.trade_plan || "暂无交易计划"}</p>

              {item.status === "open" ? (
                <div className="action-row">
                  <Button
                    size="small"
                    color="primary"
                    onClick={() => {
                      setSellTarget(item);
                      setSellPrice(String((item.buy_price * 1.05).toFixed(2)));
                    }}
                  >
                    记录卖出
                  </Button>
                </div>
              ) : (
                <div className="closed-strip">
                  <span>卖出价：{item.sell_price}</span>
                  <span>卖出原因：{item.sell_reason || "已记录"}</span>
                </div>
              )}
            </article>
          ))}
        </div>
      ) : (
        <div className="empty-panel">当前分类暂无交易记录</div>
      )}

      <Popup
        visible={!!sellTarget}
        onMaskClick={() => setSellTarget(null)}
        bodyStyle={{ borderTopLeftRadius: 24, borderTopRightRadius: 24, padding: 20 }}
      >
        {sellTarget ? (
          <div className="sheet-panel">
            <div className="sheet-head">
              <h3>记录卖出</h3>
              <p>
                <StockLink stockName={sellTarget.stock_name} stockCode={sellTarget.stock_code} />
              </p>
            </div>
            <Form
              footer={
                <Button block color="primary" onClick={submitSell}>
                  保存卖出记录
                </Button>
              }
            >
              <Form.Item label="卖出价格">
                <Input value={sellPrice} onChange={setSellPrice} placeholder="请输入卖出价格" />
              </Form.Item>
              <Form.Item label="卖出标签">
                <Selector
                  columns={3}
                  options={[
                    { label: "止盈", value: "止盈" },
                    { label: "减仓", value: "减仓" },
                    { label: "风控", value: "风控" },
                  ]}
                  value={sellTag}
                  onChange={setSellTag}
                />
              </Form.Item>
              <Form.Item label="卖出原因">
                <TextArea value={sellReason} onChange={setSellReason} rows={4} placeholder="补充本次卖出原因" />
              </Form.Item>
            </Form>
          </div>
        ) : null}
      </Popup>
    </PageShell>
  );
}
