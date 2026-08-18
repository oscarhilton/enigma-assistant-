import { EnigmaProvider } from "../enigma/EnigmaProvider";
import { useWorld } from "../pilot/WorldProvider";
import { Outlet } from "react-router-dom";
import { StreamTraceProvider } from "./StreamTraceProvider";
import { V2ThreadProvider } from "./V2ThreadProvider";
import "./v2.css";

/** v2 layout — ADR-040 remount on world switch. */
export function V2Layout() {
  const { world } = useWorld();
  return (
    <EnigmaProvider key={world}>
      <StreamTraceProvider>
        <V2ThreadProvider key={world}>
          <Outlet />
        </V2ThreadProvider>
      </StreamTraceProvider>
    </EnigmaProvider>
  );
}
