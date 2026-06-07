import { useEffect, useMemo, useRef, useState } from "react";
import { Button, Popup, SpinLoading, Toast } from "antd-mobile";

import { apiGet, apiPost, apiPut } from "../../api/client";
import type { KlineBar } from "../../components/StockDetailPopup";
import { toXueqiuUrl } from "../../components/StockLink";
import { changePctTone, compactParts, formatChangePct, formatDate, formatPrice, statusLabel, tradingSystemLabel } from "./formatters";
import type {
  TradingSystemDefinition,
  TradingSystemParamDefinition,
  WatchDetail,
  WatchRulePreviewResult,
  WatchSignalRecord,
  WatchTradeRecord,
} from "./types";
import { WatchEditForm, type WatchEditDraft } from "./WatchEditForm";
import { WatchInfoTab } from "./WatchInfoTab";
import { WatchKlineTab } from "./WatchKlineTab";
import { WatchRulePreview } from "./WatchRulePreview";
import { WatchSignalHistoryTab } from "./WatchSignalHistoryTab";
import { WatchTradeHistoryTab } from "./WatchTradeHistoryTab";

type DetailTab = "kline" | "detail" | "signals" | "trades";

type Props = {
  detail: WatchDetail | null;
  systems: TradingSystemDefinition[];
  onClose: () => void;
  onSaved: (detail: WatchDetail) => void;
  onRefresh: () => void;
  onConfirmBuy: (signal: WatchSignalRecord) => void;
  onAbandonSignal: (signal: WatchSignalRecord) => void;
  onConfirmSell: (tradeId: number) => void;
  onToggleMonitor: (detail: WatchDetail) => void;
  onMarkInvalid: (detail: WatchDetail) => void;
  onRemove: (detail: WatchDetail) => void;
  onBlacklist: (detail: WatchDetail) => void;
};

function terminalWatch(detail: WatchDetail) {
  return (
    detail.active === false
    || detail.card_tone === "terminal"
    || detail.display_group === "terminal"
    || ["removed", "invalid", "blacklist", "archived"].includes(detail.status || "")
  );
}

function createDraft(detail: WatchDetail): WatchEditDraft {
  const params = { ...(detail.system_params_json || {}) };
  if (params.key_observe_price == null && detail.key_observe_price != null) params.key_observe_price = detail.key_observe_price;
  if (params.auto_remove_price == null && detail.auto_remove_price != null) params.auto_remove_price = detail.auto_remove_price;
  if (params.invalid_condition == null && detail.invalid_condition) params.invalid_condition = detail.invalid_condition;
  const code = detail.trading_system_code || detail.trading_system || "";
  return {
    trading_system: code,
    trading_system_code: code,
    system_params_json: Object.fromEntries(Object.entries(params).map(([key, value]) => [key, value == null ? "" : String(value)])),
    entry_reason: detail.entry_reason || detail.reason || "",
    key_observe_price: String(params.key_observe_price || ""),
    auto_remove_price: String(params.auto_remove_price || ""),
    invalid_condition: String(params.invalid_condition || ""),
    risk_tags: detail.risk_tags || [],
    user_remark: detail.user_remark || detail.remark || "",
    adjust_reason: "",
  };
}

