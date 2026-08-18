import type { GoosePixelLicence } from "../enigma/goosePixels";
import type { ProvenanceView } from "../enigma/types";

/** Read-model for minimal inspectability — no semantic reconstruction in React. */
export type WhyProjection = {
  workLabels: string[];
  workSemanticToken: string;
  provenance: ProvenanceView | null;
  provenanceLoading: boolean;
};

export function buildWhyProjection(
  licence: GoosePixelLicence,
  provenance: ProvenanceView | null,
  provenanceLoading: boolean,
): WhyProjection {
  return {
    workLabels: licence.inspectLabels,
    workSemanticToken: licence.workSemanticToken,
    provenance,
    provenanceLoading,
  };
}
