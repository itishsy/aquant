import type { WatchRulePreviewResult } from "./types";

function conclusion(preview: WatchRulePreviewResult) {
  if (preview.would_generate_signal) return "满足买点条件，正式扫描会生成买点信号";
  if (!preview.required_passed) return "必要条件未满足，暂不会生成信号";
  if (!preview.buy_signal_triggered) return "必要条件满足，但买点信号未触发";
  return "暂不会生成信号";
}

export function WatchRulePreview({ preview }: { preview: WatchRulePreviewResult }) {
  return (
    <section className={`watch-rule-preview ${preview.would_generate_signal ? "watch-rule-preview--triggered" : ""}`}>
      <h4>规则试算：{conclusion(preview)}</h4>
      <div className="watch-detail-stack watch-detail-stack--compact">
        {(preview.rules || []).map((rule) => (
          <div className="watch-history-item" key={rule.rule_code}>
            <div className="watch-history-item__head">
              <strong>{rule.rule_display_name || rule.rule_name || rule.rule_code}</strong>
              <span className={rule.triggered ? "is-positive" : "is-negative"}>{rule.triggered ? "满足" : "未满足"}</span>
            </div>
            <p>{[rule.rule_type, rule.timeframe, rule.required ? "必需" : "可选", rule.logic_group].filter(Boolean).join(" | ")}</p>
            {rule.reason && <p>{rule.reason}</p>}
          </div>
        ))}
      </div>
    </section>
  );
}
