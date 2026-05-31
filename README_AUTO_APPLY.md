# Naukri Auto-Apply — React Developer & DevOps Engineer

Automatically search [Naukri.com](https://www.naukri.com) for **React Developer** and **DevOps Engineer** jobs across India and apply to roles that support **Easy Apply** (one-click apply on Naukri).

Built on the [NopeRi](https://github.com/Traverser25/NopeRi) API client (no browser needed for search/apply).

## What it does

1. Logs into your Naukri account
2. Searches for React and DevOps related keywords (all locations)
3. Filters jobs whose title matches React or DevOps roles
4. Applies automatically to Easy Apply jobs
5. Skips jobs that redirect to external company sites
6. Auto-fills basic questionnaires when possible
7. Saves applied job IDs to `applied_jobs.csv` so you never apply twice

## Setup

### 1. Install Python 3.10+

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Sign in (Google users — most common)

If you use **Sign in with Google** on Naukri, run this once:

```bash
python google_login.py
```

- Chrome opens the Naukri login page
- Click **Sign in with Google** and complete login
- Session is saved to `naukri_cookies.json`
- Re-run only when the session expires (usually days/weeks)

### 4. Run auto-apply

```bash
python react_devops_auto_apply.py
```

### Alternative: email/password sign-in

If you use email + password (not Google), create `.env`:

```bash
copy .env.example .env
```

```env
USERNAME=your_email@example.com
PASSWORD=your_naukri_password
```

## Configuration

Edit `config.py` to customize:

| Setting | Default | Description |
|---------|---------|-------------|
| `SEARCH_QUERIES` | React, DevOps keywords | What to search on Naukri |
| `TITLE_KEYWORDS` | react, devops, sre, aws... | Title filter after search |
| `EXPERIENCE_YEARS` | 2 | Your experience level |
| `JOB_AGE_DAYS` | 3 | Only jobs posted in last N days |
| `PAGES_PER_QUERY` | 2 | Result pages per keyword |

## Important notes

- **Run from home IP** — Naukri often blocks cloud/datacenter IPs (Azure, GitHub Actions). Home broadband works best.
- **Easy Apply only** — Jobs that send you to a company website are skipped (you must apply there manually).
- **MFA/OTP** — If login fails, log in once in your browser from the same network, then retry.
- **Terms of service** — Use only on your own account. Respect [Naukri's Terms](https://www.naukri.com/termsAndConditions).

## Schedule daily runs (optional)

**Windows Task Scheduler:** Create a task that runs:

```
python d:\animioui\webscraper\react_devops_auto_apply.py
```

**Linux/macOS cron** (example — daily at 9 AM):

```
0 9 * * * cd /path/to/webscraper && python react_devops_auto_apply.py
```

## Output (Excel)

All job data is saved to **`naukri_jobs.xlsx`** in the project folder.

- **First run** — creates the Excel file with headers
- **Every next run** — new rows are **added below** previous data (never overwritten)

Each row includes:

| Column | Description |
|--------|-------------|
| Run Date / Run Time | When you ran the script |
| Job ID, Title, Company | Job details |
| Location, Experience, Salary | From Naukri listing |
| Posted Date | When job was posted |
| Search Keyword | Which search found it |
| Skills | Required skills |
| Job URL | Link to the job |
| Status | Applied / Failed / Skipped |
| Applied At | Timestamp if applied |
| Notes | Error or skip reason |

A **run summary row** is added at the end of each run.

Change the file name in `config.py`: `EXCEL_FILE = "naukri_jobs.xlsx"`

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `403 Forbidden` on search | Run from home IP; nkparam token may be blocked |
| Login failed / OTP | Google users: run `python google_login.py` again |
| No jobs found | Increase `JOB_AGE_DAYS` or `PAGES_PER_QUERY` in `config.py` |
| Questionnaire failed | Update salary/experience in `src/client/job_client.py` PROFILE dict |

## Project structure

```
webscraper/
├── google_login.py              # One-time Google sign-in (run first)
├── react_devops_auto_apply.py   # Main script — run this daily
├── naukri_cookies.json          # Saved session (auto-created, do not share)
├── config.py                    # Search keywords & filters
├── .env                         # Your credentials (not committed)
├── applied_jobs.csv             # Applied job history (auto-created)
└── src/                         # Naukri API client (from NopeRi)
```
