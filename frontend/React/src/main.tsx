import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router";
import "@fontsource-variable/google-sans-flex";
import "@fontsource-variable/google-sans-code";
import "@fontsource-variable/noto-sans-jp";
import "./styles/global.css";
import { isDemoLocation } from "./hooks/useMyLocation";
import { AdminLoginPage } from "./pages/AdminLoginPage";
import { AdminPage } from "./pages/AdminPage";
import { RegionRedirect } from "./pages/RegionRedirect";
import { ContributePage } from "./pages/ContributePage";
import { HomePage } from "./pages/HomePage";
import { PendingPage } from "./pages/PendingPage";

// Reads ?demo=1 / ?demo=0 once on load, so the demo location setting sticks for the tab.
isDemoLocation();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/regions/:regionId" element={<RegionRedirect />} />
        <Route path="/contribute" element={<ContributePage />} />
        <Route path="/admin" element={<AdminLoginPage />} />
        <Route path="/admin/:area" element={<AdminPage />} />
        <Route path="*" element={<PendingPage />} />
      </Routes>
    </BrowserRouter>
  </StrictMode>,
);
