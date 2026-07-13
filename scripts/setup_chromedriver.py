"""Download ChromeDriver locally (bypasses blocked selenium-manager.exe on Windows)."""

from __future__ import annotations

import json
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRIVERS_DIR = ROOT / 'drivers'
CHROMEDRIVER_EXE = DRIVERS_DIR / 'chromedriver.exe'

CHROME_CANDIDATES = [
    Path(r'C:\Program Files\Google\Chrome\Application\chrome.exe'),
    Path(r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe'),
    Path.home() / 'AppData/Local/Google/Chrome/Application/chrome.exe',
]

MILESTONES_URL = (
    'https://googlechromelabs.github.io/chrome-for-testing/'
    'latest-versions-per-milestone-with-downloads.json'
)


def detect_chrome_version() -> str | None:
    env = __import__('os').getenv('CHROME_BINARY_PATH', '').strip()
    if env:
        candidates = [Path(env)]
    else:
        candidates = CHROME_CANDIDATES

    for chrome in candidates:
        if not chrome.is_file():
            continue
        app_dir = chrome.parent
        for child in sorted(app_dir.iterdir(), reverse=True):
            if child.is_dir() and child.name[0].isdigit():
                return child.name
        try:
            import win32api  # type: ignore
        except ImportError:
            pass
        try:
            from ctypes import create_string_buffer, windll, sizeof, byref
            from ctypes.wintypes import DWORD

            class VSFixedFileInfo:
                pass

            ver = windll.version.GetFileVersionInfoSizeW(str(chrome), None)
            if ver:
                buf = create_string_buffer(ver)
                windll.version.GetFileVersionInfoW(str(chrome), 0, ver, buf)
                ptr = DWORD()
                length = DWORD()
                windll.version.VerQueryValueW(buf, '\\', byref(ptr), byref(length))
        except Exception:
            pass
    return None


def _download_url_for_version(version: str) -> str | None:
    major = version.split('.')[0]
    try:
        with urllib.request.urlopen(MILESTONES_URL, timeout=30) as resp:
            data = json.load(resp)
    except Exception as exc:
        print(f'Could not fetch Chrome milestones: {exc}')
        return None

    entry = data.get('milestones', {}).get(major)
    if not entry:
        return None
    for item in entry.get('downloads', {}).get('chromedriver', []):
        if item.get('platform') == 'win64':
            return item.get('url')
    return None


def download_chromedriver(version: str | None = None) -> Path:
    version = version or detect_chrome_version()
    if not version:
        raise RuntimeError(
            'Could not detect Google Chrome version. Install Chrome or set CHROME_BINARY_PATH.'
        )

    url = _download_url_for_version(version)
    if not url:
        url = (
            f'https://storage.googleapis.com/chrome-for-testing-public/'
            f'{version}/win64/chromedriver-win64.zip'
        )

    print(f'Chrome version: {version}')
    print(f'Downloading: {url}')
    DRIVERS_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = DRIVERS_DIR / 'chromedriver-win64.zip'

    try:
        urllib.request.urlretrieve(url, zip_path)
    except Exception as exc:
        raise RuntimeError(
            f'Download failed: {exc}\n'
            f'Manually download chromedriver for Chrome {version} from:\n'
            '  https://googlechromelabs.github.io/chrome-for-testing/'
        ) from exc

    with zipfile.ZipFile(zip_path, 'r') as zf:
        members = [n for n in zf.namelist() if n.endswith('chromedriver.exe')]
        if not members:
            raise RuntimeError('chromedriver.exe not found inside zip')
        extracted = DRIVERS_DIR / 'chromedriver.exe'
        with zf.open(members[0]) as src, extracted.open('wb') as dst:
            shutil.copyfileobj(src, dst)

    zip_path.unlink(missing_ok=True)
    print(f'Saved: {extracted}')
    return extracted


def main() -> int:
    try:
        path = download_chromedriver()
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 1
    print()
    print('Add to .env (optional — auto-detected if file exists):')
    print(f'CHROMEDRIVER_PATH={path}')
    print('USE_BRAVE_BROWSER=false')
    return 0


if __name__ == '__main__':
    sys.exit(main())
