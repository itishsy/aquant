export function taskErrorText(value?: string | null) {
  if (!value) return "-";
  return value.length > 80 ? `${value.slice(0, 80)}...` : value;
}

export function taskTimeText(value?: string | null) {
  if (!value) return "未运行";
  return String(value).replace("T", " ").slice(0, 19);
}

export function taskConfigSummary(config?: Record<string, any>) {
  if (!config || !Object.keys(config).length) return "未配置";
  const parts = [
    config.interval_minutes ? `间隔 ${config.interval_minutes} 分钟` : "",
    config.run_window ? `窗口 ${config.run_window}` : "",
    Array.isArray(config.timeframes) && config.timeframes.length ? `周期 ${config.timeframes.join("/")}` : "",
    config.max_requests_per_run ? `请求上限 ${config.max_requests_per_run}` : "",
    config.max_stocks_per_run ? `股票上限 ${config.max_stocks_per_run}` : "",
    config.only_trade_day ? "仅交易日" : "",
  ].filter(Boolean);
  return parts.length ? parts.join(" · ") : JSON.stringify(config);
}

export function blankSystemForm() {
  return { system_code: "", system_name: "", description: "", lifecycle_desc: "", enabled: true, sort_order: 0 };
}

export function blankRuleForm() {
  return { rule_code: "", rule_name: "", rule_type: "buy_signal", timeframe: "15m", executor_key: "", description: "", enabled: true };
}

export function blankParamForm() {
  return { param_key: "", param_name: "", param_type: "number", required: false, default_value: "", description: "", sort_order: 0, enabled: true };
}

export function blankBindingForm(ruleCode: string) {
  return { rule_code: ruleCode, stage: "observe", required: false, logic_group: "", logic_operator: "AND", enabled: true, sort_order: 0 };
}

export function normalizeSystemForm(form: any) {
  return { ...form, system_code: String(form.system_code || "").trim(), system_name: String(form.system_name || "").trim(), sort_order: Number(form.sort_order || 0), enabled: !!form.enabled };
}

export function normalizeRuleForm(form: any) {
  return { ...form, rule_code: String(form.rule_code || "").trim(), rule_name: String(form.rule_name || "").trim(), executor_key: String(form.executor_key || "").trim(), enabled: !!form.enabled };
}

export function normalizeParamForm(form: any) {
  return { ...form, param_key: String(form.param_key || "").trim(), param_name: String(form.param_name || "").trim(), sort_order: Number(form.sort_order || 0), required: !!form.required, enabled: !!form.enabled };
}

export function normalizeBindingForm(form: any) {
  return { ...form, sort_order: Number(form.sort_order || 0), required: !!form.required, enabled: !!form.enabled };
}

