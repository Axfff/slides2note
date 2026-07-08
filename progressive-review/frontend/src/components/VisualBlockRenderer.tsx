import { BarChart3, Check, Circle, Grid2X2, LayoutTemplate, MessageSquareQuote, MousePointerClick, Route, Table2 } from "lucide-react";
import { useState } from "react";
import type { AgentLayoutSpec, SourceRef, VisualBlockPlacement, VisualInteractiveBlock } from "../types/review";
import { SourceLink } from "./SourceLink";

type Props = {
  blocks: VisualInteractiveBlock[];
  placement: VisualBlockPlacement;
  layoutSpec?: AgentLayoutSpec | null;
  onSourceSelect: (sourceRef: SourceRef) => void;
  sourceRefAttributes?: (sourceRef?: SourceRef | null) => Record<string, string | undefined>;
  selectedGeneratedId?: string | null;
};

type StatItem = {
  label: string;
  value: string | number;
};

type TimelineEvent = {
  label: string;
  summary?: string;
  source_ref?: SourceRef;
};

type ChecklistItem = {
  id: string;
  label: string;
  source_ref?: SourceRef;
};

type ConceptItem = {
  tag?: string;
  title?: string;
  body?: string;
};

type QuestionItem = {
  label?: string;
  question?: string;
  answer?: string;
  source_ref?: SourceRef;
};

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function asSourceRef(value: unknown): SourceRef | undefined {
  if (!value || typeof value !== "object") {
    return undefined;
  }
  const candidate = value as Partial<SourceRef>;
  return typeof candidate.source_frame_id === "string" ? (candidate as SourceRef) : undefined;
}

function firstSourceRef(block: VisualInteractiveBlock): SourceRef | undefined {
  return block.source_refs.find((ref) => ref.source_frame_id);
}

export function VisualBlockGroup({ blocks, placement, layoutSpec, onSourceSelect, sourceRefAttributes, selectedGeneratedId }: Props) {
  const placedBlocks = blocks.filter((block) => block.placement === placement);
  const slots = (layoutSpec?.slots.filter((slot) => slot.placement === placement) ?? []).filter(
    (slot) => !placedBlocks.some((block) => slot.allowed_block_types.includes(block.type)),
  );

  if (!placedBlocks.length && !slots.length) {
    return null;
  }

  return (
    <div className={`visual-block-group visual-block-group--${placement}`}>
      {slots.length ? (
        <div className="agent-layout-slots" aria-label={`${placement} layout slots`}>
          {slots.map((slot) => (
            <div className="agent-layout-slot" key={slot.slot_id}>
              <LayoutTemplate size={15} aria-hidden />
              <div>
                <strong>{slot.title}</strong>
                <span>{slot.allowed_block_types.join(", ")}</span>
              </div>
            </div>
          ))}
        </div>
      ) : null}
      {placedBlocks.map((block) => (
        <VisualBlock
          key={block.block_id}
          block={block}
          onSourceSelect={onSourceSelect}
          sourceRefAttributes={sourceRefAttributes}
          selected={selectedGeneratedId === `generated-${block.block_id}`}
        />
      ))}
    </div>
  );
}

