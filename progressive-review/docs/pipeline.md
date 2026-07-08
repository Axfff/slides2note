# Pipeline

1. `POST /api/documents/upload` stores the PDF in `generated/jobs/{job_id}/source.pdf`, writes queued workflow state, enqueues `process_document_job`, and returns immediately.
2. The Celery worker runs deterministic extraction first: page PNGs under `generated/jobs/{job_id}/pages/`, page text, and text-block bounding boxes.
3. `SectionSegmenter` creates a rule-based outline optimized for lecture notes and learning sheets.
4. The selected `AgentProvider` plans review blocks, writes a partial `ProgressiveReviewIR`, then generates overview, section briefs, claims, evidence cards, and validation sequentially.
5. `workflow.json`, `status.json`, and `ir.json` are updated after every stage and block so the frontend can poll progress.

## Agent Output Instructions

Agent providers must return structured JSON fields only. Generated prose may include formulas, but formulas must stay as LaTeX text using `$...$` for inline math and `$$...$$` for display math. Providers must not emit HTML for formulas; the frontend owns formula rendering and converts those delimiters with KaTeX.
6. `GET /api/jobs/{job_id}/ir?allow_partial=true` serves the current structured `ProgressiveReviewIR`.
7. The React app displays partial blocks as they arrive, plus the outline, progressive review, and source page viewer side by side.

Provider selection:

- `AGENT_PROVIDER=mock` requires no key.
- `AGENT_PROVIDER=openai` uses `OPENAI_API_KEY` and `OPENAI_MODEL`.
- `AGENT_PROVIDER=deepseek` uses DeepSeek's OpenAI-compatible endpoint with `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL`, and `DEEPSEEK_MODEL`.
- `AGENT_PROVIDER=qwen` uses Alibaba Cloud Model Studio / DashScope's OpenAI-compatible endpoint with `DASHSCOPE_API_KEY`, `QWEN_BASE_URL`, and `QWEN_MODEL`.

Detail levels are presentation-only:

- Map: overview and structure map
- Brief: overview and section summaries
- Standard: summaries and claims
- Evidence: claims plus evidence cards
- Full: extracted full notes and source quotes
