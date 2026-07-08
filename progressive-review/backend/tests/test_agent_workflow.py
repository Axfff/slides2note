from pathlib import Path

import fitz
from fastapi.testclient import TestClient

import app.main as main_module
from app.agents.mock_provider import MockAgentProvider
from app.agents.factory import get_agent_provider
from app.agents.qwen_provider import normalize_qwen_model
from app.services.agent_workflow import AgentWorkflowRunner
from app.storage.file_store import FileStore


def _make_pdf(path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Week 8: Time Complexity & Class P")
    page.insert_text((72, 104), "Textbook Def. 7.12 - P is decidable in polynomial time.")
    doc.save(path)
    doc.close()


def test_agent_workflow_writes_stage_transitions_and_complete_ir(tmp_path, monkeypatch):
    pdf_path = tmp_path / "sample.pdf"
    _make_pdf(pdf_path)
    store = FileStore(tmp_path / "jobs")
    job_id = store.create_job()
    store.save_upload(job_id, pdf_path, "sample.pdf")
    stages: list[str] = []
    original_write_workflow = store.write_workflow

    def record_workflow(job_id_arg, workflow):
        stages.append(workflow["stage"])
        original_write_workflow(job_id_arg, workflow)

    monkeypatch.setattr(store, "write_workflow", record_workflow)

    ir = AgentWorkflowRunner(store).run(job_id, store.job_dir(job_id) / "source.pdf", "mock")
    workflow = store.read_workflow(job_id)

    assert "extracting" in stages
    assert "planning" in stages
    assert "generating_overview" in stages
    assert "generating_blocks" in stages
    assert "validating" in stages
    assert workflow["stage"] == "complete"
    assert workflow["progress"]["completed_blocks"] == workflow["progress"]["total_blocks"]
    assert not ir.is_partial
    assert ir.generation_plan
    assert all(block.status == "complete" for block in ir.block_statuses)
    assert all(claim.source_refs for claim in ir.claims)
    assert all(card.source_refs for card in ir.evidence_cards)


def test_agent_workflow_preserves_partial_ir_on_failure(tmp_path, monkeypatch):
    class FailingProvider(MockAgentProvider):
        name = "failing"

        def generate_claims(self, section, extracted, start_index):
            raise RuntimeError("provider failed")

    pdf_path = tmp_path / "sample.pdf"
    _make_pdf(pdf_path)
    store = FileStore(tmp_path / "jobs")
    job_id = store.create_job()
    store.save_upload(job_id, pdf_path, "sample.pdf")
    monkeypatch.setattr("app.services.agent_workflow.get_agent_provider", lambda _name=None: FailingProvider())

    try:
        AgentWorkflowRunner(store).run(job_id, store.job_dir(job_id) / "source.pdf", "failing")
    except RuntimeError:
        pass

    workflow = store.read_workflow(job_id)
    ir = store.read_json(job_id, "ir.json")

    assert workflow["stage"] == "failed"
    assert workflow["error"] == "provider failed"
    assert ir["is_partial"]
    assert ir["source_frames"]
    assert ir["outline"]


def test_upload_enqueues_job_and_returns_queued(tmp_path, monkeypatch):
    pdf_path = tmp_path / "sample.pdf"
    _make_pdf(pdf_path)
    store = FileStore(tmp_path / "jobs")
    enqueued: list[tuple[str, str]] = []

    class FakeTask:
        @staticmethod
        def delay(job_id, provider_name):
            enqueued.append((job_id, provider_name))

    monkeypatch.setattr(main_module, "store", store)
    monkeypatch.setattr(main_module, "workflow_runner", AgentWorkflowRunner(store))
    monkeypatch.setattr(main_module, "process_document_job", FakeTask)

    client = TestClient(main_module.app)
    response = client.post(
        "/api/documents/upload",
        files={"file": ("sample.pdf", pdf_path.read_bytes(), "application/pdf")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "queued"
    assert enqueued == [(data["job_id"], "mock")]
    assert store.read_status(data["job_id"])["stage"] == "queued"


def test_deepseek_provider_requires_key(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    try:
        get_agent_provider("deepseek")
    except RuntimeError as exc:
        assert "DEEPSEEK_API_KEY" in str(exc)
    else:
        raise AssertionError("DeepSeek provider should require DEEPSEEK_API_KEY")


def test_deepseek_provider_plans_with_deepseek_name(tmp_path, monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    pdf_path = tmp_path / "sample.pdf"
    _make_pdf(pdf_path)
    store = FileStore(tmp_path / "jobs")
    job_id = store.create_job()
    store.save_upload(job_id, pdf_path, "sample.pdf")

    ir = AgentWorkflowRunner(store).run(job_id, store.job_dir(job_id) / "source.pdf", "deepseek")

    assert ir.generation_plan
    assert ir.generation_plan.provider == "deepseek"
    assert store.read_workflow(job_id)["provider"] == "deepseek"


def test_qwen_provider_requires_key(monkeypatch):
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    monkeypatch.delenv("QWEN_API_KEY", raising=False)

    try:
        get_agent_provider("qwen")
    except RuntimeError as exc:
        assert "DASHSCOPE_API_KEY" in str(exc)
    else:
        raise AssertionError("Qwen provider should require DASHSCOPE_API_KEY or QWEN_API_KEY")


def test_qwen_provider_plans_with_qwen_name(tmp_path, monkeypatch):
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    pdf_path = tmp_path / "sample.pdf"
    _make_pdf(pdf_path)
    store = FileStore(tmp_path / "jobs")
    job_id = store.create_job()
    store.save_upload(job_id, pdf_path, "sample.pdf")

    ir = AgentWorkflowRunner(store).run(job_id, store.job_dir(job_id) / "source.pdf", "qwen")

    assert ir.generation_plan
    assert ir.generation_plan.provider == "qwen"
    assert store.read_workflow(job_id)["provider"] == "qwen"


def test_qwen_model_alias_normalization():
    assert normalize_qwen_model("qwen3.7max") == "qwen3.7-max"
    assert normalize_qwen_model("qwen-plus") == "qwen-plus"
