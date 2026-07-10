import os

_IS_VERCEL = bool(os.getenv('VERCEL') or os.getenv('VERCEL_ENV'))


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ('1', 'true', 'yes', 'on')


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


LOOP_INTERVAL_MINUTES = _env_int('LOOP_INTERVAL_MINUTES', 30)
ENABLE_NAUKRI = _env_bool('ENABLE_NAUKRI', True)
ENABLE_LINKEDIN = _env_bool('ENABLE_LINKEDIN', not _IS_VERCEL)
ENABLE_FOUNDIT = _env_bool('ENABLE_FOUNDIT', True)
ENABLE_REMOTE_OK = _env_bool('ENABLE_REMOTE_OK', True)
ENABLE_SURELY_REMOTE = _env_bool('ENABLE_SURELY_REMOTE', True)
ENABLE_REMOTIVE = _env_bool('ENABLE_REMOTIVE', True)

EXTERNAL_BOARD_KEYWORDS = [
    'DevOps Engineer',
    'DevOps',
    'AWS DevOps Engineer',
    'Site Reliability Engineer',
    'Platform Engineer',
    'Kubernetes Engineer',
]
FOUNDIT_MAX_PAGES = 2 if _IS_VERCEL else 5

SKIP_IF_COMPANY_ALREADY_APPLIED = _env_bool('SKIP_IF_COMPANY_ALREADY_APPLIED', True)
NAUKRI_LOCATION = os.getenv('NAUKRI_LOCATION', '')

SEARCH_QUERIES = [
    {'keyword': 'AWS', 'location': NAUKRI_LOCATION},
    {'keyword': 'AWS DevOps', 'location': NAUKRI_LOCATION},
    {'keyword': 'Cloud Engineer', 'location': NAUKRI_LOCATION},
    {'keyword': 'Cloud Computing', 'location': NAUKRI_LOCATION},
    {'keyword': 'DevOps Engineer', 'location': NAUKRI_LOCATION},
    {'keyword': 'DevOps', 'location': NAUKRI_LOCATION},
    {'keyword': 'React Developer', 'location': NAUKRI_LOCATION},
    {'keyword': 'React.js Developer', 'location': NAUKRI_LOCATION},
    {'keyword': 'Frontend React Developer', 'location': NAUKRI_LOCATION},
    {'keyword': 'AWS DevOps Engineer', 'location': NAUKRI_LOCATION},
    {'keyword': 'Site Reliability Engineer', 'location': NAUKRI_LOCATION},
    {'keyword': 'Platform Engineer', 'location': NAUKRI_LOCATION},
    {'keyword': 'Kubernetes', 'location': NAUKRI_LOCATION},
    {'keyword': 'Terraform', 'location': NAUKRI_LOCATION},
]

TITLE_KEYWORDS = [
    'react', 'reactjs', 'react.js', 'react native', 'frontend', 'front-end', 'full stack',
    'devops', 'dev ops', 'sre', 'site reliability', 'platform engineer', 'cloud',
    'aws', 'azure', 'gcp', 'kubernetes', 'docker', 'terraform', 'ci/cd', 'jenkins',
    'infrastructure', 'linux',
]

EXPERIENCE_YEARS = _env_int('EXPERIENCE_YEARS', 2)
JOB_AGE_DAYS = _env_int('JOB_AGE_DAYS', 14)
MAX_PAGES_PER_QUERY = _env_int('MAX_PAGES_PER_QUERY', 3 if _IS_VERCEL else 10)
PAGES_PER_QUERY = MAX_PAGES_PER_QUERY
NAUKRI_RESULTS_PER_PAGE = _env_int('NAUKRI_RESULTS_PER_PAGE', 20)

SEARCH_DELAY_SEC = 1.5
APPLY_DELAY_SEC = 3
EXCEL_FILE = os.getenv('EXCEL_FILE', 'job_applications.xlsx')
APPLIED_JOBS_CSV = 'applied_jobs.csv'

LINKEDIN_COOKIES_FILE = 'linkedin_cookies.json'
LINKEDIN_LOCATION = 'India'
LINKEDIN_MAX_JOBS_PER_QUERY = _env_int('LINKEDIN_MAX_JOBS_PER_QUERY', 15)
LINKEDIN_SEARCH_QUERIES = [
    'AWS DevOps', 'Cloud Engineer', 'DevOps Engineer', 'DevOps',
    'React Developer', 'React.js Developer', 'Site Reliability Engineer',
]
LINKEDIN_HEADLESS = _env_bool('LINKEDIN_HEADLESS', False)
USE_BRAVE_BROWSER = True
BRAVE_BINARY_PATH = ''
LINKEDIN_EASY_APPLY_MAX_STEPS = 25
USE_OPENROUTER_FOR_LINKEDIN = True
OPENROUTER_MODEL = 'openai/gpt-oss-120b:free'

APPLICANT_PROFILE = {
    'current_ctc_annual': 168000,
    'expected_ctc_annual': 500000,
    'exp_total': '2',
    'current_location': 'Pune',
    'willing_to_relocate': True,
    'notice_days': 30,
    'skills': [
        'react', 'javascript', 'typescript', 'redux', 'aws', 'cloud', 'devops',
        'docker', 'kubernetes', 'ci/cd', 'jenkins', 'terraform', 'linux', 'git',
    ],
}
 