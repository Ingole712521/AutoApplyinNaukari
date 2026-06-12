from src.client.naukri_client import NaukriLoginClient
from src.client.job_client import NaukriJobClient
from src.client.jop_classifier import JobFilterPipeline2
from src.exceptions.exceptions import NaukriAuthError, NaukriParseError
from dotenv import load_dotenv
from colorama import Fore, Back, Style, init
import os
import time
import csv
import logging
from datetime import datetime
load_dotenv()
init(autoreset=True)
logger = logging.getLogger(__name__)
CSV_FILE = 'applied_jobs.csv'

def load_applied_jobs() -> set:
    if not os.path.exists(CSV_FILE):
        return set()
    with open(CSV_FILE, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return set((row['job_id'] for row in reader))

def save_applied_job(job) -> None:
    file_exists = os.path.exists(CSV_FILE)
    with open(CSV_FILE, 'a', newline='', encoding='utf-8') as f:
        fieldnames = ['job_id', 'title', 'company', 'applied_at']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow({'job_id': job.job_id, 'title': job.title, 'company': job.company, 'applied_at': datetime.utcnow().isoformat()})
LINE = f"{Fore.WHITE}{'─' * 68}{Style.RESET_ALL}"
THIN = f"{Fore.WHITE}{'·' * 68}{Style.RESET_ALL}"

def print_section_title(text: str) -> None:
    print(f'\n{LINE}')
    print(f'  {Fore.CYAN}{Style.BRIGHT}{text.upper()}{Style.RESET_ALL}')
    print(LINE)

def print_job_header(index: int, total: int, job, score=None, ai_detail=None) -> None:
    now = datetime.utcnow().strftime('%Y-%m-%d  %H:%M UTC')
    score_str = ''
    if score is not None:
        score_color = Fore.GREEN if score >= 70 else Fore.YELLOW if score >= 50 else Fore.RED
        score_bar = _score_bar(score)
        score_str = f'  {score_color}{score}/100{Style.RESET_ALL}  {score_bar}'
    print(f'\n{LINE}')
    print(f'  {Fore.CYAN}{Style.BRIGHT}JOB {index}/{total}{Style.RESET_ALL}  {Fore.WHITE}{now}{Style.RESET_ALL}')
    print(THIN)
    print(f'  {Fore.WHITE}Title   :{Style.RESET_ALL}  {Style.BRIGHT}{job.title}{Style.RESET_ALL}')
    print(f'  {Fore.WHITE}Company :{Style.RESET_ALL}  {Fore.YELLOW}{job.company}{Style.RESET_ALL}')
    print(f'  {Fore.WHITE}Job ID  :{Style.RESET_ALL}  {Fore.BLUE}{job.job_id}{Style.RESET_ALL}')
    print(f'  {Fore.WHITE}URL     :{Style.RESET_ALL}  {Fore.BLUE}https://www.naukri.com/job-listings-{job.job_id}{Style.RESET_ALL}')
    if score is not None:
        detail_text = f'  {Fore.WHITE}({ai_detail}){Style.RESET_ALL}' if ai_detail else ''
        print(f'  {Fore.WHITE}Score   :{Style.RESET_ALL}{score_str}{detail_text}')
    if job.tags:
        tag_str = '  '.join((f'{Fore.CYAN}[{t}]{Style.RESET_ALL}' for t in job.tags))
        print(f'  {Fore.WHITE}Tags    :{Style.RESET_ALL}  {tag_str}')

def _score_bar(score: int, width: int=10) -> str:
    filled = int(score / 100 * width)
    bar = '█' * filled + '░' * (width - filled)
    color = Fore.GREEN if score >= 70 else Fore.YELLOW if score >= 50 else Fore.RED
    return f'{color}{bar}{Style.RESET_ALL}'

def print_status_applied(applied_at=None) -> None:
    ts = f'  {Fore.WHITE}at {applied_at}{Style.RESET_ALL}' if applied_at else ''
    print(f'  {Fore.GREEN}Status  :  Applied successfully{Style.RESET_ALL}{ts}')

def print_status_skipped_external() -> None:
    print(f'  {Fore.YELLOW}Status  :  Skipped — external apply (open URL manually){Style.RESET_ALL}')

def print_status_failed(error) -> None:
    print(f'  {Fore.RED}Status  :  Failed — {error}{Style.RESET_ALL}')

def print_questionnaire_notice() -> None:
    print(f'  {Fore.CYAN}           Questionnaire detected, handling automatically{Style.RESET_ALL}')

def print_pipeline_results(final_jobs: list) -> None:
    print_section_title(f'AI filter — {len(final_jobs)} jobs passed')
    col_w = [4, 35, 28, 6]
    header = f"  {Fore.WHITE}{'#':<{col_w[0]}}  {'Title':<{col_w[1]}}  {'Company':<{col_w[2]}}  {'Score':>{col_w[3]}}{Style.RESET_ALL}"
    print(header)
    print(f"  {Fore.WHITE}{'─' * sum(col_w)}{Style.RESET_ALL}")
    for i, job in enumerate(final_jobs, 1):
        score = job.get('score')
        score_color = Fore.GREEN if score and score >= 70 else Fore.YELLOW if score and score >= 50 else Fore.RED
        score_display = f'{score_color}{score:>3}{Style.RESET_ALL}' if score is not None else '  ?'
        title = (job.get('title') or '')[:col_w[1]]
        company = (job.get('company') or '')[:col_w[2]]
        print(f'  {Fore.CYAN}{i:<{col_w[0]}}{Style.RESET_ALL}  {title:<{col_w[1]}}  {Fore.YELLOW}{company:<{col_w[2]}}{Style.RESET_ALL}  {score_display}')

def print_fetch_progress(keyword: str, location: str, exp: int, page: int, fetched: int, new: int) -> None:
    loc = location or 'All India'
    kw_display = keyword[:30].ljust(30)
    loc_display = loc[:12].ljust(12)
    new_color = Fore.GREEN if new > 0 else Fore.WHITE
    print(f'  {Fore.WHITE}[{kw_display} | {loc_display} | exp={exp} | p{page}]{Style.RESET_ALL}  {Fore.WHITE}{fetched:>3} fetched  {new_color}{new:>3} new{Style.RESET_ALL}')

def print_summary(total_found: int, total_allowed: int, applied: int, skipped_ext: int, failed: int) -> None:
    print_section_title('run summary')
    rows = [('Jobs fetched (total unique)', str(total_found), Fore.WHITE), ('Jobs passed AI filter', str(total_allowed), Fore.CYAN), ('Applied successfully', str(applied), Fore.GREEN), ('Skipped (external apply)', str(skipped_ext), Fore.YELLOW), ('Failed', str(failed), Fore.RED)]
    for label, value, color in rows:
        print(f'  {Fore.WHITE}{label:<30}{Style.RESET_ALL}  {color}{Style.BRIGHT}{value}{Style.RESET_ALL}')
    print(LINE + '\n')

def fetch_all_jobs(jc: NaukriJobClient) -> list:
    BQUERIES = [{'keyword': 'Node.js backend developer', 'location': 'Bangalore'}, {'keyword': 'Python Developer', 'location': ''}, {'keyword': 'Node.js Developer', 'location': ''}, {'keyword': 'python backend developer', 'location': 'Pune'}]
    EXPERIENCE_LEVELS = [2]
    PAGES = 1
    JOB_AGE = 2
    seen_ids = set()
    all_jobs = []
    print_section_title(f'fetching jobs  ({len(BQUERIES)} queries x {len(EXPERIENCE_LEVELS)} exp x {PAGES} page)')
    for q in BQUERIES:
        for exp in EXPERIENCE_LEVELS:
            for page in range(1, PAGES + 1):
                try:
                    jobs = jc.search_jobs(keyword=q['keyword'], location=q['location'], experience=exp, job_age=JOB_AGE, page=page)
                    new_jobs = []
                    for job in jobs:
                        job_id = getattr(job, 'id', None) or getattr(job, 'job_id', None)
                        if job_id and job_id not in seen_ids:
                            seen_ids.add(job_id)
                            new_jobs.append(job)
                    all_jobs.extend(new_jobs)
                    print_fetch_progress(q['keyword'], q['location'], exp, page, fetched=len(jobs), new=len(new_jobs))
                    if len(jobs) == 0:
                        break
                    time.sleep(1.2)
                except Exception as e:
                    print(f"  {Fore.RED}[FAIL]{Style.RESET_ALL}  {q['keyword']} @ {q['location']}  exp={exp} p={page}  ->  {e}")
                    time.sleep(3)
    print(f'\n  {Fore.CYAN}Total unique jobs collected: {Style.BRIGHT}{len(all_jobs)}{Style.RESET_ALL}')
    return all_jobs
if __name__ == '__main__':
    username = os.getenv('USERNAME')
    password = os.getenv('PASSWORD')
    ai_key = os.getenv('OPEN_API_KEY')
    print_section_title('logging in to naukri')
    client = NaukriLoginClient(username, password)
    client.login()
    print(f'  {Fore.GREEN}Logged in as {Fore.YELLOW}{username}{Style.RESET_ALL}')
    jc = NaukriJobClient(client)
    jobs = fetch_all_jobs(jc)
    if not jobs:
        print(f'\n{Fore.YELLOW}  No jobs found. Exiting.{Style.RESET_ALL}')
        exit(0)
    print_section_title('running AI filter pipeline')
    pipeline = JobFilterPipeline2(openai_api_key=ai_key)
    final_jobs = pipeline.run(jobs)
    score_map = {j['job_id']: j for j in final_jobs}
    allow = set(score_map.keys())
    print_pipeline_results(final_jobs)
    applied_jobs_set = load_applied_jobs()
    applied_count = 0
    skipped_ext = 0
    failed_count = 0
    allowed_jobs = [j for j in jobs if j.job_id in allow]
    print_section_title(f'applying to {len(allowed_jobs)} filtered jobs')
    for index, job in enumerate(allowed_jobs, start=1):
        meta = score_map.get(job.job_id, {})
        score = meta.get('score')
        ai_detail = meta.get('ai_detail')
        print_job_header(index=index, total=len(allowed_jobs), job=job, score=score, ai_detail=ai_detail)
        if jc.is_external_apply(job.job_id):
            print_status_skipped_external()
            skipped_ext += 1
            continue
        mandatory = job.tags[:2] if job.tags else []
        optional = job.tags[2:] if len(job.tags) > 2 else []
        try:
            result = jc.apply_job(job, mandatory_skills=mandatory, optional_skills=optional, source='search')
            job_result = (result.get('jobs') or [{}])[0]
            if job_result.get('questionnaire'):
                print_questionnaire_notice()
                sid = datetime.utcnow().strftime('%Y%m%d%H%M%S') + '0000000'
                result = jc.handle_static_questionnaire_and_apply(job, questionnaire=job_result['questionnaire'], sid=sid, mandatory_skills=mandatory, optional_skills=optional, source='search')
            applied_at = datetime.utcnow().strftime('%H:%M:%S UTC')
            print_status_applied(applied_at)
            save_applied_job(job)
            applied_jobs_set.add(job.job_id)
            applied_count += 1
        except Exception as e:
            print_status_failed(e)
            failed_count += 1
        time.sleep(3)
    print_summary(total_found=len(jobs), total_allowed=len(allowed_jobs), applied=applied_count, skipped_ext=skipped_ext, failed=failed_count)
