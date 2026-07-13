from __future__ import annotations
import argparse
import os
import sys
import time
from datetime import datetime
from colorama import Fore, Style, init
from dotenv import load_dotenv

from config import (
    APPLY_DELAY_SEC,
    APPLIED_JOBS_CSV,
    ENABLE_FOUNDIT,
    ENABLE_LINKEDIN,
    ENABLE_NAUKRI,
    ENABLE_NAUKRI_RECOMMENDED,
    ENABLE_REMOTIVE,
    ENABLE_REMOTE_OK,
    ENABLE_SURELY_REMOTE,
    EXCEL_FILE,
    EXPERIENCE_YEARS,
    EXTERNAL_BOARD_KEYWORDS,
    FOUNDIT_MAX_PAGES,
    JOB_AGE_DAYS,
    LINKEDIN_COOKIES_FILE,
    LINKEDIN_HEADLESS,
    LINKEDIN_LOCATION,
    LINKEDIN_MAX_JOBS_PER_QUERY,
    LINKEDIN_SCROLL_ROUNDS,
    LINKEDIN_SEARCH_QUERIES,
    LINKEDIN_TITLE_KEYWORDS,
    LOOP_INTERVAL_MINUTES,
    MAX_PAGES_PER_QUERY,
    NAUKRI_RESULTS_PER_PAGE,
    PAGES_PER_QUERY,
    SEARCH_DELAY_SEC,
    SEARCH_QUERIES,
    SKIP_IF_COMPANY_ALREADY_APPLIED,
    TITLE_KEYWORDS,
)
from src.client.job_client import NaukriJobClient
from src.client.naukri_client import NaukriLoginClient
from src.exceptions.exceptions import NaukriAuthError
from src.utils.company_tracker import normalize_company
from src.utils.excel_logger import ExcelJobLogger, load_csv_applied_job_ids, normalize_job_id
load_dotenv()
init(autoreset=True)
LINE = f"{Fore.WHITE}{'─' * 68}{Style.RESET_ALL}"

def print_section(title: str) -> None:
    print(f'\n{LINE}')
    print(f' {Fore.CYAN}{Style.BRIGHT}{title.upper()}{Style.RESET_ALL}')
    print(LINE)


def title_matches_role(title: str) -> bool:
    lower = title.lower()
    return any(kw in lower for kw in TITLE_KEYWORDS)


def linkedin_title_matches(title: str) -> bool:
    lower = title.lower()
    return any(kw in lower for kw in LINKEDIN_TITLE_KEYWORDS)


def should_skip_company(excel: ExcelJobLogger, company: str, applied_companies: set[str]) -> bool:
    if not SKIP_IF_COMPANY_ALREADY_APPLIED:
        return False
    return excel.is_company_applied(company, applied_companies)


def bootstrap_applied_ids(excel: ExcelJobLogger, jc: NaukriJobClient | None = None) -> tuple[set[str], set[str]]:
    applied_ids = excel.load_applied_job_ids()
    csv_ids = load_csv_applied_job_ids(APPLIED_JOBS_CSV)
    if csv_ids:
        applied_ids |= csv_ids
        print(f' {Fore.CYAN}Loaded {len(csv_ids)} job ID(s) from {APPLIED_JOBS_CSV}{Style.RESET_ALL}')
    naukri_count = 0
    if jc is not None:
        try:
            history = jc.fetch_all_application_history(days=90, page_size=50)
            for item in history:
                jid = normalize_job_id(item.job_id)
                if jid:
                    applied_ids.add(jid)
            naukri_count = len(history)
            if naukri_count:
                print(f' {Fore.CYAN}Synced {naukri_count} job(s) from Naukri apply history{Style.RESET_ALL}')
        except Exception as exc:
            print(f' {Fore.YELLOW}Naukri history sync skipped: {exc}{Style.RESET_ALL}')
    applied_companies = excel.load_applied_companies()
    return applied_ids, applied_companies


