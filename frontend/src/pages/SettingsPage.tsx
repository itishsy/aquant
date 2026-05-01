import { PageShell } from "../components/PageShell";

export function SettingsPage() {
  return (
    <PageShell title="设置" hideHero>
      <article className="feature-card">
        <div className="card-head">
          <div className="card-headline">
            <span className="icon-badge">⚙</span>
            <h2>设置</h2>
          </div>
          <span className="soft-tag">v1.1</span>
        </div>

        <div className="stack-list">
          <div className="row-card">
            <div>
              <strong>数据模式</strong>
              <p>当前支持 mock provider 与已授权真实数据落库配置。</p>
            </div>
          </div>

          <div className="row-card">
            <div>
              <strong>合规边界</strong>
              <p>仅提供行情监测、辅助分析、信号提醒与人工确认，不提供自动化委托行为。</p>
            </div>
          </div>

          <div className="row-card">
            <div>
              <strong>严格模式</strong>
              <p>严格模式只限制系统内确认流程，不连接真实账户。仅作为交易辅助，请结合个人交易计划确认。</p>
            </div>
          </div>
        </div>
      </article>
    </PageShell>
  );
}
