import type { Stage } from "@/types";
import { StageSpectrum } from "@/components/Dispersion";

/** Kept as the page-facing name: the pipeline is one dispersed band. */
export function StageStepper({ stages }: { stages: Stage[] }) {
  return <StageSpectrum stages={stages} />;
}