function VisualBlock({
  block,
  onSourceSelect,
  sourceRefAttributes,
  selected,
}: {
  block: VisualInteractiveBlock;
  onSourceSelect: (sourceRef: SourceRef) => void;
  sourceRefAttributes?: (sourceRef?: SourceRef | null) => Record<string, string | undefined>;
  selected: boolean;
}) {
  const ref = firstSourceRef(block);
  const className = ["visual-block", `visual-block--${block.type}`, selected ? "generated-active" : ""].filter(Boolean).join(" ");

  return (
    <section
      id={`generated-${block.block_id}`}
      {...sourceRefAttributes?.(ref)}
      className={className}
      role={ref ? "button" : undefined}
      tabIndex={ref ? 0 : undefined}
      onClick={() => {
        if (ref) {
          onSourceSelect(ref);
        }
      }}
      onKeyDown={(event) => {
        if ((event.key === "Enter" || event.key === " ") && ref) {
          event.preventDefault();
          onSourceSelect(ref);
        }
      }}
    >
      <div className="visual-block__top">
        <div className="visual-block__title">
          {block.type === "visual_summary" ? <BarChart3 size={18} aria-hidden /> : null}
          {block.type === "hero" ? <MessageSquareQuote size={18} aria-hidden /> : null}
          {block.type === "concept_grid" ? <Grid2X2 size={18} aria-hidden /> : null}
          {block.type === "callout" ? <MessageSquareQuote size={18} aria-hidden /> : null}
          {block.type === "comparison_table" ? <Table2 size={18} aria-hidden /> : null}
          {block.type === "question_bank" ? <MessageSquareQuote size={18} aria-hidden /> : null}
          {block.type === "source_timeline" ? <Route size={18} aria-hidden /> : null}
          {block.type === "interactive_checklist" ? <MousePointerClick size={18} aria-hidden /> : null}
          {block.type === "agent_slot" ? <LayoutTemplate size={18} aria-hidden /> : null}
          <h3>{block.title}</h3>
        </div>
        {ref ? <SourceLink sourceRef={ref} onSelect={onSourceSelect} /> : null}
      </div>
      {block.type === "hero" ? <HeroBlock block={block} /> : null}
      {block.type === "visual_summary" ? <VisualSummary block={block} /> : null}
      {block.type === "concept_grid" ? <ConceptGrid block={block} /> : null}
      {block.type === "callout" ? <CalloutBlock block={block} /> : null}
      {block.type === "comparison_table" ? <ComparisonTable block={block} /> : null}
      {block.type === "question_bank" ? <QuestionBank block={block} onSourceSelect={onSourceSelect} /> : null}
      {block.type === "source_timeline" ? <SourceTimeline block={block} onSourceSelect={onSourceSelect} /> : null}
      {block.type === "interactive_checklist" ? <InteractiveChecklist block={block} onSourceSelect={onSourceSelect} /> : null}
      {block.type === "agent_slot" ? <AgentSlot block={block} /> : null}
    </section>
  );
}

function HeroBlock({ block }: { block: VisualInteractiveBlock }) {
  const kicker = typeof block.payload.kicker === "string" ? block.payload.kicker : "Source-linked review";
  const lead = typeof block.payload.lead === "string" ? block.payload.lead : "";
  const pills = asArray(block.payload.pills).filter((item): item is string => typeof item === "string");
  const codeLines = asArray(block.payload.code_lines).filter((item): item is string => typeof item === "string");

  return (
    <div className="cheatsheet-hero__body">
      <span className="cheatsheet-kicker">{kicker}</span>
      <h2>{block.title}</h2>
      {lead ? <p className="cheatsheet-lead">{lead}</p> : null}
      {pills.length ? (
        <div className="cheatsheet-meta">
          {pills.map((pill) => (
            <span key={pill}>{pill}</span>
          ))}
        </div>
      ) : null}
      {codeLines.length ? (
        <pre className="cheatsheet-codebox">
          {codeLines.map((line) => (
            <code key={line}>{line}</code>
          ))}
        </pre>
      ) : null}
    </div>
  );
}

function VisualSummary({ block }: { block: VisualInteractiveBlock }) {
  const stats = asArray(block.payload.stats).filter((item): item is StatItem => {
    return Boolean(item && typeof item === "object" && "label" in item && "value" in item);
  });
  const items = asArray(block.payload.items).filter((item): item is string => typeof item === "string");

  return (
    <>
      {stats.length ? (
        <div className="visual-stats">
          {stats.map((stat) => (
            <div key={stat.label}>
              <span>{stat.value}</span>
              <p>{stat.label}</p>
            </div>
          ))}
        </div>
      ) : null}
      {items.length ? (
        <div className="visual-pills">
          {items.map((item) => (
            <span key={item}>{item}</span>
          ))}
        </div>
      ) : null}
    </>
  );
}

function ConceptGrid({ block }: { block: VisualInteractiveBlock }) {
  const items = asArray(block.payload.items).filter((item): item is ConceptItem => Boolean(item && typeof item === "object"));
  return (
    <div className="concept-grid">
      {items.map((item, index) => (
        <article className="concept-mini" key={`${item.title ?? "concept"}-${index}`}>
          {item.tag ? <span className={`concept-tag concept-tag--${item.tag.toLowerCase()}`}>{item.tag}</span> : null}
          {item.title ? <h4>{item.title}</h4> : null}
          {item.body ? <p>{item.body}</p> : null}
        </article>
      ))}
    </div>
  );
}

