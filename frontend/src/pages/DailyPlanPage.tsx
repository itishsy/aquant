import { useEffect, useState } from "react";
import { Button, ErrorBlock, Form, Input, Popup, SpinLoading, TextArea, Toast } from "antd-mobile";
import { apiGet, apiPost } from "../api/client";
import { PageShell } from "../components/PageShell";
import { shiftTradeDate, todayString } from "../lib/tradeDates";

type PlanItem = {
  item_id: number;
  stock_code: string;
  stock_name: string;
  action_type: string;
  trigger_condition: string;
  stop_loss_price?: number;
  target_price?: number;
  position_ratio: number;
  invalid_condition: string;
  status: string;
};

type DailyPlan = {
  plan_id: number;
  trade_date: string;
  market_score: number;
  market_state: string;
  trade_permission: string;
  max_total_position: number;
  max_single_position: number;
  key_sectors: Array<{ sector_name: string; sector_score: number }>;
  risk_summary: string;
  discipline_note: string;
  plan_status: string;
  execution_summary?: Record<string, unknown>;
};

export function DailyPlanPage() {
  const [tradeDate, setTradeDate] = useState(todayString());
  const [plan, setPlan] = useState<DailyPlan | null>(null);
  const [items, setItems] = useState<PlanItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [checkOpen, setCheckOpen] = useState(false);
  const [selected, setSelected] = useState<PlanItem | null>(null);
  const [stopLoss, setStopLoss] = useState("");
  const [targetPrice, setTargetPrice] = useState("");
  const [positionRatio, setPositionRatio] = useState("0.1");
  const [checkResult, setCheckResult] = useState<any>(null);

  async function load(nextDate = tradeDate) {
    setLoading(true);
    setError("");
    try {
      const response = await apiGet<DailyPlan | null>(`/v1/daily-plans/${nextDate}`);
      setPlan(response);
      if (response?.plan_id) {
        const planItems = await apiGet<PlanItem[]>(`/v1/daily-plans/${response.plan_id}/items`);
        setItems(planItems);
      } else {
        setItems([]);
      }
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  async function generate() {
    setLoading(true);
    try {
      const response = await apiPost<DailyPlan>("/v1/daily-plans/generate", { trade_date: tradeDate });
      setPlan(response);
      const planItems = await apiGet<PlanItem[]>(`/v1/daily-plans/${response.plan_id}/items`);
      setItems(planItems);
      Toast.show({ content: "今日计划已生成" });
    } catch (err) {
      Toast.show({ content: `生成失败：${String(err)}` });
    } finally {
      setLoading(false);
    }
  }

  async function buildChecklist() {
    if (!selected) return;
    try {
      const response = await apiPost("/v1/trade-checklists/build", {
        plan_item_id: selected.item_id,
        stock_code: selected.stock_code,
        trade_date: tradeDate,
        stop_loss_price: Number(stopLoss || selected.stop_loss_price || 0),
        target_price: Number(targetPrice || selected.target_price || 0),
        position_ratio: Number(positionRatio),
        manual_reason: selected.trigger_condition,
      });
      setCheckResult(response);
    } catch (err) {
      Toast.show({ content: `检查失败：${String(err)}` });
    }
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <PageShell
      title="今日计划"
      dateText={tradeDate}
      onPrevDate={() => {
        const next = shiftTradeDate(tradeDate, -1);
        setTradeDate(next);
        load(next);
      }}
      onNextDate={() => {
        const next = shiftTradeDate(tradeDate, 1);
        setTradeDate(next);
        load(next);
      }}
    >
      {loading && <SpinLoading />}
      {error && <ErrorBlock description="今日计划加载失败" />}

      <article className="feature-card">
        <div className="card-head">
          <div className="card-headline">
            <span className="icon-badge">计</span>
            <h2>交易权限</h2>
          </div>
          <Button color="primary" size="small" onClick={generate}>
            生成计划
          </Button>
        </div>
        {plan ? (
          <>
            <div className="metric-grid">
              <div className="metric-tile">
                <span>市场状态</span>
                <strong>{plan.market_state}</strong>
              </div>
              <div className="metric-tile">
                <span>交易权限</span>
                <strong>{plan.trade_permission}</strong>
              </div>
              <div className="metric-tile">
                <span>最大总仓位</span>
                <strong>{Math.round(plan.max_total_position * 100)}%</strong>
              </div>
              <div className="metric-tile">
                <span>单笔上限</span>
                <strong>{Math.round(plan.max_single_position * 100)}%</strong>
              </div>
            </div>
            <p className="card-note">{plan.discipline_note}</p>
          </>
        ) : (
          <div className="empty-panel">当前日期暂无今日计划</div>
        )}
      </article>

      <article className="feature-card compact-card">
        <div className="card-head">
          <div className="card-headline">
            <span className="icon-badge">股</span>
            <h2>计划项</h2>
          </div>
          <span className="soft-tag">人工确认</span>
        </div>
        {items.length ? (
          <div className="stack-list">
            {items.map((item) => (
              <div className="row-card row-card-action" key={item.item_id}>
                <div>
                  <strong>
                    {item.stock_name} {item.stock_code}
                  </strong>
                  <p>{item.trigger_condition}</p>
                  <p>止损：{item.stop_loss_price ?? "-"} / 目标：{item.target_price ?? "-"}</p>
                  <p>失效：{item.invalid_condition}</p>
                </div>
                <Button
                  size="mini"
                  color="primary"
                  onClick={() => {
                    setSelected(item);
                    setStopLoss(String(item.stop_loss_price || ""));
                    setTargetPrice(String(item.target_price || ""));
                    setCheckOpen(true);
                  }}
                >
                  检查
                </Button>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-panel">计划生成后会从核心池同步重点观察股</div>
        )}
      </article>

      <Popup visible={checkOpen} onMaskClick={() => setCheckOpen(false)} bodyStyle={{ borderTopLeftRadius: 24, borderTopRightRadius: 24, padding: 20 }}>
        <div className="sheet-panel">
          <div className="sheet-head">
            <h3>买入前检查清单</h3>
            <p>仅作为交易辅助，请结合个人交易计划确认。</p>
          </div>
          <Form footer={<Button block color="primary" onClick={buildChecklist}>生成检查清单</Button>}>
            <Form.Item label="止损价">
              <Input value={stopLoss} onChange={setStopLoss} placeholder="必须填写止损价" />
            </Form.Item>
            <Form.Item label="目标价">
              <Input value={targetPrice} onChange={setTargetPrice} placeholder="目标价或卖出条件" />
            </Form.Item>
            <Form.Item label="仓位比例">
              <Input value={positionRatio} onChange={setPositionRatio} placeholder="例如 0.1" />
            </Form.Item>
          </Form>
          {checkResult ? (
            <div className="review-note-panel">
              <strong>{checkResult.all_passed ? "检查通过" : "检查未通过"}</strong>
              <p>{(checkResult.failed_items || []).join("；") || "所有检查项通过，仍需人工确认。"}</p>
            </div>
          ) : null}
        </div>
      </Popup>
    </PageShell>
  );
}