def _skip_already_applied(job, keyword: str, applied_ids: set[str], excel: ExcelJobLogger, stats: dict) -> bool:
    jid = normalize_job_id(job.job_id)
    if not jid or jid not in applied_ids:
        return False
    print(f' {Fore.WHITE}Skipped — already applied (Excel / Naukri history / CSV){Style.RESET_ALL}')
    excel.append_job(
        job, keyword, status='Skipped - Already Applied',
        notes='Known applied job — not sending apply again', platform='Naukri',
    )
    stats['skipped_applied'] += 1
    return True


def fetch_naukri_jobs(jc: NaukriJobClient, applied_ids: set[str] | None = None) -> list[tuple]:
    seen: set[str] = set()
    results: list[tuple] = []

    known = applied_ids or set()

    if ENABLE_NAUKRI_RECOMMENDED:
        print_section(f'Naukri recommended jobs — skipping {len(known)} known IDs')
        try:
            rec_jobs = jc.get_recommended_jobs()
            new_count = 0
            for job in rec_jobs:
                jid = normalize_job_id(job.job_id)
                if not jid or jid in seen or jid in known:
                    continue
                seen.add(jid)
                results.append((job, 'Recommended', 'recommended'))
                new_count += 1
            print(
                f' {Fore.WHITE}[Recommended]{Style.RESET_ALL} '
                f'{len(rec_jobs):>3} fetched, {Fore.GREEN}{new_count:>3} new{Style.RESET_ALL}'
            )
        except NaukriAuthError as exc:
            print(f' {Fore.RED}[AUTH]{Style.RESET_ALL} recommended jobs: {exc}')
        except Exception as exc:
            print(f' {Fore.RED}[FAIL]{Style.RESET_ALL} recommended jobs: {exc}')

    print_section(
        f'Naukri search — {len(SEARCH_QUERIES)} queries, up to {MAX_PAGES_PER_QUERY} page(s), '
        f'{NAUKRI_RESULTS_PER_PAGE}/page, exp={EXPERIENCE_YEARS}yr, skipping {len(known)} known IDs'
    )

    for query in SEARCH_QUERIES:
        keyword = query['keyword']
        location = query.get('location', '')

        for page in range(1, MAX_PAGES_PER_QUERY + 1):
            try:
                jobs = jc.search_jobs(
                    keyword=keyword,
                    location=location,
                    experience=EXPERIENCE_YEARS,
                    job_age=JOB_AGE_DAYS,
                    page=page,
                    results_per_page=NAUKRI_RESULTS_PER_PAGE,
                )
            except NaukriAuthError as exc:
                print(f' {Fore.RED}[AUTH]{Style.RESET_ALL} {keyword} p{page}: {exc}')
                time.sleep(3)
                continue
            except Exception as exc:
                print(f' {Fore.RED}[FAIL]{Style.RESET_ALL} {keyword} p{page}: {exc}')
                time.sleep(3)
                continue
            new_count = 0
            for job in jobs:
                jid = normalize_job_id(job.job_id)
                if not jid or jid in seen or jid in known:
                    continue
                if not title_matches_role(job.title):
                    continue
                seen.add(jid)
                results.append((job, keyword, 'search'))
                new_count += 1
            loc_label = location or 'All India'
            print(f' {Fore.WHITE}[{keyword[:28]:<28} | {loc_label[:12]:<12} | p{page}]{Style.RESET_ALL} {len(jobs):>3} fetched, {Fore.GREEN}{new_count:>3} new matches{Style.RESET_ALL}')
            if not jobs:
                break
            time.sleep(SEARCH_DELAY_SEC)
    print(f'\n {Fore.CYAN}Naukri matching jobs: {Style.BRIGHT}{len(results)}{Style.RESET_ALL}')
    return results

