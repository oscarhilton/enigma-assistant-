import { WORLD_LABELS, WORLD_SUBTITLES, type WorldId } from "./types";
import { useWorld } from "./WorldProvider";

const OPTIONS: WorldId[] = ["my_enigma", "alex_lab"];

export function WorldSwitcher() {
  const { world, switchWorld } = useWorld();

  return (
    <label className="world-switcher">
      <span className="sr-only">Active world</span>
      <select
        data-testid="world-switcher"
        value={world}
        aria-label="Active world"
        title={WORLD_SUBTITLES[world]}
        onChange={(event) => {
          void switchWorld(event.target.value as WorldId);
        }}
      >
        {OPTIONS.map((id) => (
          <option key={id} value={id}>
            {WORLD_LABELS[id]}
          </option>
        ))}
      </select>
    </label>
  );
}
