# Architecture

This MVP converts a PDF into a source-linked progressive review through a structured pipeline:

```text
PDF upload
-> deterministic extraction
-> SourceFrame / SourceUnit source map
-> rule-based section segmentation
-> mock review generation
-> validation
-> React review workspace
```

The core abstraction is `SourceFrame`. In this milestone, each frame is one PDF page. Each page contains `SourceUnit` text blocks with optional bounding boxes from PyMuPDF.

Generated review content is stored in `ProgressiveReviewIR` JSON. The frontend renders that IR and never relies on model-written HTML. Generated formulas are stored as LaTeX text with `$...$` or `$$...$$` delimiters and rendered client-side with KaTeX. Claims and evidence cards must include `source_refs` so the source viewer can jump back to the original page and highlight a text block when coordinates are available.

The agent layer is represented by `AgentProvider`. `MockAgentProvider` is the default no-key provider. `OpenAIAgentProvider`, `DeepSeekAgentProvider`, and `QwenAgentProvider` can be enabled with environment variables. DeepSeek and Qwen use OpenAI-compatible APIs, with Qwen configured through `DASHSCOPE_API_KEY`, `QWEN_BASE_URL`, and `QWEN_MODEL`. Uploads enqueue a Celery task; the worker writes partial IR and workflow progress after each block so the UI can progressively update by polling.
