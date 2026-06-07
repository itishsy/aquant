import { useEffect, useState } from "react";
import { Button, Dialog, ErrorBlock, Input, Popup, Selector, SpinLoading, TextArea, Toast } from "antd-mobile";

import { apiDelete, apiGet, apiPost } from "../api/client";
import { PageShell } from "../components/PageShell";
import { WatchDetailDrawer } from "./watch-pool/WatchDetailDrawer";
import { WatchOverviewHeader } from "./watch-pool/WatchOverviewHeader";
import { WatchOverviewList } from "./watch-pool/WatchOverviewList";
import type {
  TradingSystemDefinition,
  WatchDetail,
  WatchOverviewItem,
  WatchOverviewResponse,
  WatchOverviewSummary,
  WatchSignalRecord,
} from "./watch-pool/types";

const EMPTY_SUMMARY: WatchOverviewSummary = {
  total: 0,
  active_total: 0,
  terminal_total: 0,
  today_signal_count: 0,
  today_trade_count: 0,
};

const emotionOptions = [
  { label: "冷静", value: "calm" },
  { label: "犹豫", value: "hesitant" },
  { label: "冲动", value: "impulsive" },
  { label: "害怕踏空", value: "fearful" },
];

export function WatchPoolPage() {
  const [items, setItems] = useState<WatchOverviewItem[]>([]);
  const [summary, setSummary] = useState<WatchOverviewSummary>(EMPTY_SUMMARY);
  const [systems, setSystems] = useState<TradingSystemDefinition[]>([]);
  const [detail, setDetail] = useState<WatchDetail | null>(null);
  const [buyForm, setBuyForm] = useState<Record<string, unknown> | null>(null);
  const [sellForm, setSellForm] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadOverview() {
    setLoading(true);
    try {
      const overview = await apiGet<WatchOverviewResponse>("/h5/watch-pool/overview");
      setItems(overview?.items || []);
      setSummary(overview?.summary || EMPTY_SUMMARY);
      setError("");
    } catch (loadError) {
      setError(String(loadError));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadOverview();
    apiGet<TradingSystemDefinition[]>("/h5/trading-systems")
      .then((rows) => setSystems(rows || []))
      .catch(() => setSystems([]));
  }, []);

  async function openDetail(item: WatchOverviewItem) {
    try {
      const full = await apiGet<WatchDetail>(`/h5/watch-pool/${item.watch_id}`);
      setDetail({ ...item, ...full, active_trade: item.active_trade });
    } catch (openError) {
      Toast.show({ content: openError instanceof Error ? openError.message : "获取自选详情失败" });
    }
  }

  async function refreshDetail() {
    if (!detail) return;
    const overviewItem = items.find((item) => item.watch_id === detail.watch_id);
    const full = await apiGet<WatchDetail>(`/h5/watch-pool/${detail.watch_id}`);
    setDetail({ ...(overviewItem || detail), ...full, active_trade: overviewItem?.active_trade || detail.active_trade });
  }

  function openBuyForm(signal: WatchSignalRecord) {
    setBuyForm({
      signal_id: signal.signal_id,
      stock_name: signal.stock_name,
      stock_code: signal.stock_code,
      buy_price: signal.trigger_price != null ? String(signal.trigger_price) : "",
      amount: "",
      position_ratio: "",
      stop_loss_price: signal.stop_loss_price != null ? String(signal.stop_loss_price) : "",
      target_price: signal.target_price != null ? String(signal.target_price) : "",
      buy_reason: signal.trigger_reason || "",
      trade_plan: "",
      emotion_state: "calm",
    });
  }

  async function confirmBuy() {
    if (!buyForm?.stop_loss_price) {
      Toast.show({ content: "止损价必填" });
      return;
    }
    await apiPost(`/h5/watch-signals/${buyForm.signal_id}/confirm-buy`, {
      buy_price: Number(buyForm.buy_price),
      amount: Number(buyForm.amount),
      position_ratio: buyForm.position_ratio ? Number(buyForm.position_ratio) : undefined,
      stop_loss_price: Number(buyForm.stop_loss_price),
      target_price: buyForm.target_price ? Number(buyForm.target_price) : undefined,
      buy_reason: buyForm.buy_reason,
      trade_plan: buyForm.trade_plan,
      emotion_state: buyForm.emotion_state,
      buy_point_confirmed: true,
    });
    Toast.show({ content: "已记录人工确认买入" });
    setBuyForm(null);
    setDetail(null);
    loadOverview();
  }

  async function abandonSignal(signal: WatchSignalRecord) {
    const confirmed = await Dialog.confirm({ content: `放弃 ${signal.stock_name} 本次机会？`, confirmText: "放弃本次机会", cancelText: "取消" });
    if (!confirmed) return;
    await apiPost(`/h5/watch-signals/${signal.signal_id}/abandon`, { reason: "用户放弃本次机会" });
    Toast.show({ content: "已放弃本次机会" });
    setDetail(null);
    loadOverview();
  }

  async function openSellForm(tradeId: number) {
    try {
      const trade = await apiGet<Record<string, unknown>>(`/h5/watch-trades/${tradeId}`);
      setSellForm({
        trade_id: trade.trade_id,
        stock_name: trade.stock_name,
        stock_code: trade.stock_code,
        remaining_amount: trade.remaining_amount || 0,
        sell_price: "",
        sell_reason: "manual_full_exit",
        execution_comment: "",
      });
    } catch (tradeError) {
      Toast.show({ content: tradeError instanceof Error ? tradeError.message : "获取交易详情失败" });
    }
  }

  async function confirmFullSell() {
    if (!sellForm?.sell_price) {
      Toast.show({ content: "请填写卖出价" });
      return;
    }
    await apiPost(`/h5/watch-trades/${sellForm.trade_id}/confirm-sell`, {
      sell_price: Number(sellForm.sell_price),
      amount: Number(sellForm.remaining_amount),
      execution_type: "sell",
      execution_reason: `${sellForm.sell_reason}${sellForm.execution_comment ? `：${sellForm.execution_comment}` : ""}`,
      is_full_exit: true,
    });
    Toast.show({ content: "已记录全部卖出，请进入复盘" });
    setSellForm(null);
    setDetail(null);
    loadOverview();
  }

  async function toggleMonitor(item: WatchDetail) {
    const enabled = item.monitor_enabled !== false && item.signal_enabled !== false;
    await apiPost(`/h5/watch-pool/${item.watch_id}/monitor/${enabled ? "disable" : "enable"}`, { reason: enabled ? "用户关闭监控" : "用户开启监控" });
    Toast.show({ content: enabled ? "已关闭监控" : "已开启监控" });
    await loadOverview();
    await refreshDetail();
  }

  async function markInvalid(item: WatchDetail) {
    const confirmed = await Dialog.confirm({ content: `确认将 ${item.stock_name} 标记为失效？`, confirmText: "标记失效", cancelText: "取消" });
    if (!confirmed) return;
    await apiPost(`/h5/watch-pool/${item.watch_id}/invalid`, { invalid_reason: "用户标记失效" });
    Toast.show({ content: "已标记失效" });
    setDetail(null);
    loadOverview();
  }

  async function removeWatch(item: WatchDetail) {
    const confirmed = await Dialog.confirm({ content: `确认剔除 ${item.stock_name}？历史记录仍会保留。`, confirmText: "确认剔除", cancelText: "取消" });
    if (!confirmed) return;
    await apiDelete(`/h5/watch-pool/${item.watch_id}`);
    Toast.show({ content: "已剔除" });
    setDetail(null);
    loadOverview();
  }

  async function blacklistWatch(item: WatchDetail) {
    const confirmed = await Dialog.confirm({ content: `确认将 ${item.stock_name} 加入黑名单？`, confirmText: "加入黑名单", cancelText: "取消" });
    if (!confirmed) return;
    await apiPost(`/h5/watch-pool/${item.watch_id}/blacklist`, { reason: "用户加入黑名单" });
    Toast.show({ content: "已加入黑名单" });
    setDetail(null);
    loadOverview();
  }

  return (
    <PageShell title="自选" hideHero>
      {loading && <SpinLoading />}
      {error && <ErrorBlock description="自选页加载失败" />}
      {!loading && !error && (
        <article className="feature-card">
          <WatchOverviewHeader summary={summary} />
          <WatchOverviewList items={items} onOpenDetail={openDetail} />
        </article>
      )}

      <WatchDetailDrawer
        detail={detail}
        systems={systems}
        onClose={() => setDetail(null)}
        onSaved={setDetail}
        onRefresh={loadOverview}
        onConfirmBuy={openBuyForm}
        onAbandonSignal={abandonSignal}
        onConfirmSell={openSellForm}
        onToggleMonitor={toggleMonitor}
        onMarkInvalid={markInvalid}
        onRemove={removeWatch}
        onBlacklist={blacklistWatch}
      />

      <Popup visible={Boolean(buyForm)} onMaskClick={() => setBuyForm(null)} bodyClassName="watch-action-popup">
        {buyForm && (
          <div className="watch-detail-stack">
            <div><h3>确认买入</h3><p>{String(buyForm.stock_name)} {String(buyForm.stock_code)}</p></div>
            <Input type="number" value={String(buyForm.buy_price)} placeholder="买入价" onChange={(value) => setBuyForm({ ...buyForm, buy_price: value })} />
            <Input type="number" value={String(buyForm.amount)} placeholder="数量" onChange={(value) => setBuyForm({ ...buyForm, amount: value })} />
            <Input type="number" value={String(buyForm.position_ratio)} placeholder="仓位，例如 0.2" onChange={(value) => setBuyForm({ ...buyForm, position_ratio: value })} />
            <Input type="number" value={String(buyForm.stop_loss_price)} placeholder="止损价（必填）" onChange={(value) => setBuyForm({ ...buyForm, stop_loss_price: value })} />
            <Input type="number" value={String(buyForm.target_price)} placeholder="目标价" onChange={(value) => setBuyForm({ ...buyForm, target_price: value })} />
            <TextArea value={String(buyForm.buy_reason)} rows={3} placeholder="买入理由" onChange={(value) => setBuyForm({ ...buyForm, buy_reason: value })} />
            <TextArea value={String(buyForm.trade_plan)} rows={3} placeholder="交易计划" onChange={(value) => setBuyForm({ ...buyForm, trade_plan: value })} />
            <Selector options={emotionOptions} value={[String(buyForm.emotion_state)]} onChange={(value) => setBuyForm({ ...buyForm, emotion_state: value[0] })} />
            <div className="watch-detail-actions"><Button block onClick={() => setBuyForm(null)}>取消</Button><Button block color="primary" onClick={confirmBuy}>确认</Button></div>
          </div>
        )}
      </Popup>

      <Popup visible={Boolean(sellForm)} onMaskClick={() => setSellForm(null)} bodyClassName="watch-action-popup">
        {sellForm && (
          <div className="watch-detail-stack">
            <div><h3>确认全部卖出</h3><p>{String(sellForm.stock_name)} {String(sellForm.stock_code)}</p></div>
            <Input type="number" value={String(sellForm.sell_price)} placeholder="卖出价" onChange={(value) => setSellForm({ ...sellForm, sell_price: value })} />
            <Input value={String(sellForm.remaining_amount)} disabled />
            <Input value={String(sellForm.sell_reason)} placeholder="卖出原因" onChange={(value) => setSellForm({ ...sellForm, sell_reason: value })} />
            <TextArea value={String(sellForm.execution_comment)} rows={3} placeholder="执行说明" onChange={(value) => setSellForm({ ...sellForm, execution_comment: value })} />
            <div className="watch-detail-actions"><Button block onClick={() => setSellForm(null)}>取消</Button><Button block color="danger" onClick={confirmFullSell}>确认全部卖出</Button></div>
          </div>
        )}
      </Popup>
    </PageShell>
  );
}
