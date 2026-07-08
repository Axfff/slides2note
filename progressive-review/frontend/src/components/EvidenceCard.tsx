import type { EvidenceCard as EvidenceCardType, SourceRef } from "../types/review";
import { MathText } from "./MathText";
import { SourceLink } from "./SourceLink";

type Props = {
  evidence: EvidenceCardType;
  onSourceSelect: (sourceRef: SourceRef) => void;
  sourceRefAttributes?: (sourceRef?: SourceRef | null) => Record<string, string | undefined>;
  selectedGeneratedId?: string | null;
};

export function EvidenceCard({ evidence, onSourceSelect, sourceRefAttributes, selectedGeneratedId }: Props) {
  const firstRef = evidence.source_refs[0];
  const openSource = () => {
    if (firstRef) {
      onSourceSelect(firstRef);
    }
  };

  return (
    <article
      id={`generated-${evidence.evidence_id}`}
      {...sourceRefAttributes?.(firstRef)}
      className={selectedGeneratedId === `generated-${evidence.evidence_id}` ? "evidence-card generated-active" : "evidence-card"}
      role={firstRef ? "button" : undefined}
      tabIndex={firstRef ? 0 : undefined}
      onClick={openSource}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          openSource();
        }
      }}
    >
      <div className="evidence-card__top">
        <MathText as="span" className="evidence-card__title" text={evidence.title} />
        {firstRef ? <SourceLink sourceRef={firstRef} onSelect={onSourceSelect} /> : null}
      </div>
      <MathText as="blockquote" text={evidence.evidence_text} />
      <MathText as="p" text={evidence.why_it_matters} />
      {evidence.caveat ? (
        <small>
          <MathText text={evidence.caveat} />
        </small>
      ) : null}
    </article>
  );
}
