import { useState } from "react";
import { Button, Popup, Toast } from "antd-mobile";
import { apiPost, apiPut } from "../../../api/client";

export function RuleLibraryPanel({ rules, executors, onSaved }: { rules: any[]; executors: string[]; onSaved: () => void }) {
  const [form, setForm] = useState({ rule_code: "", rule_name: "", rule_type: "buy_signal", timeframe: "15m", executor_key: "", description: "", enabled: true, config_json: {} as any });
  const [editing, setEditing] = useState<any>(null);
  const [submitting, setSubmitting] = useState(false);
  const [filter, setFilter] = useState({ keyword: "", rule_type: "", enabled: "" });
  const [showForm, setShowForm] = useState(false);

  const registered = new Set(executors);
  const filtered = rules.filter((r) => {
    if (filter.enabled === "enabled" && !r.enabled) return false;
    if (filter.enabled === "disabled" && r.enabled) return false;
    if (filter.rule_type && r.rule_type !== filter.rule_type) return false;
    if (filter.keyword) {
      const kw = filter.keyword.toLowerCase();
      return (r.rule_name || "").includes(kw) || (r.rule_code || "").includes(kw) || (r.executor_key || "").includes(kw);
    }
    return true;
  });

  const RULE_TYPE_LABELS: Record<string, string> = { buy_signal: "买点信号", sell_signal: "卖点信号", stop_loss: "止损信号", filter: "过滤条件", confirm: "确认条件", observe_risk: "观察风险", invalid_signal: "观察失效", remove_signal: "自动剔除" };

  function resetForm() { setForm({ rule_code: "", rule_name: "", rule_type: "buy_signal", timeframe: "15m", executor_key: "", description: "", enabled: true, config_json: {} }); setEditing(null); setShowForm(true); }
  function editRule(r: any) { setForm({ rule_code: r.rule_code, rule_name: r.rule_name, rule_type: r.rule_type, timeframe: r.timeframe, executor_key: r.executor_key, description: r.description || "", enabled: r.enabled, config_json: r.config_json || {} }); setEditing(r); setShowForm(true); }

  async function save() {
    if (!form.rule_code || !form.rule_name || !form.executor_key) { Toast.show({ content: "请填写规则编码、名称和执行器键" }); return; }
    setSubmitting(true);
    try {
      if (editing) {
        await apiPut(`/admin/trading-rules/${editing.rule_code}`, form);
      } else {
        await apiPost("/admin/trading-rules", form);
      }
      Toast.show({ content: "规则已保存" }); setShowForm(false); onSaved();
    } catch { Toast.show({ content: "保存失败" }); }
    finally { setSubmitting(false); }
  }

  return (
    <div style={{ display: "grid", gap: 12 }}>
      <div style={{ borderRadius: 14, background: "#fff", padding: 14 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
          <h3 style={{ margin: 0, fontSize: 15 }}>规则库 ({filtered.length}/{rules.length})</h3>
          <Button size="mini" color="primary" onClick={resetForm}>+ 新增</Button>
        </div>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 10 }}>
          <input placeholder="搜索" value={filter.keyword} onChange={(e) => setFilter({ ...filter, keyword: e.target.value })} style={{ flex: 1, minWidth: 80, padding: "6px 10px", borderRadius: 10, border: "1px solid #ddd", fontSize: 12 }} />
          <select value={filter.rule_type} onChange={(e) => setFilter({ ...filter, rule_type: e.target.value })} style={{ padding: "6px 8px", borderRadius: 10, border: "1px solid #ddd", fontSize: 12 }}>
            <option value="">全部类型</option>
            {Object.entries(RULE_TYPE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
          <select value={filter.enabled} onChange={(e) => setFilter({ ...filter, enabled: e.target.value })} style={{ padding: "6px 8px", borderRadius: 10, border: "1px solid #ddd", fontSize: 12 }}>
            <option value="">全部状态</option><option value="enabled">已启用</option><option value="disabled">已停用</option>
          </select>
        </div>
        {filtered.map((r) => (
          <div key={r.rule_code} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 0", borderBottom: "1px solid #f0f0f0", fontSize: 12 }}>
            <div style={{ minWidth: 0 }}>
              <strong style={{ fontSize: 13 }}>{r.rule_name}</strong>
              <span style={{ color: "#888", marginLeft: 6 }}>{r.rule_code}</span>
              <div style={{ color: "#888", marginTop: 2 }}>
                <span style={{ display: "inline-block", padding: "2px 6px", borderRadius: 6, background: "#eef2ff", color: "#4b63ee", fontSize: 11, fontWeight: 700 }}>{RULE_TYPE_LABELS[r.rule_type] || r.rule_type}</span>
                <span style={{ marginLeft: 4 }}>{r.timeframe} · {r.executor_key}</span>
                {!registered.has(r.executor_key) && <span style={{ color: "#b54708", marginLeft: 4 }}>【无执行器】</span>}
              </div>
            </div>
            <Button size="mini" fill="outline" onClick={() => editRule(r)}>编辑</Button>
          </div>
        ))}
      </div>
      <Popup
        visible={showForm}
        onMaskClick={() => setShowForm(false)}
        bodyStyle={{
          borderTopLeftRadius: 18,
          borderTopRightRadius: 18,
          maxHeight: "82vh",
          overflowY: "auto",
          padding: "14px max(14px, env(safe-area-inset-right)) max(18px, env(safe-area-inset-bottom)) max(14px, env(safe-area-inset-left))",
        }}
      >
        <div style={{ display: "grid", gap: 10 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 }}>
            <h3 style={{ margin: 0, fontSize: 15 }}>{editing ? "编辑规则" : "新增规则"}</h3>
            <Button size="mini" fill="none" onClick={() => setShowForm(false)}>关闭</Button>
          </div>
          <div><div style={{ color: "#5b6d8a", fontSize: 11, fontWeight: 700, marginBottom: 2 }}>rule_code</div><input value={form.rule_code} onChange={(e) => setForm({ ...form, rule_code: e.target.value })} disabled={!!editing} style={{ width: "100%", padding: "6px 10px", borderRadius: 10, border: "1px solid #ddd", fontSize: 12 }} /></div>
          <div><div style={{ color: "#5b6d8a", fontSize: 11, fontWeight: 700, marginBottom: 2 }}>rule_name</div><input value={form.rule_name} onChange={(e) => setForm({ ...form, rule_name: e.target.value })} style={{ width: "100%", padding: "6px 10px", borderRadius: 10, border: "1px solid #ddd", fontSize: 12 }} /></div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
            <div><div style={{ color: "#5b6d8a", fontSize: 11, fontWeight: 700, marginBottom: 2 }}>rule_type</div><select value={form.rule_type} onChange={(e) => setForm({ ...form, rule_type: e.target.value })} style={{ width: "100%", padding: "6px 8px", borderRadius: 10, border: "1px solid #ddd", fontSize: 12 }}>{Object.entries(RULE_TYPE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></div>
            <div><div style={{ color: "#5b6d8a", fontSize: 11, fontWeight: 700, marginBottom: 2 }}>timeframe</div><select value={form.timeframe} onChange={(e) => setForm({ ...form, timeframe: e.target.value })} style={{ width: "100%", padding: "6px 8px", borderRadius: 10, border: "1px solid #ddd", fontSize: 12 }}><option value="5m">5m</option><option value="15m">15m</option><option value="30m">30m</option><option value="daily">daily</option></select></div>
          </div>
          <div><div style={{ color: "#5b6d8a", fontSize: 11, fontWeight: 700, marginBottom: 2 }}>executor_key</div>
            <select value={form.executor_key} onChange={(e) => setForm({ ...form, executor_key: e.target.value })} style={{ width: "100%", padding: "6px 8px", borderRadius: 10, border: "1px solid #ddd", fontSize: 12 }}>
              <option value="">选择执行器</option>
              {executors.map((ex: string) => <option key={ex} value={ex}>{ex}</option>)}
            </select></div>
          <div><div style={{ color: "#5b6d8a", fontSize: 11, fontWeight: 700, marginBottom: 2 }}>description</div><textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} rows={2} style={{ width: "100%", padding: "6px 10px", borderRadius: 10, border: "1px solid #ddd", fontSize: 12 }} /></div>
          <div style={{ borderRadius: 12, background: "#f8fafc", padding: 10 }}>
            <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 4 }}>高级配置 JSON</div>
            <textarea
              value={JSON.stringify(form.config_json || {}, null, 2)}
              onChange={(e) => { try { setForm({ ...form, config_json: JSON.parse(e.target.value) }); } catch {} }}
              rows={4}
              style={{ width: "100%", padding: "6px 10px", borderRadius: 10, border: "1px solid #ddd", fontSize: 11, fontFamily: "monospace" }}
            />
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <Button block color="primary" size="small" loading={submitting} onClick={save}>保存</Button>
            <Button block fill="none" size="small" onClick={() => setShowForm(false)}>取消</Button>
          </div>
        </div>
      </Popup>
    </div>
  );
}
