import { Button, Input } from "antd-mobile";
import type { TradingParam, TradingRuleBinding } from "../types";

export function FormLabel({ text }: { text: string }) {
  return <div style={{ fontSize: 12, color: "#5b6d8a", fontWeight: 700, marginBottom: 2 }}>{text}</div>;
}

export function PlaceholderCard({ label }: { label: string }) {
  return (
    <div style={{ padding: 20, borderRadius: 14, background: "#fff", textAlign: "center" }}>
      <p style={{ color: "#667085", fontSize: 14 }}>{label}已接入后台框架</p>
      <p style={{ color: "#98a2b3", fontSize: 12 }}>后台写操作应继续通过 /api/admin/** 接口并记录操作日志。</p>
    </div>
  );
}


export function StatCard({ label, value }: { label: string; value: any }) {
  return (
    <div style={{ background: "#fff", borderRadius: 14, padding: 16 }}>
      <p style={{ margin: 0, color: "#667085", fontSize: 12 }}>{label}</p>
      <strong style={{ display: "block", marginTop: 8, fontSize: 26, color: "#1d2939" }}>{value}</strong>
    </div>
  );
}

export function TableCard({ rows, empty }: { rows: string[]; empty: string }) {
  return (
    <div style={{ background: "#fff", borderRadius: 14, padding: 14, display: "grid", gap: 8 }}>
      {rows.length ? rows.map((row) => (
        <div key={row} style={{ padding: "9px 10px", borderRadius: 10, background: "#f8fafc", color: "#344054", fontSize: 13 }}>{row}</div>
      )) : <div style={{ color: "#98a2b3", textAlign: "center", padding: 20 }}>{empty}</div>}
    </div>
  );
}


export function ParamRow({ param }: { param: TradingParam }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "minmax(120px, 180px) 1fr", gap: 10, padding: "10px 12px", borderRadius: 10, background: "#f8fafc" }}>
      <div>
        <strong style={{ display: "block", color: "#1d2d50", fontSize: 13 }}>{param.param_name}</strong>
        <span style={{ color: "#667085", fontSize: 12 }}>{param.param_key}</span>
      </div>
      <div style={{ display: "grid", gap: 4 }}>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          <SmallTag>{param.param_type}</SmallTag>
          <SmallTag>{param.required ? "必填" : "非必填"}</SmallTag>
          <SmallTag>{param.enabled ? "启用" : "停用"}</SmallTag>
        </div>
        <span style={{ color: "#667085", fontSize: 12 }}>{param.description || "-"}</span>
      </div>
    </div>
  );
}


export function RuleStageCard({ title, items }: { title: string; items: TradingRuleBinding[] }) {
  return (
    <div style={{ background: "#fff", borderRadius: 14, padding: 14 }}>
      <h3 style={{ margin: "0 0 10px", color: "#1d2d50" }}>{title}</h3>
      <div style={{ display: "grid", gap: 8 }}>
        {items.length ? items.map((binding) => (
          <div key={binding.binding_id} style={{ padding: "10px 12px", borderRadius: 10, background: "#f8fafc" }}>
            <div style={{ display: "flex", justifyContent: "space-between", gap: 10, flexWrap: "wrap" }}>
              <strong style={{ color: "#1d2d50", fontSize: 13 }}>{binding.rule?.rule_name || binding.rule_code}</strong>
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                <SmallTag>{binding.logic_group || "-"}</SmallTag>
                <SmallTag>{binding.logic_operator}</SmallTag>
                <SmallTag>{binding.required ? "必需" : "可选"}</SmallTag>
              </div>
            </div>
            <div style={{ display: "grid", gap: 4, marginTop: 8, color: "#667085", fontSize: 12 }}>
              <span>规则编码：{binding.rule_code}</span>
              <span>类型/周期：{binding.rule?.rule_type || "-"} / {binding.rule?.timeframe || "-"}</span>
              <span>执行器键：{binding.rule?.executor_key || "-"}</span>
              <span>{binding.rule?.description || "暂无描述"}</span>
            </div>
          </div>
        )) : <div style={{ color: "#98a2b3", fontSize: 13 }}>暂无规则绑定</div>}
      </div>
    </div>
  );
}


export function SmallTag({ children, tone = "primary" }: { children: string | number; tone?: "primary" | "muted" }) {
  const muted = tone === "muted";
  return (
    <span style={{ borderRadius: 999, padding: "2px 7px", background: muted ? "#eef0f3" : "#eef2ff", color: muted ? "#98a2b3" : "#4052d2", fontSize: 11, fontWeight: 700 }}>
      {children}
    </span>
  );
}


export function EditCard({ title, children }: { title: string; children: any }) {
  return (
    <div style={{ background: "#fff", borderRadius: 14, padding: 14, display: "grid", gap: 12 }}>
      <h3 style={{ margin: 0, color: "#1d2d50" }}>{title}</h3>
      {children}
    </div>
  );
}


export function TextField({ label, value, disabled, onChange }: { label: string; value: string; disabled?: boolean; onChange: (value: string) => void }) {
  return (
    <label style={{ display: "grid", gap: 4 }}>
      <FormLabel text={label} />
      <Input value={value} disabled={disabled} onChange={onChange} style={{ "--background": "#f8fafc", "--border-radius": "8px", "--padding-left": "10px" } as any} />
    </label>
  );
}


export function SelectField({ label, value, options, onChange }: { label: string; value: string; options: string[]; onChange: (value: string) => void }) {
  return (
    <label style={{ display: "grid", gap: 4 }}>
      <FormLabel text={label} />
      <select value={value} onChange={(event) => onChange(event.target.value)} style={{ height: 34, border: "1px solid #e4e7ec", borderRadius: 8, background: "#f8fafc", color: "#344054", padding: "0 8px" }}>
        {options.map((option) => <option key={option} value={option}>{option}</option>)}
      </select>
    </label>
  );
}


export function CheckField({ label, checked, onChange }: { label: string; checked: boolean; onChange: (value: boolean) => void }) {
  return (
    <label style={{ display: "flex", alignItems: "center", gap: 8, minHeight: 52, color: "#344054", fontSize: 13, fontWeight: 700 }}>
      <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} />
      {label}
    </label>
  );
}


export function WarningText() {
  return <div style={{ borderRadius: 8, background: "#fff7ed", color: "#b54708", padding: "8px 10px", fontSize: 12, fontWeight: 700 }}>该规则暂无执行器，不能参与自动监控</div>;
}


export function SimpleRows({ rows, empty }: { rows: { key: string; title: string; desc: string; enabled: boolean; warning?: boolean; onEdit: () => void }[]; empty: string }) {
  const sortedRows = [...rows].sort((a, b) => Number(b.enabled) - Number(a.enabled));
  return (
    <div style={{ display: "grid", gap: 8 }}>
      {sortedRows.length ? sortedRows.map((row) => (
        <div key={row.key} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10, padding: "9px 10px", borderRadius: 10, background: row.enabled ? "#f8fafc" : "#f2f4f7", opacity: row.enabled ? 1 : 0.72 }}>
          <div style={{ display: "grid", gap: 4, minWidth: 0 }}>
            <strong style={{ color: row.enabled ? "#1d2d50" : "#667085", fontSize: 13 }}>{row.title}</strong>
            <span style={{ color: row.enabled ? "#667085" : "#98a2b3", fontSize: 12 }}>{row.desc}</span>
            {row.warning && <span style={{ color: "#b54708", fontSize: 12 }}>该规则暂无执行器，不能参与自动监控</span>}
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <SmallTag tone={row.enabled ? "primary" : "muted"}>{row.enabled ? "启用" : "停用"}</SmallTag>
            <Button size="mini" onClick={row.onEdit}>编辑</Button>
          </div>
        </div>
      )) : <div style={{ color: "#98a2b3", fontSize: 13 }}>{empty}</div>}
    </div>
  );
}

