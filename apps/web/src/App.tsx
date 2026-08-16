import { NavLink, Route, Routes } from "react-router-dom";
import { HomePage } from "./pages/HomePage";
import { SettingsPage } from "./pages/SettingsPage";

export function App() {
  return (
    <div className="shell">
      <header className="topbar">
        <NavLink to="/" className="brand">
          personal-enigma
        </NavLink>
        <nav>
          <NavLink to="/">Home</NavLink>
          <NavLink to="/settings">Settings</NavLink>
        </nav>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </main>
    </div>
  );
}
