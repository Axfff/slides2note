import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import JOBS_DIR


class FileStore:
    def __init__(self, jobs_dir: Path = JOBS_DIR):
        self.jobs_dir = jobs_dir
        self.jobs_dir.mkdir(parents=True, exist_ok=True)

    def create_job(self) -> str:
        job_id = uuid.uuid4().hex[:12]
        self.job_dir(job_id).mkdir(parents=True, exist_ok=False)
        self.pages_dir(job_id).mkdir(parents=True, exist_ok=True)
        return job_id

    def job_dir(self, job_id: str) -> Path:
        return self.jobs_dir / job_id

    def pages_dir(self, job_id: str) -> Path:
        return self.job_dir(job_id) / "pages"

    def save_upload(self, job_id: str, source_file: Path, original_name: str) -> Path:
        suffix = Path(original_name).suffix or ".pdf"
        dest = self.job_dir(job_id) / f"source{suffix}"
        shutil.copyfile(source_file, dest)
        return dest

    def write_json(self, job_id: str, name: str, data: dict[str, Any]) -> Path:
        path = self.job_dir(job_id) / name
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def read_json(self, job_id: str, name: str) -> dict[str, Any]:
        path = self.job_dir(job_id) / name
        return json.loads(path.read_text(encoding="utf-8"))

    def status_path(self, job_id: str) -> Path:
        return self.job_dir(job_id) / "status.json"

    def write_status(self, job_id: str, status: dict[str, Any]) -> None:
        self.write_json(job_id, "status.json", status)

    def read_status(self, job_id: str) -> dict[str, Any]:
        return self.read_json(job_id, "status.json")

    def write_workflow(self, job_id: str, workflow: dict[str, Any]) -> None:
        self.write_json(job_id, "workflow.json", workflow)

    def read_workflow(self, job_id: str) -> dict[str, Any]:
        return self.read_json(job_id, "workflow.json")

    def list_jobs(self) -> list[dict[str, Any]]:
        jobs: list[dict[str, Any]] = []
        for job_dir in self.jobs_dir.iterdir():
            if not job_dir.is_dir():
                continue
            status_path = job_dir / "status.json"
            if status_path.exists():
                try:
                    status = json.loads(status_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    status = {"job_id": job_dir.name, "status": "invalid", "error": "Invalid status.json"}
            else:
                status = {"job_id": job_dir.name, "status": "unknown"}

            workflow_path = job_dir / "workflow.json"
            if workflow_path.exists():
                try:
                    workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
                    status = {**status, **{key: value for key, value in workflow.items() if key not in {"block_statuses"}}}
                except json.JSONDecodeError:
                    status.setdefault("workflow_error", "Invalid workflow.json")

            stat = status_path.stat() if status_path.exists() else job_dir.stat()
            updated_at = datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()
            status.setdefault("job_id", job_dir.name)
            status.setdefault("updated_at", updated_at)
            status.setdefault("created_at", updated_at)
            jobs.append(status)

        return sorted(jobs, key=lambda item: item.get("updated_at", ""), reverse=True)

    def delete_job(self, job_id: str) -> None:
        job_dir = self.job_dir(job_id)
        if not job_dir.exists():
            raise FileNotFoundError(job_id)
        shutil.rmtree(job_dir)
