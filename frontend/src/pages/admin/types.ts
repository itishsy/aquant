export type TradingSystem = {
  system_id: number;
  system_code: string;
  system_name: string;
  description: string;
  lifecycle_desc: string;
  enabled: boolean;
  sort_order: number;
};

export type TradingParam = {
  param_id: number;
  system_code: string;
  param_key: string;
  param_name: string;
  param_type: string;
  required: boolean;
  default_value?: string | null;
  description: string;
  sort_order: number;
  enabled: boolean;
};

export type TradingRule = {
  rule_id: number;
  rule_code: string;
  rule_name: string;
  rule_type: string;
  timeframe: string;
  executor_key: string;
  description: string;
  enabled: boolean;
};

export type TradingRuleBinding = {
  binding_id: number;
  system_code: string;
  rule_code: string;
  stage: string;
  required: boolean;
  logic_group: string;
  logic_operator: string;
  enabled: boolean;
  sort_order: number;
  config_json?: Record<string, unknown>;
  rule?: TradingRule | null;
};

