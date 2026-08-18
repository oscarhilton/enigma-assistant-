import type { ReactNode } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../components/ui/card";
import { NOT_CAPTURED, type ForensicSectionStatus } from "./types";

const STATUS_LABEL: Record<ForensicSectionStatus, string> = {
  wired: "Wired",
  unavailable: "Unavailable",
  empty: "Empty",
};

type Props = {
  title: string;
  status: ForensicSectionStatus;
  description?: string;
  children: ReactNode;
  testId?: string;
};

function JsonBlock({ value }: { value: unknown }) {
  if (value === null || value === undefined) {
    return <p className="text-sm text-muted-foreground">None</p>;
  }
  return (
    <pre className="text-xs overflow-x-auto rounded-md bg-muted/60 p-3 font-mono leading-relaxed">
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}

export function ForensicSectionCard({ title, status, description, children, testId }: Props) {
  return (
    <Card data-testid={testId}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between gap-2">
          <CardTitle>{title}</CardTitle>
          <span
            className="rounded-full border border-border px-2 py-0.5 text-[10px] uppercase tracking-wide text-muted-foreground"
            data-testid={testId ? `${testId}-status` : undefined}
          >
            {STATUS_LABEL[status]}
          </span>
        </div>
        {description ? <CardDescription>{description}</CardDescription> : null}
      </CardHeader>
      <CardContent>
        {status === "unavailable" ? (
          <p className="text-sm text-muted-foreground" data-testid={testId ? `${testId}-unavailable` : undefined}>
            {NOT_CAPTURED}
          </p>
        ) : (
          children
        )}
      </CardContent>
    </Card>
  );
}

ForensicSectionCard.Json = JsonBlock;
