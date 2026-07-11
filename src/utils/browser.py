from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import SessionNotCreatedException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

try:
    from config import BRAVE_BINARY_PATH, USE_BRAVE_BROWSER
except ImportError:
    USE_BRAVE_BROWSER = True
    BRAVE_BINARY_PATH = ''


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ('1', 'true', 'yes', 'on')


def find_brave_binary() -> str | None:
    if BRAVE_BINARY_PATH:
        path = Path(BRAVE_BINARY_PATH)
        if path.is_file():
            return str(path)
    env_path = os.getenv('BRAVE_BINARY_PATH', '').strip()
    if env_path and Path(env_path).is_file():
        return env_path
    candidates = [
        Path(r'C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe'),
        Path(r'C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe'),
        Path.home() / 'AppData/Local/BraveSoftware/Brave-Browser/Application/brave.exe',
    ]
    for path in candidates:
        if path.is_file():
            return str(path)
    return None


def find_chrome_binary() -> str | None:
    env_path = os.getenv('CHROME_BINARY_PATH', '').strip()
    if env_path and Path(env_path).is_file():
        return env_path
    candidates = [
        Path(r'C:\Program Files\Google\Chrome\Application\chrome.exe'),
        Path(r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe'),
        Path.home() / 'AppData/Local/Google/Chrome/Application/chrome.exe',
    ]
    for path in candidates:
        if path.is_file():
            return str(path)
    return None


def _build_options(*, binary: str | None, headless: bool, user_data_dir: str) -> Options:
    options = Options()
    if binary:
        options.binary_location = binary
    if headless:
        options.add_argument('--headless=new')
    options.add_argument('--start-maximized')
    options.add_argument('--no-first-run')
    options.add_argument('--no-default-browser-check')
    options.add_argument('--disable-popup-blocking')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--remote-debugging-port=0')
    options.add_argument(f'--user-data-dir={user_data_dir}')
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)
    return options


def _start_driver(options: Options) -> webdriver.Chrome:
    service = Service(log_output=os.devnull)
    return webdriver.Chrome(service=service, options=options)


def create_webdriver(*, headless: bool = False) -> webdriver.Chrome:
    use_brave = _env_bool('USE_BRAVE_BROWSER', USE_BRAVE_BROWSER)
    user_data_dir = tempfile.mkdtemp(prefix='autoapply-browser-')
    attempts: list[tuple[str, str | None]] = []

    if use_brave and find_brave_binary():
        attempts.append(('Brave', find_brave_binary()))
    attempts.append(('Chrome', find_chrome_binary()))

    last_error: Exception | None = None
    for browser_name, binary in attempts:
        if binary is None and browser_name == 'Chrome':
            continue
        options = _build_options(binary=binary, headless=headless, user_data_dir=user_data_dir)
        try:
            driver = _start_driver(options)
            driver._auto_apply_browser = browser_name
            driver._auto_apply_profile_dir = user_data_dir
            if browser_name == 'Chrome' and use_brave and find_brave_binary():
                print('Using Google Chrome (Brave could not start).')
            return driver
        except (SessionNotCreatedException, WebDriverException) as exc:
            last_error = exc
            hint = ''
            if browser_name == 'Brave':
                hint = ' (often ChromeDriver/Brave version mismatch — set USE_BRAVE_BROWSER=false in .env to use Chrome only)'
            print(f'Warning: {browser_name} failed to start{hint}. Trying next browser...')

    shutil.rmtree(user_data_dir, ignore_errors=True)
    if last_error:
        raise last_error
    raise RuntimeError('No Chromium browser found. Install Brave or Chrome, or set BRAVE_BINARY_PATH / CHROME_BINARY_PATH.')


def quit_webdriver(driver: webdriver.Chrome | None) -> None:
    if driver is None:
        return
    profile_dir = getattr(driver, '_auto_apply_profile_dir', None)
    try:
        driver.quit()
    except Exception:
        pass
    if profile_dir:
        shutil.rmtree(profile_dir, ignore_errors=True)


def browser_label() -> str:
    if _env_bool('USE_BRAVE_BROWSER', USE_BRAVE_BROWSER) and find_brave_binary():
        return 'Brave'
    if find_chrome_binary():
        return 'Chrome'
    return 'Chromium'
