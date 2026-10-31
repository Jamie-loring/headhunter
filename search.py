#!/usr/bin/env python3
"""
Job search agent — runs every 3 hours via cron.
100% free. Sources:
  - Remotive (JSON API, no key)
  - We Work Remotely (RSS, no key)
  - Remote OK (JSON API, no key)
  - Dice (HTML scrape, no key)
  - USAJOBS (JSON API — free key, set USAJOBS_API_KEY env var)
    Register free at: https://developer.usajobs.gov/APIRequest/Index
"""
import os, re, json, logging, requests
from datetime import datetime, timezone
from xml.etree import ElementTree as ET

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[logging.StreamHandler()]
)
log = logging.getLogger(__name__)

API_BASE = 'http://localhost:5005'

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

TECH_KW = [
    'Microsoft Sentinel','Defender for Cloud','Entra ID','Azure AD','Azure Policy',
    'CSPM','EASM','Purview','DLP','KQL','Kusto','PowerShell','Python',
    'Microsoft Graph','SIEM','SOAR','XDR','EDR','Sophos','Meraki','Cisco',
    'Palo Alto','CrowdStrike','Okta','MITRE ATT&CK','threat hunting',
    'threat intelligence','incident response','penetration testing',
    'red team','purple team','SOC','SOC 2','NIST','CIS','FedRAMP','CMMC',
    'Zero Trust','IAM','PAM','Terraform','Bicep','DevSecOps','Docker',
    'Kubernetes','Splunk','QRadar','CyberArk','vulnerability management',
    'Nessus','Qualys','log ingestion','detection engineering','analytics rules',
    'Public Trust','Secret','Top Secret','TS/SCI','clearance',
    'Security+','CISSP','CISM','CASP','SecurityX','AZ-500','SC-200',
    'Shodan','attack surface','TLS','PKI','certificate management',
]

SKIP_TERMS = [
    'helpdesk','help desk','desktop support','tier 1','level 1','intern',
    'entry level','entry-level','junior','physical security','security guard',
    'loss prevention','sales','account executive',
]

REQUIRE_ONE = [
    'azure','sentinel','cloud security','siem','defender','threat engineer',
    'security engineer','security architect','detection engineer','cspm',
    'entra','cloud infrastructure security',
]


# ── Remotive — free JSON API, great remote coverage ─────────────────────────
REMOTIVE_SEARCHES = [
    # Core
    'azure security',
    'microsoft sentinel',
    'cloud security engineer',
    'siem engineer',
    # Detection & response
    'threat detection engineer',
    'detection and response',
    'detection engineer',
    'security operations engineer',
    # Architecture / posture
    'cloud security architect',
    'devsecops',
    'zero trust',
    # Identity & access
    'identity security engineer',
    # Threat intel / hunting
    'threat intelligence',
    'threat hunter',
    # Broad blue-team
    'cyber defense engineer',
    'incident response engineer',
    'soar engineer',
]

