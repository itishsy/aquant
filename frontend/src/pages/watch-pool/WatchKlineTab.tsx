import { useMemo } from "react";

import { KlineChart, type KlineBar, type KlineLevelMarker } from "../../components/StockDetailPopup";
import type { WatchDetail } from "./types";

type Props = {
  detail: WatchDetail;
  data: KlineBar[];
  loading: boolean;
};

function validPrice(value: unknown): number | null {
  if (value === undefined || value === null || value === "") return null;
  const price = Number(value);
  return Number.isFinite(price) && price > 0 ? price : null;
}

function firstPrice(...values: unknown[]): number | null {
  for (const value of values) {
    const price = validPrice(value);
    if (price !== null) return price;
  }
  return null;
}

export function buildWatchKlineLevels(detail: WatchDetail): KlineLevelMarker[] {
  const params = detail.system_params_json || {};
  const support = firstPrice(
    params.platform_support_price,
    detail.active_trade?.stop_loss_price,
    detail.key_observe_price,
  );
  const target = firstPrice(
    detail.active_trade?.target_price,
    params.platform_upper_price,
  );

  if (support !== null && target !== null && support === target) {
    return [{ name: "支撑位 / 目标位", price: support, color: "#3b82a0" }];
  }

  const levels: KlineLevelMarker[] = [];
  if (support !== null) levels.push({ name: "支撑位", price: support, color: "#26968f" });
  if (target !== null) levels.push({ name: "目标位", price: target, color: "#d97732" });
  return levels;
}

export function WatchKlineTab({ detail, data, loading }: Props) {
  const levels = useMemo(() => buildWatchKlineLevels(detail), [
    detail.watch_id,
    detail.key_observe_price,
    detail.active_trade?.stop_loss_price,
    detail.active_trade?.target_price,
    detail.system_params_json,
  ]);

  return <KlineChart data={data} loading={loading} levels={levels} />;
}
