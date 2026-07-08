# Progressive Review MVP

Local MVP for converting a PDF into a progressive, source-linked review workspace.

## Docker Compose

The easiest way to launch the full system is Docker Compose. It starts:

- FastAPI backend on `http://localhost:8000`
- Celery worker
- Redis
- Vite frontend on `http://localhost:5173`

Create a local env file first:

```bash
cp .env.example .env
```

For the default no-key mock provider, leave `AGENT_PROVIDER=mock`. For Qwen/DeepSeek/OpenAI, set the relevant provider and key in `.env`.

Start everything:

```bash
docker compose up --build
```

Open:

```text
http://localhost:5173
```

Useful commands:

```bash
docker compose ps
docker compose logs -f backend
docker compose logs -f worker
docker compose down
docker compose down -v   # also removes Redis and generated job volumes
```

Generated jobs are stored in the named Docker volume `progressive-review_generated-data`.

## Backend

```bash
cd progressive-review/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Health check:

```bash
curl http://localhost:8000/health
```

## Worker

The agent workflow uses Redis + Celery. Start Redis first, then run a worker from the backend folder:

```bash
redis-server
cd progressive-review/backend
celery -A app.worker.celery_app worker --loglevel=info
```

By default the workflow uses the deterministic mock provider and does not need API keys. To use OpenAI for supported agent steps:

```bash
export AGENT_PROVIDER=openai
export OPENAI_API_KEY=...
export OPENAI_MODEL=gpt-4.1-mini
```

To use DeepSeek through its OpenAI-compatible API:

```bash
export AGENT_PROVIDER=deepseek
export DEEPSEEK_API_KEY=...
export DEEPSEEK_BASE_URL=https://api.deepseek.com
export DEEPSEEK_MODEL=deepseek-v4-flash
```

To use Qwen through Alibaba Cloud Model Studio / DashScope's OpenAI-compatible API:

```bash
export AGENT_PROVIDER=qwen
export DASHSCOPE_API_KEY=...
export QWEN_BASE_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1
export QWEN_MODEL=qwen-plus
```

For the China Beijing endpoint, set `QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1`.

Agent workflow output should remain structured JSON. When an agent includes formulas, it should preserve them as LaTeX text with `$...$` for inline math and `$$...$$` for display math; the frontend renders those delimiters with KaTeX.

## Frontend

```bash
cd progressive-review/frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The default page is the project/job history dashboard where you can create a new PDF generation job, watch block-level progress, open previous jobs, export HTML, refresh status, or delete generated job folders.

## Generated Files

Jobs are stored under:

```text
progressive-review/generated/jobs/{job_id}/
```

Each job contains:

- `source.pdf`
- `pages/page_001.png`, etc.
- `source_frames.json`
- `ir.json`
- `status.json`
- `workflow.json`

## Tests

```bash
cd progressive-review/backend
pytest
```

## Current Limitations

- PDF only.
- No OCR for scanned pages.
- Rule-based segmentation and extractive claim generation.
- Real workflow execution requires Redis and a Celery worker.
- BBox highlights depend on PyMuPDF text blocks and may be coarse.
- HTML export is a simple structured JSON export; the React app is the primary view.
