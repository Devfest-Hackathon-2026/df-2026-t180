import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router";
import "@fontsource-variable/google-sans-flex";
import "@fontsource-variable/google-sans-code";
import "@fontsource-variable/noto-sans-jp";
import "./styles/global.css";
import { RegionRedirect } from "./pages/RegionRedirect";
import { HomePage } from "./pages/HomePage";
import { PendingPage } from "./pages/PendingPage";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/regions/:regionId" element={<RegionRedirect />} />
        <Route path="*" element={<PendingPage />} />
      </Routes>
    </BrowserRouter>
  </StrictMode>,
);
