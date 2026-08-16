import { NavLink, Route, Routes } from "react-router-dom";
import { DemoModeBanner } from "./demo";
import { ChatPage } from "./pages/ChatPage";
import { HomePage } from "./pages/HomePage";
import { PrivacyInspectorPage } from "./pages/PrivacyInspectorPage";
import { SettingsPage } from "./pages/SettingsPage";

export function App() {
  return (
    <div className="shell">
      <DemoModeBanner />
      <header className="topbar">
        <NavLink to="/" className="brand">
          personal-enigma
        </NavLink>
        <nav>
          <NavLink to="/">Home</NavLink>
          <NavLink to="/settings">Settings</NavLink>
          <NavLink to="/privacy">Privacy</NavLink>
          <NavLink to="/chat">Chat</NavLink>
        </nav>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/privacy" element={<PrivacyInspectorPage />} />
          <Route path="/chat" element={<ChatPage />} />
        </Routes>
      </main>
    </div>
  );
}
