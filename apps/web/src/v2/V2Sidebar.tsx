import { Button } from "../components/ui/button";
import { Separator } from "../components/ui/separator";

/** Sidebar placeholder until UI2-04 conversation continuity. */
export function V2Sidebar() {
  return (
    <aside className="v2-sidebar" data-testid="v2-sidebar" aria-label="Chats">
      <div className="p-3">
        <Button variant="secondary" size="sm" className="w-full" disabled>
          New chat
        </Button>
      </div>
      <Separator />
      <div className="p-3 flex-1">
        <p className="text-xs text-muted-foreground">Chats coming in UI2-04</p>
      </div>
    </aside>
  );
}
