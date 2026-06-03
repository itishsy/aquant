import { useEffect, useState } from "react";
import { Button, SpinLoading, Toast } from "antd-mobile";
import { apiPost, apiPut } from "../../../api/client";
import type { TradingParam, TradingRule, TradingRuleBinding, TradingSystem } from "../types";
import { LOGIC_OPERATORS, PARAM_TYPES, SYSTEM_STAGES } from "../constants";
import { blankBindingForm, blankParamForm, blankRuleForm, blankSystemForm, normalizeBindingForm, normalizeParamForm, normalizeRuleForm, normalizeSystemForm } from "../utils";
import { CheckField, EditCard, SimpleRows, TextField, SelectField, WarningText } from "../components/common";

export function TradingSystemPanelEditor({
  systems,
  selectedCode,
  selectedSystem,
  params,
  bindings,
  loading,
  onSelect,
  rules,
  executors,
  onSaved,
  onSystemUpdated,
}: {
  systems: TradingSystem[];
  selectedCode: string;
  selectedSystem: TradingSystem | null;
  params: TradingParam[];
  bindings: TradingRuleBinding[];
  loading: boolean;
  onSelect: (code: string) => void;
  rules: TradingRule[];
  executors: string[];
  onSaved: () => void;
  onSystemUpdated?: (system: TradingSystem) => void;
}) {
  const registeredExecutors = new Set(executors);
  const [saving, setSaving] = useState(false);
  const [systemForm, setSystemForm] = useState<any>(null);
  const [ruleForm, setRuleForm] = useState<any>(blankRuleForm());
  const [paramForm, setParamForm] = useState<any>(blankParamForm());
  const [bindingForm, setBindingForm] = useState<any>(blankBindingForm(rules[0]?.rule_code || ""));

  useEffect(() => {
    if (selectedSystem) {
      setSystemForm({ ...selectedSystem });
    } else {
      setSystemForm(blankSystemForm());
    }
  }, [selectedSystem?.system_code]);

  useEffect(() => {
    setBindingForm((prev: any) => ({ ...prev, rule_code: prev.rule_code || rules[0]?.rule_code || "" }));
  }, [rules.length]);

  const selectedBindingRule = rules.find((item) => item.rule_code === bindingForm.rule_code);
  const ruleExecutorMissing = !!ruleForm.executor_key && !registeredExecutors.has(ruleForm.executor_key);
  const bindingExecutorMissing = !!selectedBindingRule?.executor_key && !registeredExecutors.has(selectedBindingRule.executor_key);

  async function saveWithToast(action: () => Promise<void>) {
    setSaving(true);
    try {
      await action();
      Toast.show({ content: "已保存" });
      await onSaved();
    } catch (err: any) {
      Toast.show({ content: err?.message || "保存失败" });
    } finally {
      setSaving(false);
    }
  }

  async function saveSystem() {
    if (!systemForm?.system_code || !systemForm?.system_name) {
      Toast.show({ content: "请填写体系编码和名称" });
      return;
    }
    setSaving(true);
    try {
      const payload = normalizeSystemForm(systemForm);
      let data: TradingSystem;
      if (systemForm.system_id) {
        data = await apiPut<TradingSystem>(`/admin/trading-systems/${systemForm.system_code}`, payload);
      } else {
        data = await apiPost<TradingSystem>(`/admin/trading-systems`, payload);
        onSelect(systemForm.system_code);
      }
      Toast.show({ content: "已保存" });
      setSystemForm({ ...data });
      if (onSystemUpdated) onSystemUpdated(data);
    } catch (err: any) {
      Toast.show({ content: err?.message || "保存失败" });
    } finally {
      setSaving(false);
    }
  }

  async function saveRule() {
    if (!ruleForm.rule_code || !ruleForm.rule_name || !ruleForm.executor_key) {
      Toast.show({ content: "请填写规则编码、名称和执行器" });
      return;
    }
    await saveWithToast(async () => {
      const payload = normalizeRuleForm(ruleForm);
      if (ruleForm.rule_id) {
        await apiPut(`/admin/trading-rules/${ruleForm.rule_code}`, payload);
      } else {
        await apiPost(`/admin/trading-rules`, payload);
      }
      setRuleForm(blankRuleForm());
    });
  }

  async function saveParam() {
    if (!selectedCode) {
      Toast.show({ content: "请先选择交易体系" });
      return;
    }
    if (!paramForm.param_key || !paramForm.param_name) {
      Toast.show({ content: "请填写参数编码和名称" });
      return;
    }
    await saveWithToast(async () => {
      const payload = normalizeParamForm(paramForm);
      if (paramForm.param_id) {
        await apiPut(`/admin/trading-params/${paramForm.param_id}`, payload);
      } else {
        await apiPost(`/admin/trading-systems/${selectedCode}/params`, payload);
      }
      setParamForm(blankParamForm());
    });
  }

  async function saveBinding() {
    if (!selectedCode) {
      Toast.show({ content: "请先选择交易体系" });
      return;
    }
    if (!bindingForm.rule_code || !bindingForm.stage) {
      Toast.show({ content: "请选择规则和阶段" });
      return;
    }
    await saveWithToast(async () => {
      const payload = normalizeBindingForm(bindingForm);
      if (bindingForm.binding_id) {
        await apiPut(`/admin/trading-rule-bindings/${bindingForm.binding_id}`, payload);
      } else {
        await apiPost(`/admin/trading-systems/${selectedCode}/rules`, payload);
      }
      setBindingForm(blankBindingForm(rules[0]?.rule_code || ""));
    });
  }

  return (
    <section style={{ display: "grid", gap: 14 }}>
      <div style={{ background: "#fff", borderRadius: 14, padding: 14, display: "grid", gap: 10 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
          <h3 style={{ margin: 0, color: "#1d2d50" }}>交易体系管理</h3>
          <Button size="mini" onClick={() => { setSystemForm(blankSystemForm()); onSelect(""); }}>新增</Button>
        </div>
        <div style={{ display: "flex", gap: 8, overflowX: "auto", paddingBottom: 2 }}>
          {systems.length ? systems.map((system) => (
            <button
              key={system.system_code}
              onClick={() => onSelect(system.system_code)}
              style={{
                border: 0,
                borderRadius: 999,
                padding: "10px 16px",
                textAlign: "left",
                background: selectedCode === system.system_code ? "linear-gradient(135deg, #5570ff, #4052d2)" : "#f4f6fb",
                color: selectedCode === system.system_code ? "#fff" : "#344054",
                cursor: "pointer",
                minWidth: 150,
                flex: "0 0 auto",
              }}
            >
              <strong style={{ display: "block", fontSize: 14, lineHeight: 1.2, whiteSpace: "nowrap" }}>{system.system_name}</strong>
              <span style={{ display: "block", marginTop: 4, fontSize: 12, opacity: 0.78, whiteSpace: "nowrap" }}>{system.system_code}</span>
            </button>
          )) : <div style={{ color: "#98a2b3", fontSize: 13 }}>暂无交易体系</div>}
        </div>
      </div>

      <div style={{ display: "grid", gap: 14 }}>
        {loading && <div style={{ display: "grid", placeItems: "center", minHeight: 120, background: "#fff", borderRadius: 14 }}><SpinLoading /></div>}

        {!loading && (
          <>
            <EditCard title={systemForm?.system_id ? "编辑交易体系" : "新增交易体系"}>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 10 }}>
                <TextField label="体系编码" value={systemForm?.system_code || ""} disabled={!!systemForm?.system_id} onChange={(v) => setSystemForm({ ...systemForm, system_code: v })} />
                <TextField label="体系名称" value={systemForm?.system_name || ""} onChange={(v) => setSystemForm({ ...systemForm, system_name: v })} />
                <TextField label="描述" value={systemForm?.description || ""} onChange={(v) => setSystemForm({ ...systemForm, description: v })} />
                <TextField label="生命周期说明" value={systemForm?.lifecycle_desc || ""} onChange={(v) => setSystemForm({ ...systemForm, lifecycle_desc: v })} />
                <TextField label="排序" value={String(systemForm?.sort_order ?? 0)} onChange={(v) => setSystemForm({ ...systemForm, sort_order: v })} />
                <CheckField label="启用" checked={!!systemForm?.enabled} onChange={(v) => setSystemForm({ ...systemForm, enabled: v })} />
              </div>
              <Button color="primary" size="small" loading={saving} onClick={saveSystem}>保存体系</Button>
            </EditCard>

            {selectedCode && selectedSystem && (
              <>
                <EditCard title="参数定义">
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 10 }}>
                    <TextField label="参数编码" value={paramForm.param_key} disabled={!!paramForm.param_id} onChange={(v) => setParamForm({ ...paramForm, param_key: v })} />
                    <TextField label="参数名称" value={paramForm.param_name} onChange={(v) => setParamForm({ ...paramForm, param_name: v })} />
                    <SelectField label="类型" value={paramForm.param_type} options={PARAM_TYPES} onChange={(v) => setParamForm({ ...paramForm, param_type: v })} />
                    <TextField label="默认值" value={paramForm.default_value || ""} onChange={(v) => setParamForm({ ...paramForm, default_value: v })} />
                    <TextField label="排序" value={String(paramForm.sort_order ?? 0)} onChange={(v) => setParamForm({ ...paramForm, sort_order: v })} />
                    <CheckField label="必填" checked={!!paramForm.required} onChange={(v) => setParamForm({ ...paramForm, required: v })} />
                    <CheckField label="启用" checked={!!paramForm.enabled} onChange={(v) => setParamForm({ ...paramForm, enabled: v })} />
                    <TextField label="说明" value={paramForm.description || ""} onChange={(v) => setParamForm({ ...paramForm, description: v })} />
                  </div>
                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                    <Button color="primary" size="small" loading={saving} onClick={saveParam}>保存参数</Button>
                    <Button size="small" onClick={() => setParamForm(blankParamForm())}>新增参数</Button>
                  </div>
                  <SimpleRows
                    empty="暂无参数定义"
                    rows={params.map((param) => ({
                      key: String(param.param_id),
                      title: `${param.param_name} / ${param.param_key}`,
                      desc: `${param.param_type} / ${param.required ? "必填" : "非必填"} / 排序 ${param.sort_order}`,
                      enabled: param.enabled,
                      onEdit: () => setParamForm({ ...param }),
                    }))}
                  />
                </EditCard>

                <EditCard title="体系规则绑定">
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 10 }}>
                    <SelectField label="规则" value={bindingForm.rule_code} options={rules.map((rule) => rule.rule_code)} onChange={(v) => setBindingForm({ ...bindingForm, rule_code: v })} />
                    <SelectField label="阶段" value={bindingForm.stage} options={SYSTEM_STAGES} onChange={(v) => setBindingForm({ ...bindingForm, stage: v })} />
                    <TextField label="logic_group" value={bindingForm.logic_group || ""} onChange={(v) => setBindingForm({ ...bindingForm, logic_group: v })} />
                    <SelectField label="logic_operator" value={bindingForm.logic_operator} options={LOGIC_OPERATORS} onChange={(v) => setBindingForm({ ...bindingForm, logic_operator: v })} />
                    <TextField label="排序" value={String(bindingForm.sort_order ?? 0)} onChange={(v) => setBindingForm({ ...bindingForm, sort_order: v })} />
                    <CheckField label="required" checked={!!bindingForm.required} onChange={(v) => setBindingForm({ ...bindingForm, required: v })} />
                    <CheckField label="启用" checked={!!bindingForm.enabled} onChange={(v) => setBindingForm({ ...bindingForm, enabled: v })} />
                  </div>
                  {bindingExecutorMissing && <WarningText />}
                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                    <Button color="primary" size="small" loading={saving} onClick={saveBinding}>保存绑定</Button>
                    <Button size="small" onClick={() => setBindingForm(blankBindingForm(rules[0]?.rule_code || ""))}>新增绑定</Button>
                  </div>
                  <SimpleRows
                    empty="暂无规则绑定"
                    rows={bindings.map((binding) => ({
                      key: String(binding.binding_id),
                      title: `${binding.rule?.rule_name || binding.rule_code} / ${binding.stage}`,
                      desc: `${binding.logic_group || "-"} ${binding.logic_operator} / ${binding.required ? "必需" : "可选"} / ${binding.rule?.executor_key || "-"}`,
                      enabled: binding.enabled,
                      warning: !!binding.rule?.executor_key && !registeredExecutors.has(binding.rule.executor_key),
                      onEdit: () => setBindingForm({ ...binding }),
                    }))}
                  />
                </EditCard>
              </>
            )}

          </>
        )}
      </div>
    </section>
  );
}
