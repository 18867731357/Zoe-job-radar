# Zoey Job Radar — Auto Update

This repository can automatically rebuild and deploy Zoey's Job Radar to GitHub Pages every day at 08:30 China Standard Time.

## Files
- `update_jobs.py` — searches, filters, scores and generates the website
- `profile.json` — Zoey's profile and matching priorities
- `requirements.txt` — Python dependencies
- `.github/workflows/daily-job-radar.yml` — daily GitHub Actions job
- `site/` — generated static website

## One-time setup

### 1. Upload all files to your GitHub repository
Keep the folder structure unchanged.

### 2. Create a Serper API key
Go to https://serper.dev/ and create an API key.

### 3. Add the key to GitHub
Repository → Settings → Secrets and variables → Actions → New repository secret

Name:
`SERPER_API_KEY`

Value:
your Serper API key

### 4. Enable GitHub Pages from Actions
Repository → Settings → Pages → Build and deployment → Source → GitHub Actions

### 5. Test it
Repository → Actions → Daily Zoey Job Radar → Run workflow

After a successful run, GitHub Pages will deploy the newly generated site.

## Daily schedule
`30 0 * * *` means 00:30 UTC, which is 08:30 China Standard Time.

## Notes
Search results are automatically filtered and scored. Job status changes quickly, so the website always links back to the original source for final verification.
