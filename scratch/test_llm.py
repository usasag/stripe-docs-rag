import os
import httpx

# Read key from .env
for line in open('.env'):
    if line.startswith('LITELLM_API_KEY='):
        os.environ['LITELLM_API_KEY'] = line.split('=', 1)[1].strip()

key = os.environ.get('LITELLM_API_KEY', '')
print(f"Key loaded: {key[:20]}...")

r = httpx.post(
    'https://models.inference.ai.azure.com/chat/completions',
    headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
    json={'model': 'gpt-4o-mini', 'messages': [{'role': 'user', 'content': 'Say hello in one sentence'}], 'max_tokens': 30},
    timeout=10.0,
)
print(r.status_code, r.text[:400])
