import { NavLink, Outlet, Route, Routes, useLocation } from "react-router-dom";
import {
  DemoAttentionPage,
  DemoLayout,
  DemoMemoryPage,
  DemoModeBanner,
  DemoOverviewPage,
  DemoPrivacyPage,
  DemoSuppressedPage,
  DemoWhyPage,
} from "./demo";
import { EnigmaProvider } from "./enigma/EnigmaProvider";
import { ChatPage } from "./pages/ChatPage";
import { HomePage } from "./pages/HomePage";
import { PrivacyInspectorPage } from "./pages/PrivacyInspectorPage";
import { SettingsPage } from "./pages/SettingsPage";
import { CasesSurface, PilotShell, WorldProvider, useWorld } from "./pilot";
import { ShadowModeBanner } from "./shadow";
import { V2DebugRoute, V2Layout, V2Shell } from "./v2";

function PersistentModeBanners() {
  const { pathname } = useLocation();
  const onDemoRoute = pathname === "/demo" || pathname.startsWith("/demo/");
  const shadowEnv =
    typeof import.meta !== "undefined" &&
    import.meta.env?.VITE_ENIGMA_MODE === "shadow";
  // Demo chrome must not override an active Shadow session (ADR-008 / S01).
  return (
    <>
      <DemoModeBanner
        active={onDemoRoute ? (shadowEnv ? false : true) : undefined}
      />
      <ShadowModeBanner />
    </>
  );
}

function PilotLayout() {
  const { world } = useWorld();
  // ADR-040: remount world-derived React state on switch (conversation, Today, Cases, Goose).
  return (
    <EnigmaProvider key={world}>
      <PilotShell />
    </EnigmaProvider>
  );
}

function SecondaryShell() {
  return (
    <div className="shell">
      <header className="topbar">
        <NavLink to="/" className="brand">
          Enigma
        </NavLink>
        <nav>
          <NavLink to="/">Today</NavLink>
          <NavLink to="/settings">Settings</NavLink>
          <NavLink to="/privacy">Privacy</NavLink>
          <NavLink to="/chat">Chat</NavLink>
          <NavLink to="/demo">Demo</NavLink>
        </nav>
      </header>
      <main>
        <Outlet />
      </main>
    </div>
  );
}

export function App() {
  return (
    <WorldProvider persistToApi={import.meta.env.MODE !== "test"}>
      <PersistentModeBanners />
      <Routes>
        <Route element={<PilotLayout />}>
          <Route path="/" element={<HomePage />} />
          <Route path="/cases" element={<CasesSurface />} />
        </Route>
        <Route element={<SecondaryShell />}>
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/privacy" element={<PrivacyInspectorPage />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/demo" element={<DemoLayout />}>
            <Route index element={<DemoOverviewPage />} />
            <Route path="attention" element={<DemoAttentionPage />} />
            <Route path="memory" element={<DemoMemoryPage />} />
            <Route path="privacy" element={<DemoPrivacyPage />} />
            <Route path="suppressed" element={<DemoSuppressedPage />} />
            <Route path="why/:itemId" element={<DemoWhyPage />} />
          </Route>
        </Route>
        <Route path="/v2" element={<V2Layout />}>
          <Route index element={<V2Shell />} />
          <Route path="debug" element={<V2DebugRoute />} />
        </Route>
      </Routes>
    </WorldProvider>
  );
}
