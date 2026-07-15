from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from src.utils.browser import browser_label, create_webdriver, quit_webdriver

LOGIN_URL = 'https://www.naukri.com/nlogin/login'
HOME_URL = 'https://www.naukri.com/mnjuser/homepage'
RECOMMENDED_URL = 'https://www.naukri.com/mnjuser/recommendedjobs'
OUTPUT_FILE = Path('naukri_cookies.json')
PROFILE_DIR = Path('.browser-profiles') / 'naukri-google-login'
TIMEOUT_SEC = 300


def _has_login_cookie(driver) -> bool:
    try:
        cookies = driver.get_cookies()
    except Exception:
        return False
    return any(c.get('name') == 'nauk_at' for c in cookies)


def _save_cookies(driver) -> int:
    cookies = driver.get_cookies()
    OUTPUT_FILE.write_text(json.dumps(cookies, indent=2), encoding='utf-8')
    return len(cookies)


def _page_looks_blank(driver) -> bool:
    try:
        url = (driver.current_url or '').lower()
        title = (driver.title or '').strip().lower()
        body = ''
        try:
            body = (driver.find_element('tag name', 'body').text or '').strip()
        except Exception:
            body = ''
        if url in ('', 'about:blank', 'data:,'):
            return True
        if 'accounts.google.com' in url and len(body) < 40 and title in ('', 'google', 'sign in'):
            return True
        if len(body) < 20 and 'naukri' not in url and 'google' in url:
            return True
    except Exception:
        return False
    return False


def _focus_best_window(driver, main_handle: str) -> None:
    try:
        handles = list(driver.window_handles)
    except Exception:
        return
    if not handles:
        return

    # Prefer a Naukri tab if one exists; otherwise keep Google auth tabs alive.
    for handle in handles:
        try:
            driver.switch_to.window(handle)
            url = (driver.current_url or '').lower()
            if 'naukri.com' in url and 'login' not in url:
                return
        except Exception:
            continue

    for handle in handles:
        try:
            driver.switch_to.window(handle)
            url = (driver.current_url or '').lower()
            if 'accounts.google.com' in url or 'naukri.com' in url:
                return
        except Exception:
            continue

    try:
        if main_handle in handles:
            driver.switch_to.window(main_handle)
        else:
            driver.switch_to.window(handles[0])
    except Exception:
        pass


def _recover_from_white_screen(driver, main_handle: str, last_recover_at: float) -> float:
    if time.time() - last_recover_at < 8:
        return last_recover_at
    if not _page_looks_blank(driver):
        return last_recover_at

    print('  White/blank Google page detected — recovering...')
    try:
        handles = list(driver.window_handles)
    except Exception:
        handles = []

    # Close blank Google popups; keep the original Naukri window.
    for handle in list(handles):
        if handle == main_handle:
            continue
        try:
            driver.switch_to.window(handle)
            url = (driver.current_url or '').lower()
            if _page_looks_blank(driver) or 'accounts.google.com' in url:
                driver.close()
        except Exception:
            pass

    try:
        remaining = list(driver.window_handles)
        if main_handle in remaining:
            driver.switch_to.window(main_handle)
        elif remaining:
            driver.switch_to.window(remaining[0])
            main_handle = remaining[0]
    except Exception:
        pass

    # After phone approval, cookies may already exist even if the UI hung.
    for url in (HOME_URL, RECOMMENDED_URL, LOGIN_URL):
        try:
            driver.get(url)
            time.sleep(2)
            if _has_login_cookie(driver):
                return time.time()
        except Exception:
            continue
    return time.time()


def main() -> int:
    label = browser_label()
    print('=' * 60)
    print(' Naukri Google Sign-In')
    print('=' * 60)
    print()
    print(f'1. {label} will open the Naukri login page')
    print("2. Click 'Continue with Google' / 'Sign in with Google'")
    print('3. Approve on your phone when asked')
    print('4. If Brave shows a white screen, leave it — this script recovers')
    print('5. Cookies save automatically when login succeeds')
    print()
    print('Tip: If white screen keeps happening, use Chrome instead:')
    print('  set USE_BRAVE_BROWSER=false')
    print()
    print(f'Waiting up to {TIMEOUT_SEC // 60} minutes...')
    print()

    driver = create_webdriver(persistent_profile=str(PROFILE_DIR))
    main_handle = ''
    last_recover_at = 0.0
    try:
        driver.get(LOGIN_URL)
        main_handle = driver.current_window_handle
        start = time.time()
        while time.time() - start < TIMEOUT_SEC:
            _focus_best_window(driver, main_handle)
            try:
                main_handle = driver.current_window_handle
            except Exception:
                pass

            if _has_login_cookie(driver):
                count = _save_cookies(driver)
                print(f'Login successful. Saved {count} cookies to {OUTPUT_FILE}')
                print()
                print('Next step:')
                print('  python react_devops_auto_apply.py')
                return 0

            last_recover_at = _recover_from_white_screen(driver, main_handle, last_recover_at)
            if _has_login_cookie(driver):
                count = _save_cookies(driver)
                print(f'Login successful after recovery. Saved {count} cookies to {OUTPUT_FILE}')
                print()
                print('Next step:')
                print('  python react_devops_auto_apply.py')
                return 0

            elapsed = int(time.time() - start)
            if elapsed > 0 and elapsed % 15 == 0:
                try:
                    url = driver.current_url
                except Exception:
                    url = '(unknown)'
                print(f'  Still waiting... ({elapsed}s) — current page: {url}')
            time.sleep(2)

        print('Timed out waiting for login. Try again and finish sign-in within 5 minutes.')
        print('If Brave keeps going white after phone Yes:')
        print('  1) Close Brave fully')
        print('  2) In .env set: USE_BRAVE_BROWSER=false')
        print('  3) Run: python google_login.py')
        return 1
    finally:
        quit_webdriver(driver)


if __name__ == '__main__':
    sys.exit(main())
