export type WatchCardTone = "trading" | "today_signal" | "watching" | "terminal";

export type WatchDisplayGroup = WatchCardTone;

export type DynamicFields = Record<string, unknown>;

export type WatchLatestSignal = {
  signal_id: number;
  signal_type: string;
  signal_status: string;
  rule_code?: string | null;
  rule_name?: string | null;
  trigger_time?: string | null;
};

export type WatchActiveTrade = {
  trade_id: number;
  trade_status: string;
  target_price?: number | null;
  stop_loss_price?: number | null;
  current_stage?: string | null;
  remaining_amount?: number | null;
};

export type WatchOverviewSummary = {
  total: number;
  active_total: number;
  terminal_total: number;
  today_signal_count: number;
  today_trade_count: number;
};

export type WatchOverviewItem = {
  watch_id: number;
  stock_code: string;
  stock_name: string;
  latest_price?: number | null;
  change_pct?: number | null;
  sector_name?: string | null;
  entry_date?: string | null;
  entry_source?: string | null;
  trading_system_code?: string | null;
  trading_system_name?: string | null;
  status?: string | null;
  status_name?: string | null;
  system_stage?: string | null;
  display_group: WatchDisplayGroup;
  sort_priority: number;
  sort_time?: string | null;
  card_tone: WatchCardTone;
  latest_signal?: WatchLatestSignal | null;
  active_trade?: WatchActiveTrade | null;
};

export type WatchOverviewResponse = {
  summary: WatchOverviewSummary;
  items: WatchOverviewItem[];
};

export type WatchDetail = WatchOverviewItem & {
  active?: boolean;
  trading_system?: string | null;
  labels?: string[];
  entry_reason?: string | null;
  system_params_json: DynamicFields;
  active_rule_codes_json?: string[];
  next_action?: string | null;
  key_observe_price?: number | null;
  auto_remove_price?: number | null;
  invalid_condition?: string | null;
  risk_tags?: string[];
  signal_enabled?: boolean;
  monitor_enabled?: boolean;
  user_remark?: string | null;
  remark?: string | null;
  reason?: string | null;
  created_at?: string | null;
  removed_at?: string | null;
};

export type WatchSignalRecord = {
  signal_id: number;
  watch_id?: number | null;
  stock_code: string;
  stock_name: string;
  signal_type: string;
  signal_status: string;
  rule_code?: string | null;
  rule_name?: string | null;
  rule_display_name?: string | null;
  rule_timeframe?: string | null;
  rule_type?: string | null;
  trigger_time?: string | null;
  trigger_date?: string | null;
  trigger_price?: number | null;
  trigger_reason?: string | null;
  risk_desc?: string | null;
  stop_loss_price?: number | null;
  target_price?: number | null;
  related_trade_id?: number | null;
  notification_sent?: boolean;
  notification_error?: string | null;
  snapshot_json?: DynamicFields;
};

export type WatchTradeRecord = {
  record_type: "execution" | "trade_summary";
  record_time?: string | null;
  execution_id?: number | null;
  trade_id: number;
  execution_type: string;
  execution_type_name: string;
  execution_reason?: string | null;
  execution_time?: string | null;
  execution_price?: number | null;
  execution_amount?: number | null;
  pnl_amount?: number | null;
  pnl_ratio?: number | null;
  trade_status: string;
};

export type RulePreviewRule = {
  rule_code: string;
  rule_name?: string | null;
  rule_display_name?: string | null;
  rule_type?: string | null;
  timeframe?: string | null;
  required?: boolean;
  logic_group?: string | null;
  triggered: boolean;
  reason?: string | null;
};

export type WatchRulePreviewResult = {
  required_passed: boolean;
  buy_signal_triggered: boolean;
  would_generate_signal: boolean;
  rules: RulePreviewRule[];
};

export type TradingSystemDefinition = {
  system_code: string;
  system_name: string;
  enabled: boolean;
  description?: string | null;
  lifecycle_desc?: string | null;
  sort_order?: number;
};

export type TradingSystemParamDefinition = {
  param_id: number;
  system_code: string;
  param_key: string;
  param_name: string;
  param_type: "number" | "text" | "select" | "boolean";
  required: boolean;
  default_value?: string | null;
  description?: string | null;
  sort_order: number;
  enabled?: boolean;
};