function CalloutBlock({ block }: { block: VisualInteractiveBlock }) {
  const body = typeof block.payload.body === "string" ? block.payload.body : "";
  const tone = typeof block.payload.tone === "string" ? block.payload.tone : "default";
  return <div className={`cheatsheet-callout cheatsheet-callout--${tone}`}>{body}</div>;
}

function ComparisonTable({ block }: { block: VisualInteractiveBlock }) {
  const columns = asArray(block.payload.columns).filter((item): item is string => typeof item === "string");
  const rows = asArray(block.payload.rows).filter((row): row is string[] => Array.isArray(row));
  if (!columns.length || !rows.length) {
    return null;
  }
  return (
    <div className="comparison-table">
      <table>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column}>{column}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={`${row[0] ?? "row"}-${rowIndex}`}>
              {columns.map((column, columnIndex) => (
                <td key={`${column}-${columnIndex}`}>{row[columnIndex] ?? ""}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function QuestionBank({ block, onSourceSelect }: { block: VisualInteractiveBlock; onSourceSelect: (sourceRef: SourceRef) => void }) {
  const questions = asArray(block.payload.questions).filter((item): item is QuestionItem => Boolean(item && typeof item === "object"));
  return (
    <div className="question-bank">
      {questions.map((item, index) => {
        const ref = asSourceRef(item.source_ref);
        return (
          <details className="question-card" key={`${item.question ?? "question"}-${index}`}>
            <summary>
              {item.label ? <span>{item.label}</span> : null}
              {item.question ?? "Review question"}
            </summary>
            <div className="question-card__answer">
              {item.answer ? <p>{item.answer}</p> : null}
              {ref ? <SourceLink sourceRef={ref} onSelect={onSourceSelect} /> : null}
            </div>
          </details>
        );
      })}
    </div>
  );
}

function SourceTimeline({ block, onSourceSelect }: { block: VisualInteractiveBlock; onSourceSelect: (sourceRef: SourceRef) => void }) {
  const events = asArray(block.payload.events).filter((item): item is TimelineEvent => {
    return Boolean(item && typeof item === "object" && "label" in item);
  });

  return (
    <div className="source-timeline">
      {events.map((event, index) => {
        const ref = asSourceRef(event.source_ref);
        return (
          <button
            type="button"
            key={`${event.label}-${index}`}
            className="timeline-node"
            onClick={(clickEvent) => {
              clickEvent.stopPropagation();
              if (ref) {
                onSourceSelect(ref);
              }
            }}
          >
            <span>{event.label}</span>
            {event.summary ? <p>{event.summary}</p> : null}
          </button>
        );
      })}
    </div>
  );
}

function InteractiveChecklist({ block, onSourceSelect }: { block: VisualInteractiveBlock; onSourceSelect: (sourceRef: SourceRef) => void }) {
  const [checked, setChecked] = useState<Set<string>>(() => new Set());
  const items = asArray(block.payload.items).filter((item): item is ChecklistItem => {
    return Boolean(item && typeof item === "object" && "id" in item && "label" in item);
  });

  return (
    <div className="interactive-checklist">
      {items.map((item) => {
        const isChecked = checked.has(item.id);
        const ref = asSourceRef(item.source_ref);
        return (
          <button
            type="button"
            key={item.id}
            className={isChecked ? "check-item check-item--done" : "check-item"}
            onClick={(event) => {
              event.stopPropagation();
              setChecked((current) => {
                const next = new Set(current);
                if (next.has(item.id)) {
                  next.delete(item.id);
                } else {
                  next.add(item.id);
                }
                return next;
              });
              if (ref) {
                onSourceSelect(ref);
              }
            }}
          >
            {isChecked ? <Check size={16} aria-hidden /> : <Circle size={16} aria-hidden />}
            <span>{item.label}</span>
          </button>
        );
      })}
    </div>
  );
}

function AgentSlot({ block }: { block: VisualInteractiveBlock }) {
  const accepted = asArray(block.payload.accepted).filter((item): item is string => typeof item === "string");
  return (
    <div className="agent-slot-placeholder">
      <LayoutTemplate size={20} aria-hidden />
      <div>
        <strong>{String(block.payload.slot_id ?? block.block_id)}</strong>
        {accepted.length ? <p>{accepted.join(", ")}</p> : null}
      </div>
    </div>
  );
}
