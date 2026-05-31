"""Configuration for Naukri auto-apply (React Developer & DevOps Engineer)."""

# Search keywords — jobs are fetched for each entry (All India when location is empty)
SEARCH_QUERIES = [
    {"keyword": "React Developer", "location": ""},
    {"keyword": "React.js Developer", "location": ""},
    {"keyword": "Frontend React Developer", "location": ""},
    {"keyword": "React Native Developer", "location": ""},
    {"keyword": "DevOps Engineer", "location": ""},
    {"keyword": "DevOps", "location": ""},
    {"keyword": "AWS DevOps Engineer", "location": ""},
    {"keyword": "Site Reliability Engineer", "location": ""},
]

# Only apply when job title matches at least one of these (case-insensitive)
TITLE_KEYWORDS = [
    "react",
    "reactjs",
    "react.js",
    "react native",
    "frontend",
    "front-end",
    "devops",
    "dev ops",
    "sre",
    "site reliability",
    "platform engineer",
    "cloud engineer",
    "kubernetes",
    "docker",
    "aws",
    "azure",
    "gcp",
    "ci/cd",
    "jenkins",
    "terraform",
]

# Experience in years (Naukri search filter)
EXPERIENCE_YEARS = 2

# Max age of job postings in days (1 = today, 3 = last 3 days)
JOB_AGE_DAYS = 3

# Pages to fetch per search query
PAGES_PER_QUERY = 2

# Delay between API calls (seconds) — avoid rate limits
SEARCH_DELAY_SEC = 1.5
APPLY_DELAY_SEC = 3

# Excel file — all runs append to this same file
EXCEL_FILE = "naukri_jobs.xlsx"

# Legacy CSV (optional backup; Excel is the main store)
APPLIED_JOBS_CSV = "applied_jobs.csv"

# Your profile — used when Naukri asks questions during apply
APPLICANT_PROFILE = {
    "current_ctc_annual": 168000,   # ₹1,68,000 per year
    "expected_ctc_annual": 500000,  # ₹5,00,000 per year
    "exp_total": "2",               # years of experience (all questions)
    "current_location": "Pune",
    "willing_to_relocate": True,
    "notice_days": 30,
    "skills": [
        "react", "javascript", "typescript", "redux",
        "docker", "kubernetes", "aws", "ci/cd",
        "jenkins", "terraform", "linux", "git",
    ],
}
