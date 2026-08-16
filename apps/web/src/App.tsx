import { NavLink, Route, Routes, useLocation } from "react-router-dom";
import {
  DemoAttentionPage,
  DemoLayout,
  DemoMemoryPage,
  DemoModeBanner,
  DemoOverviewPage,
  DemoPrivacyPage,
  DemoWhyPage,
} from "./demo";
import { ChatPage } from "./pages/ChatPage";
import { HomePage } from "./pages/HomePage";
import { PrivacyInspectorPage } from "./pages/PrivacyInspectorPage";
import { SettingsPage } from "./pages/SettingsPage";

function PersistentDemoBanner() {
  const { pathname } = useLocation();
  const onDemoRoute = pathname === "/demo" || pathname.startsWith("/demo/");
  return <DemoModeBanner active={onDemoRoute ? true : undefined} />;
}

export function App() {
  return (
    <div className="shell">
      <PersistentDemoBanner />
      <header className="topbar">
        <NavLink to="/" className="brand">
          personal-enigma
        </NavLink>
        <nav>
          <NavLink to="/">Home</NavLink>
          <NavLink to="/settings">Settings</NavLink>
          <NavLink to="/privacy">Privacy</NavLink>
          <NavLink to="/chat">Chat</NavLink>
          <NavLink to="/demo">Demo</NavLink>
        </nav>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/privacy" element={<PrivacyInspectorPage />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/demo" element={<DemoLayout />}>
            <Route index element={<DemoOverviewPage />} />
            <Route path="attention" element={<DemoAttentionPage />} />
            <Route path="memory" element={<DemoMemoryPage />} />
            <Route path="privacy" element={<DemoPrivacyPage />} />
            <Route path="why/:itemId" element={<DemoWhyPage />} />
          </Route>
        </Routes>
      </main>
    </div>
  );
}
