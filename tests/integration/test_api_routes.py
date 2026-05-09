from fastapi.testclient import TestClient

from app.main import app


def test_search_chat_sessions_ingest_and_evals_routes() -> None:
    client = TestClient(app)

    search_res = client.post(
        "/search",
        json={"query": "How do I confirm a PaymentIntent?", "top_k": 5},
    )
    if search_res.status_code != 200:
        print(f"ERROR: {search_res.text}")
    assert search_res.status_code == 200
    search_body = search_res.json()
    assert "rewritten_query" in search_body
    assert "results" in search_body

    chat_res = client.post(
        "/chat",
        json={"message": "How do I confirm a PaymentIntent?", "top_k": 5, "max_citations": 3},
    )
    assert chat_res.status_code == 200
    chat_body = chat_res.json()
    assert chat_body["session_id"]
    assert "answer" in chat_body
    assert "citations" in chat_body

    session_id = chat_body["session_id"]
    sess_res = client.get(f"/sessions/{session_id}")
    assert sess_res.status_code == 200
    assert sess_res.json()["session_id"] == session_id

    msgs_res = client.get(f"/sessions/{session_id}/messages")
    assert msgs_res.status_code == 200
    assert len(msgs_res.json()["messages"]) >= 2

    ingest_run = client.post("/ingest/run", json={"scope": "payments"})
    assert ingest_run.status_code == 200
    ingest_job = ingest_run.json()["job_id"]

    ingest_status = client.get(f"/ingest/status/{ingest_job}")
    assert ingest_status.status_code == 200
    assert ingest_status.json()["job_id"] == ingest_job
    assert ingest_status.json()["status"] in {"completed", "running"}

    eval_run = client.post("/evals/run", json={"suite_name": "smoke"})
    assert eval_run.status_code == 200
    eval_body = eval_run.json()
    assert eval_body["eval_run_id"]
    assert "summary" in eval_body

    latest = client.get("/evals/latest")
    assert latest.status_code == 200
    assert latest.json()["eval_run_id"] == eval_body["eval_run_id"]
