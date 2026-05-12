import httpx
import re

html1 = httpx.get('https://docs.stripe.com/api/setup_intents').text
html2 = httpx.get('https://docs.stripe.com/payments/payment-intents').text

print("API Docs articles:", len(re.findall(r'<article[^>]*>', html1, re.IGNORECASE)))
print("Normal Docs articles:", len(re.findall(r'<article[^>]*>', html2, re.IGNORECASE)))
