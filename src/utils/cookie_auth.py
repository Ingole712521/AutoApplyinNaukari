from __future__ import annotations
import json
from pathlib import Path
from typing import Any

def load_cookies(path: str | Path) -> list[dict[str, Any]]:
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError('Cookie file must be a JSON array')
    return data

def save_cookies(path: str | Path, cookies: list[dict[str, Any]]) -> None:
    Path(path).write_text(json.dumps(cookies, indent=2), encoding='utf-8')

def apply_cookies_to_session(session, cookies: list[dict[str, Any]]) -> None:
    for cookie in cookies:
        session.set_cookie(name=cookie['name'], value=cookie['value'], domain=cookie.get('domain', '.naukri.com'), path=cookie.get('path', '/'), secure=cookie.get('secure', True), http_only=cookie.get('httpOnly', cookie.get('http_only', False)))

def get_nauk_at_token(session) -> str | None:
    cookie = session.get_cookie('nauk_at')
    return cookie.value if cookie else None

def cookies_to_dict(cookies: list[dict[str, Any]]) -> dict[str, str]:
    return {c['name']: c['value'] for c in cookies}
