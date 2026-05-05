import { useEffect, useState } from "react";
import { ErrorBlock, SpinLoading } from "antd-mobile";
import { apiGet } from "../api/client";
import { PageShell } from "../components/PageShell";

export function SettingsPage() {
  const [profile, setProfile] = useState<any>(null);
  const [todos, setTodos] = useState<any>(null);
  const [summary, setSummary] = useState<any>(null);
  const [backendEntry, setBackendEntry] = useState<any>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([
      apiGet("/h5/me/profile"),
      apiGet("/h5/me/todos"),
      apiGet("/h5/me/system-summary"),
      apiGet("/h5/me/backend-entry"),
    ])
      .then(([profileData, todosData, summaryData, entryData]) => {
        setProfile(profileData);
        setTodos(todosData);
        setSummary(summaryData);
        setBackendEntry(entryData);
        setError("");
      })
      .catch((err) => setError(String(err)));
  }, []);

  return (
    <PageShell title="我的" hideHero>
      {error && <ErrorBlock description="我的页面加载失败" />}
      {!profile && !error && <SpinLoading />}
      {profile && (
        <article className="feature-card">
          <div className="card-head">
            <div className="card-headline">
              <span className="icon-badge">我</span>
              <h2>{profile.nickname || "Aquant 用户"}</h2>
            </div>
            <span className="soft-tag">单用户</span>
          </div>

          <div className="stack-list">
            <div className="row-card">
              <div>
                <strong>待办提醒</strong>
                <p>待复盘：{todos?.pending_reviews ?? 0} / 未读消息：{todos?.unread_notifications ?? 0}</p>
              </div>
            </div>

            <div className="row-card">
              <div>
                <strong>个人偏好</strong>
                <p>偏好配置通过后台字典和我的模块维护，敏感配置不会返回前端。</p>
              </div>
            </div>

            <div className="row-card">
              <div>
                <strong>系统状态</strong>
                <p>模式：{summary?.mode || "single-user"} / 自选数量：{summary?.watch_count ?? 0}</p>
              </div>
            </div>

            <div className="row-card">
              <div>
                <strong>后台管理入口</strong>
                <p>{backendEntry?.enabled ? `可进入：${backendEntry.entry_url}` : "当前未开放"}</p>
              </div>
            </div>

            <div className="row-card">
              <div>
                <strong>合规边界</strong>
                <p>系统只做行情、信号、记录和复盘辅助，不连接真实账户。仅作为交易辅助，请结合个人交易规则确认。</p>
              </div>
            </div>
          </div>
        </article>
      )}
    </PageShell>
  );
}
