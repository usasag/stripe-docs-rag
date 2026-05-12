"""
Interactive helper to configure LLM provider credentials in .env.

Behavior:
- If a supported API key is already set, prints "API keys set successfully".
- Otherwise asks the user to choose provider (github|anthropic), enter key,
  validates it with a lightweight API call, and writes env vars to .env.
"""

from __future__ import annotations

from pathlib import Path

import httpx


ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / '.env'


def _parse_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding='utf-8').splitlines():
        s = line.strip()
        if not s or s.startswith('#') or '=' not in s:
            continue
        k, v = s.split('=', 1)
        out[k.strip()] = v.strip()
    return out


def _write_env(path: Path, updates: dict[str, str]) -> None:
    lines = path.read_text(encoding='utf-8').splitlines() if path.exists() else []
    keys = set(updates.keys())
    seen: set[str] = set()
    out_lines: list[str] = []

    for line in lines:
        if '=' in line and not line.strip().startswith('#'):
            k = line.split('=', 1)[0].strip()
            if k in updates:
                out_lines.append(f"{k}={updates[k]}")
                seen.add(k)
                continue
        out_lines.append(line)

    for k in keys - seen:
        out_lines.append(f"{k}={updates[k]}")

    path.write_text('\n'.join(out_lines).rstrip() + '\n', encoding='utf-8')


def _validate_github(key: str, model: str) -> tuple[bool, str]:
    try:
        resp = httpx.post(
            'https://models.inference.ai.azure.com/chat/completions',
            headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
            json={
                'model': model,
                'messages': [{'role': 'user', 'content': 'ping'}],
                'max_tokens': 5,
                'temperature': 0.0,
            },
            timeout=15.0,
        )
        if resp.status_code >= 400:
            return False, f'GitHub validation failed: HTTP {resp.status_code} {resp.text[:200]}'
        return True, 'GitHub key validated.'
    except Exception as e:
        return False, f'GitHub validation error: {e}'


def _validate_anthropic(key: str, model: str) -> tuple[bool, str]:
    try:
        resp = httpx.post(
            'https://api.anthropic.com/v1/messages',
            headers={
                'x-api-key': key,
                'anthropic-version': '2023-06-01',
                'Content-Type': 'application/json',
            },
            json={
                'model': model,
                'max_tokens': 5,
                'messages': [{'role': 'user', 'content': 'ping'}],
            },
            timeout=15.0,
        )
        if resp.status_code >= 400:
            return False, f'Anthropic validation failed: HTTP {resp.status_code} {resp.text[:200]}'
        return True, 'Anthropic key validated.'
    except Exception as e:
        return False, f'Anthropic validation error: {e}'


def main() -> int:
    env = _parse_env(ENV_PATH)

    has_github = bool(env.get('LITELLM_API_KEY', '').strip())
    has_anthropic = bool(env.get('ANTHROPIC_API_KEY', '').strip())
    if has_github or has_anthropic:
        print('API keys set successfully')
        return 0

    provider = input('Choose LLM provider (github/anthropic): ').strip().lower()
    if provider not in {'github', 'anthropic'}:
        print('Invalid provider. Choose github or anthropic.')
        return 1

    if provider == 'github':
        model = 'gpt-4o-mini'
        print(f'Using fixed model for GitHub provider: {model}')
        key = input('Enter GitHub API key: ').strip()
        ok, msg = _validate_github(key, model)
        print(msg)
        if not ok:
            return 1
        _write_env(
            ENV_PATH,
            {
                'LLM_PROVIDER': 'github',
                'LLM_MODEL': model,
                'LITELLM_API_KEY': key,
            },
        )
    else:
        model = 'claude-sonnet-4-5-20250929'
        print(f'Using fixed model for Anthropic provider: {model}')
        key = input('Enter Anthropic API key: ').strip()
        ok, msg = _validate_anthropic(key, model)
        print(msg)
        if not ok:
            return 1
        _write_env(
            ENV_PATH,
            {
                'LLM_PROVIDER': 'anthropic',
                'LLM_MODEL': model,
                'ANTHROPIC_API_KEY': key,
            },
        )

    print('API keys set successfully')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
