import { useEnigmaConversation } from "../enigma/EnigmaProvider";

export function CasesSurface() {
  const { selectedCaseId, selectCase, attention } = useEnigmaConversation();
  const candidates = [...(attention?.needs_you ?? []), ...(attention?.context ?? [])];
  const selected = candidates.find((row) => row.id === selectedCaseId) ?? null;

  return (
    <section className="page cases-surface" data-testid="cases-surface">
      <h1>Cases</h1>
      {candidates.length === 0 ? (
        <p>Open loops will live here. This world has none yet.</p>
      ) : (
        <ul>
          {candidates.map((row) => (
            <li key={row.id}>
              <button
                type="button"
                data-testid={`select-case-${row.id}`}
                aria-pressed={selected?.id === row.id}
                onClick={() => selectCase(row.id)}
              >
                {row.title}
              </button>
            </li>
          ))}
        </ul>
      )}
      {selected ? (
        <p data-testid="selected-case" data-case-id={selected.id}>
          {selected.title}
        </p>
      ) : null}
    </section>
  );
}