export function WatchDetailDrawer(props: Props) {
  const { detail } = props;
  const [tab, setTab] = useState<DetailTab>("kline");
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<WatchEditDraft | null>(null);
  const [params, setParams] = useState<TradingSystemParamDefinition[]>([]);
  const [kline, setKline] = useState<KlineBar[] | null>(null);
  const [signals, setSignals] = useState<WatchSignalRecord[] | null>(null);
  const [trades, setTrades] = useState<WatchTradeRecord[] | null>(null);
  const [preview, setPreview] = useState<WatchRulePreviewResult | null>(null);
  const [loadingTabs, setLoadingTabs] = useState<Partial<Record<DetailTab, boolean>>>({});
  const [saving, setSaving] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  const watchIdRef = useRef(detail?.watch_id);

  const terminal = detail ? terminalWatch(detail) : false;
  const systemCode = draft?.trading_system_code || detail?.trading_system_code || detail?.trading_system || "";
  const systemOptions = useMemo(() => props.systems.filter((item) => item.enabled !== false), [props.systems]);

  useEffect(() => {
    watchIdRef.current = detail?.watch_id;
    setTab("kline");
    setEditing(false);
    setDraft(detail ? createDraft(detail) : null);
    setKline(null);
    setSignals(null);
    setTrades(null);
    setPreview(null);
    setParams([]);
    setLoadingTabs({});
  }, [detail?.watch_id]);

  useEffect(() => {
    if (!detail || !systemCode) return;
    const watchId = detail.watch_id;
    apiGet<TradingSystemParamDefinition[]>(`/h5/trading-systems/${systemCode}/params`)
      .then((rows) => {
        if (watchIdRef.current === watchId) setParams(rows || []);
      })
      .catch(() => {
        if (watchIdRef.current === watchId) setParams([]);
      });
  }, [detail?.watch_id, systemCode]);

  useEffect(() => {
    if (!detail) return;
    const watchId = detail.watch_id;
    const setTabLoading = (key: DetailTab, loading: boolean) => {
      if (watchIdRef.current !== watchId) return;
      setLoadingTabs((current) => ({ ...current, [key]: loading }));
    };
    if (tab === "kline" && kline === null) {
      setTabLoading("kline", true);
      apiGet<KlineBar[]>(`/h5/market/stocks/${encodeURIComponent(detail.stock_code)}/kline-daily?limit=100`)
        .then((rows) => {
          if (watchIdRef.current === watchId) setKline(rows || []);
        })
        .catch(() => {
          if (watchIdRef.current === watchId) setKline([]);
        })
        .finally(() => setTabLoading("kline", false));
    }
    if (tab === "signals" && signals === null) {
      setTabLoading("signals", true);
      apiGet<WatchSignalRecord[]>(`/h5/watch-pool/${detail.watch_id}/signals`)
        .then((rows) => {
          if (watchIdRef.current === watchId) setSignals(rows || []);
        })
        .catch(() => {
          if (watchIdRef.current === watchId) setSignals([]);
        })
        .finally(() => setTabLoading("signals", false));
    }
    if (tab === "trades" && trades === null) {
      setTabLoading("trades", true);
      apiGet<WatchTradeRecord[]>(`/h5/watch-pool/${detail.watch_id}/trade-records`)
        .then((rows) => {
          if (watchIdRef.current === watchId) setTrades(rows || []);
        })
        .catch(() => {
          if (watchIdRef.current === watchId) setTrades([]);
        })
        .finally(() => setTabLoading("trades", false));
    }
  }, [detail, tab, kline, signals, trades]);

  if (!detail) return null;

  const subtitle = compactParts([
    detail.sector_name,
    formatDate(detail.entry_date || detail.created_at),
    tradingSystemLabel(detail.trading_system_code || detail.trading_system, detail.trading_system_name),
    statusLabel(detail.status, detail.status_name),
  ]);

  function changeSystem(code: string) {
    if (!draft) return;
    const nextParams: Record<string, unknown> = {};
    for (const key of ["key_observe_price", "auto_remove_price", "invalid_condition"]) {
      const value = draft.system_params_json[key];
      if (value !== undefined && value !== "") nextParams[key] = value;
    }
    setDraft({ ...draft, trading_system: code, trading_system_code: code, system_params_json: nextParams });
  }

  async function saveEdit() {
    if (!draft) return;
    if (!draft.adjust_reason.trim()) {
      Toast.show({ content: "请填写调整原因" });
      return;
    }
    const missing = params.find((item) => item.required && !String(draft.system_params_json[item.param_key] ?? "").trim());
    if (missing) {
      Toast.show({ content: `请填写${missing.param_name}` });
      return;
    }
    setSaving(true);
    try {
      const booleanKeys = new Set(params.filter((item) => item.param_type === "boolean").map((item) => item.param_key));
      const systemParams = Object.fromEntries(Object.entries(draft.system_params_json).map(([key, value]) => [
        key,
        booleanKeys.has(key) ? value === true || value === "true" : value,
      ]));
      const updated = await apiPut<WatchDetail>(`/h5/watch-pool/${detail.watch_id}`, {
        trading_system_code: draft.trading_system_code,
        trading_system: draft.trading_system,
        system_params_json: systemParams,
        entry_reason: draft.entry_reason,
        key_observe_price: draft.key_observe_price ? Number(draft.key_observe_price) : null,
        auto_remove_price: draft.auto_remove_price ? Number(draft.auto_remove_price) : null,
        invalid_condition: draft.invalid_condition,
        risk_tags: draft.risk_tags,
        user_remark: draft.user_remark,
        adjust_reason: draft.adjust_reason,
      });
      Toast.show({ content: "观察参数已调整" });
      setEditing(false);
      props.onSaved({ ...detail, ...updated, active_trade: detail.active_trade });
      props.onRefresh();
    } catch (error) {
      Toast.show({ content: error instanceof Error ? error.message : "保存失败，请重试" });
    } finally {
      setSaving(false);
    }
  }

  async function runPreview() {
    setPreviewing(true);
    try {
      const result = await apiPost<WatchRulePreviewResult>(`/h5/watch-pool/${detail.watch_id}/rule-preview`);
      setPreview(result);
      setTab("detail");
    } catch (error) {
      Toast.show({ content: error instanceof Error ? error.message : "规则试算失败" });
    } finally {
      setPreviewing(false);
    }
  }

  const tabs: Array<{ key: DetailTab; label: string }> = [
    { key: "kline", label: "K线" },
    { key: "detail", label: "详情" },
    { key: "signals", label: "信号记录" },
    { key: "trades", label: "交易记录" },
  ];

  return (
    <Popup visible onMaskClick={props.onClose} bodyClassName="watch-detail-drawer">
      <div className="watch-detail-drawer__inner">
        {editing && draft ? (
          <WatchEditForm
            detail={detail}
            draft={draft}
            systems={systemOptions}
            params={params}
            saving={saving}
            onChange={setDraft}
            onSystemChange={changeSystem}
            onSave={saveEdit}
            onCancel={() => setEditing(false)}
          />
        ) : (
          <>
            <header className="watch-detail-header">
              <div>
                <h3>
                  {detail.stock_name}（{formatPrice(detail.latest_price)}，
                  <span className={`watch-overview-item__change--${changePctTone(detail.change_pct)}`}>{formatChangePct(detail.change_pct)}</span>）
                </h3>
                <p>{subtitle}</p>
              </div>
              {toXueqiuUrl(detail.stock_code) && (
                <button className="watch-detail-header__xueqiu" type="button" title="雪球" onClick={() => window.open(toXueqiuUrl(detail.stock_code), "_blank")}>↗</button>
              )}
            </header>

            <nav className="watch-detail-tabs">
              {tabs.map((item) => (
                <button type="button" className={tab === item.key ? "is-active" : ""} key={item.key} onClick={() => setTab(item.key)}>
                  {item.label}
                </button>
              ))}
            </nav>

            <div className="watch-detail-content">
              {tab === "kline" && (
                <div className="watch-detail-kline">
                  <WatchKlineTab detail={detail} data={kline || []} loading={Boolean(loadingTabs.kline)} />
                </div>
              )}
              {tab === "detail" && (
                <div className="watch-detail-stack">
                  <WatchInfoTab
                    detail={detail}
                    paramDefinitions={params}
                    terminal={terminal}
                    onToggleMonitor={() => props.onToggleMonitor(detail)}
                    onMarkInvalid={() => props.onMarkInvalid(detail)}
                    onRemove={() => props.onRemove(detail)}
                    onBlacklist={() => props.onBlacklist(detail)}
                  />
                  {preview && <WatchRulePreview preview={preview} />}
                </div>
              )}
              {tab === "signals" && (
                <WatchSignalHistoryTab
                  records={signals}
                  loading={Boolean(loadingTabs.signals)}
                  onConfirmBuy={props.onConfirmBuy}
                  onAbandon={props.onAbandonSignal}
                />
              )}
              {tab === "trades" && <WatchTradeHistoryTab records={trades} loading={Boolean(loadingTabs.trades)} onConfirmSell={props.onConfirmSell} />}
            </div>

            <footer className="watch-detail-footer">
              {!terminal && <Button block fill="outline" onClick={() => setEditing(true)}>编辑</Button>}
              {!terminal && <Button block fill="outline" loading={previewing} onClick={runPreview}>试算</Button>}
              <Button block fill="outline" onClick={props.onClose}>关闭</Button>
            </footer>
          </>
        )}
      </div>
    </Popup>
  );
}
