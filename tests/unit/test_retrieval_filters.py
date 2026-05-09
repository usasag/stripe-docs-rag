from app.retrieval.metadata_filters import infer_filters


def test_infer_filters_detects_product_area() -> None:
    filters = infer_filters("How do I confirm a PaymentIntent in checkout?")

    assert filters.get("product_area") == "checkout"


def test_infer_filters_empty_when_no_signals() -> None:
    filters = infer_filters("How does Stripe API work generally?")

    assert filters == {}
