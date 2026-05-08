import { TabBar } from "antd-mobile";
import { useLocation, useNavigate } from "react-router-dom";

const tabs = [
  { key: "/market", title: "市场", icon: "■" },
  { key: "/watch-pool", title: "自选", icon: "★" },
  { key: "/reviews", title: "复盘", icon: "◆" },
  { key: "/me", title: "我的", icon: "●" },
];

export function BottomTabs() {
  const location = useLocation();
  const navigate = useNavigate();
  const active =
    tabs.find((tab) => location.pathname.startsWith(tab.key))?.key ||
    (location.pathname.startsWith("/settings") ? "/me" : "") ||
    (location.pathname.startsWith("/signals") ? "/watch-pool" : "/market");

  return (
    <div className="bottom-tabs">
      <TabBar activeKey={active} onChange={(value) => navigate(value)}>
        {tabs.map((item) => (
          <TabBar.Item
            key={item.key}
            icon={<span className="tab-icon">{item.icon}</span>}
            title={item.title}
          />
        ))}
      </TabBar>
    </div>
  );
}
