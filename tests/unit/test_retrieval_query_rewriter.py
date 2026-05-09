from app.retrieval.query_rewriter import rewrite_query


def test_rewrite_query_passthrough_for_standalone_question() -> None:
    q = "How do I confirm a PaymentIntent?"

    rewritten = rewrite_query(q, session_messages=[])

    assert rewritten == "how do i confirm a paymentintent"


def test_rewrite_query_uses_recent_context_for_followup() -> None:
    session_messages = [
        {"role": "user", "content": "How do I create a PaymentIntent?"},
        {"role": "assistant", "content": "Use the Payments API and confirm it later."},
    ]

    rewritten = rewrite_query("What about webhooks?", session_messages=session_messages)

    assert "paymentintent" in rewritten
    assert "webhooks" in rewritten
