import { Button } from "../components/ui/button";
import { ScrollArea } from "../components/ui/scroll-area";
import { Separator } from "../components/ui/separator";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "../components/ui/tooltip";
import { useV2Threads } from "./V2ThreadProvider";

export function V2Sidebar() {
  const { threads, activeThreadId, selectThread, createNewThread } = useV2Threads();

  return (
    <aside className="v2-sidebar" data-testid="v2-sidebar" aria-label="Chats">
      <div className="p-v2-3">
        <TooltipProvider delayDuration={300}>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="secondary"
                size="sm"
                className="w-full"
                data-testid="v2-new-chat"
                onClick={createNewThread}
              >
                New chat
              </Button>
            </TooltipTrigger>
            <TooltipContent>Start a fresh conversation</TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>
      <Separator />
      <ScrollArea className="flex-1 min-h-0">
        <nav className="p-v2-2" aria-label="Chat history" data-testid="v2-thread-list">
          {threads.map((thread) => (
            <button
              key={thread.id}
              type="button"
              className="v2-thread-item"
              data-testid={`v2-thread-${thread.id}`}
              data-active={thread.id === activeThreadId ? "true" : "false"}
              aria-current={thread.id === activeThreadId ? "true" : undefined}
              onClick={() => selectThread(thread.id)}
            >
              <span className="truncate">{thread.title}</span>
            </button>
          ))}
        </nav>
      </ScrollArea>
    </aside>
  );
}
