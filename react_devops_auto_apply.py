"""
Naukri Auto-Apply — React Developer & DevOps Engineer

Searches Naukri.com for React and DevOps roles across India and applies
automatically to jobs that support Easy Apply (one-click apply on Naukri).

Usage:
    Google sign-in (recommended):
        1. python google_login.py          # one-time browser login
        2. python react_devops_auto_apply.py

    Email/password sign-in:
        1. Copy .env.example to .env and add credentials
        2. python react_devops_auto_apply.py

Run from your home network IP for best results (Naukri may block cloud/datacenter IPs).
"""

from __future__ import annotations

import os
import sys
import time
from datetime import datetime

from colorama import Fore, Style, init
from dotenv import load_dotenv

from config import (
    APPLY_DELAY_SEC,
    EXCEL_FILE,
    EXPERIENCE_YEARS,
    JOB_AGE_DAYS,
    PAGES_PER_QUERY,
    SEARCH_DELAY_SEC,
    SEARCH_QUERIES,
    TITLE_KEYWORDS,
)
from src.client.job_client import NaukriJobClient
from src.client.naukri_client import NaukriLoginClient
from src.exceptions.exceptions import NaukriAuthError
from src.utils.excel_logger import ExcelJobLogger

load_dotenv()
init(autoreset=True)

LINE = f"{Fore.WHITE}{'─' * 68}{Style.RESET_ALL}"


def print_section(title: str) -> None:
    print(f"\n{LINE}")
    print(f" {Fore.CYAN}{Style.BRIGHT}{title.upper()}{Style.RESET_ALL}")
    print(LINE)


def title_matches_role(title: str) -> bool:
    """Return True if job title looks like React or DevOps."""
    lower = title.lower()
    return any(kw in lower for kw in TITLE_KEYWORDS)


def fetch_jobs(jc: NaukriJobClient) -> list[tuple]:
    """Fetch and dedupe jobs. Returns list of (job, source_keyword) tuples."""
    seen: set[str] = set()
    results: list[tuple] = []

    print_section(
        f"Searching Naukri — {len(SEARCH_QUERIES)} queries, "
        f"{PAGES_PER_QUERY} page(s) each, exp={EXPERIENCE_YEARS}yr"
    )

    for query in SEARCH_QUERIES:
        keyword = query["keyword"]
        location = query.get("location", "")

        for page in range(1, PAGES_PER_QUERY + 1):
            try:
                jobs = jc.search_jobs(
                    keyword=keyword,
                    location=location,
                    experience=EXPERIENCE_YEARS,
                    job_age=JOB_AGE_DAYS,
                    page=page,
                )
            except NaukriAuthError as exc:
                print(f" {Fore.RED}[AUTH]{Style.RESET_ALL} {keyword} p{page}: {exc}")
                print(
                    f" {Fore.YELLOW}Tip: Run from home IP. "
                    f"If MFA triggered, complete OTP in browser first.{Style.RESET_ALL}"
                )
                time.sleep(3)
                continue
            except Exception as exc:
                print(f" {Fore.RED}[FAIL]{Style.RESET_ALL} {keyword} p{page}: {exc}")
                time.sleep(3)
                continue

            new_count = 0
            for job in jobs:
                if job.job_id in seen:
                    continue
                if not title_matches_role(job.title):
                    continue
                seen.add(job.job_id)
                results.append((job, keyword))
                new_count += 1

            loc_label = location or "All India"
            print(
                f" {Fore.WHITE}[{keyword[:28]:<28} | {loc_label[:12]:<12} | p{page}]"
                f"{Style.RESET_ALL} {len(jobs):>3} fetched, "
                f"{Fore.GREEN}{new_count:>3} new matches{Style.RESET_ALL}"
            )

            if not jobs:
                break
            time.sleep(SEARCH_DELAY_SEC)

    print(f"\n {Fore.CYAN}Total matching jobs: {Style.BRIGHT}{len(results)}{Style.RESET_ALL}")
    return results


