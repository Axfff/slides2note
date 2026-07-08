export type DetailLevel = "map" | "brief" | "standard" | "evidence" | "full";

export type BBox = [number, number, number, number];

export type SourceUnit = {
  unit_id: string;
  type: "text_block" | "image_region" | "table";
  text: string;
  bbox?: BBox | null;
};

export type SourceFrame = {
  source_frame_id: string;
  type: "pdf_page";
  index: number;
  image_path: string;
  width?: number | null;
  height?: number | null;
  text: string;
  units: SourceUnit[];
};

export type SourceRef = {
  source_frame_id: string;
  source_unit_id?: string | null;
  page_index?: number | null;
  bbox?: BBox | null;
  quote?: string | null;
};

export type Claim = {
  claim_id: string;
  text: string;
  explanation?: string | null;
  source_refs: SourceRef[];
  confidence: number;
  tags: string[];
  progressive_level: "overview" | "brief" | "standard" | "evidence" | "full";
};

export type EvidenceCard = {
  evidence_id: string;
  claim_id: string;
  title: string;
  evidence_text: string;
  why_it_matters: string;
  caveat?: string | null;
  source_refs: SourceRef[];
};

export type ReviewSection = {
  section_id: string;
  title: string;
  level: number;
  summary: string;
  source_frame_ids: string[];
  children: ReviewSection[];
  key_claim_ids: string[];
  full_notes?: string | null;
};

export type WorkflowProgress = {
  completed_blocks: number;
  total_blocks: number;
};

export type ReviewGenerationPlan = {
  provider: string;
  block_ids: string[];
  strategy: string;
  layout_strategy?: string;
  quality_targets?: string[];
  allowed_visual_block_types?: VisualBlockType[];
};

export type ReviewBlockStatus = {
  block_id: string;
  type: string;
  title: string;
  status: "queued" | "running" | "complete" | "failed";
  source_frame_ids: string[];
  error?: string | null;
  updated_at: string;
};

export type VisualBlockPlacement = "hero" | "after_overview" | "before_sections" | "after_sections" | "source_rail";

export type VisualBlockType =
  | "hero"
  | "visual_summary"
  | "concept_grid"
  | "callout"
  | "comparison_table"
  | "question_bank"
  | "interactive_checklist"
  | "source_timeline"
  | "agent_slot";

export type AgentLayoutSlot = {
  slot_id: string;
  title: string;
  placement: VisualBlockPlacement;
  allowed_block_types: VisualBlockType[];
  source_frame_ids: string[];
  description?: string | null;
  agent_editable: boolean;
};

export type AgentLayoutSpec = {
  mode: "default" | "agent_composed";
  density: "compact" | "comfortable";
  style_preset?: "workspace" | "cheatsheet";
  reading_width_px?: number;
  review_column_min_px: number;
  source_column_min_px: number;
  slots: AgentLayoutSlot[];
  quality_targets?: string[];
  notes?: string | null;
};

export type VisualInteractiveBlock = {
  block_id: string;
  type: VisualBlockType;
  title: string;
  placement: VisualBlockPlacement;
  source_refs: SourceRef[];
  payload: Record<string, unknown>;
  status: "queued" | "running" | "complete" | "failed";
};

export type ProgressiveReviewIR = {
  document_id: string;
  title: string;
  document_type: string;
  source_frames: SourceFrame[];
  outline: ReviewSection[];
  claims: Claim[];
  evidence_cards: EvidenceCard[];
  generated_at: string;
  pipeline_version: string;
  validation?: {
    valid: boolean;
    warnings: string[];
  } | null;
  is_partial?: boolean;
  generation_plan?: ReviewGenerationPlan | null;
  block_statuses?: ReviewBlockStatus[];
  layout_spec?: AgentLayoutSpec | null;
  visual_blocks?: VisualInteractiveBlock[];
};

export type JobSummary = {
  job_id: string;
  status: "queued" | "processing" | "complete" | "failed" | "invalid" | "unknown" | string;
  stage?: string;
  provider?: string;
  progress?: WorkflowProgress;
  is_partial?: boolean;
  current_block_id?: string | null;
  title?: string;
  page_count?: number;
  claim_count?: number;
  evidence_count?: number;
  valid?: boolean;
  warnings?: string[];
  error?: string;
  created_at?: string;
  updated_at?: string;
};
