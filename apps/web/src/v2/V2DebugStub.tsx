import { Link } from "react-router-dom";
import { buildIdentityLabel } from "./buildIdentity";

export function V2DebugStub() {
  return (
    <div className="v2-root min-h-dvh p-8 max-w-xl mx-auto">
      <p className="text-sm text-muted-foreground mb-2">{buildIdentityLabel()}</p>
      <h1 className="text-xl font-semibold mb-2">Semantic Forensics</h1>
      <p className="text-sm text-muted-foreground mb-4">Coming soon — see UI2-DEBUG.</p>
      <Link to="/v2" className="text-sm underline">
        Back to chat
      </Link>
    </div>
  );
}
