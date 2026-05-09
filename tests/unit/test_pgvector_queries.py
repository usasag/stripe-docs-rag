import json

from app.db.pgvector_queries import build_match_document_chunks_sql


def test_build_match_query_defaults_filters_to_empty_json() -> None:
    sql, params = build_match_document_chunks_sql(top_k=8, filters=None)

    assert "match_document_chunks" in sql
    assert params["match_count"] == 8
    assert params["filters"] == {}


def test_build_match_query_keeps_filter_values() -> None:
    sql, params = build_match_document_chunks_sql(
        top_k=5,
        filters={"product_area": "payments", "doc_type": "guide"},
    )

    assert "match_document_chunks" in sql
    assert json.dumps(params["filters"], sort_keys=True) == json.dumps(
        {"product_area": "payments", "doc_type": "guide"}, sort_keys=True
    )
