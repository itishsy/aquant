import type { WatchCardTone } from "./types";

export const WATCH_STATUS_LABELS: Record<string, string> = {
  watching: "观察中",
  signal_generated: "已出信号",
  waiting_buy_point: "等待买点",
  buy_pending_confirm: "买入待确认",
  trading: "交易中",
  sell_signal_pending: "卖出待处理",
  sell_delayed: "卖出延后",
  sold: "已卖出",
  pending_review: "待复盘",
  archived: "已归档",
  invalid: "已失效",
  blacklist: "黑名单",
  removed: "已剔除",
};

export const TRADING_SYSTEM_LABELS: Record<string, string> = {
  platform_breakout: "平台突破",
  limit_relay: "涨停接力",
  oversold_rebound: "超跌反弹",
  breakout: "突破",
  uptrend: "趋势",
  relay: "接力",
  rebound: "反弹",
};

export const WATCH_CARD_TONE_CLASS: Record<WatchCardTone, string> = {
  trading: "watch-overview-item--trading",
  today_signal: "watch-overview-item--today-signal",
  watching: "watch-overview-item--watching",
  terminal: "watch-overview-item--terminal",
};
