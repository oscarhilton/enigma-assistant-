import { useEffect, useMemo, useRef, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { Composer } from "../enigma/Composer";
import { useEnigmaConversation } from "../enigma/EnigmaProvider";
import { GoosePresence } from "../enigma/GoosePresence";
import { licenceFromConversation, type GoosePixelLicence } from "../enigma/goosePixels";
import { inspectGooseEvent, projectGooseEvents, recordGooseTelemetry } from "../enigma/gooseTelemetry";
import { useWorld } from "./WorldProvider";
import { WorldSwitcher } from "./WorldSwitcher";

export function PilotShell() {
  const { world } = useWorld();
  const { items, busy, loading, sendMessage, error, clearError, client } = useEnigmaConversation();
  const [workExplanation, setWorkExplanation] = useState<string[]>([]);
  const gooseLicence = useMemo(
    () => licenceFromConversation({ items, busy, loading }),
    [items, busy, loading],
  );
  const previousGooseLicence = useRef<GoosePixelLicence | null>(null);

  useEffect(() => {
    recordGooseTelemetry(projectGooseEvents(previousGooseLicence.current, gooseLicence));
    previousGooseLicence.current = gooseLicence;
  }, [gooseLicence]);

  function inspectGooseWork() {
    recordGooseTelemetry([inspectGooseEvent(gooseLicence)]);
    const target = gooseLicence.inspectTarget;
    if (target) {
      void client.getProvenance(target).catch(() => {
        setWorkExplanation(gooseLicence.inspectLabels);
      });
      return;
    }
    setWorkExplanation(gooseLicence.inspectLabels);
  }

  return (
    <div className="pilot-shell" data-testid="pilot-shell" data-world={world}>
      <header className="pilot-chrome">
        <NavLink to="/" className="brand">
          Enigma
        </NavLink>
        <div className="pilot-chrome-tools">
          <WorldSwitcher />
          <GoosePresence licence={gooseLicence} onInspect={inspectGooseWork} />
        </div>
      </header>
      <div className="pilot-body">
        <nav className="pilot-nav" aria-label="Daily">
          <NavLink to="/" end>
            Today
          </NavLink>
          <NavLink to="/cases">Cases</NavLink>
        </nav>
        <div className="pilot-main">
          <Outlet />
          {workExplanation.length > 0 ? (
            <section className="work-explanation" data-testid="work-explanation" aria-label="Work explanation">
              <ul>
                {workExplanation.map((line) => (
                  <li key={line}>{line}</li>
                ))}
              </ul>
            </section>
          ) : null}
          <Composer
            onSend={sendMessage}
            disabled={loading}
            busy={busy}
            error={error}
            onDismissError={clearError}
          />
        </div>
      </div>
    </div>
  );
}
