import sqlite3, json, os, re, subprocess, imaplib, email, urllib.request, urllib.parse
import concurrent.futures
from email.header import decode_header as email_decode_header
from flask import Flask, jsonify, request, send_from_directory
from datetime import datetime, timezone
from collections import Counter
import json
import re
import email
import imaplib
import email

app = Flask(__name__)
DB = '/data/jobs.db'
CLAUDE_BIN = '/usr/local/bin/claude'

TIER_MAP = {
    'BrassRing': 'legacy', 'iCIMS': 'legacy', 'SuccessFactors': 'legacy',
    'Taleo': 'legacy', 'UKG': 'legacy',
    'BambooHR': 'standard', 'Jobvite': 'standard', 'Rippling': 'standard',
    'SmartRecruiters': 'standard', 'Workable': 'standard', 'Workday': 'standard',
    'Greenhouse': 'modern', 'Lever': 'modern', 'Ashby': 'modern',
    'LinkedIn Easy Apply': 'easy_apply', 'Indeed Easy Apply': 'easy_apply',
    'Dice Easy Apply': 'easy_apply',
    'Direct Contact': 'direct',
}
TIER_GUIDE = {
    'legacy':     'LEGACY ATS: ASCII only. No Unicode or symbols. Hyphen bullets (- ). Standard section headers only.',
    'standard':   'STANDARD ATS: Clean standard formatting. Keyword density is critical.',
    'modern':     'MODERN ATS: Standard formatting. Focus on keyword precision and compelling bullets.',
    'easy_apply': 'EASY APPLY (platform algorithmic scoring): The platform scores your resume against the JD automatically before a human ever sees it. MAXIMIZE keyword density — repeat the JD\'s exact skill terms and phrases throughout every section (summary, skills, bullets). Add a CORE COMPETENCIES section packed with JD terms. Every bullet should contain at least one JD keyword. Standard clean formatting is fine. The goal is the highest possible algorithmic match score.',
    'direct':     'DIRECT CONTACT (no ATS — human eyes only): This resume goes straight to a recruiter or hiring manager, bypassing automated screening entirely. Prioritize readability, narrative flow, and standout achievements over keyword density. Lead with impact. Every bullet should answer "so what?" — make the accomplishment and its significance immediately obvious to a non-technical reader as well as a technical one. Clean, polished formatting. Make them want to pick up the phone.',
}

DEFAULT_RESUME = """JAMIE LORING
623-297-8499 | jamie@jamieloring.com | Glendale, AZ

PROFESSIONAL SUMMARY
Senior cybersecurity engineer with 8+ years of experience specializing in offensive security, vulnerability management, and cloud defense. Builds and operates penetration testing frameworks, performs external attack surface management (EASM), and translates findings into developer-ready remediation. Operates Microsoft Sentinel SIEM, Defender for Cloud, and Entra ID at enterprise scale. CompTIA SecurityX (CASP+) certified; DoD Public Trust clearance active.

OFFENSIVE SECURITY & PROJECTS
- ShellShock: custom Parrot OS-based pentesting framework for network enumeration, exploitation, and post-exploitation automation
- EASM: built tooling for continuous external asset discovery, subdomain enumeration, and exposure tracking across client environments
- HackTheBox: global top 1% ranking across Active Directory, web exploitation, privilege escalation, and red team challenges
- LLM Automation: developed Python/Claude-based agents for automated security research, threat intelligence enrichment, and workflow automation
- Python scripting: security tooling, API integrations, log parsing, and operational automation across multiple roles

EXPERIENCE

Cloud & Threat Security Engineer | Troon | Jun 2026 - Oct 2026
- Designed and maintained Microsoft Sentinel SIEM with custom KQL detection rules, threat hunting playbooks, and automated incident response
- Managed Defender for Cloud security posture, Entra ID identity protection, and Azure Policy / CSPM across enterprise environment
- Developed Python automation for security operations workflows and LLM-assisted threat intelligence enrichment
- Collaborated with developers via Azure DevOps to triage, prioritize, and track vulnerability remediation to closure

Azure Security Engineer | Arrivia | Jul 2025 - Jun 2026
- Implemented Microsoft Sentinel log ingestion pipelines, analytics rules, and SOAR playbooks for cloud environment
- Managed Entra ID conditional access policies, MFA enforcement, and identity security posture
- Conducted threat hunting using KQL and MITRE ATT&CK framework; reduced false-positive alert volume through detection tuning
- Performed internal vulnerability assessments and coordinated with engineering teams via GitHub for remediation tracking

Azure SIEM Engineer | OPM | Jul 2023 - Jul 2024
- Built and maintained Microsoft Sentinel SIEM for federal civilian environment under FISMA / NIST 800-53 requirements
- Developed PowerShell and Microsoft Graph API automation for security operations and continuous monitoring reporting
- Supported ATO documentation and security control assessments for cloud-hosted federal systems

Sentinel Engineer | Microsoft Azure / Insight Global | Nov 2021 - Apr 2023
- Deployed Microsoft Sentinel for enterprise clients; built custom KQL workbooks, alerts, and threat hunting queries
- Integrated Defender for Cloud with Sentinel for unified threat detection and automated incident response workflows
- Designed zero trust architecture and conditional access implementations for Azure AD environments
- Performed external attack surface assessments to reduce client exposure prior to Sentinel onboarding

Network Security Analyst | Avnet | Feb 2020 - Nov 2021
- Managed Sophos endpoint security and Cisco Meraki network infrastructure across multi-site enterprise environment
- Performed incident response, forensic triage, and security automation workflows using Python and PowerShell
- Maintained IAM, RBAC policies, and vulnerability remediation tracking

SKILLS
Offensive Security: Penetration Testing | EASM | Vulnerability Management | Parrot OS / ShellShock | HackTheBox (Top 1%)
Cloud Security: Microsoft Sentinel | Defender for Cloud | Entra ID / Azure AD | Azure Policy | CSPM | EASM
SIEM / Detection: KQL | Log Ingestion Pipelines | MITRE ATT&CK | Threat Hunting | SOAR | Incident Response
Identity & IAM: Conditional Access | MFA | SSO | RBAC | Microsoft Graph API
Automation & Dev: Python | PowerShell | Bash | Azure DevOps | GitHub | LLM Automation
Compliance: FISMA | NIST 800-53 | FedRAMP | CMMC | Zero Trust Architecture
Endpoint & Network: Sophos | Cisco Meraki | Forensic Triage

CERTIFICATIONS
CompTIA SecurityX ce (CASP+) - Mar 2026
CompTIA Security+ - Apr 2024
Microsoft Azure Fundamentals (AZ-900)
DoD Public Trust Clearance (Active)

EDUCATION
B.S. Network Security & Administration | ITT Technical Institute | 2011-2014

--- KEYWORD POOL (optimizer use only — not resume content) ---
Draw from this pool when a JD uses these terms and they accurately reflect my background.
Do not invent experience. Only surface terms I have genuine hands-on exposure to.

SIEM / Detection Engineering:
Microsoft Sentinel, Azure Sentinel, KQL, Kusto Query Language, Log Analytics, Data Collection Rules,
DCR, Log Ingestion API, Custom Logs, Analytics Rules, Scheduled Query Rules, Fusion Rules,
SOAR, Playbooks, Logic Apps, Azure Automation, Watchlists, Threat Intelligence, TI indicators,
Workbooks, Dashboards, Hunting Queries, Notebooks, UEBA, Entity Analytics,
Splunk (exposure), Elastic SIEM (exposure), QRadar (exposure)

Cloud Security (Microsoft):
Microsoft Defender for Cloud, Defender for Servers, Defender for Containers,
Defender for Storage, Defender for SQL, Defender for Key Vault, Defender for DNS,
Defender XDR, Microsoft 365 Defender, Defender for Endpoint (MDE), Defender for Identity (MDI),
Defender for Office 365, Defender for Cloud Apps (MCAS), Azure Security Center,
Secure Score, Security Posture Management, CSPM, CWPP,
Entra ID, Azure Active Directory, Azure AD, Conditional Access, Identity Protection,
Privileged Identity Management (PIM), Entitlement Management, Access Reviews,
MFA, SSPR, B2B, B2C, Managed Identity, Service Principals, App Registrations,
Azure Policy, Policy Initiatives, Blueprints, Management Groups, RBAC, Resource Locks,
Azure Firewall, NSG, WAF, Application Gateway, Front Door, DDoS Protection,
Azure Key Vault, Secrets Management, Certificate Management, Disk Encryption,
Azure Monitor, Diagnostic Settings, Activity Log, Resource Graph,
Microsoft Purview, DLP, Information Protection, Sensitivity Labels, Insider Risk Management,
EASM, External Attack Surface Management, Defender EASM

Cloud Security (Multi-cloud):
AWS Security Hub, GuardDuty, CloudTrail, IAM (AWS), SCPs (exposure),
GCP Security Command Center (exposure),
Prisma Cloud (exposure), Wiz (exposure), Orca (exposure)

Identity & Access Management:
Zero Trust Architecture, Zero Trust Network Access (ZTNA),
SSO, SAML, OAuth 2.0, OIDC, Federation,
RBAC, ABAC, PAM, Privileged Access, Just-In-Time Access,
Active Directory, Group Policy, On-premises AD, AD Connect, Hybrid Identity,
CyberArk (exposure), BeyondTrust (exposure)

Offensive Security / Pentesting:
Penetration Testing, Network Penetration Testing, Web Application Penetration Testing,
Internal Penetration Testing, External Penetration Testing,
ShellShock (custom framework), Parrot OS, Kali Linux,
Nmap, Nessus, Metasploit, Burp Suite, Gobuster, Nikto, Impacket,
OSINT, Reconnaissance, Enumeration, Exploitation, Post-Exploitation, Lateral Movement,
Privilege Escalation, Persistence, Active Directory Attacks, Kerberoasting, Pass-the-Hash,
HackTheBox (Top 1% globally), TryHackMe,
Red Team, Adversary Simulation, Purple Team, Assumed Breach

Vulnerability Management:
Vulnerability Assessment, Vulnerability Scanning, Risk Prioritization, CVSS,
Remediation Tracking, Patch Management, Attack Surface Reduction,
Tenable, Qualys (exposure), Rapid7 (exposure),
EASM, External Exposure, Asset Discovery, Subdomain Enumeration

Incident Response & Threat Hunting:
Incident Response, IR Playbooks, Triage, Containment, Eradication, Recovery,
Digital Forensics, Memory Forensics, Disk Forensics, Log Forensics,
Threat Hunting, Hypothesis-Driven Hunting, MITRE ATT&CK, ATT&CK Navigator,
Threat Intelligence, IOC, IOA, TTPs, Kill Chain, Diamond Model,
DFIR, SOC Operations, Tier 1/2/3 Analysis, Escalation, Alert Triage

Compliance & Governance:
FISMA, NIST SP 800-53, NIST CSF, NIST 800-171,
FedRAMP, ATO, System Security Plan (SSP), POA&M, Continuous Monitoring,
CMMC, ITAR, DoD Public Trust Clearance,
CIS Controls, CIS Benchmarks, DISA STIGs,
SOC 2 (Type I/II awareness), ISO 27001 (awareness),
HIPAA (awareness), PCI DSS (awareness),
GRC, Risk Management, Security Policy, Audit Support

Automation & Development:
Python, PowerShell, Bash, KQL, Microsoft Graph API,
REST APIs, JSON, Azure Logic Apps, Azure Functions,
Git, GitHub, Azure DevOps, CI/CD awareness,
LLM integration, AI-assisted security workflows, Prompt Engineering,
Infrastructure as Code (IaC) awareness, Bicep (exposure), Terraform (exposure)

Networking & Endpoint:
TCP/IP, DNS, DHCP, VPN, TLS/SSL, HTTP/S, SMTP,
Firewall Management, Network Segmentation, VLAN, NAC,
Cisco Meraki, Sophos, Endpoint Detection and Response (EDR),
SASE (awareness), SD-WAN (awareness)
--- END KEYWORD POOL ---"""

