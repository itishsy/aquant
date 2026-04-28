import { PageShell } from "../components/PageShell";

export function SettingsPage() {
  return (
    <PageShell title="设置">
      <article className="feature-card">
        <div className="card-head">
          <div className="card-headline">
            <span className="icon-badge">⚙</span>
            <h2>设置</h2>
          </div>
          <span className="soft-tag">MVP</span>
        </div>
        <div className="stack-list">
          <div className="row-card">
            <div>
              <strong>数据模式</strong>
              <p>当前使用 mock provider + 真实 MySQL 落库</p>
            </div>
          </div>
          <div className="row-card">
            <div>
              <strong>合规边界</strong>
              <p>仅提供行情监测、辅助分析、信号提醒与人工确认，不提供自动交易</p>
            </div>
          </div>
        </div>
      </article>
    </PageShell>
  );
}