def apply_naukri_jobs(jc: NaukriJobClient, job_entries: list[tuple], applied_ids: set[str], applied_companies: set[str], excel: ExcelJobLogger) -> dict:
    stats = {'applied': 0, 'skipped_applied': 0, 'skipped_company': 0, 'skipped_external': 0, 'failed': 0}
    print_section(
        f'Naukri apply — {len(job_entries)} new jobs, '
        f'{len(applied_ids)} known applied IDs in memory'
    )
    for index, entry in enumerate(job_entries, start=1):
        if len(entry) == 3:
            job, keyword, source = entry
        else:
            job, keyword = entry
            source = 'search'
        print(f'\n{LINE}')
        print(f' {Fore.CYAN}{Style.BRIGHT}[{index}/{len(job_entries)}]{Style.RESET_ALL} {Style.BRIGHT}{job.title}{Style.RESET_ALL}')
        print(f' {Fore.WHITE}Company:{Style.RESET_ALL} {Fore.YELLOW}{job.company}{Style.RESET_ALL}')
        print(f' {Fore.WHITE}Source:{Style.RESET_ALL} {keyword}')
        if _skip_already_applied(job, keyword, applied_ids, excel, stats):
            continue
        if should_skip_company(excel, job.company, applied_companies):
            print(f' {Fore.WHITE}Skipped — company already applied{Style.RESET_ALL}')
            excel.append_job(job, keyword, status='Skipped - Company Applied', notes='Applied to this company earlier', platform='Naukri')
            jid = normalize_job_id(job.job_id)
            if jid:
                applied_ids.add(jid)
            stats['skipped_company'] += 1
            continue
        if jc.is_external_apply(job.job_id):
            external_url = jc.get_external_apply_url(job.job_id)
            print(f' {Fore.YELLOW}External apply — URL saved to Excel{Style.RESET_ALL}')
            print(f' {Fore.BLUE}{external_url}{Style.RESET_ALL}')
            excel.append_job(job, keyword, status='Skipped - External Apply', notes='Apply on company website (URL saved)', platform='Naukri', external_apply_url=external_url)
            jid = normalize_job_id(job.job_id)
            if jid:
                applied_ids.add(jid)
            stats['skipped_external'] += 1
            continue
        mandatory = job.tags[:2] if job.tags else []
        optional = job.tags[2:] if len(job.tags) > 2 else []
        try:
            sid = datetime.utcnow().strftime('%Y%m%d%H%M%S') + '0000000'
            result = jc.apply_job(
                job, mandatory_skills=mandatory, optional_skills=optional, sid=sid, source=source,
            )
            job_result = (result.get('jobs') or [{}])[0]
            if job_result.get('questionnaire'):
                print(f' {Fore.CYAN}Questionnaire — auto-filling{Style.RESET_ALL}')
                result = jc.handle_static_questionnaire_and_apply(
                    job, questionnaire=job_result['questionnaire'], sid=sid,
                    mandatory_skills=mandatory, optional_skills=optional, source=source,
                )
            ok, msg, already_on_naukri = jc.parse_apply_result(result, normalize_job_id(job.job_id))
            if not ok:
                raise RuntimeError(msg)
            jid = normalize_job_id(job.job_id)
            applied_ids.add(jid)
            if already_on_naukri:
                print(f' {Fore.WHITE}Already on Naukri — no duplicate apply sent{Style.RESET_ALL}')
                excel.append_job(
                    job, keyword, status='Skipped - Already Applied',
                    notes=msg, platform='Naukri',
                )
                stats['skipped_applied'] += 1
            else:
                applied_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                print(f' {Fore.GREEN}Applied successfully{Style.RESET_ALL}')
                excel.append_job(
                    job, keyword, status='Applied', applied_at=applied_at,
                    notes=msg, platform='Naukri',
                )
                norm = normalize_company(job.company)
                if norm:
                    applied_companies.add(norm)
                stats['applied'] += 1
        except Exception as exc:
            print(f' {Fore.RED}Failed — {exc}{Style.RESET_ALL}')
            excel.append_job(job, keyword, status='Failed', notes=str(exc), platform='Naukri')
            jid = normalize_job_id(job.job_id)
            if jid:
                applied_ids.add(jid)
            stats['failed'] += 1
        time.sleep(APPLY_DELAY_SEC)
    return stats

