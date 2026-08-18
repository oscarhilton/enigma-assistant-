import { useEffect } from "react";

/** Opens semantic forensics at ⌘⇧D (Meta+Shift+D on macOS). */
export function useDebugShortcut(onOpen: () => void) {
  useEffect(() => {
    function handler(event: KeyboardEvent) {
      if (!(event.metaKey || event.ctrlKey) || !event.shiftKey) {
        return;
      }
      if (event.key.toLowerCase() !== "d") {
        return;
      }
      event.preventDefault();
      onOpen();
    }

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onOpen]);
}
