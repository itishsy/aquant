import { TRADING_SYSTEM_LABELS, WATCH_STATUS_LABELS } from "./constants";
import type { WatchLatestSignal, WatchOverviewItem } from "./types";

function finiteNumber(value: unknown): number | null {
  if (value === null || value === undefined || value === "") return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

export function compactParts(parts: Array<string | null | undefined>): string {
  return parts.map((part) => part?.trim()).filter(Boolean).join(" | ");
}

export function statusLabel(status?: string | null, providedLabel?: string | null): string {
  return providedLabel || WATCH_STATUS_LABELS[status || ""] || status || "状态未知";
}

export function tradingSystemLabel(code?: string | null, providedName?: string | null): string {
  return providedName || TRADING_SYSTEM_LABELS[code || ""] || code || "";
}

export function formatDate(value?: string | null): string {
  if (!value) return "";
  return value.slice(0, 10);
}

export function formatDateTime(value?: string | null): string {
  if (!value) return "";
  return value.replace("T", " ").slice(0, 16);
}

export function formatPrice(value: unknown): string {
  const number = finiteNumber(value);
  if (number === null) return "-";
  return number.toFixed(2).replace(/\.?0+$/, "");
}

export function formatChangePct(value: unknown): string {
  const number = finiteNumber(value);
  if (number === null) return "-";
  return `${number >= 0 ? "+" : ""}${number.toFixed(2)}%`;
}

export function changePctTone(value: unknown): "up" | "down" | "flat" {
  const number = finiteNumber(value);
  if (number === null || number === 0) return "flat";
  return number > 0 ? "up" : "down";
}

export function overviewMeta(item: WatchOverviewItem): string {
  return compactParts([
    item.sector_name,
    formatDate(item.entry_date),
    tradingSystemLabel(item.trading_system_code, item.trading_system_name),
  ]);
}

export function signalRuleLabel(signal?: WatchLatestSignal | null): string {
  return signal?.rule_name || signal?.rule_code || "";
}

export function latestSignalSummary(signal?: WatchLatestSignal | null): string {
  if (!signal) return "暂无信号记录";
  return compactParts([formatDateTime(signal.trigger_time), signalRuleLabel(signal)]) || "暂无信号记录";
}
