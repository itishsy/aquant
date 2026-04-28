export const TRADE_DATES = ["2026-04-24", "2026-04-25", "2026-04-26"] as const;

export function shiftTradeDate(current: string, step: -1 | 1) {
  const index = TRADE_DATES.indexOf(current as (typeof TRADE_DATES)[number]);
  if (index === -1) {
    return TRADE_DATES[0];
  }
  const nextIndex = Math.min(Math.max(index + step, 0), TRADE_DATES.length - 1);
  return TRADE_DATES[nextIndex];
}
