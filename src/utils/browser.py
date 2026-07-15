from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import NoSuchDriverException, SessionNotCreatedException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

try:
    from config import BRAVE_BINARY_PATH, USE_BRAVE_BROWSER
except ImportError:
    USE_BRAVE_BROWSER = True
    BRAVE_BINARY_PATH = ''

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CHROMEDRIVER = ROOT / 'drivers' / 'chromedriver.exe'

APP_CONTROL_HINT = (
    'Windows blocked selenium-manager.exe (Application Control policy).\n'
    'Fix: run  python scripts/setup_chromedriver.py\n'
    'Then set in .env:  CHROMEDRIVER_PATH=drivers/chromedriver.exe\n'
    '                 USE_BRAVE_BROWSER=false'
)


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


def find_chromedriver() -> str | None:
    env_path = os.getenv('CHROMEDRIVER_PATH', '').strip()
    if env_path:
        path = Path(env_path)
        if not path.is_absolute():
            path = ROOT / path
        if path.is_file():
            return str(path.resolve())

    if DEFAULT_CHROMEDRIVER.is_file():
        return str(DEFAULT_CHROMEDRIVER.resolve())

    which = shutil.which('chromedriver')
    if which:
        return which
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
    # Google OAuth often hangs on a white page when Brave Shields / fingerprinting
    # block third-party cookies and redirect callbacks after phone approval.
    options.add_argument(
        '--disable-features=IsolateOrigins,site-per-process,'
        'BraveAdblockCookieListDefault,BraveDarkModeBlock'
    )
    options.add_argument('--disable-site-isolation-trials')
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_experimental_option(
        'prefs',
        {
            'credentials_enable_service': False,
            'profile.password_manager_enabled': False,
            'profile.default_content_setting_values.notifications': 2,
            'profile.cookie_controls_mode': 0,
        },
    )
    return options


def _is_app_control_block(exc: BaseException) -> bool:
    text = str(exc).lower()
    return '4551' in text or 'application control' in text


def _start_driver(options: Options) -> webdriver.Chrome:
    chromedriver = find_chromedriver()
    if chromedriver:
        service = Service(executable_path=chromedriver, log_output=os.devnull)
        return webdriver.Chrome(service=service, options=options)

    try:
        service = Service(log_output=os.devnull)
        return webdriver.Chrome(service=service, options=options)
    except (NoSuchDriverException, WebDriverException, OSError) as exc:
        if _is_app_control_block(exc):
            raise RuntimeError(APP_CONTROL_HINT) from exc
        raise


def create_webdriver(
    *,
    headless: bool = False,
    persistent_profile: str | None = None,
) -> webdriver.Chrome:
    use_brave = _env_bool('USE_BRAVE_BROWSER', USE_BRAVE_BROWSER)
    keep_profile = False
    if persistent_profile:
        profile_path = Path(persistent_profile)
        if not profile_path.is_absolute():
            profile_path = ROOT / profile_path
        profile_path.mkdir(parents=True, exist_ok=True)
        user_data_dir = str(profile_path.resolve())
        keep_profile = True
    else:
        user_data_dir = tempfile.mkdtemp(prefix='autoapply-browser-')

    chromedriver = find_chromedriver()
    if not chromedriver:
        print(
            'Note: No local chromedriver found. If login fails, run:\n'
            '  python scripts/setup_chromedriver.py'
        )

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
            driver._auto_apply_keep_profile = keep_profile
            try:
                driver.execute_cdp_cmd(
                    'Page.addScriptToEvaluateOnNewDocument',
                    {
                        'source': (
                            'Object.defineProperty(navigator, "webdriver", '
                            '{get: () => undefined});'
                        ),
                    },
                )
            except Exception:
                pass
            if browser_name == 'Chrome' and use_brave and find_brave_binary():
                print('Using Google Chrome (Brave could not start).')
            return driver
        except (SessionNotCreatedException, WebDriverException, RuntimeError, OSError) as exc:
            last_error = exc
            if isinstance(exc, RuntimeError) and 'Application Control' in str(exc):
                if not keep_profile:
                    shutil.rmtree(user_data_dir, ignore_errors=True)
                raise
            hint = ''
            if browser_name == 'Brave':
                hint = ' — set USE_BRAVE_BROWSER=false in .env'
            print(f'Warning: {browser_name} failed to start{hint}. Trying next browser...')

    if not keep_profile:
        shutil.rmtree(user_data_dir, ignore_errors=True)
    if last_error and _is_app_control_block(last_error):
        raise RuntimeError(APP_CONTROL_HINT) from last_error
    if last_error:
        raise last_error
    raise RuntimeError('No Chromium browser found. Install Chrome or set CHROME_BINARY_PATH.')


def quit_webdriver(driver: webdriver.Chrome | None) -> None:
    if driver is None:
        return
    profile_dir = getattr(driver, '_auto_apply_profile_dir', None)
    keep_profile = getattr(driver, '_auto_apply_keep_profile', False)
    try:
        driver.quit()
    except Exception:
        pass
    if profile_dir and not keep_profile:
        shutil.rmtree(profile_dir, ignore_errors=True)


def browser_label() -> str:
    if _env_bool('USE_BRAVE_BROWSER', USE_BRAVE_BROWSER) and find_brave_binary():
        return 'Brave'
    if find_chrome_binary():
        return 'Chrome'
    return 'Chromium'
