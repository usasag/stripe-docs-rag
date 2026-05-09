from __future__ import annotations


def infer_filters(query: str) -> dict[str, str]:
    q = query.lower()
    filters: dict[str, str] = {}

    if 'checkout' in q:
        filters['product_area'] = 'checkout'
    elif 'billing' in q or 'subscription' in q:
        filters['product_area'] = 'billing'
    elif 'webhook' in q:
        filters['product_area'] = 'webhooks'
    elif 'paymentintent' in q or 'payments' in q:
        filters['product_area'] = 'payments'

    return filters
