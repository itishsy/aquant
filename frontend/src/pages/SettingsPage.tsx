import { useEffect, useState } from "react";
import { Button, ErrorBlock, SpinLoading, Toast } from "antd-mobile";
import { apiGet, apiPost } from "../api/client";
import { PageShell } from "../components/PageShell";

export function SettingsPage() {
  const [profile, setProfile] = useState<any>(null);
  const [todos, setTodos] = useState<any>(null);
  const [summary, setSummary] = useState<any>(null);
  const [backendEntry, setBackendEntry] = useState<any>(null);
  const [error, setError] = useState("");
  const [collecting, setCollecting] = useState(false);

  async function load() {
    try {
      const [profileData, todosData, summaryData, entryData] = await Promise.all([
        apiGet("/h5/me/profile"),
        apiGet("/h5/me/todos"),
        apiGet("/h5/me/system-summary"),
        apiGet("/h5/me/backend-entry"),
      ]);
      setProfile(profileData);
      setTodos(todosData);
      setSummary(summaryData);
      setBackendEntry(entryData);
      setError("");
    } catch (err) {
      setError(String(err));
    }
  }

  useEffect(() => { load(); }, []);

  async function doCollect() {
    setCollecting(true);
    try {
      const res: any = await apiPost("/h5/me/collect-market");
      Toast.show({ content: `采集完成 (${res.collect_time?.slice(11, 19) || "ok"})` });
      load();
    } catch {
      Toast.show({ content: "采集失败" });
    } finally {
      setCollecting(false);
    }
  }

  function fmtTime(iso?: string) {
    if (!iso) return "暂无";
    const d = new Date(iso + "Z");
    const pad = (n: number) => String(n).padStart(2, "0");
    return `${d.getMonth() + 1}/${d.getDate()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
  }

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
                <strong>市场数据采集</strong>
                <p>最近采集：{fmtTime(summary?.last_collect_time)}</p>
                <p style={{ fontSize: 11, color: "#aaa" }}>定时任务：每日 18:00 自动采集大盘/热榜/涨停数据</p>
              </div>
              <Button size="small" loading={collecting} onClick={doCollect}>
                立即采集
              </Button>
            </div>

            <div className="row-card">
              <div>
                <strong>系统状态</strong>
                <p>模式：{summary?.mode || "single-user"} / 自选数量：{summary?.watch_count ?? 0}</p>
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
