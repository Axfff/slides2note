import { Layers } from "lucide-react";
import type { DetailLevel } from "../types/review";

const levels: Array<{ id: DetailLevel; label: string }> = [
  { id: "map", label: "Map" },
  { id: "brief", label: "Brief" },
  { id: "standard", label: "Standard" },
  { id: "evidence", label: "Evidence" },
  { id: "full", label: "Full" },
];

type Props = {
  value: DetailLevel;
  onChange: (value: DetailLevel) => void;
};

export function DetailLevelControl({ value, onChange }: Props) {
  return (
    <div className="detail-control" aria-label="Detail level">
      <Layers size={18} aria-hidden />
      <div className="segmented">
        {levels.map((level) => (
          <button
            key={level.id}
            type="button"
            className={value === level.id ? "active" : ""}
            onClick={() => onChange(level.id)}
          >
            {level.label}
          </button>
        ))}
      </div>
    </div>
  );
}

