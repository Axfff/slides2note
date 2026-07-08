import { FileText } from "lucide-react";
import type { ReviewSection } from "../types/review";

type Props = {
  sections: ReviewSection[];
  activeSectionId?: string;
};

function flatten(sections: ReviewSection[]): ReviewSection[] {
  return sections.flatMap((section) => [section, ...flatten(section.children ?? [])]);
}

export function OutlineSidebar({ sections, activeSectionId }: Props) {
  const items = flatten(sections).filter((section) => section.section_id !== "overview");

  return (
    <aside className="outline">
      <div className="panel-heading">
        <FileText size={18} aria-hidden />
        <span>Outline</span>
      </div>
      <nav>
        {items.map((section) => (
          <a
            key={section.section_id}
            href={`#${section.section_id}`}
            className={activeSectionId === section.section_id ? "active" : ""}
            style={{ paddingLeft: `${12 + section.level * 10}px` }}
          >
            {section.title}
          </a>
        ))}
      </nav>
    </aside>
  );
}

