import { ExternalLink } from "lucide-react";
import type { SourceRef } from "../types/review";

type Props = {
  sourceRef: SourceRef;
  onSelect: (sourceRef: SourceRef) => void;
};

export function SourceLink({ sourceRef, onSelect }: Props) {
  return (
    <button
      type="button"
      className="source-link"
      onClick={(event) => {
        event.stopPropagation();
        onSelect(sourceRef);
      }}
    >
      <ExternalLink size={14} aria-hidden />
      Page {sourceRef.page_index ?? sourceRef.source_frame_id.replace("page_", "")}
    </button>
  );
}
