import { useEnigmaConversation } from "../enigma/EnigmaProvider";

export function V2CasesSurface() {
  const { selectedCaseId, selectCase, attention } = useEnigmaConversation();
  const candidates = [...(attention?.needs_you ?? []), ...(attention?.context ?? [])];
  const selected = candidates.find((row) => row.id === selectedCaseId) ?? null;

  return (
    <section className="v2-cases p-v2-4" data-testid="v2-cases-surface">
      <h1 className="text-lg font-semibold mb-v2-3">Cases</h1>
      {candidates.length === 0 ? (
        <p className="text-sm text-muted-foreground">Open loops will live here. This world has none yet.</p>
      ) : (
        <ul className="space-y-2">
          {candidates.map((row) => (
            <li key={row.id}>
              <button
                type="button"
                className="text-sm hover:underline"
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
        <p className="mt-v2-4 text-sm" data-testid="selected-case" data-case-id={selected.id}>
          {selected.title}
        </p>
      ) : null}
    </section>
  );
}
