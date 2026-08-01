import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { BottomTabs } from "./components/BottomTabs";
import { AdminPage } from "./pages/AdminPage";
import { AutoTradingPage } from "./pages/AutoTradingPage";
import { MarketPage } from "./pages/MarketPage";
import { ReviewsPage } from "./pages/ReviewsPage";
import { SettingsPage } from "./pages/SettingsPage";
import { StockDetailPage } from "./pages/StockDetailPage";
import { TradeReviewDetailPage } from "./pages/TradeReviewDetailPage";
import { WatchPoolPage } from "./pages/WatchPoolPage";

export function App() {
  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  );
}

function AppRoutes() {
  const isAdmin = window.location.pathname.startsWith("/admin");
  return (
    <>
      <main className={isAdmin ? "admin-frame" : "app-frame"}>
        <Routes>
          <Route path="/" element={<Navigate to="/market" replace />} />
          <Route path="/market" element={<MarketPage />} />
          <Route path="/watch-pool" element={<WatchPoolPage />} />
          <Route path="/auto-trading" element={<AutoTradingPage />} />
          <Route path="/stocks/:stockCode" element={<StockDetailPage />} />
          <Route path="/trades/:tradeId/review" element={<TradeReviewDetailPage />} />
          <Route path="/reviews" element={<ReviewsPage />} />
          <Route path="/me" element={<SettingsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/admin/*" element={<AdminPage />} />
        </Routes>
      </main>
      {!isAdmin && <BottomTabs />}
    </>
  );
}
