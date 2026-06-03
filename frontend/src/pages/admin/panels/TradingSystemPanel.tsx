import { SpinLoading } from "antd-mobile";
import type { TradingParam, TradingRuleBinding, TradingSystem } from "../types";
import { ParamRow, RuleStageCard } from "../components/common";

export function TradingSystemPanel({
  systems,
  selectedCode,
  selectedSystem,
  params,
  bindings,
  loading,
  onSelect,
}: {
  systems: TradingSystem[];
  selectedCode: string;
  selectedSystem: TradingSystem | null;
  params: TradingParam[];
  bindings: TradingRuleBinding[];
  loading: boolean;
  onSelect: (code: string) => void;
}) {
  const observeBindings = bindings.filter((item) => item.stage === "observe");
  const tradingBindings = bindings.filter((item) => item.stage === "trading");
  const stopLossBindings = bindings.filter((item) => item.stage === "stop_loss");

  return (
    <div style={{ display: "grid", gridTemplateColumns: "minmax(180px, 260px) 1fr", gap: 14 }}>
      <div style={{ background: "#fff", borderRadius: 14, padding: 14, display: "grid", gap: 8, alignContent: "start" }}>
        <h3 style={{ margin: "0 0 4px", color: "#1d2d50" }}>交易体系列表</h3>
        {systems.length ? systems.map((system) => (
          <button
            key={system.system_code}
            onClick={() => onSelect(system.system_code)}
            style={{
              border: 0,
              borderRadius: 10,
              padding: "10px 12px",
              textAlign: "left",
              background: selectedCode === system.system_code ? "linear-gradient(135deg, #5570ff, #4052d2)" : "#f4f6fb",
              color: selectedCode === system.system_code ? "#fff" : "#344054",
              cursor: "pointer",
            }}
          >
            <strong style={{ display: "block", fontSize: 14 }}>{system.system_name}</strong>
            <span style={{ display: "block", marginTop: 4, fontSize: 12, opacity: 0.78 }}>{system.system_code}</span>
          </button>
        )) : <div style={{ color: "#98a2b3", fontSize: 13 }}>暂无交易体系</div>}
      </div>

      <div style={{ display: "grid", gap: 14 }}>
        {loading && <div style={{ display: "grid", placeItems: "center", minHeight: 120, background: "#fff", borderRadius: 14 }}><SpinLoading /></div>}

        {!loading && selectedSystem && (
          <>
            <div style={{ background: "#fff", borderRadius: 14, padding: 14 }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "flex-start" }}>
                <div>
                  <h3 style={{ margin: 0, color: "#1d2d50" }}>{selectedSystem.system_name}</h3>
                  <p style={{ margin: "6px 0 0", color: "#667085", fontSize: 13 }}>{selectedSystem.system_code}</p>
                </div>
                <span style={{ borderRadius: 999, padding: "4px 8px", background: selectedSystem.enabled ? "#ecfdf3" : "#f2f4f7", color: selectedSystem.enabled ? "#027a48" : "#667085", fontSize: 12, fontWeight: 700 }}>
                  {selectedSystem.enabled ? "启用" : "停用"}
                </span>
              </div>
              <p style={{ margin: "12px 0 0", color: "#344054", fontSize: 13 }}>{selectedSystem.description || "暂无描述"}</p>
              <p style={{ margin: "6px 0 0", color: "#667085", fontSize: 12 }}>生命周期：{selectedSystem.lifecycle_desc || "-"}</p>
            </div>

            <div style={{ background: "#fff", borderRadius: 14, padding: 14 }}>
              <h3 style={{ margin: "0 0 10px", color: "#1d2d50" }}>观察参数</h3>
              <div style={{ display: "grid", gap: 8 }}>
                {params.length ? params.map((param) => (
                  <ParamRow key={param.param_id} param={param} />
                )) : <div style={{ color: "#98a2b3", fontSize: 13 }}>暂无参数定义</div>}
              </div>
            </div>

            <RuleStageCard title="观察阶段规则" items={observeBindings} />
            <RuleStageCard title="交易阶段卖点规则" items={tradingBindings} />
            <RuleStageCard title="止损规则" items={stopLossBindings} />
          </>
        )}

        {!loading && !selectedSystem && (
          <div style={{ background: "#fff", borderRadius: 14, padding: 20, textAlign: "center", color: "#98a2b3" }}>
            请选择一个交易体系
          </div>
        )}
      </div>
    </div>
  );
}

