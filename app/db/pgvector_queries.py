from typing import Any


def build_match_document_chunks_sql(
    *,
    top_k: int,
    filters: dict[str, Any] | None,
) -> tuple[str, dict[str, Any]]:
    if top_k <= 0:
        raise ValueError("top_k must be positive")

    sql = """
    select *
    from match_document_chunks(
        query_embedding => %(query_embedding)s,
        match_count => %(match_count)s,
        filters => %(filters)s
    );
    """.strip()

    params: dict[str, Any] = {
        "query_embedding": None,
        "match_count": top_k,
        "filters": filters or {},
    }
    return sql, params
