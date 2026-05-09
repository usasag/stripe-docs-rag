from app.ingestion.normalizer import normalize_document
from app.ingestion.parser import parse_html_document


def test_parser_extracts_title_h1_and_sections() -> None:
    html = """
    <html><head><title>Accept a payment</title></head>
    <body>
      <main>
        <h1>Accept a payment</h1>
        <h2 id="create-paymentintent">Create a PaymentIntent</h2>
        <p>Use PaymentIntent to track lifecycle.</p>
      </main>
    </body></html>
    """

    parsed = parse_html_document("https://docs.stripe.com/payments/accept-a-payment", html)

    assert parsed.title == "Accept a payment"
    assert parsed.h1 == "Accept a payment"
    assert parsed.sections[0].anchor == "create-paymentintent"
    assert "PaymentIntent" in parsed.sections[0].content


def test_normalizer_adds_product_area_metadata() -> None:
    html = """
    <html><body><main><h1>Accept a payment</h1><p>Content.</p></main></body></html>
    """
    parsed = parse_html_document("https://docs.stripe.com/payments/accept-a-payment", html)

    normalized = normalize_document(parsed)

    assert normalized.product_area == "payments"
    assert normalized.metadata["source_domain"] == "docs.stripe.com"
