import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { EnigmaClient } from "../enigma/client";
import type { GoosePixelLicence } from "../enigma/goosePixels";
import type { ProvenanceView } from "../enigma/types";
import type { WorldId } from "../pilot/types";
import { buildWhyProjection, type WhyProjection } from "./whyProjection";

export type V2InspectSheetState = {
  open: boolean;
  projection: WhyProjection;
  openInspect: () => void;
  onOpenChange: (open: boolean) => void;
};

export function useV2InspectSheet(
  licence: GoosePixelLicence,
  client: EnigmaClient,
  world: WorldId,
): V2InspectSheetState {
  const [open, setOpen] = useState(false);
  const [provenance, setProvenance] = useState<ProvenanceView | null>(null);
  const [provenanceLoading, setProvenanceLoading] = useState(false);
  const fetchGeneration = useRef(0);

  useEffect(() => {
    setOpen(false);
    setProvenance(null);
    setProvenanceLoading(false);
    fetchGeneration.current += 1;
  }, [world]);

  const projection = useMemo(
    () => buildWhyProjection(licence, provenance, provenanceLoading),
    [licence, provenance, provenanceLoading],
  );

  const openInspect = useCallback(() => {
    setOpen(true);
    const target = licence.inspectTarget;
    if (!target) {
      setProvenance(null);
      setProvenanceLoading(false);
      return;
    }
    const generation = fetchGeneration.current + 1;
    fetchGeneration.current = generation;
    setProvenanceLoading(true);
    void client
      .getProvenance(target)
      .then((view) => {
        if (fetchGeneration.current === generation) {
          setProvenance(view);
        }
      })
      .catch(() => {
        if (fetchGeneration.current === generation) {
          setProvenance(null);
        }
      })
      .finally(() => {
        if (fetchGeneration.current === generation) {
          setProvenanceLoading(false);
        }
      });
  }, [client, licence.inspectTarget]);

  const onOpenChange = useCallback(
    (next: boolean) => {
      if (next) {
        openInspect();
        return;
      }
      setOpen(false);
    },
    [openInspect],
  );

  return { open, projection, openInspect, onOpenChange };
}