def fetch_linkedin_jobs(li, applied_ids: set[str] | None = None) -> list[tuple]:
    all_jobs: list[tuple] = []
    seen: set[str] = set()
    known = applied_ids or set()
    print_section(
        f'LinkedIn DevOps/AWS — {len(LINKEDIN_SEARCH_QUERIES)} keywords, '
        f'up to {LINKEDIN_MAX_JOBS_PER_QUERY} Easy Apply jobs each'
    )
    for keyword in LINKEDIN_SEARCH_QUERIES:
        try:
            jobs = li.search_jobs(
                keyword,
                LINKEDIN_LOCATION,
                LINKEDIN_MAX_JOBS_PER_QUERY,
                scroll_rounds=LINKEDIN_SCROLL_ROUNDS,
            )
        except Exception as exc:
            print(f' {Fore.RED}[FAIL]{Style.RESET_ALL} {keyword}: {exc}')
            continue
        new = 0
        for job in jobs:
            jid = normalize_job_id(job.job_id)
            if not jid or jid in seen or jid in known:
                continue
            if not linkedin_title_matches(job.title):
                continue
            seen.add(jid)
            all_jobs.append((job, keyword))
            new += 1
        print(f' {Fore.WHITE}[{keyword[:40]:<40}]{Style.RESET_ALL} {len(jobs):>3} listed, {Fore.GREEN}{new:>3} DevOps/AWS matches{Style.RESET_ALL}')
        time.sleep(SEARCH_DELAY_SEC)
    print(f'\n {Fore.CYAN}LinkedIn DevOps/AWS jobs to apply: {Style.BRIGHT}{len(all_jobs)}{Style.RESET_ALL}')
    return all_jobs

def apply_linkedin_jobs(li, excel: ExcelJobLogger, applied_ids: set[str], applied_companies: set[str], job_entries: list[tuple] | None=None) -> dict:
    stats = {'applied': 0, 'skipped_applied': 0, 'skipped_company': 0, 'skipped_external': 0, 'failed': 0}
    all_jobs = job_entries if job_entries is not None else fetch_linkedin_jobs(li)
    print_section(f'LinkedIn apply — {len(all_jobs)} jobs')
    for index, (job, keyword) in enumerate(all_jobs, start=1):
        print(f'\n{LINE}')
        print(f' {Fore.CYAN}{Style.BRIGHT}[{index}/{len(all_jobs)}]{Style.RESET_ALL} {Style.BRIGHT}{job.title}{Style.RESET_ALL}')
        print(f' {Fore.WHITE}Company:{Style.RESET_ALL} {Fore.YELLOW}{job.company}{Style.RESET_ALL}')
        jid = normalize_job_id(job.job_id)
        if jid in applied_ids:
            print(f' {Fore.WHITE}Skipped — job ID already applied{Style.RESET_ALL}')
            excel.append_job(job, keyword, status='Skipped - Already Applied', notes='Same job ID on a later run', platform='LinkedIn')
            stats['skipped_applied'] += 1
            continue
        if should_skip_company(excel, job.company, applied_companies):
            print(f' {Fore.WHITE}Skipped — company already applied{Style.RESET_ALL}')
            excel.append_job(job, keyword, status='Skipped - Company Applied', notes='Applied to this company earlier', platform='LinkedIn')
            stats['skipped_company'] += 1
            continue
        try:
            result = li.apply_job(job)
            status = result.get('status', 'failed')
            external_url = result.get('external_url', '')
            notes = result.get('notes', '')
            if status == 'applied':
                applied_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                print(f' {Fore.GREEN}Applied successfully{Style.RESET_ALL}')
                excel.append_job(job, keyword, status='Applied', applied_at=applied_at, notes=notes, platform='LinkedIn')
                applied_ids.add(job.job_id)
                norm = normalize_company(job.company)
                if norm:
                    applied_companies.add(norm)
                stats['applied'] += 1
            elif status == 'already_applied':
                print(f' {Fore.WHITE}Skipped — already applied on LinkedIn{Style.RESET_ALL}')
                excel.append_job(job, keyword, status='Skipped - Already Applied', notes=notes, platform='LinkedIn')
                applied_ids.add(job.job_id)
                stats['skipped_applied'] += 1
            elif status == 'external':
                print(f' {Fore.YELLOW}External apply — URL saved to Excel{Style.RESET_ALL}')
                print(f' {Fore.BLUE}{external_url}{Style.RESET_ALL}')
                excel.append_job(job, keyword, status='Skipped - External Apply', notes=notes, platform='LinkedIn', external_apply_url=external_url)
                stats['skipped_external'] += 1
            else:
                print(f' {Fore.RED}Failed — {notes}{Style.RESET_ALL}')
                excel.append_job(job, keyword, status='Failed', notes=notes, platform='LinkedIn')
                stats['failed'] += 1
        except Exception as exc:
            print(f' {Fore.RED}Failed — {exc}{Style.RESET_ALL}')
            excel.append_job(job, keyword, status='Failed', notes=str(exc), platform='LinkedIn')
            stats['failed'] += 1
        time.sleep(APPLY_DELAY_SEC)

    return stats, len(all_jobs)


