from app.ingestion.crawler import CrawlConfig, extract_links, is_allowed_url


def test_is_allowed_url_restricts_domain_and_path_prefix() -> None:
    cfg = CrawlConfig(
        seeds=["https://docs.stripe.com/payments"],
        allowed_domains={"docs.stripe.com"},
        allowed_path_prefixes=("/payments", "/checkout"),
    )

    assert is_allowed_url("https://docs.stripe.com/payments/accept-a-payment", cfg)
    assert not is_allowed_url("https://stripe.com/payments", cfg)
    assert not is_allowed_url("https://docs.stripe.com/billing", cfg)


def test_extract_links_filters_and_normalizes_urls() -> None:
    cfg = CrawlConfig(
        seeds=["https://docs.stripe.com/payments"],
        allowed_domains={"docs.stripe.com"},
        allowed_path_prefixes=("/payments",),
    )
    html = """
    <a href="/payments/accept">A</a>
    <a href="https://docs.stripe.com/payments/accept#fragment">B</a>
    <a href="https://docs.stripe.com/billing">C</a>
    <a href="https://example.com/payments">D</a>
    """

    links = extract_links(html, "https://docs.stripe.com/payments", cfg)

    assert links == ["https://docs.stripe.com/payments/accept"]
