import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "../components/ui/sheet";
import type { WhyProjection } from "./whyProjection";

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projection: WhyProjection;
};

export function V2InspectSheet({ open, onOpenChange, projection }: Props) {
  const title = projection.provenance?.headline ?? "What Enigma did";

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="bottom"
        className="v2-inspect-sheet max-h-[45vh] rounded-t-xl"
        data-testid="v2-inspect-sheet"
        aria-describedby={undefined}
      >
        <SheetHeader className="text-left">
          <SheetTitle className="text-base">{title}</SheetTitle>
        </SheetHeader>

        {projection.workLabels.length > 0 ? (
          <ul
            className="mt-3 list-disc space-y-1 pl-5 text-sm text-foreground"
            data-testid="v2-inspect-work-labels"
          >
            {projection.workLabels.map((label) => (
              <li key={label}>{label}</li>
            ))}
          </ul>
        ) : null}

        {projection.provenanceLoading ? (
          <p className="mt-3 text-sm text-muted-foreground" data-testid="v2-inspect-loading">
            Loading details…
          </p>
        ) : null}

        {projection.provenance ? (
          <ul
            className="mt-3 list-disc space-y-1 pl-5 text-sm text-muted-foreground"
            data-testid="v2-inspect-why"
          >
            {projection.provenance.why_now.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        ) : null}
      </SheetContent>
    </Sheet>
  );
}