def print_summary(platform: str, total: int, stats: dict, excel_file: str) -> None:
    print_section(f'{platform} run summary')
    rows = [('Jobs matched', total, Fore.WHITE), ('Already applied (skipped)', stats['skipped_applied'], Fore.WHITE), ('Company already applied', stats.get('skipped_company', 0), Fore.WHITE), ('Applied this run', stats['applied'], Fore.GREEN), ('External (URL in Excel)', stats['skipped_external'], Fore.YELLOW), ('Failed', stats['failed'], Fore.RED), ('Excel file', excel_file, Fore.CYAN)]
    for label, value, color in rows:
        print(f' {Fore.WHITE}{label:<32}{Style.RESET_ALL} {color}{value}{Style.RESET_ALL}')
    print(LINE)

def _print_search_only_jobs(platform: str, entries: list[tuple]) -> None:
    print_section(f'{platform} — jobs found (search only)')
    if not entries:
        print(f' {Fore.YELLOW}No matching jobs.{Style.RESET_ALL}')
        return
    for index, entry in enumerate(entries, start=1):
        if len(entry) == 3:
            job, keyword, _source = entry
        else:
            job, keyword = entry
        print(f' {Fore.CYAN}[{index}]{Style.RESET_ALL} {Style.BRIGHT}{job.title}{Style.RESET_ALL} @ {Fore.YELLOW}{job.company}{Style.RESET_ALL}')
        print(f' {Fore.WHITE}Query:{Style.RESET_ALL} {keyword}')
        url = getattr(job, 'apply_link', None) or getattr(job, 'job_url', '')
        if url:
            print(f' {Fore.BLUE}{url}{Style.RESET_ALL}')

