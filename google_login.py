"""
One-time Google sign-in for Naukri.com

Opens Chrome so you can sign in with Google. After login, saves session
cookies to naukri_cookies.json for use by react_devops_auto_apply.py.

Usage:
    python google_login.py

You only need to run this again when the session expires (usually days/weeks).
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

LOGIN_URL = "https://www.naukri.com/nlogin/login"
OUTPUT_FILE = Path("naukri_cookies.json")
TIMEOUT_SEC = 300


def main() -> int:
    print("=" * 60)
    print(" Naukri Google Sign-In")
    print("=" * 60)
    print()
    print("1. Chrome will open the Naukri login page")
    print("2. Click 'Sign in with Google' and complete login")
    print("3. Cookies will be saved automatically when login succeeds")
    print()
    print(f"Waiting up to {TIMEOUT_SEC // 60} minutes...")
    print()

    options = Options()
    options.add_argument("--start-maximized")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])

    driver = webdriver.Chrome(options=options)

    try:
        driver.get(LOGIN_URL)
        start = time.time()

        while time.time() - start < TIMEOUT_SEC:
            cookies = driver.get_cookies()
            nauk_at = next((c for c in cookies if c.get("name") == "nauk_at"), None)

            if nauk_at:
                OUTPUT_FILE.write_text(json.dumps(cookies, indent=2), encoding="utf-8")
                print(f"Login successful. Saved {len(cookies)} cookies to {OUTPUT_FILE}")
                print()
                print("Next step:")
                print("  python react_devops_auto_apply.py")
                return 0

            elapsed = int(time.time() - start)
            if elapsed > 0 and elapsed % 15 == 0:
                print(f"  Still waiting... ({elapsed}s) — complete Google sign-in in Chrome")

            time.sleep(2)

        print("Timed out waiting for login. Try again and finish sign-in within 5 minutes.")
        return 1

    finally:
        driver.quit()


if __name__ == "__main__":
    sys.exit(main())
