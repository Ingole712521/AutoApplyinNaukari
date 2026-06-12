import json
import os
import re
import requests

class JobFilterPipeline2:
    MY_STACK = ['node', 'node.js', 'nodejs', 'python', 'javascript', 'typescript', 'express', 'express.js', 'fastapi', 'flask', 'nestjs', 'nest.js', 'django', 'hapi', 'koa', 'mongodb', 'mongoose', 'postgresql', 'mysql', 'redis', 'sqlite', 'dynamodb', 'firestore', 'cassandra', 'elasticsearch', 'sql', 'nosql', 'aws', 'gcp', 'azure', 'docker', 'kubernetes', 'ci/cd', 'github actions', 'jenkins', 'terraform', 'linux', 'nginx', 'ec2', 's3', 'lambda', 'cloudwatch', 'rest', 'rest api', 'restful', 'graphql', 'websocket', 'grpc', 'kafka', 'rabbitmq', 'celery', 'bull', 'socket.io', 'selenium', 'playwright', 'puppeteer', 'beautifulsoup', 'scrapy', 'web scraping', 'automation', 'n8n', 'trigger.dev', 'zapier', 'langchain', 'openai', 'llm', 'rag', 'vector db', 'pinecone', 'weaviate', 'chromadb', 'huggingface', 'embeddings', 'genai', 'langsmith', 'llamaindex', 'git', 'github', 'postman', 'swagger', 'jwt', 'oauth', 'microservices', 'system design', 'api design']
    VETO_TITLES = ['walk-in', 'walkin', 'walk in', 'android developer', 'ios developer', 'flutter developer', 'frontend developer', 'front-end developer', 'principal engineer', 'staff engineer', 'architect', 'vp of', 'head of engineering', 'head of technology', 'founder', 'tutor', 'trainer', 'data scientist', 'ml engineer', 'data engineer', 'intern', 'internship', 'engineering manager', 'etl engineer', 'prompt engineer', 'analyst', 'associate is engineer', 'infra engineer', 'observability engineer', 'Manager']
    VETO_COMPANIES = {'accenture', 'wipro', 'infosys', 'tcs', 'cognizant', 'capgemini', 'hcl', 'tech mahindra', 'mphasis', 'hexaware', 'ltimindtree', 'persistent', 'birlasoft'}
    DESC_RED_FLAGS = {'walk-in': 'walk.?in|walkin', 'venue listed': 'venue\\s*:|interview venue|bring your resume|carry your resume'}
    SOFTWARE_KEYWORDS = {'software', 'developer', 'engineer', 'engineering', 'backend', 'full stack', 'fullstack', 'python', 'node', 'nodejs', 'javascript', 'typescript', 'django', 'fastapi', 'flask', 'golang', 'devops', 'cloud', 'sre', 'platform', 'api', 'microservices', 'infrastructure', 'tech lead', 'sde', 'swe', 'mts', 'programmer', 'react'}
    FRONTEND_VETO_KEYWORDS = {'frontend', 'front-end', 'front end', 'angular', 'vue', 'ui developer', 'ui engineer', 'android', 'ios', 'flutter', 'mobile', 'kotlin', 'swift', 'embedded', 'firmware', 'ml engineer', 'data engineer', 'data scientist', 'intern', 'internship', 'lead', 'Golang', 'MLops', 'devops', 'mlops', 'golang', ' Web developer - Java Technologies', ' Member of Technical Staff - MTS'}

    def __init__(self, openai_api_key, cache_file='score_cache.json', daily_apply_limit=50, min_apply_score=50, ai_score_limit=300, batch_size=50):
        self.api_key = openai_api_key
        self.url = 'https://api.openai.com/v1/chat/completions'
        self.cache_file = cache_file
        self.daily_apply_limit = daily_apply_limit
        self.min_apply_score = min_apply_score
        self.ai_score_limit = ai_score_limit
        self.batch_size = batch_size
        self.cache = self._load_cache()

    def run(self, jobs):
        print('\nRAW JOBS:', len(jobs))
        jobs = self.normalize_jobs(jobs)
        print('AFTER NORMALIZE:', len(jobs))
        jobs = self.dedup(jobs)
        print('AFTER DEDUP:', len(jobs))
        jobs = self.hard_veto(jobs)
        print('AFTER HARD VETO:', len(jobs))
        jobs = self.experience_filter(jobs)
        print('AFTER EXP FILTER:', len(jobs))
        jobs = self.desc_red_flag_check(jobs)
        print('AFTER RED FLAG CHECK:', len(jobs))
        jobs = self.title_filter(jobs)
        print('AFTER TITLE FILTER:', len(jobs))
        jobs = self.company_veto(jobs)
        print('AFTER COMPANY VETO:', len(jobs))
        jobs = self.tag_presort(jobs)
        jobs = jobs[:self.ai_score_limit]
        print('AFTER LIMIT:', len(jobs))
        jobs = self.ai_score_batch(jobs)
        jobs = self.rank(jobs)
        print('AFTER RANK:', len(jobs))
        jobs = self.select(jobs)
        print('FINAL SELECTED:', len(jobs))
        for j in jobs:
            print(f"  {j.get('ai_score'):>3}  {j.get('title')} @ {j.get('company')}  |  {j.get('ai_reason', '')}")
        return jobs

    def normalize_jobs(self, jobs):
        normalized = []
        for j in jobs:
            job = j if isinstance(j, dict) else j.__dict__
            posted = (job.get('posted_date') or '').lower()
            days_old = 7
            if 'today' in posted or 'hour' in posted or 'just now' in posted:
                days_old = 0
            elif 'yesterday' in posted:
                days_old = 1
            else:
                m = re.search('(\\d+)\\s*day', posted)
                if m:
                    days_old = int(m.group(1))
                else:
                    m = re.search('(\\d+)\\s*week', posted)
                    if m:
                        days_old = int(m.group(1)) * 7
            exp = job.get('experience') or ''
            exp_min, exp_max = (0, 10)
            nums = re.findall('\\d+', exp)
            if len(nums) >= 2:
                exp_min, exp_max = (int(nums[0]), int(nums[1]))
            elif len(nums) == 1:
                exp_min = exp_max = int(nums[0])
            raw_tags = job.get('tags') or job.get('skills') or []
            if isinstance(raw_tags, str):
                raw_tags = re.split('[,;|]', raw_tags)
            tags = [t.strip().lower() for t in raw_tags if t.strip()]
            normalized.append({'job_id': job.get('job_id'), 'title': (job.get('title') or '').strip(), 'company': (job.get('company') or '').strip(), 'location': (job.get('location') or '').strip(), 'description': (job.get('description') or '').strip(), 'tags': tags, 'mandatory_tags': tags[:2], 'optional_tags': tags[2:], 'days_old': days_old, 'experience_min': exp_min, 'experience_max': exp_max})
        return normalized

    def dedup(self, jobs):
        seen, result = (set(), [])
        for j in jobs:
            job_id = j.get('job_id')
            if job_id is None:
                result.append(j)
                continue
            if job_id in seen:
                continue
            seen.add(job_id)
            result.append(j)
        return result

    def hard_veto(self, jobs):
        clean = []
        for j in jobs:
            title = (j.get('title') or '').lower()
            if any((kw in title for kw in self.VETO_TITLES)):
                print(f"  [VETO] {j.get('title')}")
                continue
            clean.append(j)
        return clean

    def experience_filter(self, jobs):
        return [j for j in jobs if j.get('experience_min', 0) <= 4 and j.get('experience_max', 10) > 0]

    def desc_red_flag_check(self, jobs):
        clean = []
        for j in jobs:
            desc = (j.get('description') or '').lower()
            flagged = [label for label, pat in self.DESC_RED_FLAGS.items() if re.search(pat, desc)]
            if flagged:
                print(f"  [RED FLAG {flagged}] {j.get('title')}")
                continue
            clean.append(j)
        return clean

    def title_filter(self, jobs):
        result = []
        for j in jobs:
            title = (j.get('title') or '').lower()
            if not any((kw in title for kw in self.SOFTWARE_KEYWORDS)):
                print(f"  [TITLE FILTER - not software] {j.get('title')}")
                continue
            if any((kw in title for kw in self.FRONTEND_VETO_KEYWORDS)):
                print(f"  [TITLE FILTER - frontend/mobile] {j.get('title')}")
                continue
            result.append(j)
        return result

    def company_veto(self, jobs):
        clean = []
        for j in jobs:
            company = (j.get('company') or '').lower()
            if any((vc in company for vc in self.VETO_COMPANIES)):
                print(f"  [COMPANY VETO] {j.get('title')} @ {j.get('company')}")
                continue
            clean.append(j)
        return clean

    def tag_presort(self, jobs):
        my_stack = set(self.MY_STACK)

        def overlap(j):
            tags = set(j.get('tags', []))
            mandatory_hit = sum((1 for t in j.get('mandatory_tags', []) if t in my_stack))
            total_hit = len(tags & my_stack)
            recency_bonus = max(0, 7 - j.get('days_old', 7))
            return mandatory_hit * 3 + total_hit + recency_bonus
        return sorted(jobs, key=overlap, reverse=True)

    def ai_score_batch(self, jobs):
        result = []
        for i in range(0, len(jobs), self.batch_size):
            batch = jobs[i:i + self.batch_size]
            scores = self._call_ai(batch)
            for idx, job in enumerate(batch):
                jid = str(job.get('job_id') or '')
                data = self.cache.get(jid) if jid else None
                if not data:
                    data = scores.get(str(idx), {'score': 0, 'reason': 'no response'})
                    if not isinstance(data.get('score'), int):
                        data = {'score': 0, 'reason': 'parse error'}
                    if jid:
                        self.cache[jid] = data
                job['ai_score'] = data.get('score', 0)
                job['ai_reason'] = data.get('reason', '')
                result.append(job)
        self._save_cache()
        return result

    def _call_ai(self, jobs):
        job_block = ''
        for i, j in enumerate(jobs):
            mandatory = ', '.join(j.get('mandatory_tags', [])) or 'none'
            optional = ', '.join(j.get('optional_tags', [])) or 'none'
            exp = f"{j.get('experience_min', 0)}-{j.get('experience_max', 10)} yrs"
            job_block += f"Job {i}:\n  Title:     {j.get('title')}\n  Company:   {j.get('company')}\n  Mandatory: {mandatory}\n  Optional:  {optional}\n  Exp:       {exp}\n  Days old:  {j.get('days_old', 7)}\n---\n"
        prompt2 = f"""\nYou are a strict job filter for a backend developer. Score each job 0-100.\nBe precise — avoid clustering scores at 85 or 60. Use the full range.\n\nCANDIDATE:\n- 2.3 years experience, backend-focused\n- Core stack: Node.js, Python, MongoDB, REST APIs, AWS\n- Also knows: Docker, CI/CD, automation, Selenium, Playwright, web scraping,\n  n8n, trigger.dev, LangChain, RAG, vector DBs, FastAPI, Flask, Express\n- Looking for: SDE1 / junior-mid backend or fullstack-backend roles\n- Prefers: startups, product companies, AI/automation work, remote/hybrid\n- Will NOT do: pure frontend, mobile, ML research, data science, DevOps-only\n\nSCORING RUBRIC — use the full range, not just 85/60:\n\n90-100 — perfect fit, apply immediately\n  Node.js OR Python is mandatory tag + backend/fullstack role or python/node js is in the title of the job\n  + exp 0-2 yrs + familiar supporting stack. Startup or product company.\n\n75-89 — strong fit, apply\n  Node.js or Python present (mandatory or optional) + backend lean\n  + exp 0-3 yrs. Maybe one unfamiliar tag but overall good match.\n\n55-74 — decent fit, apply with lower priority\n  Some stack overlap, role is fullstack but not backend-heavy,\n  or exp is 3-4 yrs, or company type unclear.\n\n30-54 — weak, skip unless nothing better\n  Familiar tech present but role is vague, frontend-leaning,\n  or exp mismatch 4-5 yrs.\n\n10-29 — poor match\n  Very little stack overlap, or role is clearly not backend and have java,  \n\n0-9 — do not apply\n   That contain Java  and dotnet  Zero stack overlap (Java+Spring only, PHP only, .NET only etc.)\n  OR walk-in / venue / intern role.\n\nRULES:\n- Node.js + MongoDB + 0-2yr backend → 90+, no exceptions\n- Java alongside Node/Python is fine — judge the full picture\n- Fullstack with Node backend → 65-80 depending on tag quality\n- "Software Engineer" with Python/Node tags → treat as backend, score 70-85\n- Pure React/Angular/Vue with no backend tags → 0-15\n- DevOps/infra-only with no app dev → 20-40\n- Intern roles → 0\n- Missing stack items is normal, don't over-penalise\n- Recency: 0-1 days old → mentally add 5 points\n\nReturn ONLY valid JSON, no explanation outside it:\n{{\n  "0": {{"score": 92, "reason": "Node.js + MongoDB mandatory, 0-2yr, startup backend"}},\n  "1": {{"score": 0,  "reason": "Java/Spring only, zero overlap"}}\n}}\n\nJobs:\n{job_block}\n"""
        prompt = f"""\nYou are scoring job listings for a backend developer. Score each job 0-100.\n\nCANDIDATE:\n- 2 years experience, backend-focused\n- Core stack: Node.js, Python, MongoDB, REST APIs, AWS\n- Also knows: automation, Selenium, web scraping, Docker, CI/CD, n8n, trigger.dev,\n  Playwright, Postman, Git, LangChain, RAG, vector DBs\n- Looking for: SDE1 or junior-mid backend/fullstack-backend roles\n- Likes: startups, product companies, AI/automation work, remote/hybrid\n\nSCORING:\n\n85-100 — apply immediately\n  Node.js or Python is a mandatory tag, other tags are familiar stack,\n  exp is 0-3 yrs or not specified, role is backend or fullstack-backend.\n\n60-84 — good fit, apply\n  Node.js or Python present but not mandatory, or fullstack role with\n  backend-heavy tags, or slight exp mismatch (3-4 yrs).\n\n35-59 — decent, worth applying\n  Some stack overlap but role is vague or tags are mixed frontend/backend,\n  or exp is borderline 4-5 yrs.\n\n10-34 — weak match, skip unless desperate\n  Familiar tech present but frontend-dominated, or very little tag overlap.\n\n0 — do not apply\n  Tags are entirely foreign stack (Java+Spring+Hibernate only, PHP only, etc.)\n  with zero overlap with candidate's stack. OR walk-in / venue in title.\n\nCOMMON SENSE RULES (these matter):\n- Java appearing alongside Node.js or Python is FINE — score on the whole picture.\n- "Fullstack" with Node backend is a GOOD fit (60-80 range).\n- Missing one or two stack items is normal — don't penalise heavily.\n- A job tagged [node.js, mongodb] with exp 0-2 yrs should score 85+.\n- A job tagged [java, spring, hibernate] with NO node/python should score 0-15.\n- Recency matters: jobs 0-1 days old get +5 bonus mentally.\n\nReturn ONLY valid JSON, no explanation outside it:\n{{\n  "0": {{"score": 85, "reason": "Node.js + MongoDB mandatory, 0-2yr, startup"}},\n  "1": {{"score": 0,  "reason": "Java/Spring only, zero stack overlap"}}\n}}\n\nJobs:\n{job_block}\n"""
        try:
            res = requests.post(self.url, headers={'Authorization': f'Bearer {self.api_key}', 'Content-Type': 'application/json'}, json={'model': 'gpt-4o-mini', 'messages': [{'role': 'user', 'content': prompt2}], 'temperature': 0.2}, timeout=90)
            if res.status_code != 200:
                print('AI HTTP ERROR:', res.status_code, res.text[:200])
                return {}
            content = res.json()['choices'][0]['message']['content']
            content = re.sub('```json|```', '', content).strip()
            match = re.search('\\{.*\\}', content, re.S)
            if not match:
                print('AI PARSE ERROR — raw:', content[:300])
                return {}
            data = json.loads(match.group(0))
            return data if isinstance(data, dict) else {}
        except Exception as e:
            print('AI call error:', e)
            return {}

    def rank(self, jobs):
        return sorted(jobs, key=lambda j: j.get('ai_score', 0) + max(0, 3 - j.get('days_old', 7)), reverse=True)

    def select(self, jobs):
        apply_list = [j for j in jobs if j.get('ai_score', 0) >= self.min_apply_score]
        review_list = [j for j in jobs if 10 <= j.get('ai_score', 0) < self.min_apply_score]
        if review_list:
            print(f'\n── REVIEW MANUALLY ({len(review_list)}) ──')
            for j in review_list:
                print(f"  score={j.get('ai_score')}  {j.get('title')} @ {j.get('company')}  |  {j.get('ai_reason', '')}")
        return apply_list[:self.daily_apply_limit]

    def _load_cache(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file) as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_cache(self):
        with open(self.cache_file, 'w') as f:
            json.dump(self.cache, f, indent=2)
