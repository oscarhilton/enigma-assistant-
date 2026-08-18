import { useOutletContext } from "react-router-dom";
import { V2ConversationViewport } from "./V2ConversationViewport";
import type { V2OutletContext } from "./V2Shell";

export function V2ChatPage() {
  const { items, streamingRow, loading, demoMode, onWhy, onApproveAssist, onHelpAssist } =
    useOutletContext<V2OutletContext>();

  return (
    <V2ConversationViewport
      items={items}
      loading={loading}
      streamingRow={streamingRow}
      demoMode={demoMode}
      onWhy={onWhy}
      onApproveAssist={onApproveAssist}
      onHelpAssist={onHelpAssist}
    />
  );
}