def run_cycle(excel_file: str, search_only: bool = False, linkedin_only: bool = False) -> int:
    excel = ExcelJobLogger(excel_file)
    applied_ids, applied_companies = bootstrap_applied_ids(excel)
    if excel.filepath.exists():
        print(
            f' {Fore.CYAN}Excel: {excel_file} — {len(applied_ids)} known job IDs, '
            f'{len(applied_companies)} companies applied{Style.RESET_ALL}'
        )
    else:
        print(f' {Fore.CYAN}Excel: {excel_file} (created on first save){Style.RESET_ALL}')
    exit_code = 0
    run_naukri = ENABLE_NAUKRI and not linkedin_only
    run_linkedin = ENABLE_LINKEDIN
    if run_naukri:
        cookies_file = os.getenv('COOKIES_FILE', 'naukri_cookies.json')
        username = os.getenv('USERNAME') or os.getenv('NAUKRI_USERNAME')
        password = os.getenv('PASSWORD') or os.getenv('NAUKRI_PASSWORD')
        client = NaukriLoginClient(username, password)
        print_section('Naukri login')
        if os.path.exists(cookies_file):
            try:
                client.login_from_cookies(cookies_file)
                print(f' {Fore.GREEN}Logged in ({cookies_file}){Style.RESET_ALL}')
            except NaukriAuthError as exc:
                print(f' {Fore.RED}Cookie login failed: {exc}{Style.RESET_ALL}')
                print(f' {Fore.YELLOW}Run: python google_login.py{Style.RESET_ALL}')
                exit_code = 1
        elif username and password:
            try:
                client.login()
                print(f' {Fore.GREEN}Logged in as {username}{Style.RESET_ALL}')
            except NaukriAuthError as exc:
                print(f' {Fore.RED}Login failed: {exc}{Style.RESET_ALL}')
                exit_code = 1
        else:
            print(f' {Fore.YELLOW}Naukri: run google_login.py or set .env credentials{Style.RESET_ALL}')
            exit_code = 1
        if exit_code == 0:
            jc = NaukriJobClient(client)
            applied_ids, applied_companies = bootstrap_applied_ids(excel, jc)
            entries = fetch_naukri_jobs(jc, applied_ids)
            if search_only:
                _print_search_only_jobs('Naukri', entries)
            elif entries:
                stats = apply_naukri_jobs(jc, entries, applied_ids, applied_companies, excel)
                excel.append_run_summary(stats, total_found=len(entries), platform='Naukri')
                print_summary('Naukri', len(entries), stats, excel_file)
            else:
                print(f'\n{Fore.YELLOW}No matching Naukri jobs this cycle.{Style.RESET_ALL}')
    if run_linkedin:
        from src.client.linkedin_client import LinkedInApplyClient
        li_cookies = os.getenv('LINKEDIN_COOKIES_FILE', LINKEDIN_COOKIES_FILE)
        li = LinkedInApplyClient(li_cookies, headless=LINKEDIN_HEADLESS)
        print_section('LinkedIn (browser)')
        try:
            li.start()
            print(f' {Fore.GREEN}LinkedIn session ready{Style.RESET_ALL}')
            li_entries = fetch_linkedin_jobs(li, applied_ids)
            if search_only:
                _print_search_only_jobs('LinkedIn', li_entries)
            else:
                stats, total = apply_linkedin_jobs(li, excel, applied_ids, applied_companies, job_entries=li_entries)
                excel.append_run_summary(stats, total_found=total, platform='LinkedIn')
                print_summary('LinkedIn', total, stats, excel_file)
        except FileNotFoundError as exc:
            print(f' {Fore.YELLOW}{exc}{Style.RESET_ALL}')
            print(f' {Fore.YELLOW}Run: python linkedin_login.py{Style.RESET_ALL}')
            exit_code = 1
        except Exception as exc:
            print(f' {Fore.RED}LinkedIn error: {exc}{Style.RESET_ALL}')
            exit_code = 1
        finally:
            li.stop()

    return exit_code


