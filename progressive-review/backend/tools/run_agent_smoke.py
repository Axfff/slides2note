import argparse
import json
from pathlib import Path

import fitz

from app.services.agent_workflow import AgentWorkflowRunner
from app.storage.file_store import FileStore


def make_sample_pdf(path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Agent smoke test: Source-linked review")
    page.insert_text((72, 104), "Textbook Def. 1 - A supported claim must cite its source page.")
    page.insert_text((72, 136), "Example: Clicking a generated claim should jump to the original PDF evidence.")
    doc.save(path)
    doc.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", default="mock")
    parser.add_argument("--pdf", type=Path)
    args = parser.parse_args()

    store = FileStore()
    job_id = store.create_job()
    source_pdf = args.pdf
    if source_pdf is None:
        source_pdf = store.job_dir(job_id) / "smoke-source.pdf"
        make_sample_pdf(source_pdf)
    pdf_path = store.save_upload(job_id, source_pdf, source_pdf.name)

    original_write_workflow = store.write_workflow

    def monitored_write(job_id_arg: str, workflow: dict) -> None:
        original_write_workflow(job_id_arg, workflow)
        print(
            json.dumps(
                {
                    "event": "workflow",
                    "job_id": job_id_arg,
                    "stage": workflow.get("stage"),
                    "status": workflow.get("status"),
                    "provider": workflow.get("provider"),
                    "current_block_id": workflow.get("current_block_id"),
                    "progress": workflow.get("progress"),
                    "error": workflow.get("error"),
                },
                ensure_ascii=False,
            ),
            flush=True,
        )

    store.write_workflow = monitored_write  # type: ignore[method-assign]
    ir = AgentWorkflowRunner(store).run(job_id, pdf_path, args.provider)
    print(
        json.dumps(
            {
                "event": "complete",
                "job_id": job_id,
                "title": ir.title,
                "claims": len(ir.claims),
                "evidence_cards": len(ir.evidence_cards),
                "is_partial": ir.is_partial,
                "valid": ir.validation.valid if ir.validation else None,
                "warnings": ir.validation.warnings if ir.validation else [],
            },
            ensure_ascii=False,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
