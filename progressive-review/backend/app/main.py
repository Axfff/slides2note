import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse

from app.models.review_ir import ProgressiveReviewIR
from app.config import AGENT_PROVIDER
from app.services.agent_workflow import AgentWorkflowRunner
from app.storage.file_store import FileStore
from app.worker import process_document_job


app = FastAPI(title="Progressive Review MVP")
store = FileStore()
workflow_runner = AgentWorkflowRunner(store)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):517[3-9]",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/providers")
def providers() -> dict:
    configured = {
        "mock": True,
        "openai": bool(os.getenv("OPENAI_API_KEY")),
        "deepseek": bool(os.getenv("DEEPSEEK_API_KEY")),
        "qwen": bool(os.getenv("DASHSCOPE_API_KEY") or os.getenv("QWEN_API_KEY")),
    }
    return {
        "default": AGENT_PROVIDER or "mock",
        "providers": [
            {"id": "mock", "label": "Mock", "configured": configured["mock"], "uses_ai": False},
            {"id": "qwen", "label": "Qwen", "configured": configured["qwen"], "uses_ai": True},
            {"id": "deepseek", "label": "DeepSeek", "configured": configured["deepseek"], "uses_ai": True},
            {"id": "openai", "label": "OpenAI", "configured": configured["openai"], "uses_ai": True},
        ],
    }


@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...), provider: str | None = Form(default=None)) -> dict[str, str]:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF uploads are supported in this MVP.")
    provider_name = (provider or AGENT_PROVIDER).lower().strip()
    if provider_name not in {"mock", "openai", "deepseek", "qwen"}:
        raise HTTPException(status_code=400, detail="Unsupported agent provider.")
    if provider_name == "openai" and not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(status_code=400, detail="OPENAI_API_KEY is required for OpenAI jobs.")
    if provider_name == "deepseek" and not os.getenv("DEEPSEEK_API_KEY"):
        raise HTTPException(status_code=400, detail="DEEPSEEK_API_KEY is required for DeepSeek jobs.")
    if provider_name == "qwen" and not (os.getenv("DASHSCOPE_API_KEY") or os.getenv("QWEN_API_KEY")):
        raise HTTPException(status_code=400, detail="DASHSCOPE_API_KEY or QWEN_API_KEY is required for Qwen jobs.")

    job_id = store.create_job()
    with NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp_path = Path(tmp.name)
        while chunk := await file.read(1024 * 1024):
            tmp.write(chunk)

    try:
        pdf_path = store.save_upload(job_id, tmp_path, file.filename)
        workflow_runner.initialize_queued_job(job_id, provider_name)
        process_document_job.delay(job_id, provider_name)
    except Exception as exc:
        try:
            workflow = store.read_status(job_id)
            workflow.update({"status": "failed", "stage": "failed", "error": str(exc), "is_partial": True})
            store.write_status(job_id, workflow)
        except FileNotFoundError:
            pass
        raise HTTPException(status_code=503, detail=f"Could not enqueue document job: {exc}") from exc
    finally:
        tmp_path.unlink(missing_ok=True)

    return {"job_id": job_id, "status": "queued"}


@app.get("/api/jobs")
def list_jobs() -> dict[str, list[dict]]:
    return {"jobs": store.list_jobs()}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict:
    try:
        return store.read_status(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc


@app.delete("/api/jobs/{job_id}")
def delete_job(job_id: str) -> dict[str, str]:
    try:
        store.delete_job(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc
    return {"job_id": job_id, "status": "deleted"}


@app.get("/api/jobs/{job_id}/ir", response_model=ProgressiveReviewIR)
def get_ir(job_id: str, allow_partial: bool = True) -> dict:
    try:
        return store.read_json(job_id, "ir.json")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="IR not found") from exc


@app.get("/api/jobs/{job_id}/frames/{frame_id}/image")
def get_frame_image(job_id: str, frame_id: str) -> FileResponse:
    try:
        ir = store.read_json(job_id, "ir.json")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc

    frame = next((item for item in ir["source_frames"] if item["source_frame_id"] == frame_id), None)
    if not frame:
        raise HTTPException(status_code=404, detail="Frame not found")
    image_path = store.job_dir(job_id) / frame["image_path"]
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(image_path, media_type="image/png")


@app.get("/api/jobs/{job_id}/export/html")
def export_html(job_id: str) -> HTMLResponse:
    try:
        ir = store.read_json(job_id, "ir.json")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="IR not found") from exc

    title = ir.get("title", "Progressive Review")
    ir_json = json.dumps(ir, ensure_ascii=False)
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <style>
    body {{ font-family: Inter, system-ui, sans-serif; margin: 0; background: #f7f7f5; color: #1c1c1a; }}
    main {{ max-width: 920px; margin: 0 auto; padding: 32px; }}
    section {{ border-bottom: 1px solid #ddd; padding: 18px 0; }}
    button {{ border: 1px solid #888; background: white; border-radius: 6px; padding: 6px 10px; cursor: pointer; }}
    pre {{ white-space: pre-wrap; background: #fff; padding: 12px; border: 1px solid #ddd; border-radius: 8px; }}
  </style>
</head>
<body>
  <main>
    <h1>{title}</h1>
    <p>Exported structured review. Use the local React app for side-by-side source sync.</p>
    <pre id="ir"></pre>
  </main>
  <script>
    const ir = {ir_json};
    document.getElementById("ir").textContent = JSON.stringify(ir, null, 2);
  </script>
</body>
</html>"""
    return HTMLResponse(html)
