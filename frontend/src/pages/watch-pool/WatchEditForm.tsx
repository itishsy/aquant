import { Button, Input, Selector, TextArea } from "antd-mobile";

import type { TradingSystemDefinition, TradingSystemParamDefinition, WatchDetail } from "./types";

export type WatchEditDraft = {
  trading_system: string;
  trading_system_code: string;
  system_params_json: Record<string, unknown>;
  entry_reason: string;
  key_observe_price: string;
  auto_remove_price: string;
  invalid_condition: string;
  risk_tags: string[];
  user_remark: string;
  adjust_reason: string;
};

const RISK_OPTIONS = [
  { label: "高位", value: "high_position" },
  { label: "封板弱", value: "weak_seal" },
  { label: "放量异常", value: "abnormal_volume" },
  { label: "板块转弱", value: "sector_weak" },
  { label: "跌破支撑", value: "break_support" },
];

type Props = {
  detail: WatchDetail;
  draft: WatchEditDraft;
  systems: TradingSystemDefinition[];
  params: TradingSystemParamDefinition[];
  saving: boolean;
  onChange: (draft: WatchEditDraft) => void;
  onSystemChange: (systemCode: string) => void;
  onSave: () => void;
  onCancel: () => void;
};

export function WatchEditForm(props: Props) {
  const { draft } = props;
  function update(key: keyof WatchEditDraft, value: unknown) {
    props.onChange({ ...draft, [key]: value });
  }
  function updateParam(key: string, value: unknown) {
    const next = { ...draft.system_params_json, [key]: value };
    props.onChange({
      ...draft,
      system_params_json: next,
      key_observe_price: key === "key_observe_price" ? String(value) : draft.key_observe_price,
      auto_remove_price: key === "auto_remove_price" ? String(value) : draft.auto_remove_price,
      invalid_condition: key === "invalid_condition" ? String(value) : draft.invalid_condition,
    });
  }

  return (
    <div className="watch-detail-stack">
      <div>
        <h3 className="watch-detail-edit-title">调整观察参数</h3>
        <p className="watch-detail-edit-subtitle">{props.detail.stock_name} {props.detail.stock_code}</p>
      </div>
      <section className="watch-detail-section">
        <h4>交易体系</h4>
        <Selector
          options={props.systems.map((item) => ({ label: item.system_name, value: item.system_code }))}
          value={[draft.trading_system_code]}
          onChange={(values) => props.onSystemChange(String(values[0] || ""))}
        />
      </section>
      <section className="watch-detail-section">
        <h4>交易体系参数</h4>
        <div className="watch-detail-stack watch-detail-stack--compact">
          {props.params.length ? props.params.map((param) => {
            const value = String(draft.system_params_json[param.param_key] ?? "");
            return (
              <label className="watch-edit-field" key={param.param_key}>
                <span>{param.param_name}{param.required ? " *" : ""}</span>
                {param.param_type === "text" ? (
                  <TextArea value={value} rows={2} onChange={(next) => updateParam(param.param_key, next)} />
                ) : param.param_type === "boolean" ? (
                  <Selector options={[{ label: "是", value: "true" }, { label: "否", value: "false" }]} value={[value || "false"]} onChange={(next) => updateParam(param.param_key, next[0])} />
                ) : (
                  <Input type={param.param_type === "number" ? "number" : "text"} value={value} onChange={(next) => updateParam(param.param_key, next)} />
                )}
              </label>
            );
          }) : <div className="watch-detail-muted">当前体系暂无参数定义</div>}
        </div>
      </section>
      <section className="watch-detail-section">
        <h4>观察说明</h4>
        <div className="watch-detail-stack watch-detail-stack--compact">
          <label className="watch-edit-field"><span>入选理由</span><TextArea value={draft.entry_reason} rows={2} onChange={(value) => update("entry_reason", value)} /></label>
          <label className="watch-edit-field"><span>失效条件</span><TextArea value={draft.invalid_condition} rows={2} onChange={(value) => updateParam("invalid_condition", value)} /></label>
          <label className="watch-edit-field"><span>风险标签</span><Selector multiple options={RISK_OPTIONS} value={draft.risk_tags} onChange={(value) => update("risk_tags", value as string[])} /></label>
          <label className="watch-edit-field"><span>用户备注</span><TextArea value={draft.user_remark} rows={2} onChange={(value) => update("user_remark", value)} /></label>
          <label className="watch-edit-field"><span>本次调整原因 *</span><TextArea value={draft.adjust_reason} rows={2} onChange={(value) => update("adjust_reason", value)} /></label>
        </div>
      </section>
      <div className="watch-detail-actions">
        <Button block onClick={props.onCancel}>取消</Button>
        <Button block color="primary" loading={props.saving} onClick={props.onSave}>保存</Button>
      </div>
    </div>
  );
}