STOP = {
    'the','and','for','with','that','this','have','from','will','are','not',
    'you','all','can','has','been','was','its','our','your','their','they',
    'what','which','when','where','who','how','any','such','each','must',
    'also','both','but','than','then','into','more','most','some','other',
    'these','those','about','would','could','should','shall','may','might',
    'need','use','using','used','work','working','works','provide','providing',
    'include','including','ensure','ensuring','support','supporting','develop',
    'developing','manage','managing','maintain','maintaining','implement',
    'implementing','design','designing','build','building','create','creating',
    'review','reviewing','help','helping','drive','driving','lead','leading',
    'collaborate','collaborating','communicate','communicating','assist',
    'assisting','participate','participating','monitor','monitoring',
    'prevent','preventing','protect','protecting','detect','detecting',
    'report','reporting','address','addressing','define','defining',
    'experience','required','preferred','responsibilities','requirements',
    'ability','skills','knowledge','understanding','strong','excellent',
    'good','great','role','team','position','company','job','candidate',
    'ideal','looking','seeking','years','year','within','across','multiple',
    'various','highly','well','effectively','efficiently','accurately',
    'systems','solutions','function','designs','approach','approaches',
    'strategy','strategies','initiative','initiatives','activity','activities',
    'effort','efforts','process','processes','procedure','procedures',
    'practice','practices','task','tasks','duty','duties','project','projects',
    'program','programs','service','services','product','products',
    'resource','resources','issue','issues','event','events','alert','alerts',
    'document','documents','standard','standards','regulation','regulations',
    'control','controls','attack','attacks','breach','breaches','risk','risks',
    'challenge','challenges','policy','policies','framework','frameworks',
    'environment','environments','platform','platforms','infrastructure',
    'unauthorized','access','threats','threat','protect',
    'pay','range','salary','compensation','benefits','bonus','package',
    'hourly','annual','rate','exempt','non-exempt','full-time','part-time',
}
BOOST = {
    'azure','sentinel','defender','entra','intune','purview','microsoft',
    'siem','soar','edr','xdr','dlp','casb','iam','pam','mfa','sso',
    'splunk','qradar','crowdstrike','elastic','logrhythm','sumo',
    'aws','gcp','terraform','ansible','kubernetes','docker','devops',
    'powershell','python','kql','kusto','bicep','cli','bash',
    'cissp','cism','ccsp','oscp','gcih','gcia','gsec','ceh',
    'casp','comptia','securityx','az-500','sc-200','sc-300','az-104',
    'nist','fedramp','cmmc','mitre','hipaa','sox','pci','dod',
    'rbac','governance','compliance','zero trust','conditional access',
    'vulnerability','penetration','incident response','threat hunting',
    'security operations','cloud security','identity','network security',
    'soc','cert','clearance','public trust',
}


def score_for_discover(jd_text, resume_text):
    """Score a job for discovery.

    Title hits score 20 pts each; description hits score 5 pts each.
    This keeps scores meaningful even with truncated API descriptions (500 chars).
    """
    parts = jd_text.split('\n', 1)
    title_l = parts[0].lower()
    desc_l = (parts[1] if len(parts) > 1 else '').lower()

    # Curated core skills — the terms most diagnostic of a good match
    CORE = [
        'sentinel', 'kql', 'defender', 'entra', 'azure', 'microsoft sentinel',
        'defender for cloud', 'entra id', 'cloud security', 'siem',
        'threat hunting', 'conditional access', 'powershell', 'mitre',
        'incident response', 'zero trust', 'iam', 'soc',
    ]

    def _match(term, text):
        return bool(re.search(r'(?<![a-z])' + re.escape(term) + r'(?![a-z])', text))

    matched = []
    missing = []
    score = 0
    for term in CORE:
        in_title = _match(term, title_l)
        in_desc = _match(term, desc_l)
        if in_title:
            score += 40
            matched.append(term)
        elif in_desc:
            score += 7
            matched.append(term)
        else:
            missing.append(term)

    score = min(100, score)
    missing_chips = [t for t in missing if any(w in BOOST for w in t.split())][:8]
    return {
        'score': score,
        'matched': matched[:15],
        'missing': missing_chips,
        'missing_count': len(missing),
    }


