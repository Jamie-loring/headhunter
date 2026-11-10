# Headhunter

Personal job-hunt dashboard — lead tracking, ATS auto-apply, Gmail sync, cover letter generation, and scoring.

Runs as a Docker container on the media server (`jobhunt` container, port 5005). Accessible at `hunt.lan`.

---

## Architecture

```
hunt.lan (Flask + SQLite)         claude-box (host networking)
   |                                    |
   |-- /api/leads/<id>/apply/greenhouse --> http://172.18.0.1:2346/apply
                                           |
                                           apply_agent.js (PM2, port 2346)
                                           |
                                           node playwright/greenhouse.js <config.json>
                                           |
                                           Chromium (headless) --> Greenhouse ATS
```

### Services

| Component | Location | Purpose |
|---|---|---|
| Flask app | `/opt/appdata/jobhunt/app.py` | REST API + web UI, served in Docker |
| SQLite DB | `/opt/appdata/jobhunt/data/jobs.db` | Leads, applications, settings |
| apply_agent.js | `/opt/jobhunt/playwright/apply_agent.js` | HTTP bridge; spawns Playwright scripts |
| greenhouse.js | `/opt/jobhunt/playwright/greenhouse.js` | Fills + submits Greenhouse ATS forms |
| PM2 | claude-box | Manages apply_agent as a persistent service |

### Docker networking

`jobhunt` container is on the `arr_default` bridge network (gateway `172.18.0.1`).  
`claude-box` uses host networking — apply_agent binds `0.0.0.0:2346` so the bridge gateway can reach it.

---

## Greenhouse auto-apply

### How it works

1. Add a lead with a Greenhouse job URL (e.g. `https://job-boards.greenhouse.io/3cloud/jobs/8582239002`).
2. `POST /api/leads/<lead_id>/apply/greenhouse` with custom questions in the body.
3. Flask extracts the company slug and token from the URL, reads applicant info from the settings table, and POSTs to `apply_agent` on port 2346.
4. `apply_agent` writes the config to a temp file and runs `greenhouse.js` via `node`.
5. `greenhouse.js` launches Chromium (headless), fills the form, uploads the resume, selects dropdown answers, and submits.
6. On success, the lead status is set to `applied` and an application record is inserted.

### Calling the endpoint

```bash
curl -s -X POST http://hunt.lan:5005/api/leads/<lead_id>/apply/greenhouse \
  -H 'Content-Type: application/json' \
  -d '{
    "for": "company-slug",
    "token": "1234567890",
    "questions": [
      {"label": "LinkedIn Profile", "value": "https://linkedin.com/in/you", "type": "text"},
      {"label": "require sponsorship", "value": "No", "type": "dropdown"},
      {"label": "comfortable receiving text messages", "value": "Yes", "type": "dropdown"}
    ],
    "eeo": {"gender": "Male", "hispanic": false, "race": "White", "veteran": "I am not a protected veteran"}
  }'
```

`for` and `token` override URL detection when provided directly.

### greenhouse.js question types

| `type` | Selector used |
|---|---|
| `text` | `#<fieldId>` via label `for` attribute |
| `dropdown` | React Select (`.select__control:has(#react-select-<fieldId>-placeholder)`) or GH button flyout |

**React Select quirk:** Greenhouse uses two React Select patterns. `waitForSelector` times out when hidden `select__menu` elements remain from earlier dropdowns (e.g. the country combobox). The fix is waiting for a visible `select__option` element matching the target text rather than the menu container.

**EEO section:** Fields that don't exist on a given form fail fast with "label not found" (no 30-second timeout). Some forms skip EEO entirely.

### Config file format

See `playwright/greenhouse_sample.json` for a template.  
The `screenshot_before_submit` key (optional) saves a full-page PNG before clicking Submit — useful for debugging.

### Running manually

```bash
# On claude-box
cd /opt/jobhunt/playwright
node greenhouse.js /tmp/my_config.json
```

---

## apply_agent.js

Lightweight HTTP server (port 2346) managed by PM2.

```bash
pm2 status apply-agent          # check status
pm2 restart apply-agent         # restart (required after code changes)
pm2 logs apply-agent --lines 50 # tail logs
```

**PM2 environment:** Requires `HOME=/root` and `ldconfig` to have run so Chromium finds its shared libraries. If Chromium fails with `libnspr4.so` errors, run `ldconfig` then `pm2 restart apply-agent`.

Endpoints:
- `GET /health` — `{"ok": true}`
- `POST /apply` — body: `{ats, for, token, resume_path, applicant, questions, eeo}` — runs the matching `playwright/<ats>.js` script

Script timeout: 180 seconds (`timeout: 180000` in `execFile`).

---

## Settings table

Applicant defaults live in the `settings` table (SQLite):

| key | description |
|---|---|
| `first_name` | Applicant first name |
| `last_name` | Applicant last name |
| `email` | Contact email |
| `phone` | 10-digit phone |
| `city` | City, ST |
| `linkedin` | LinkedIn profile URL |
| `resume_path` | Absolute path to resume file accessible from claude-box |
| `resume` | Full resume text (used for LLM-based resume rewriting and cover letters) |

---

## Flask app

Key routes:

| Method | Route | Purpose |
|---|---|---|
| GET | `/api/leads` | List all leads |
| POST | `/api/leads` | Add a lead |
| POST | `/api/leads/<id>/apply/greenhouse` | Trigger Greenhouse auto-apply |
| GET | `/api/applications` | List all submitted applications |
| POST | `/api/cover-letter` | Generate cover letter via Claude API |
| POST | `/api/gmail-sync` | Sync job alert emails from Gmail |

Env vars (`.env` file, excluded from git):

```
ANTHROPIC_API_KEY=...
GMAIL_ADDRESS=...
GMAIL_APP_PASSWORD=...
```

---

## Setup

### On the media server (claude-box)

```bash
cd /opt/jobhunt/playwright
npm install
npx playwright install chromium
pm2 start apply_agent.js --name apply-agent --env HOME=/root
pm2 save
```

### Docker (jobhunt container)

```bash
cd /opt/appdata/jobhunt
docker compose -f /opt/arr/docker-compose.yml up -d jobhunt
```

The container bind-mounts `/opt/appdata/jobhunt` to `/app` and `/opt/appdata/jobhunt/data` to `/data`.

---

## search.py

Utility that checks Gmail job alert emails for location classification. Useful for tuning the Phoenix-metro / remote / other workplace classifier. Reads Gmail credentials from the Docker container environment (`/proc/1/environ`).

```bash
docker exec jobhunt python3 /app/search.py
```