def fetch_remotive(search):
    try:
        r = requests.get(
            'https://remotive.com/api/remote-jobs',
            params={'category': 'software-dev', 'search': search, 'limit': 20},
            headers=HEADERS, timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        results = []
        for j in data.get('jobs', []):
            desc_html = j.get('description', '')
            desc = re.sub(r'<[^>]+>', ' ', desc_html)
            results.append(dict(
                role=j.get('title', ''),
                company=j.get('company_name', ''),
                location=j.get('candidate_required_location', 'Remote'),
                url=j.get('url', ''),
                salary=j.get('salary') or None,
                description=desc,
                source='Remotive',
            ))
        return results
    except Exception as e:
        log.warning(f'Remotive "{search}": {e}')
        return []


# ── We Work Remotely — RSS, free, no key ─────────────────────────────────────
WWR_FEEDS = [
    'https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss',
    'https://weworkremotely.com/categories/remote-full-stack-programming-jobs.rss',
]

def fetch_wwr(feed_url):
    try:
        r = requests.get(feed_url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        items = []
        for item in root.findall('.//item'):
            def t(tag):
                el = item.find(tag)
                return el.text.strip() if el is not None and el.text else ''
            title_raw = t('title')
            # WWR titles: "Company: Role Title"
            if ': ' in title_raw:
                co, role = title_raw.split(': ', 1)
            else:
                co, role = '', title_raw
            link = t('link')
            if not link:
                for g in item.findall('{http://www.w3.org/2005/Atom}link'):
                    link = g.get('href', '')
            desc = re.sub(r'<[^>]+>', ' ', t('description'))
            region_el = item.find('{https://weworkremotely.com}region')
            loc = region_el.text.strip() if region_el is not None and region_el.text else 'Remote'
            items.append(dict(
                role=role.strip(),
                company=co.strip(),
                location=loc,
                url=link,
                description=desc,
                source='We Work Remotely',
            ))
        return items
    except Exception as e:
        log.warning(f'WWR "{feed_url}": {e}')
        return []


# ── Remote OK — free JSON API ─────────────────────────────────────────────────
REMOTEOK_TAGS = ['security', 'azure', 'cloud', 'devops']

def fetch_remoteok(tag):
    try:
        r = requests.get(
            f'https://remoteok.com/api?tags={tag}',
            headers={**HEADERS, 'Accept': 'application/json'},
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        items = []
        for j in data:
            if not isinstance(j, dict) or not j.get('position'):
                continue
            desc = re.sub(r'<[^>]+>', ' ', j.get('description', ''))
            items.append(dict(
                role=j.get('position', ''),
                company=j.get('company', ''),
                location=j.get('location', 'Remote'),
                url=j.get('url', ''),
                salary=j.get('salary') or None,
                description=desc,
                source='Remote OK',
            ))
        return items
    except Exception as e:
        log.warning(f'RemoteOK "{tag}": {e}')
        return []


# ── Dice — HTML scrape, no key ────────────────────────────────────────────────
DICE_QUERIES = [
    'azure security engineer',
    'microsoft sentinel engineer',
    'cloud security engineer',
]

def fetch_dice(q):
    try:
        from bs4 import BeautifulSoup
        r = requests.get(
            'https://www.dice.com/jobs',
            params={'q': q, 'location': 'Remote', 'filters.postedDate': 'ONE_WEEK'},
            headers=HEADERS, timeout=20,
        )
        r.raise_for_status()
        soup = BeautifulSoup(r.text, 'html.parser')
        items = []
        for card in soup.select('[data-testid="job-card"], dhi-search-card')[:15]:
            a = card.select_one('a[data-testid="job-title"], a.card-title-link, h5 a')
            if not a:
                continue
            role = a.get_text(strip=True)
            href = a.get('href', '')
            if href and not href.startswith('http'):
                href = 'https://www.dice.com' + href
            co = ''
            for sel in ['[data-testid="company-name"]', '.company-name', '[data-cy="search-result-company-name"]']:
                el = card.select_one(sel)
                if el:
                    co = el.get_text(strip=True)
                    break
            loc = 'Remote'
            for sel in ['[data-testid="location"]', '.location', '[data-cy="search-result-location"]']:
                el = card.select_one(sel)
                if el:
                    loc = el.get_text(strip=True)
                    break
            items.append(dict(
                role=role, company=co, location=loc, url=href,
                description=role + ' ' + co, source='Dice',
            ))
        return items
    except Exception as e:
        log.warning(f'Dice "{q}": {e}')
        return []


# ── JobSpy — LinkedIn, Indeed, Glassdoor, ZipRecruiter (no login, no key) ────
# https://github.com/speedyapply/JobSpy
JOBSPY_REMOTE_QUERIES = [
    'azure security engineer',
    'cloud security engineer',
    'microsoft sentinel engineer',
    'siem engineer',
    'detection engineer',
    'devsecops engineer',
]

JOBSPY_LOCAL_QUERIES = [
    'security engineer',
    'cloud security engineer',
    'information security engineer',
]

SITE_LABELS = {
    'linkedin': 'LinkedIn',
    'indeed': 'Indeed',
    'glassdoor': 'Glassdoor',
    'zip_recruiter': 'ZipRecruiter',
}

def fetch_jobspy(query, location=None, is_remote=False):
    try:
        import time
        import pandas as pd
        from jobspy import scrape_jobs
        kwargs = dict(
            site_name=['linkedin', 'indeed', 'glassdoor', 'zip_recruiter'],
            search_term=query,
            results_wanted=20,
            hours_old=168,
            country_indeed='USA',
            verbose=0,
        )
        if location:
            kwargs['location'] = location
            kwargs['distance'] = 20
        if is_remote:
            kwargs['is_remote'] = True
        df = scrape_jobs(**kwargs)
        items = []
        for _, j in df.iterrows():
            url = j.get('job_url') or j.get('job_url_direct', '')
            if not url or (hasattr(url, '__class__') and pd.isna(url)):
                continue
            url = str(url)
            loc = j.get('location', '')
            if not loc or (hasattr(loc, '__class__') and pd.isna(loc)):
                loc = 'Remote' if is_remote else ''
            salary = None
            try:
                min_a, max_a = j.get('min_amount'), j.get('max_amount')
                if min_a and max_a and not pd.isna(min_a) and not pd.isna(max_a):
                    suffix = '/hr' if str(j.get('interval', '')).lower() == 'hourly' else ''
                    salary = f'${int(min_a):,}–${int(max_a):,}{suffix}'
            except Exception:
                pass
            site = str(j.get('site', '') or '')
            items.append(dict(
                role=str(j.get('title', '') or ''),
                company=str(j.get('company', '') or ''),
                location=str(loc),
                url=url,
                salary=salary,
                description=str(j.get('description', '') or ''),
                source=SITE_LABELS.get(site, site.title()),
            ))
        return items
    except Exception as e:
        log.warning(f'JobSpy "{query}" (remote={is_remote} loc={location}): {e}')
        return []


# ── Adzuna — free API, location + radius search ───────────────────────────────
# Register free at: https://developer.adzuna.com/
# Set ADZUNA_APP_ID and ADZUNA_APP_KEY env vars in docker-compose
ADZUNA_QUERIES = [
    'azure security engineer',
    'cloud security engineer',
    'information security engineer',
    'microsoft sentinel engineer',
    'siem engineer',
    'security operations engineer',
    'devsecops engineer',
    'threat detection engineer',
]

def fetch_adzuna(query):
    app_id = os.environ.get('ADZUNA_APP_ID', '')
    app_key = os.environ.get('ADZUNA_APP_KEY', '')
    if not app_id or not app_key:
        return []
    try:
        r = requests.get(
            'https://api.adzuna.com/v1/api/jobs/us/search/1',
            params={
                'app_id': app_id,
                'app_key': app_key,
                'what': query,
                'where': 'Glendale, AZ',
                'distance': 20,
                'results_per_page': 20,
                'content-type': 'application/json',
            },
            timeout=15,
        )
        r.raise_for_status()
        items = []
        for j in r.json().get('results', []):
            loc = j.get('location', {}).get('display_name', 'Phoenix, AZ')
            sal_min = j.get('salary_min')
            sal_max = j.get('salary_max')
            salary = None
            if sal_min and sal_max:
                salary = f'${int(sal_min):,} – ${int(sal_max):,}'
            elif sal_min:
                salary = f'${int(sal_min):,}+'
            desc = re.sub(r'<[^>]+>', ' ', j.get('description', ''))
            items.append(dict(
                role=j.get('title', ''),
                company=j.get('company', {}).get('display_name', ''),
                location=loc,
                url=j.get('redirect_url', ''),
                salary=salary,
                description=desc,
                source='Adzuna',
            ))
        return items
    except Exception as e:
        log.warning(f'Adzuna "{query}": {e}')
        return []


# ── USAJOBS — free API key (register at developer.usajobs.gov) ───────────────
USAJOBS_QUERIES = [
    'Microsoft Sentinel security',
    'azure cloud security engineer',
    'information security engineer',
]

def fetch_usajobs(keyword):
    api_key = os.environ.get('USAJOBS_API_KEY', '')
    if not api_key:
        return []  # skip silently if no key
    try:
        r = requests.get(
            'https://data.usajobs.gov/api/search',
            params={
                'Keyword': keyword,
                'ResultsPerPage': 25,
                'SortField': 'OpenDate',
                'SortDirection': 'Desc',
            },
            headers={
                'Host': 'data.usajobs.gov',
                'User-Agent': 'jamie@jamieloring.com',
                'Authorization-Key': api_key,
            },
            timeout=15,
        )
        r.raise_for_status()
        items = []
        for hit in r.json().get('SearchResult', {}).get('SearchResultItems', []):
            mv = hit.get('MatchedObjectDescriptor', {})
            locs = mv.get('PositionLocation', [{}])
            loc = locs[0].get('LocationName', 'National') if locs else 'National'
            remu = mv.get('PositionRemuneration', [{}])
            salary = None
            if remu:
                lo = remu[0].get('MinimumRange')
                hi = remu[0].get('MaximumRange')
                if lo and hi:
                    salary = f'${int(float(lo)):,} – ${int(float(hi)):,}'
            desc = (mv.get('QualificationSummary', '') + ' ' +
                    mv.get('UserArea', {}).get('Details', {}).get('JobSummary', ''))
            items.append(dict(
                role=mv.get('PositionTitle', ''),
                company=mv.get('OrganizationName', 'U.S. Federal Government'),
                location=loc,
                url=mv.get('PositionURI', ''),
                salary=salary,
                description=desc,
                source='USAJOBS',
            ))
        return items
    except Exception as e:
        log.warning(f'USAJOBS "{keyword}": {e}')
        return []


# ── Helpers ───────────────────────────────────────────────────────────────────
def extract_keywords(text):
    tl = text.lower()
    return [kw for kw in TECH_KW if kw.lower() in tl][:20]


ROLE_REQUIRED = [
    'security','siem','sentinel','defender','threat','detection','cspm','azure',
    'cloud','devsecops','penetrat','red team','purple team','compliance','soc ',
    'infosec','cyber','iam','identity','vault','pam','sast','dast','appsec',
]

def is_relevant(role, description):
    role_lower = role.lower()
    # Irrelevant terms in title = skip immediately
    if any(s in role_lower for s in SKIP_TERMS):
        return False
    # The TITLE must contain a security/cloud signal
    if not any(t in role_lower for t in ROLE_REQUIRED):
        return False
    # Description double-check: require one strong indicator
    combined = (role + ' ' + description).lower()
    return any(t in combined for t in REQUIRE_ONE)


def get_existing_urls():
    try:
        r = requests.get(f'{API_BASE}/api/jobs', timeout=10)
        r.raise_for_status()
        return {j['url'] for j in r.json() if j.get('url')}
    except Exception as e:
        log.warning(f'Could not load existing jobs: {e}')
        return set()


def post_job(job):
    try:
        r = requests.post(f'{API_BASE}/api/jobs', json=job, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log.error(f'Failed to post job: {e}')
        return None


# ── Main ──────────────────────────────────────────────────────────────────────
def run():
    existing = get_existing_urls()
    log.info(f'Existing: {len(existing)} jobs — hunting...')

    candidates = []
    seen = set(existing)

    import time

    for q in JOBSPY_REMOTE_QUERIES:
        items = fetch_jobspy(q, is_remote=True)
        log.info(f'  JobSpy remote "{q}" → {len(items)}')
        candidates.extend(items)
        time.sleep(2)

    for q in JOBSPY_LOCAL_QUERIES:
        items = fetch_jobspy(q, location='Phoenix, AZ')
        log.info(f'  JobSpy local "{q}" → {len(items)}')
        candidates.extend(items)
        time.sleep(2)

    for q in REMOTIVE_SEARCHES:
        items = fetch_remotive(q)
        log.info(f'  Remotive "{q}" → {len(items)}')
        candidates.extend(items)

    for feed in WWR_FEEDS:
        items = fetch_wwr(feed)
        label = feed.split('/categories/')[1].split('.')[0]
        log.info(f'  WWR {label} → {len(items)}')
        candidates.extend(items)

    for tag in REMOTEOK_TAGS:
        items = fetch_remoteok(tag)
        log.info(f'  RemoteOK "{tag}" → {len(items)}')
        candidates.extend(items)

    for q in DICE_QUERIES:
        items = fetch_dice(q)
        log.info(f'  Dice "{q}" → {len(items)}')
        candidates.extend(items)

    for q in ADZUNA_QUERIES:
        items = fetch_adzuna(q)
        if items:
            log.info(f'  Adzuna "{q}" → {len(items)}')
        candidates.extend(items)

    for kw in USAJOBS_QUERIES:
        items = fetch_usajobs(kw)
        if items:
            log.info(f'  USAJOBS "{kw}" → {len(items)}')
        candidates.extend(items)

    now = datetime.now(timezone.utc).isoformat()
    added = 0

    for c in candidates:
        url = (c.get('url') or '').strip()
        if not url or url in seen:
            continue
        if not is_relevant(c.get('role', ''), c.get('description', '')):
            continue
        seen.add(url)

        raw_desc = c.get('description', '')
        kws = extract_keywords(c.get('role', '') + ' ' + raw_desc)
        job = dict(
            company=c.get('company') or 'Unknown',
            role=c.get('role', ''),
            location=c.get('location', ''),
            url=url,
            salary=c.get('salary'),
            source=c.get('source', ''),
            date_found=now,
            status='new',
            jd_keywords=kws,
            tailored={'added_keywords': kws},
            description=raw_desc[:4000] if raw_desc else '',
        )
        result = post_job(job)
        if result and not result.get('duplicate'):
            added += 1
            log.info(f'  + {job["company"]} — {job["role"]}')

    try:
        requests.post(f'{API_BASE}/api/meta', json={
            'last_run': now,
            'jobs_added_last_run': added,
        }, timeout=5)
    except Exception:
        pass

    log.info(f'Done — {added} new jobs added')


if __name__ == '__main__':
    run()
