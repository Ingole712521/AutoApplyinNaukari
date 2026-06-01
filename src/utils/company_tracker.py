from __future__ import annotations
import re

def normalize_company(name: str) -> str:
    if not name:
        return ''
    cleaned = re.sub('[^\\w\\s]', '', name.lower())
    return re.sub('\\s+', '', cleaned).strip()
