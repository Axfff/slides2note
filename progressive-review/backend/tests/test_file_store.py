from app.storage.file_store import FileStore


def test_file_store_lists_and_deletes_jobs(tmp_path):
    store = FileStore(tmp_path)
    job_id = store.create_job()
    store.write_status(
        job_id,
        {
            "job_id": job_id,
            "status": "complete",
            "title": "Example",
            "page_count": 2,
            "updated_at": "2026-05-25T00:00:00+00:00",
        },
    )

    jobs = store.list_jobs()

    assert len(jobs) == 1
    assert jobs[0]["job_id"] == job_id
    assert jobs[0]["title"] == "Example"

    store.delete_job(job_id)

    assert store.list_jobs() == []
