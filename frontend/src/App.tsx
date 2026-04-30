import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { BottomTabs } from "./components/BottomTabs";
import { DailyPlanPage } from "./pages/DailyPlanPage";
import { MarketPage } from "./pages/MarketPage";
import { MonthlyReviewPage } from "./pages/MonthlyReviewPage";
import { ReviewsPage } from "./pages/ReviewsPage";
import { SectorsPage } from "./pages/SectorsPage";
import { SettingsPage } from "./pages/SettingsPage";
import { SignalsPage } from "./pages/SignalsPage";
import { StockDetailPage } from "./pages/StockDetailPage";
import { TradesPage } from "./pages/TradesPage";
import { TradeReviewDetailPage } from "./pages/TradeReviewDetailPage";
import { WatchPoolPage } from "./pages/WatchPoolPage";

export function App() {
  return (
    <BrowserRouter>
      <main className="app-frame">
        <Routes>
          <Route path="/" element={<Navigate to="/market" replace />} />
          <Route path="/market" element={<MarketPage />} />
          <Route path="/sectors" element={<SectorsPage />} />
          <Route path="/watch-pool" element={<WatchPoolPage />} />
          <Route path="/stocks/:stockCode" element={<StockDetailPage />} />
          <Route path="/signals" element={<SignalsPage />} />
          <Route path="/daily-plan" element={<DailyPlanPage />} />
          <Route path="/trades" element={<TradesPage />} />
          <Route path="/trades/:tradeId/review" element={<TradeReviewDetailPage />} />
          <Route path="/reviews" element={<ReviewsPage />} />
          <Route path="/monthly-review" element={<MonthlyReviewPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </main>
      <BottomTabs />
    </BrowserRouter>
  );
}
