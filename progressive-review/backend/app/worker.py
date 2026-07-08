from celery import Celery

from app.config import CELERY_BROKER_URL, CELERY_RESULT_BACKEND
from app.services.agent_workflow import AgentWorkflowRunner
from app.storage.file_store import FileStore


celery_app = Celery("progressive_review", broker=CELERY_BROKER_URL, backend=CELERY_RESULT_BACKEND)


@celery_app.task(name="app.worker.process_document_job")
def process_document_job(job_id: str, provider_name: str | None = None) -> dict:
    store = FileStore()
    source_candidates = sorted(store.job_dir(job_id).glob("source.*"))
    if not source_candidates:
        raise FileNotFoundError(f"No source file found for job {job_id}")
    ir = AgentWorkflowRunner(store).run(job_id, source_candidates[0], provider_name)
    return {"job_id": job_id, "title": ir.title, "is_partial": ir.is_partial}

