import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { BottomTabs } from "./components/BottomTabs";
import { MarketPage } from "./pages/MarketPage";
import { ReviewsPage } from "./pages/ReviewsPage";
import { SettingsPage } from "./pages/SettingsPage";
import { StockDetailPage } from "./pages/StockDetailPage";
import { TradeReviewDetailPage } from "./pages/TradeReviewDetailPage";
import { WatchPoolPage } from "./pages/WatchPoolPage";

export function App() {
  return (
    <BrowserRouter>
      <main className="app-frame">
        <Routes>
          <Route path="/" element={<Navigate to="/market" replace />} />
          <Route path="/market" element={<MarketPage />} />
          <Route path="/sectors" element={<Navigate to="/market" replace />} />
          <Route path="/watch-pool" element={<WatchPoolPage />} />
          <Route path="/stocks/:stockCode" element={<StockDetailPage />} />
          <Route path="/signals" element={<Navigate to="/watch-pool" replace />} />
          <Route path="/daily-plan" element={<Navigate to="/market" replace />} />
          <Route path="/trades" element={<Navigate to="/watch-pool" replace />} />
          <Route path="/trades/:tradeId/review" element={<TradeReviewDetailPage />} />
          <Route path="/reviews" element={<ReviewsPage />} />
          <Route path="/monthly-review" element={<Navigate to="/reviews" replace />} />
          <Route path="/me" element={<SettingsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </main>
      <BottomTabs />
    </BrowserRouter>
  );
}
