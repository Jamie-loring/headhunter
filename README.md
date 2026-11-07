# Headhunter

Claude-powered job search and application platform for active job seekers.

## What it does

- **Multi-source job aggregation** -- pulls from 7+ sources on a 3-hour cron: LinkedIn, Indeed, Glassdoor, ZipRecruiter (via JobSpy), Remotive, Remote OK, We Work Remotely, Dice, Adzuna, and USAJOBS. Deduplicates, filters by relevance, and surfaces only roles that match your target.
- **ATS-aware resume optimizer** -- rewrites your resume against a job description using Claude, with explicit guidance per ATS tier (Greenhouse/Lever, Workday, legacy systems, easy-apply algorithmic scoring, direct contact). Same background, different emphasis per role.
- **Cover letter generator** -- produces tight 3-paragraph letters from your resume + JD. Strips hollow filler language, mirrors ATS keywords, matches tone to tier.
- **Application tracker** -- log and track every application with status, notes, and history.
- **Gmail sync** -- detects recruiter outreach and application confirmations from your inbox automatically.

## Stack

- **Backend**: Python / Flask
- **Frontend**: Single-file HTML/JS/CSS -- no build step
- **AI**: Claude via `claude` CLI
- **Job search**: JobSpy, Remotive, Remote OK, We Work Remotely, Dice, Adzuna, USAJOBS
- **Storage**: SQLite (`/data/jobs.db`)
- **Deploy**: Docker

## Quick start

```bash
cp .env.example .env
# Edit .env with your values
docker build -t headhunter .
docker run -d -p 5005:5005 -v $(pwd)/data:/data --env-file .env headhunter
```

Open http://localhost:5005. Go to **Settings**, paste in your resume as plain text, and configure your target role filters.

The job search agent (`search.py`) runs on a 3-hour schedule automatically, or trigger it manually from the UI.

## Configuration

| Variable | Required | Description |
|---|---|---|
| `GMAIL_ADDRESS` | For Gmail sync | Your Gmail address |
| `GMAIL_APP_PASSWORD` | For Gmail sync | [Google App Password](https://support.google.com/accounts/answer/185833) |
| `ADZUNA_APP_ID` / `ADZUNA_APP_KEY` | Optional | [Adzuna API](https://developer.adzuna.com/) -- adds local job search |
| `USAJOBS_API_KEY` | Optional | [USAJOBS API](https://developer.usajobs.gov/APIRequest/Index) -- adds federal jobs |
| `USAJOBS_USER_AGENT` | Optional | User-Agent for USAJOBS requests (defaults to `GMAIL_ADDRESS`) |

Claude must be installed and authenticated: `claude --version`

## Notes

- No LinkedIn API key required -- job scraping uses [JobSpy](https://github.com/speedyapply/JobSpy)
- SQLite database persists in `/data/` -- mount a volume to keep it across restarts
- Claude binary defaults to `/usr/local/bin/claude` -- override with `CLAUDE_BIN` env var if needed
- The keyword pool in Settings helps the optimizer surface accurate skills from your background without inventing experience
