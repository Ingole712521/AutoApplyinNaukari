import os
_IS_VERCEL = bool(os.getenv('VERCEL') or os.getenv('VERCEL_ENV'))

def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ('1', 'true', 'yes', 'on')
LOOP_INTERVAL_MINUTES = 30
ENABLE_NAUKRI = _env_bool('ENABLE_NAUKRI', True)
ENABLE_LINKEDIN = _env_bool('ENABLE_LINKEDIN', not _IS_VERCEL)
SKIP_IF_COMPANY_ALREADY_APPLIED = True
SEARCH_QUERIES = [{'keyword': 'React Developer', 'location': ''}, {'keyword': 'React.js Developer', 'location': ''}, {'keyword': 'Frontend React Developer', 'location': ''}, {'keyword': 'React Native Developer', 'location': ''}, {'keyword': 'DevOps Engineer', 'location': ''}, {'keyword': 'DevOps', 'location': ''}, {'keyword': 'AWS DevOps Engineer', 'location': ''}, {'keyword': 'Site Reliability Engineer', 'location': ''}]
TITLE_KEYWORDS = ['react', 'reactjs', 'react.js', 'react native', 'frontend', 'front-end', 'devops', 'dev ops', 'sre', 'site reliability', 'platform engineer', 'cloud engineer', 'kubernetes', 'docker', 'aws', 'azure', 'gcp', 'ci/cd', 'jenkins', 'terraform']
EXPERIENCE_YEARS = 2
JOB_AGE_DAYS = 3
PAGES_PER_QUERY = 1 if _IS_VERCEL else 2
SEARCH_DELAY_SEC = 1.5
APPLY_DELAY_SEC = 3
EXCEL_FILE = 'job_applications.xlsx'
APPLIED_JOBS_CSV = 'applied_jobs.csv'
LINKEDIN_COOKIES_FILE = 'linkedin_cookies.json'
LINKEDIN_LOCATION = 'India'
LINKEDIN_MAX_JOBS_PER_QUERY = 15
LINKEDIN_SEARCH_QUERIES = ['React Developer', 'React.js Developer', 'Frontend React Developer', 'DevOps Engineer', 'DevOps', 'AWS DevOps Engineer', 'Site Reliability Engineer']
LINKEDIN_HEADLESS = False
USE_BRAVE_BROWSER = True
BRAVE_BINARY_PATH = ''
LINKEDIN_EASY_APPLY_MAX_STEPS = 25
USE_OPENROUTER_FOR_LINKEDIN = True
OPENROUTER_MODEL = 'openai/gpt-oss-120b:free'
APPLICANT_PROFILE = {'current_ctc_annual': 168000, 'expected_ctc_annual': 500000, 'exp_total': '2', 'current_location': 'Pune', 'willing_to_relocate': True, 'notice_days': 30, 'skills': ['react', 'javascript', 'typescript', 'redux', 'docker', 'kubernetes', 'aws', 'ci/cd', 'jenkins', 'terraform', 'linux', 'git']}
