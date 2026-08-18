import { EnigmaProvider } from "../enigma/EnigmaProvider";
import { useWorld } from "../pilot/WorldProvider";
import { Outlet } from "react-router-dom";
import "./v2.css";

/** v2 layout — ADR-040 remount on world switch. */
export function V2Layout() {
  const { world } = useWorld();
  return (
    <EnigmaProvider key={world}>
      <Outlet />
    </EnigmaProvider>
  );
}