def collect_external_board_jobs(
    excel: ExcelJobLogger,
    applied_ids: set[str],
    applied_companies: set[str],
) -> dict[str, dict]:
    from src.client.external_job_sources import (
        fetch_foundit_jobs,
        fetch_remote_ok_jobs,
        fetch_remotive_jobs,
        fetch_surely_remote_jobs,
    )

    board_stats: dict[str, dict] = {}

    def _log_external(job, keyword: str, platform: str) -> dict:
        stats = {'applied': 0, 'skipped_applied': 0, 'skipped_company': 0, 'skipped_external': 0, 'failed': 0}
        jid = normalize_job_id(job.job_id)
        if jid in applied_ids:
            stats['skipped_applied'] += 1
            return stats
        if should_skip_company(excel, job.company, applied_companies):
            stats['skipped_company'] += 1
            return stats
        excel.append_job(
            job, keyword, status='Skipped - External Apply',
            notes=f'Apply on {platform}', platform=platform,
            external_apply_url=getattr(job, 'apply_link', '') or '',
        )
        applied_ids.add(jid)
        stats['skipped_external'] += 1
        return stats

    if ENABLE_FOUNDIT:
        stats = {'applied': 0, 'skipped_applied': 0, 'skipped_company': 0, 'skipped_external': 0, 'failed': 0}
        for keyword in EXTERNAL_BOARD_KEYWORDS:
            try:
                jobs = fetch_foundit_jobs(keyword, max_pages=FOUNDIT_MAX_PAGES, delay_sec=SEARCH_DELAY_SEC)
            except Exception as exc:
                print(f' {Fore.RED}[Foundit]{Style.RESET_ALL} {keyword}: {exc}')
                continue
            for job in jobs:
                for key, val in _log_external(job, keyword, 'Foundit').items():
                    stats[key] += val
        board_stats['Foundit'] = stats

    if ENABLE_REMOTE_OK:
        stats = {'applied': 0, 'skipped_applied': 0, 'skipped_company': 0, 'skipped_external': 0, 'failed': 0}
        for job in fetch_remote_ok_jobs():
            for key, val in _log_external(job, 'remote ok', 'RemoteOK').items():
                stats[key] += val
        board_stats['RemoteOK'] = stats

    if ENABLE_REMOTIVE:
        stats = {'applied': 0, 'skipped_applied': 0, 'skipped_company': 0, 'skipped_external': 0, 'failed': 0}
        for job in fetch_remotive_jobs():
            for key, val in _log_external(job, 'remotive', 'Remotive').items():
                stats[key] += val
        board_stats['Remotive'] = stats

    if ENABLE_SURELY_REMOTE:
        stats = {'applied': 0, 'skipped_applied': 0, 'skipped_company': 0, 'skipped_external': 0, 'failed': 0}
        for keyword in EXTERNAL_BOARD_KEYWORDS:
            for job in fetch_surely_remote_jobs(keyword):
                for key, val in _log_external(job, keyword, 'SurelyRemote').items():
                    stats[key] += val
        board_stats['SurelyRemote'] = stats

    return board_stats


def main() -> int:
    parser = argparse.ArgumentParser(description='Naukri + LinkedIn auto-apply')
    parser.add_argument('--once', action='store_true', help='Run one cycle and exit (default: repeat every LOOP_INTERVAL_MINUTES)')
    parser.add_argument('--search-only', action='store_true', help='Search Naukri + LinkedIn only (no apply)')
    parser.add_argument('--linkedin-only', action='store_true', help='LinkedIn DevOps/AWS Easy Apply only (skip Naukri)')
    args = parser.parse_args()

    excel_file = os.getenv("EXCEL_FILE", EXCEL_FILE)
    interval = int(os.getenv("LOOP_INTERVAL_MINUTES", LOOP_INTERVAL_MINUTES))

    print_section("Auto-apply started")
    print(f" {Fore.WHITE}Platforms:{Style.RESET_ALL} Naukri={ENABLE_NAUKRI}, LinkedIn={ENABLE_LINKEDIN}")
    mode = 'search only' if args.search_only else 'LinkedIn DevOps/AWS only' if args.linkedin_only else 'once' if args.once else f'every {interval} minutes'
    print(f' {Fore.WHITE}Mode:{Style.RESET_ALL} {mode}')
    print(f" {Fore.WHITE}Profile:{Style.RESET_ALL} 2yr exp, 30 days notice, relocate=yes, questions=yes")

    cycle = 0
    while True:
        cycle += 1
        print(f"\n{Fore.MAGENTA}{Style.BRIGHT}=== Cycle {cycle} @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ==={Style.RESET_ALL}")
        run_cycle(excel_file, search_only=args.search_only, linkedin_only=args.linkedin_only)
        if args.once:
            break
        print(f'\n{Fore.CYAN}Next run in {interval} minutes (Ctrl+C to stop)...{Style.RESET_ALL}')
        try:
            time.sleep(interval * 60)
        except KeyboardInterrupt:
            print(f'\n{Fore.YELLOW}Stopped by user.{Style.RESET_ALL}')
            break
    return 0
if __name__ == '__main__':
    sys.exit(main())