def apply_to_jobs(
    jc: NaukriJobClient,
    job_entries: list[tuple],
    applied: set[str],
    excel: ExcelJobLogger,
) -> dict:
    stats = {"applied": 0, "skipped_applied": 0, "skipped_external": 0, "failed": 0}

    print_section(f"Applying to jobs ({len(job_entries)} found, {len(applied)} already in Excel)")

    for index, (job, keyword) in enumerate(job_entries, start=1):
        print(f"\n{LINE}")
        print(
            f" {Fore.CYAN}{Style.BRIGHT}[{index}/{len(job_entries)}]{Style.RESET_ALL} "
            f"{Style.BRIGHT}{job.title}{Style.RESET_ALL}"
        )
        print(f" {Fore.WHITE}Company:{Style.RESET_ALL} {Fore.YELLOW}{job.company}{Style.RESET_ALL}")
        print(f" {Fore.WHITE}Location:{Style.RESET_ALL} {job.location}")
        print(f" {Fore.WHITE}Job ID:{Style.RESET_ALL} {job.job_id}")

        if job.job_id in applied:
            print(f" {Fore.WHITE}Skipped — already applied (in Excel){Style.RESET_ALL}")
            excel.append_job(
                job,
                keyword,
                status="Skipped - Already Applied",
                notes="Found again on a later run",
            )
            stats["skipped_applied"] += 1
            continue

        if jc.is_external_apply(job.job_id):
            print(f" {Fore.YELLOW}Skipped — external apply (apply on company site){Style.RESET_ALL}")
            excel.append_job(
                job,
                keyword,
                status="Skipped - External Apply",
                notes="Must apply on company website",
            )
            stats["skipped_external"] += 1
            continue

        mandatory = job.tags[:2] if job.tags else []
        optional = job.tags[2:] if len(job.tags) > 2 else []

        try:
            result = jc.apply_job(
                job,
                mandatory_skills=mandatory,
                optional_skills=optional,
                source="search",
            )
            job_result = (result.get("jobs") or [{}])[0]

            if job_result.get("questionnaire"):
                print(f" {Fore.CYAN}Questionnaire detected — auto-filling...{Style.RESET_ALL}")
                sid = datetime.utcnow().strftime("%Y%m%d%H%M%S") + "0000000"
                jc.handle_static_questionnaire_and_apply(
                    job,
                    questionnaire=job_result["questionnaire"],
                    sid=sid,
                    mandatory_skills=mandatory,
                    optional_skills=optional,
                    source="search",
                )

            applied_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f" {Fore.GREEN}Applied successfully{Style.RESET_ALL}")
            excel.append_job(
                job,
                keyword,
                status="Applied",
                applied_at=applied_at,
                notes="Easy apply on Naukri",
            )
            applied.add(job.job_id)
            stats["applied"] += 1

        except Exception as exc:
            print(f" {Fore.RED}Failed — {exc}{Style.RESET_ALL}")
            excel.append_job(
                job,
                keyword,
                status="Failed",
                notes=str(exc),
            )
            stats["failed"] += 1

        time.sleep(APPLY_DELAY_SEC)

    return stats


def print_summary(total: int, stats: dict, excel_file: str) -> None:
    print_section("Run summary")
    rows = [
        ("Jobs matched (React / DevOps)", total, Fore.WHITE),
        ("Already applied (skipped)", stats["skipped_applied"], Fore.WHITE),
        ("Applied this run", stats["applied"], Fore.GREEN),
        ("Skipped (external apply)", stats["skipped_external"], Fore.YELLOW),
        ("Failed", stats["failed"], Fore.RED),
        ("Excel file", excel_file, Fore.CYAN),
    ]
    for label, value, color in rows:
        print(f" {Fore.WHITE}{label:<32}{Style.RESET_ALL} {color}{value}{Style.RESET_ALL}")
    print(LINE + "\n")


def main() -> int:
    cookies_file = os.getenv("COOKIES_FILE", "naukri_cookies.json")
    excel_file = os.getenv("EXCEL_FILE", EXCEL_FILE)
    username = os.getenv("USERNAME") or os.getenv("NAUKRI_USERNAME")
    password = os.getenv("PASSWORD") or os.getenv("NAUKRI_PASSWORD")

    client = NaukriLoginClient(username, password)

    print_section("Logging in to Naukri.com")

    if os.path.exists(cookies_file):
        try:
            client.login_from_cookies(cookies_file)
            print(
                f" {Fore.GREEN}Logged in using saved Google session "
                f"({cookies_file}){Style.RESET_ALL}"
            )
        except NaukriAuthError as exc:
            print(f" {Fore.RED}Cookie login failed: {exc}{Style.RESET_ALL}")
            print(
                f"\n {Fore.YELLOW}Run this to sign in with Google again:{Style.RESET_ALL}\n"
                f"   python google_login.py"
            )
            return 1
    elif username and password:
        try:
            client.login()
            print(f" {Fore.GREEN}Logged in as {Fore.YELLOW}{username}{Style.RESET_ALL}")
        except NaukriAuthError as exc:
            print(f" {Fore.RED}Login failed: {exc}{Style.RESET_ALL}")
            return 1
    else:
        print(
            f"{Fore.YELLOW}You sign in with Google on Naukri.{Style.RESET_ALL}\n"
            f"Run this once to save your session:\n\n"
            f"   python google_login.py\n\n"
            f"Then run auto-apply:\n\n"
            f"   python react_devops_auto_apply.py"
        )
        return 1

    excel = ExcelJobLogger(excel_file)
    applied = excel.load_applied_job_ids()

    if excel.filepath.exists():
        print(f" {Fore.CYAN}Excel log: {excel_file} ({len(applied)} jobs already applied){Style.RESET_ALL}")
    else:
        print(f" {Fore.CYAN}Excel log: {excel_file} (will be created on first save){Style.RESET_ALL}")

    jc = NaukriJobClient(client)
    job_entries = fetch_jobs(jc)

    if not job_entries:
        print(f"\n{Fore.YELLOW}No matching React/DevOps jobs found. Try again later.{Style.RESET_ALL}")
        return 0

    stats = apply_to_jobs(jc, job_entries, applied, excel)
    excel.append_run_summary(stats, total_found=len(job_entries))
    print_summary(len(job_entries), stats, excel_file)
    return 0


if __name__ == "__main__":
    sys.exit(main())