def compute_score(jd, resume):
    jd_l = jd.lower()
    resume_l = resume.lower()
    jd_tokens = re.findall(r'[a-z][a-z0-9+#.\-/]*[a-z0-9+#]|[a-z]{3,}', jd_l)
    unigrams = [t for t in jd_tokens if len(t) >= 4 and t not in STOP]
    bigrams = []
    for clause in re.split(r'[,;.!?\n|/\\()\[\]]', jd_l):
        ctoks = re.findall(r'[a-z][a-z0-9+#.\-/]*[a-z0-9+#]|[a-z]{3,}', clause)
        for i in range(len(ctoks) - 1):
            a, b = ctoks[i], ctoks[i+1]
            if a not in STOP and b not in STOP and len(a) >= 3 and len(b) >= 3:
                bigrams.append(f'{a} {b}')
    freq = Counter(unigrams + bigrams)
    covered = set()
    terms = {}
    for bg, cnt in freq.items():
        if ' ' in bg:
            parts = bg.split()
            w = 3 if any(p in BOOST for p in parts) else 1.5
            terms[bg] = w * min(cnt, 3)
            covered.update(parts)
    for ug, cnt in freq.items():
        if ' ' not in ug and ug not in covered:
            terms[ug] = (3 if ug in BOOST else 1) * min(cnt, 3)
    if not terms:
        return {'score': 0, 'matched': [], 'missing': []}
    total_weight = sum(terms.values())
    matched_weight = 0
    matched = []
    missing = []
    for term, weight in terms.items():
        if term in resume_l:
            matched_weight += weight
            matched.append((term, weight))
        else:
            missing.append((term, weight))
    score = min(round(matched_weight / total_weight * 100), 100)
    matched.sort(key=lambda x: -x[1])
    missing.sort(key=lambda x: -x[1])
    missing_chips = [t for t, _ in missing if any(w in BOOST for w in t.split())][:10]
    return {
        'score': score,
        'matched': [t for t, _ in matched[:15]],
        'missing': missing_chips,
        'missing_count': len(missing),
    }


def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS applications (
            id        TEXT PRIMARY KEY,
            company   TEXT,
            role      TEXT,
            ats       TEXT,
            source    TEXT,
            timestamp INTEGER,
            date_iso  TEXT
        )''')
        for col, default in [('status', "'applied'"), ('notes', "''"), ('jd_text', "''")]:
            try:
                conn.execute(f'ALTER TABLE applications ADD COLUMN {col} TEXT DEFAULT {default}')
            except sqlite3.OperationalError:
                pass
        conn.execute('''CREATE TABLE IF NOT EXISTS hidden_jobs (
            url       TEXT PRIMARY KEY,
            hidden_at INTEGER
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT
        )''')
        conn.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)',
                     ('resume', DEFAULT_RESUME))
        
        # ── Leads tables ────────────────────────────────────────────────────
        conn.execute(
            'CREATE TABLE IF NOT EXISTS leads ('
            '  id TEXT PRIMARY KEY,'
            '  title TEXT,'
            '  company TEXT,'
            '  location TEXT,'
            '  workplace TEXT,'
            '  source TEXT,'
            '  url TEXT,'
            '  posted TEXT,'
            '  found_at TEXT,'
            '  score INTEGER DEFAULT 0,'
            '  reason TEXT,'
            '  salary TEXT,'
            '  status TEXT DEFAULT "new",'
            '  status_changed_at TEXT,'
            '  email_message_id TEXT'
            ')'
        )
        conn.execute(
            'CREATE TABLE IF NOT EXISTS lead_runs ('
            '  id INTEGER PRIMARY KEY AUTOINCREMENT,'
            '  run_at TEXT,'
            '  added INTEGER,'
            '  filtered INTEGER,'
            '  errors INTEGER'
            ')'
        )
        conn.execute(
            'CREATE TABLE IF NOT EXISTS lead_blacklist ('
            '  company TEXT PRIMARY KEY'
            ')'
        )
        conn.execute(
            'CREATE TABLE IF NOT EXISTS processed_email_ids ('
            '  message_id TEXT PRIMARY KEY,'
            '  processed_at TEXT'
            ')'
        )
        # Seed blacklist
        for _co in ('lumifi cyber', 'troon'):
            conn.execute(
                'INSERT OR IGNORE INTO lead_blacklist (company) VALUES (?)', (_co,)
            )
        # Seed leads (spec row set, Oct 31 2026)
        _seed = [
            ('li-4430481978','Senior Cybersecurity Engineer','Verra Mobility',
             'Mesa, AZ','onsite_hybrid','LinkedIn',
             'https://www.linkedin.com/jobs/view/4430481978','',
             '2026-10-31T00:00:00+00:00',82,
             'Senior engineer title at an East Valley employer; likely hands-on '
             'and close to his Azure and SIEM work. Confirm on-site vs hybrid.','','new',''),
            ('li-4485258140','Cyber Threat Hunter','Booz Allen Hamilton',
             'Phoenix, AZ','onsite_hybrid','LinkedIn',
             'https://www.linkedin.com/jobs/view/4485258140','',
             '2026-10-31T00:00:00+00:00',76,
             'Hands-on hunting fits his KQL and MITRE ATT&CK work. '
             'Booz Allen roles often need a clearance.','','new',''),
            ('li-4392277246','Cyber Threat Lead','ManTech',
             'Chandler, AZ','onsite_hybrid','LinkedIn',
             'https://www.linkedin.com/jobs/view/4392277246','',
             '2026-10-31T00:00:00+00:00',72,
             'Lead-level threat role. He applied to ManTech recently; check it '
             "isn't the same posting. Likely clearance-dependent.",'','new',''),
            ('li-4467965082','Senior Consultant Cyber Engineering','Deloitte',
             'Gilbert or Tempe, AZ','onsite_hybrid','LinkedIn',
             'https://www.linkedin.com/jobs/view/4467965082','',
             '2026-10-31T00:00:00+00:00',58,
             'Consulting role posted in two cities. He already has several '
             'Deloitte applications; check travel.','','new',''),
            ('li-4482568504','Security Operations Analyst','onsemi',
             'Scottsdale, AZ','onsite_hybrid','LinkedIn',
             'https://www.linkedin.com/jobs/view/4482568504','',
             '2026-10-31T00:00:00+00:00',48,
             'Hands-on SOC work close to home, but an analyst title, '
             'likely below his level.','','new',''),
        ]
        for _row in _seed:
            conn.execute(
                'INSERT OR IGNORE INTO leads '
                '(id,title,company,location,workplace,source,url,posted,'
                'found_at,score,reason,salary,status,status_changed_at) '
                'VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                _row
            )
        # ── End leads tables ─────────────────────────────────────────────────
        conn.commit()


def decode_mime(s):
    if not s:
        return ''
    parts = email_decode_header(s)
    result = []
    for part, enc in parts:
        if isinstance(part, bytes):
            result.append(part.decode(enc or 'utf-8', errors='replace'))
        else:
            result.append(part)
    return ''.join(result)


def _http_get(url, headers=None, timeout=8):
    req = urllib.request.Request(url, headers={'User-Agent': 'headhunter/1.0'})
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def _fetch_adzuna(seen):
    app_id  = os.environ.get('ADZUNA_APP_ID', '')
    app_key = os.environ.get('ADZUNA_APP_KEY', '')
    if not app_id or not app_key:
        return []
    searches = [
        {'what': 'Microsoft Sentinel security engineer',    'where': '', 'distance': 0},
        {'what': 'Azure Security Engineer remote',          'where': '', 'distance': 0},
        {'what': 'Defender for Cloud security',             'where': '', 'distance': 0},
        {'what': 'Cloud Security Engineer SIEM remote',     'where': '', 'distance': 0},
        {'what': 'KQL detection engineer security',         'where': '', 'distance': 0},
        {'what': 'Entra ID identity security engineer',     'where': '', 'distance': 0},
        {'what': 'CSPM cloud security posture',             'where': '', 'distance': 0},
        {'what': 'threat hunting SIEM azure',               'where': '', 'distance': 0},
        {'what': 'Microsoft Sentinel security',             'where': 'Phoenix, AZ', 'distance': 50},
        {'what': 'Azure Security Engineer',                 'where': 'Phoenix, AZ', 'distance': 50},
    ]
    results = []
    for s in searches:
        try:
            p = {
                'app_id': app_id, 'app_key': app_key,
                'results_per_page': 8, 'what': s['what'],
                'sort_by': 'date', 'content-type': 'application/json',
            }
            if s['where']:
                p['where'] = s['where']
                p['distance'] = s['distance']
            url = f'https://api.adzuna.com/v1/api/jobs/us/search/1?{urllib.parse.urlencode(p)}'
            data = _http_get(url)
            for job in data.get('results', []):
                jid = 'az-' + str(job.get('id', ''))
                if jid in seen:
                    continue
                seen.add(jid)
                sal_min = job.get('salary_min')
                sal_max = job.get('salary_max')
                sal = ''
                if sal_min and sal_max:
                    sal = f'${int(sal_min/1000)}k–${int(sal_max/1000)}k'
                elif sal_min:
                    sal = f'${int(sal_min/1000)}k+'
                desc = job.get('description', '')
                results.append({
                    'id': jid,
                    'title': job.get('title', ''),
                    'company': job.get('company', {}).get('display_name', ''),
                    'location': job.get('location', {}).get('display_name', ''),
                    'salary': sal,
                    'url': job.get('redirect_url', ''),
                    'created': job.get('created', ''),
                    'source': 'Adzuna',
                    'description': desc[:2000],
                })
        except Exception:
            continue
    return results


def _fetch_remotive(seen):
    results = []
    for q in ['azure sentinel security', 'microsoft sentinel', 'cloud security engineer azure',
              'detection engineer siem', 'identity security azure', 'defender for cloud']:
        try:
            url = f'https://remotive.com/api/remote-jobs?search={urllib.parse.quote(q)}&limit=8'
            data = _http_get(url)
            for job in data.get('jobs', []):
                jid = 'rm-' + str(job.get('id', ''))
                if jid in seen:
                    continue
                seen.add(jid)
                results.append({
                    'id': jid,
                    'title': job.get('title', ''),
                    'company': job.get('company_name', ''),
                    'location': job.get('candidate_required_location', 'Remote'),
                    'salary': job.get('salary', ''),
                    'url': job.get('url', ''),
                    'created': job.get('publication_date', ''),
                    'source': 'Remotive',
                    'description': job.get('description', '')[:2000],
                })
        except Exception:
            continue
    return results


def _fetch_jobicy(seen):
    results = []
    for tag in ['information-security', 'cloud-security', 'cybersecurity', 'devsecops']:
        try:
            url = f'https://jobicy.com/api/v2/remote-jobs?count=15&tag={tag}'
            data = _http_get(url)
            for job in data.get('jobs', []):
                jid = 'jc-' + str(job.get('id', ''))
                if jid in seen:
                    continue
                seen.add(jid)
                sal_min = job.get('annualSalaryMin')
                sal_max = job.get('annualSalaryMax')
                sal = ''
                if sal_min and sal_max:
                    sal = f'${int(sal_min/1000)}k–${int(sal_max/1000)}k'
                elif sal_min:
                    sal = f'${int(sal_min/1000)}k+'
                results.append({
                    'id': jid,
                    'title': job.get('jobTitle', ''),
                    'company': job.get('companyName', ''),
                    'location': job.get('jobGeo', 'Remote'),
                    'salary': sal,
                    'url': job.get('url', ''),
                    'created': job.get('pubDate', ''),
                    'source': 'Jobicy',
                    'description': job.get('jobExcerpt', '')[:2000],
                })
        except Exception:
            continue
    return results


def _fetch_the_muse(seen):
    results = []
    try:
        url = 'https://www.themuse.com/api/public/jobs?category=IT+%26+Security+Engineering&page=0&descending=true'
        data = _http_get(url)
        for item in data.get('results', []):
            jid = 'tm-' + str(item.get('id', ''))
            if jid in seen:
                continue
            seen.add(jid)
            locs = item.get('locations', [])
            loc = locs[0].get('name', '') if locs else ''
            results.append({
                'id': jid,
                'title': item.get('name', ''),
                'company': item.get('company', {}).get('name', ''),
                'location': loc,
                'salary': '',
                'url': item.get('refs', {}).get('landing_page', ''),
                'created': item.get('publication_date', ''),
                'source': 'The Muse',
                'description': '',
            })
    except Exception:
        pass
    return results


def _fetch_arbeitnow(seen):
    results = []
    try:
        url = 'https://www.arbeitnow.com/api/job-board-api?tags[]=information-security&remote=true'
        data = _http_get(url)
        for job in data.get('data', [])[:20]:
            jid = 'an-' + str(job.get('slug', ''))
            if jid in seen:
                continue
            seen.add(jid)
            results.append({
                'id': jid,
                'title': job.get('title', ''),
                'company': job.get('company_name', ''),
                'location': 'Remote' if job.get('remote') else job.get('location', ''),
                'salary': job.get('salary', ''),
                'url': job.get('url', ''),
                'created': job.get('created_at', ''),
                'source': 'Arbeitnow',
                'description': job.get('description', '')[:2000],
            })
    except Exception:
        pass
    return results


def _fetch_usajobs(seen):
    api_key = os.environ.get('USAJOBS_KEY', '')
    email_addr = os.environ.get('USAJOBS_EMAIL', '')
    if not api_key or not email_addr:
        return []
    results = []
    queries = [
        'azure sentinel cloud security',
        'microsoft sentinel SIEM engineer',
        'cloud security engineer azure',
        'information security azure identity',
    ]
    headers = {
        'Host': 'data.usajobs.gov',
        'User-Agent': email_addr,
        'Authorization-Key': api_key,
    }
    for q in queries:
        try:
            params = urllib.parse.urlencode({
                'Keyword': q,
                'ResultsPerPage': 10,
                'RemoteIndicator': 'True',
            })
            url = f'https://data.usajobs.gov/api/search?{params}'
            data = _http_get(url, headers=headers, timeout=10)
            items = data.get('SearchResult', {}).get('SearchResultItems', [])
            for item in items:
                d = item.get('MatchedObjectDescriptor', {})
                jid = 'uj-' + str(d.get('PositionID', ''))
                if jid in seen:
                    continue
                seen.add(jid)
                rem = d.get('PositionRemuneration', [{}])
                sal = ''
                if rem:
                    lo = rem[0].get('MinimumRange', '')
                    hi = rem[0].get('MaximumRange', '')
                    if lo and hi:
                        sal = f'${int(float(lo)/1000)}k–${int(float(hi)/1000)}k'
                results.append({
                    'id': jid,
                    'title': d.get('PositionTitle', ''),
                    'company': d.get('OrganizationName', ''),
                    'location': d.get('PositionLocationDisplay', ''),
                    'salary': sal,
                    'url': d.get('PositionURI', ''),
                    'created': d.get('PublicationStartDate', ''),
                    'source': 'USAJobs',
                    'description': d.get('UserArea', {}).get('Details', {}).get('MajorDuties', [''])[0][:2000],
                })
        except Exception:
            continue
    return results


@app.route('/')
def index():
    return send_from_directory('/app', 'index.html')


@app.route('/docx.js')
def docx_js():
    return send_from_directory('/app', 'docx.js')


@app.route('/api/optimize', methods=['POST'])
def optimize():
    data = request.json or {}
    ats    = data.get('ats', '')
    jd     = data.get('jd', '').strip()
    resume = data.get('resume', '').strip()

    if not ats or not jd or not resume:
        return jsonify({'error': 'ats, jd, and resume are required'}), 400

    tier = TIER_MAP.get(ats, 'modern')
    guide = TIER_GUIDE[tier]

    prompt = f"""You are a professional ATS resume optimizer for cybersecurity roles. Maximize the resume's ATS keyword match score AND make it compelling enough that the HR screener wants to call the candidate.

OUTPUT FORMAT — your response MUST begin with exactly these two lines, then a separator:
COMPANY: <company name from the JD, or Unknown>
ROLE: <exact job title from the JD>
---
<complete optimized resume text here>

TARGET ATS: {ats} ({tier} tier)
{guide}

CANDIDATE RESUME:
{resume}

JOB DESCRIPTION:
{jd}

OPTIMIZATION RULES:
0. IDENTIFY PRIMARY FOCUS FIRST: Read the job title and first three bullets of the JD. Name the primary discipline (e.g. offensive security / vuln mgmt, SIEM/detection engineering, cloud posture, identity/IAM, compliance). Lead the Professional Summary and Core Competencies with that discipline — never bury it.
0b. USE THE KEYWORD POOL: The resume contains a KEYWORD POOL section (marked with --- delimiters). This is a vocabulary reservoir of real skills and exposure the candidate has. When the JD uses a term that maps to something in the pool, incorporate it naturally into the optimized resume — in bullets, skills, or competencies. Never invent experience not in the pool or resume. The pool does not appear in the output — it is optimizer input only.
1. Mirror JD keyword phrases EXACTLY — use the same words, not synonyms
2. Reorder bullets within each role: most JD-relevant achievements first
3. Expand or rewrite the SKILLS section to reflect JD terminology directly
4. Add a CORE COMPETENCIES section if it increases scanner keyword density
5. Keep every factual claim accurate — never fabricate experience, metrics, or certifications
6. Preserve all contact information and dates exactly
7. For legacy ATS: strip all non-ASCII characters, use only hyphen bullets
8. The output must read compellingly to a human — not keyword soup
9. Surface the Offensive Security & Projects section prominently when the JD mentions pentesting, red team, vuln mgmt, AppSec, or EASM
10. Start with the COMPANY:/ROLE:/--- header block, then the complete resume. No other preamble or commentary."""

    try:
        result = subprocess.run(
            [CLAUDE_BIN, '--model', 'claude-opus-5-5', '-p', prompt, '--output-format', 'text'],
            capture_output=True, text=True, timeout=120,
            stdin=subprocess.DEVNULL,
            env={**os.environ, 'HOME': '/root'},
        )
        if result.returncode != 0:
            return jsonify({'error': result.stderr[:500] or 'claude exited non-zero'}), 500

        raw = result.stdout.strip()
        company = ''
        role = ''
        resume_out = raw
        lines = raw.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('COMPANY:'):
                company = line[8:].strip()
            elif line.startswith('ROLE:'):
                role = line[5:].strip()
            elif line.strip() == '---' and i < 6:
                resume_out = '\n'.join(lines[i+1:]).strip()
                break

        return jsonify({'optimized': resume_out, 'company': company, 'role': role})
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'claude timed out after 120s'}), 504
    except FileNotFoundError:
        return jsonify({'error': f'claude binary not found at {CLAUDE_BIN}'}), 503
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/cover-letter', methods=['POST'])
def cover_letter():
    data = request.json or {}
    ats     = data.get('ats', '')
    jd      = data.get('jd', '').strip()
    company = data.get('company', '').strip()
    role    = data.get('role', '').strip()

    if not jd:
        return jsonify({'error': 'jd is required'}), 400

    company_line = f'at {company}' if company else 'for this role'
    role_line    = f'the {role} position' if role else 'this position'

    prompt = f"""Write a professional cover letter for Jamie Loring applying {company_line}.

CANDIDATE BACKGROUND:
Name: Jamie Loring
Location: Glendale, AZ
Phone: 623-297-8499
Email: jamie@jamieloring.com
Background: Senior Azure cloud security engineer, 8+ years. Microsoft Sentinel SIEM, Defender for Cloud, Entra ID, Azure Policy, CSPM. CompTIA SecurityX (CASP+) certified. DoD Public Trust clearance active.
Recent roles: Cloud & Threat Security Engineer at Troon (2026), Azure Security Engineer at Arrivia (2025-2026), Azure SIEM Engineer at OPM (2023-2024), Sentinel Engineer at Microsoft/Insight Global (2021-2023).

JOB DESCRIPTION:
{jd}

COVER LETTER RULES:
1. Three paragraphs, 200-250 words total — tight and readable
2. Opening: express genuine interest in {role_line} and name 1-2 specific things from the JD that match Jamie's background
3. Middle: connect 2-3 concrete achievements from Jamie's experience directly to the JD's key requirements — be specific, not generic
4. Closing: confident, not desperate — note availability and that you'd welcome a conversation
5. Mirror the JD's exact terminology for key skills (same words the ATS will scan)
6. Do NOT use hollow phrases like "I am excited to apply" or "I believe I would be a great fit"
7. Tone: direct, confident, senior-level — not sycophantic
8. Output ONLY the cover letter text, starting with "Dear Hiring Manager," — no subject line, no date, no address block, no commentary"""

    try:
        result = subprocess.run(
            [CLAUDE_BIN, '--model', 'claude-opus-5-5', '-p', prompt, '--output-format', 'text'],
            capture_output=True, text=True, timeout=120,
            stdin=subprocess.DEVNULL,
            env={**os.environ, 'HOME': '/root'},
        )
        if result.returncode != 0:
            return jsonify({'error': result.stderr[:500] or 'claude exited non-zero'}), 500
        return jsonify({'cover_letter': result.stdout.strip()})
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'claude timed out after 120s'}), 504
    except FileNotFoundError:
        return jsonify({'error': f'claude binary not found at {CLAUDE_BIN}'}), 503
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/applications', methods=['GET'])
def get_applications():
    with get_db() as conn:
        rows = conn.execute(
            'SELECT id,company,role,ats,source,timestamp,date_iso,status,notes,jd_text FROM applications ORDER BY timestamp DESC LIMIT 500'
        ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route('/api/applications', methods=['POST'])
def add_application():
    data = request.json or {}
    ts = int(datetime.now(timezone.utc).timestamp() * 1000)
    row_id = str(ts)
    with get_db() as conn:
        conn.execute(
            'INSERT INTO applications (id,company,role,ats,source,timestamp,date_iso,status,notes,jd_text) VALUES (?,?,?,?,?,?,?,?,?,?)',
            (row_id, data.get('company', ''), data.get('role', ''),
             data.get('ats', ''), data.get('source', ''),
             ts, datetime.now(timezone.utc).isoformat(),
             'applied', '', data.get('jd_text', ''))
        )
        conn.commit()
    return jsonify({'id': row_id}), 201


@app.route('/api/applications/<app_id>', methods=['PATCH'])
def update_application(app_id):
    data = request.json or {}
    allowed = {'status', 'notes', 'company', 'role'}
    updates = {k: v for k, v in data.items() if k in allowed}
    if not updates:
        return jsonify({'error': 'nothing to update'}), 400
    set_clause = ', '.join(f'{k}=?' for k in updates)
    with get_db() as conn:
        conn.execute(
            f'UPDATE applications SET {set_clause} WHERE id=?',
            list(updates.values()) + [app_id]
        )
        conn.commit()
    return jsonify({'ok': True})


@app.route('/api/gmail-sync', methods=['POST'])
def gmail_sync():
    gmail_user = os.environ.get('GMAIL_ADDRESS', '')
    gmail_pass = os.environ.get('GMAIL_APP_PASSWORD', '')
    if not gmail_user or not gmail_pass:
        return jsonify({'error': 'GMAIL_ADDRESS and GMAIL_APP_PASSWORD env vars not set. Add an App Password in your Google account settings.'}), 503

    try:
        mail = imaplib.IMAP4_SSL('imap.gmail.com', 993)
        mail.login(gmail_user, gmail_pass)
    except Exception as e:
        return jsonify({'error': f'Gmail login failed: {e}'}), 503

    import datetime as dt
    data = request.get_json(force=True, silent=True) or {}
    days = int(data.get('days', 10))
    since = (dt.datetime.now() - dt.timedelta(days=days)).strftime('%d-%b-%Y')

    jd_keywords = [
        'application', 'position', 'role', 'opportunity',
        'interview', 'candidate', 'recruiter', 'hiring',
        'thank you for applying', 'your application', 'next steps',
    ]

    messages = []
    seen_subjects = set()
    for folder in ['INBOX', '"[Gmail]/All Mail"']:
        try:
            mail.select(folder, readonly=True)
            _, data = mail.search(None, f'(SINCE {since})')
            ids = data[0].split()
            for mid in ids[-75:]:
                try:
                    _, msg_data = mail.fetch(mid, '(RFC822.HEADER)')
                    raw = msg_data[0][1]
                    msg = email.message_from_bytes(raw)
                    subject = decode_mime(msg.get('Subject', ''))
                    sender  = msg.get('From', '')
                    date    = msg.get('Date', '')
                    key = subject.lower().strip()
                    if key in seen_subjects:
                        continue
                    if any(k in subject.lower() for k in jd_keywords):
                        seen_subjects.add(key)
                        messages.append({'subject': subject, 'from': sender, 'date': date})
                except Exception:
                    continue
        except Exception:
            continue

    mail.logout()

    if not messages:
        return jsonify({'updated': [], 'message': 'No job-related emails found in last 45 days'})

    with get_db() as conn:
        apps = [dict(r) for r in conn.execute(
            'SELECT id, company, role, status FROM applications ORDER BY timestamp DESC'
        ).fetchall()]

    if not apps:
        return jsonify({'updated': [], 'message': 'No applications to match against'})

    companies_json = json.dumps([{'id': a['id'], 'company': a['company'], 'role': a['role'], 'current_status': a['status']} for a in apps])
    emails_json = json.dumps(messages[:60])

    prompt = f"""Analyze these job application emails and match each one to an application in the database.

APPLICATIONS:
{companies_json}

EMAILS (last 45 days):
{emails_json}

For each email that clearly relates to a job application status update, output a JSON array:
[{{"id": "<app id>", "status": "<declined|interview|assessment|info_requested|offer>", "note": "<one sentence: what the email said>"}}]

Classification rules:
- declined: rejected, not moving forward, decided to pursue other candidates, regret to inform, position filled
- interview: schedule an interview, phone screen, video call, next steps (with recruiter/hiring manager)
- assessment: take-home assignment, technical test, coding challenge, skills assessment
- info_requested: asking for more information, clarification, portfolio, references
- offer: job offer, offer letter

Matching rules:
- Match company by name similarity: "Acme Corp" matches "acme.com" in sender email, or "Acme" in subject
- Skip emails you cannot confidently match to an application
- Skip emails where the current_status is already more advanced (e.g. don't overwrite "offer" with "declined" unless clearly a rejection)
- Output ONLY the JSON array. Empty array [] if no confident matches."""

    try:
        result = subprocess.run(
            [CLAUDE_BIN, '--model', 'claude-opus-5-5', '-p', prompt, '--output-format', 'text'],
            capture_output=True, text=True, timeout=60,
            stdin=subprocess.DEVNULL,
            env={**os.environ, 'HOME': '/root'},
        )
        if result.returncode != 0:
            return jsonify({'error': 'Claude classification failed: ' + result.stderr[:200]}), 500

        raw = result.stdout.strip()
        match = re.search(r'\[.*\]', raw, re.DOTALL)
        if not match:
            return jsonify({'updated': [], 'message': 'No matches found'})

        updates = json.loads(match.group(0))
        if not updates:
            return jsonify({'updated': [], 'message': 'No confident matches found'})

        updated = []
        with get_db() as conn:
            for u in updates:
                conn.execute(
                    'UPDATE applications SET status=?, notes=? WHERE id=?',
                    (u.get('status', 'applied'), u.get('note', ''), u.get('id'))
                )
                updated.append(u)
            conn.commit()

        return jsonify({'updated': updated})
    except json.JSONDecodeError:
        return jsonify({'error': 'Claude returned unparseable JSON'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/job-search', methods=['GET'])
def job_search():
    import datetime as dt
    cutoff = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=10)).date()

    app_id  = os.environ.get('ADZUNA_APP_ID', '')
    app_key = os.environ.get('ADZUNA_APP_KEY', '')

    results = []
    seen_ids = set()

    if app_id and app_key:
        searches = [
            {'what': 'Microsoft Sentinel security',        'where': 'Phoenix, AZ', 'distance': 50},
            {'what': 'Azure Security Engineer',            'where': 'Phoenix, AZ', 'distance': 50},
            {'what': 'Cloud Security Engineer SIEM remote','where': '',            'distance': 0},
            {'what': 'Azure Security Engineer remote',     'where': '',            'distance': 0},
        ]
        for s in searches:
            try:
                p = {
                    'app_id': app_id, 'app_key': app_key,
                    'results_per_page': 10, 'what': s['what'],
                    'sort_by': 'date', 'content-type': 'application/json',
                }
                if s['where']:
                    p['where'] = s['where']
                    p['distance'] = s['distance']
                params = urllib.parse.urlencode(p)
                url = f'https://api.adzuna.com/v1/api/jobs/us/search/1?{params}'
                req = urllib.request.Request(url, headers={'User-Agent': 'headhunter/1.0'})
                with urllib.request.urlopen(req, timeout=8) as r:
                    data = json.loads(r.read())
                for job in data.get('results', []):
                    jid = 'az-' + str(job.get('id', ''))
                    if jid in seen_ids:
                        continue
                    created = job.get('created', '')
                    try:
                        if dt.date.fromisoformat(created[:10]) < cutoff:
                            continue
                    except Exception:
                        pass
                    seen_ids.add(jid)
                    sal_min = job.get('salary_min')
                    sal_max = job.get('salary_max')
                    sal = ''
                    if sal_min and sal_max:
                        sal = f'${int(sal_min/1000)}k–${int(sal_max/1000)}k'
                    elif sal_min:
                        sal = f'${int(sal_min/1000)}k+'
                    results.append({
                        'id': jid,
                        'title': job.get('title', ''),
                        'company': job.get('company', {}).get('display_name', ''),
                        'location': job.get('location', {}).get('display_name', ''),
                        'salary': sal,
                        'url': job.get('redirect_url', ''),
                        'created': job.get('created', ''),
                        'source': 'Adzuna',
                    })
            except Exception:
                continue

    results.sort(key=lambda x: x.get('created', ''), reverse=True)
    return jsonify({'jobs': results[:15]})


@app.route('/api/resume-score', methods=['POST'])
def resume_score():
    data = request.get_json(force=True, silent=True) or {}
    jd = data.get('jd', '').strip()
    resume = data.get('resume', '').strip()
    if not jd or not resume:
        return jsonify({'score': 0, 'matched': [], 'missing': []})
    return jsonify(compute_score(jd, resume))


@app.route('/api/resume', methods=['GET', 'POST'])
def resume_api():
    if request.method == 'GET':
        with get_db() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key='resume'").fetchone()
        return jsonify({'resume': row['value'] if row else DEFAULT_RESUME})
    data = request.get_json(force=True, silent=True) or {}
    text = data.get('resume', '').strip()
    if not text:
        return jsonify({'error': 'resume text required'}), 400
    with get_db() as conn:
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('resume', ?)", (text,))
        conn.commit()
    return jsonify({'ok': True})


@app.route('/api/discover', methods=['GET'])
def discover():
    with get_db() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key='resume'").fetchone()
        resume_text = row['value'] if row else DEFAULT_RESUME
        hidden = {r['url'] for r in conn.execute('SELECT url FROM hidden_jobs').fetchall()}
        applied_urls = set()

    seen = set()
    fetchers = [
        lambda: _fetch_adzuna(seen),
        lambda: _fetch_remotive(seen),
        lambda: _fetch_jobicy(seen),
        lambda: _fetch_the_muse(seen),
        lambda: _fetch_arbeitnow(seen),
        lambda: _fetch_usajobs(seen),
    ]

    all_jobs = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(f) for f in fetchers]
        for future in concurrent.futures.as_completed(futures, timeout=20):
            try:
                all_jobs.extend(future.result())
            except Exception:
                continue

    # Dedup by URL, filter hidden
    seen_urls = set()
    filtered = []
    for job in all_jobs:
        url = job.get('url', '')
        if not url or url in seen_urls or url in hidden:
            continue
        seen_urls.add(url)
        filtered.append(job)

    # Score each job
    for job in filtered:
        desc = job.get('description', '') or ''
        title = job.get('title', '') or ''
        jd_text = f"{title}\n{desc}"
        if jd_text.strip():
            scored = score_for_discover(jd_text, resume_text)
            job['score'] = scored['score']
            job['missing'] = scored['missing'][:5]
        else:
            job['score'] = 0
            job['missing'] = []

    # Sort by score descending, cap at 60 results
    filtered.sort(key=lambda x: x.get('score', 0), reverse=True)
    filtered = filtered[:60]

    # Strip description from response (too large)
    for job in filtered:
        job.pop('description', None)

    return jsonify({'jobs': filtered, 'total': len(filtered), 'hidden_count': len(hidden)})


@app.route('/api/discover/hide', methods=['POST'])
def hide_job():
    data = request.json or {}
    url = data.get('url', '').strip()
    if not url:
        return jsonify({'error': 'url required'}), 400
    ts = int(datetime.now(timezone.utc).timestamp() * 1000)
    with get_db() as conn:
        conn.execute('INSERT OR REPLACE INTO hidden_jobs (url, hidden_at) VALUES (?, ?)', (url, ts))
        conn.commit()
    return jsonify({'ok': True})


@app.route('/api/discover/queue', methods=['POST'])
def queue_discover():
    data = request.json or {}
    company = data.get('company', '').strip()
    role    = data.get('role', '').strip()
    source  = data.get('source', '').strip()
    url     = data.get('url', '').strip()
    if not company or not role:
        return jsonify({'error': 'company and role required'}), 400
    ts = int(datetime.now(timezone.utc).timestamp() * 1000)
    row_id = str(ts)
    with get_db() as conn:
        conn.execute(
            'INSERT INTO applications (id,company,role,ats,source,timestamp,date_iso,status,notes,jd_text) VALUES (?,?,?,?,?,?,?,?,?,?)',
            (row_id, company, role, '', source,
             ts, datetime.now(timezone.utc).isoformat(),
             'queued', f'Discovered via {source}. URL: {url}', '')
        )
        conn.commit()
    return jsonify({'id': row_id}), 201


@app.route('/api/status', methods=['GET'])
def status():
    try:
        result = subprocess.run(
            [CLAUDE_BIN, '--version'],
            capture_output=True, text=True, timeout=10,
            stdin=subprocess.DEVNULL,
            env={**os.environ, 'HOME': '/root'},
        )
        return jsonify({'claude_ready': result.returncode == 0, 'version': result.stdout.strip()})
    except Exception as e:
        return jsonify({'claude_ready': False, 'error': str(e)})




# ═══════════════════════════════════════════════════════════════
#  LEADS TAB
# ═══════════════════════════════════════════════════════════════

LEADS_PROFILE = (
    "Senior cybersecurity engineer, 8+ years. Core stack: Microsoft Sentinel/KQL, "
    "Defender for Cloud, Entra ID/Azure AD, CSPM, EASM, threat hunting, incident response, "
    "vulnerability management, offensive security (pentesting, ShellShock framework, "
    "HackTheBox top 1%), Python, PowerShell. CompTIA SecurityX (CASP+), DoD Public Trust. "
    "Based in Phoenix AZ. Seeks hands-on technical IC roles."
)

PHOENIX_METRO = {
    'phoenix','tempe','scottsdale','chandler','mesa','gilbert','glendale','peoria',
    'surprise','avondale','goodyear','buckeye','ahwatukee','maricopa','queen creek',
    'apache junction','fountain hills','cave creek','paradise valley','sun city',
    'tolleson','el mirage','youngtown','litchfield park','az','arizona',
}

SKIP_TITLE_RE = re.compile(
    r'\b(coordinator|program manager|project manager|help desk|helpdesk|'
    r'tier[\s\-]?[1i]|intern(?:ship)?|associate consultant|'
    r'remediation (?:program|manager)|grc (?:analyst|manager)|'
    r'compliance (?:analyst|manager)|sales engineer|business development)\b',
    re.IGNORECASE
)

LEAD_SENDERS = [
    'jobalerts-noreply@linkedin.com',
    'jobalert@linkedin.com',
    'jobs-listings@linkedin.com',
    'donotreply@jobalert.indeed.com',
    'alert@indeed.com',
    'alerts@dice.com',
    'noreply@clearancejobs.com',
    'jobs@clearancejobs.com',
    'noreply@builtin.com',
]


def classify_workplace(location):
    loc = location.lower()
    has_remote  = 'remote' in loc or 'anywhere' in loc
    has_phoenix = any(c in loc for c in PHOENIX_METRO)
    if has_remote and not has_phoenix:
        other_st = re.search(r'\b([A-Z]{2})\b', location)
        if other_st and other_st.group(1) not in ('AZ', 'US'):
            return 'other'
        return 'remote'
    if has_phoenix and has_remote:
        return 'phoenix_remote'
    if has_phoenix:
        return 'onsite_hybrid'
    if has_remote:
        return 'remote'
    return 'other'


def normalize_company(name):
    return re.sub(r'\s+', ' ', name.lower().strip())


def normalize_title(title):
    t = title.lower()
    t = re.sub(r'\b(senior|sr\.?|jr\.?|lead|staff|principal|associate|junior)\b', '', t)
    t = re.sub(r'[^a-z0-9 ]', '', t)
    return re.sub(r'\s+', ' ', t).strip()


def get_email_body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            cd = str(part.get('Content-Disposition', ''))
            if ct == 'text/plain' and 'attachment' not in cd:
                try:
                    return part.get_payload(decode=True).decode(
                        part.get_content_charset() or 'utf-8', errors='replace')
                except Exception:
                    pass
        for part in msg.walk():
            if part.get_content_type() == 'text/html':
                try:
                    raw = part.get_payload(decode=True).decode(
                        part.get_content_charset() or 'utf-8', errors='replace')
                    return re.sub(r'<[^>]+>', ' ', raw)
                except Exception:
                    pass
    else:
        try:
            return msg.get_payload(decode=True).decode(
                msg.get_content_charset() or 'utf-8', errors='replace')
        except Exception:
            pass
    return ''


def parse_linkedin_alert(body):
    jobs = []
    blocks = re.split(r'-{10,}', body)
    for block in blocks:
        lines = [l.strip() for l in block.splitlines() if l.strip()]
        url_idx = None
        url = None
        for i, line in enumerate(lines):
            m = re.search(r'View job:\s*(https://\S+)', line, re.IGNORECASE)
            if m:
                url_idx = i
                url = m.group(1)
                break
        if url_idx is None or url_idx < 2:
            continue
        job_id_m = re.search(r'/jobs/view/(\d+)', url)
        if not job_id_m:
            continue
        job_id = job_id_m.group(1)
        preceding = [l for l in lines[:url_idx]
                     if l and not l.startswith('http') and len(l) > 2]
        if len(preceding) < 2:
            continue
        location = preceding[-1] if len(preceding) >= 3 else ''
        company  = preceding[-2] if len(preceding) >= 3 else preceding[-1]
        title    = preceding[-3] if len(preceding) >= 3 else preceding[-2]
        salary = ''
        sal_m = re.search(
            r'\$[\d,]+(?:\s*[-–]\s*\$[\d,]+)?(?:\s*/\s*(?:yr|year|hr|hour|mo|month))?',
            block, re.IGNORECASE)
        if sal_m:
            salary = sal_m.group(0).strip()
        jobs.append({
            'id': f'li-{job_id}',
            'title': title,
            'company': company,
            'location': location,
            'url': f'https://www.linkedin.com/jobs/view/{job_id}',
            'source': 'LinkedIn',
            'salary': salary,
            'posted': '',
        })
    return jobs


def parse_generic_alert(body, source):
    jobs = []
    url_pattern = re.compile(
        r'https?://(?:www\.)?(?:indeed\.com/rc/clk|dice\.com/job-detail|'
        r'clearancejobs\.com/jobs|builtin\.com/job)\S+',
        re.IGNORECASE
    )
    lines = body.splitlines()
    seen_urls = set()
    for i, line in enumerate(lines):
        line = line.strip()
        url_m = url_pattern.search(line)
        if not url_m:
            context = '\n'.join(lines[max(0, i-2):i+3])
            url_m = url_pattern.search(context)
        if not url_m:
            continue
        url = url_m.group(0).rstrip('.,)')
        if url in seen_urls:
            continue
        seen_urls.add(url)
        surrounding = [l.strip() for l in lines[max(0, i-4):i+4]
                       if l.strip() and 'http' not in l]
        if len(surrounding) < 2:
            continue
        title    = surrounding[0]
        company  = surrounding[1] if len(surrounding) > 1 else ''
        location = surrounding[2] if len(surrounding) > 2 else ''
        job_id   = re.sub(r'[^a-z0-9]', '', url[-20:].lower())
        src_pfx  = source[:2].lower()
        jobs.append({
            'id': f'{src_pfx}-{job_id}',
            'title': title,
            'company': company,
            'location': location,
            'url': url,
            'source': source,
            'salary': '',
            'posted': '',
        })
    return jobs


def filter_lead(job, blacklist, existing_ids, applied_companies):
    title   = job.get('title', '')
    company = job.get('company', '')
    loc     = job.get('location', '')
    lid     = job.get('id', '')

    if normalize_company(company) in blacklist:
        return False, 'blacklisted company'
    if lid in existing_ids:
        return False, 'duplicate id'
    if SKIP_TITLE_RE.search(title):
        return False, f'non-hands-on title'
    workplace = classify_workplace(loc)
    if workplace == 'other':
        return False, f'location out of area'
    job['workplace'] = workplace
    norm_co = normalize_company(company)
    norm_ti = normalize_title(title)
    if norm_co in applied_companies:
        if normalize_title(applied_companies[norm_co]) == norm_ti:
            return False, 'already applied to same role'
        job['_prior_note'] = f"Applied to {company} before ({applied_companies[norm_co]})"
    return True, ''


def score_leads_batch(jobs):
    if not jobs:
        return jobs
    jobs_for_prompt = [
        {'id': j['id'], 'title': j['title'], 'company': j['company'],
         'location': j['location'], 'workplace': j.get('workplace', ''),
         'salary': j.get('salary', '')}
        for j in jobs
    ]
    prompt = (
        "Score these job leads for a cybersecurity candidate. Return ONLY a JSON array.\n\n"
        f"CANDIDATE: {LEADS_PROFILE}\n\n"
        "SCORING (weight each): hands-on technical IC work (high), "
        "Azure/Sentinel/KQL/Defender/Entra/detection/IR/vuln mgmt/offensive security match (high), "
        "seniority near senior/lead/principal IC (high; analyst=too junior; director=too senior), "
        "Phoenix on-site or hybrid preferred, remote fine; pay $120k-$180k target.\n\n"
        'OUTPUT: JSON array — [{"id":"...","score":<0-100>,"reason":"<1-2 sentences with caveats>"}]\n\n'
        "JOBS:\n" + json.dumps(jobs_for_prompt, indent=2) +
        "\n\nOutput ONLY the JSON array."
    )
    try:
        result = subprocess.run(
            [CLAUDE_BIN, '--model', 'claude-opus-5-5', '-p', prompt, '--output-format', 'text'],
            capture_output=True, text=True, timeout=120,
            stdin=subprocess.DEVNULL,
            env={**os.environ, 'HOME': '/root'},
        )
        if result.returncode != 0:
            return jobs
        arr_m = re.search(r'\[.*\]', result.stdout.strip(), re.DOTALL)
        if not arr_m:
            return jobs
        scores = {s['id']: s for s in json.loads(arr_m.group(0)) if 'id' in s}
        for j in jobs:
            if j['id'] in scores:
                j['score']  = int(scores[j['id']].get('score', 0))
                reason = scores[j['id']].get('reason', '')
                if j.get('_prior_note'):
                    reason = j['_prior_note'] + ' — ' + reason
                j['reason'] = reason
    except Exception:
        pass
    return jobs


@app.route('/api/leads', methods=['GET'])
def get_leads():
    status    = request.args.get('status', 'new')
    workplace = request.args.get('workplace', '')
    with get_db() as conn:
        q      = 'SELECT * FROM leads WHERE status=?'
        params = [status]
        if workplace:
            q += ' AND workplace=?'
            params.append(workplace)
        q += ' ORDER BY score DESC, found_at DESC'
        rows = [dict(r) for r in conn.execute(q, params).fetchall()]
        counts = {}
        for st in ('new', 'later', 'applied', 'skip'):
            counts[st] = conn.execute(
                'SELECT COUNT(*) FROM leads WHERE status=?', (st,)).fetchone()[0]
        last_run = conn.execute(
            'SELECT run_at, added, filtered FROM lead_runs ORDER BY id DESC LIMIT 1').fetchone()
    return jsonify({'leads': rows, 'counts': counts,
                    'last_run': dict(last_run) if last_run else None})


@app.route('/api/leads/refresh', methods=['POST'])
def refresh_leads():
    import datetime as dt
    gmail_user = os.environ.get('GMAIL_ADDRESS', '')
    gmail_pass = os.environ.get('GMAIL_APP_PASSWORD', '')
    if not gmail_user or not gmail_pass:
        return jsonify({'error': 'GMAIL_ADDRESS and GMAIL_APP_PASSWORD not set'}), 503
    try:
        mail = imaplib.IMAP4_SSL('imap.gmail.com', 993)
        mail.login(gmail_user, gmail_pass)
    except Exception as e:
        return jsonify({'error': f'Gmail login failed: {e}'}), 503

    since = (dt.datetime.now() - dt.timedelta(days=3)).strftime('%d-%b-%Y')
    raw_jobs, errors = [], []

    with get_db() as conn:
        processed = {r[0] for r in conn.execute(
            'SELECT message_id FROM processed_email_ids').fetchall()}

    def _search(folder, criteria):
        try:
            mail.select(folder, readonly=True)
            _, data = mail.search(None, criteria)
            return data[0].split() if data[0] else []
        except Exception:
            return []

    all_mid = set()
    for crit in [f'(X-GM-LABELS "Job Leads" SINCE {since})',
                 f'(LABEL "Job Leads" SINCE {since})']:
        ids = _search('"[Gmail]/All Mail"', crit) or _search('INBOX', crit)
        if ids:
            all_mid.update(ids)
            break
    for sender in LEAD_SENDERS:
        ids = (_search('"[Gmail]/All Mail"', f'(FROM "{sender}" SINCE {since})')
               or _search('INBOX', f'(FROM "{sender}" SINCE {since})'))
        all_mid.update(ids)

    # Re-select All Mail so sequence numbers from All Mail search are valid
    try:
        mail.select('"[Gmail]/All Mail"', readonly=True)
    except Exception:
        try:
            mail.select('INBOX', readonly=True)
        except Exception:
            pass
    for mid in all_mid:
        try:
            _, msg_data = mail.fetch(mid, '(RFC822)')
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)
            msg_id = msg.get('Message-ID', str(mid))
            if msg_id in processed:
                continue
            sender_addr = msg.get('From', '').lower()
            body = get_email_body(msg)
            if not body:
                continue
            if 'linkedin' in sender_addr:
                jobs = parse_linkedin_alert(body)
            elif 'indeed' in sender_addr:
                jobs = parse_generic_alert(body, 'Indeed')
            elif 'dice' in sender_addr:
                jobs = parse_generic_alert(body, 'Dice')
            elif 'clearancejobs' in sender_addr:
                jobs = parse_generic_alert(body, 'ClearanceJobs')
            elif 'builtin' in sender_addr:
                jobs = parse_generic_alert(body, 'BuiltIn')
            else:
                jobs = parse_generic_alert(body, 'Email')
            for j in jobs:
                j['email_message_id'] = msg_id
            raw_jobs.extend(jobs)
            processed.add(msg_id)
        except Exception as ex:
            errors.append(str(ex))

    mail.logout()

    with get_db() as conn:
        blacklist = {r[0] for r in conn.execute(
            'SELECT company FROM lead_blacklist').fetchall()}
        existing_ids = {r[0] for r in conn.execute('SELECT id FROM leads').fetchall()}
        apps = conn.execute('SELECT company, role FROM applications').fetchall()
        applied_companies = {normalize_company(r[0]): r[1] for r in apps}

    kept, filtered_count = [], 0
    for job in raw_jobs:
        keep, _ = filter_lead(job, blacklist, existing_ids, applied_companies)
        if keep:
            kept.append(job)
            existing_ids.add(job['id'])
        else:
            filtered_count += 1

    kept = score_leads_batch(kept)

    now_iso = dt.datetime.now(dt.timezone.utc).isoformat()
    with get_db() as conn:
        for j in kept:
            conn.execute(
                'INSERT OR IGNORE INTO leads '
                '(id,title,company,location,workplace,source,url,posted,'
                'found_at,score,reason,salary,status,email_message_id) '
                'VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                (j['id'], j.get('title',''), j.get('company',''),
                 j.get('location',''), j.get('workplace','remote'),
                 j.get('source',''), j.get('url',''), j.get('posted',''),
                 now_iso, j.get('score',0), j.get('reason',''),
                 j.get('salary',''), 'new', j.get('email_message_id',''))
            )
        for mid in processed:
            conn.execute(
                'INSERT OR IGNORE INTO processed_email_ids '
                '(message_id, processed_at) VALUES (?,?)',
                (mid, now_iso))
        conn.execute(
            'INSERT INTO lead_runs (run_at, added, filtered, errors) VALUES (?,?,?,?)',
            (now_iso, len(kept), filtered_count, len(errors)))
        conn.commit()

    return jsonify({'added': len(kept), 'filtered': filtered_count, 'errors': errors})


@app.route('/api/leads/<lead_id>/status', methods=['POST'])
def set_lead_status(lead_id):
    import datetime as dt
    data   = request.get_json(force=True, silent=True) or {}
    status = data.get('status', '')
    if status not in ('new', 'later', 'applied', 'skip'):
        return jsonify({'error': 'invalid status'}), 400
    now_iso = dt.datetime.now(dt.timezone.utc).isoformat()
    with get_db() as conn:
        conn.execute('UPDATE leads SET status=?, status_changed_at=? WHERE id=?',
                     (status, now_iso, lead_id))
        if status == 'applied':
            lead = conn.execute('SELECT * FROM leads WHERE id=?',
                                (lead_id,)).fetchone()
            if lead:
                lead = dict(lead)
                app_id = str(int(dt.datetime.now().timestamp() * 1000))
                conn.execute(
                    'INSERT OR IGNORE INTO applications '
                    '(id,company,role,ats,source,timestamp,date_iso,status,notes,jd_text) '
                    'VALUES (?,?,?,?,?,?,?,?,?,?)',
                    (app_id, lead['company'], lead['title'], '',
                     lead['source'],
                     int(dt.datetime.now().timestamp() * 1000),
                     dt.datetime.now().date().isoformat(),
                     'applied', '', lead.get('url', ''))
                )
        conn.commit()
    return jsonify({'ok': True})


@app.route('/api/leads/blacklist', methods=['GET'])
def get_blacklist():
    with get_db() as conn:
        rows = [r[0] for r in conn.execute(
            'SELECT company FROM lead_blacklist ORDER BY company').fetchall()]
    return jsonify({'blacklist': rows})


@app.route('/api/leads/blacklist', methods=['POST'])
def add_blacklist():
    data = request.get_json(force=True, silent=True) or {}
    company = normalize_company(data.get('company', ''))
    if not company:
        return jsonify({'error': 'company required'}), 400
    with get_db() as conn:
        conn.execute('INSERT OR IGNORE INTO lead_blacklist (company) VALUES (?)', (company,))
        conn.commit()
    return jsonify({'ok': True})


@app.route('/api/leads/blacklist/<path:company>', methods=['DELETE'])
def remove_blacklist(company):
    with get_db() as conn:
        conn.execute('DELETE FROM lead_blacklist WHERE company=?',
                     (normalize_company(company),))
        conn.commit()
    return jsonify({'ok': True})

if __name__ == '__main__':
    os.makedirs('/data', exist_ok=True)
    init_db()
    app.run(host='0.0.0.0', port=5005, debug=False)
