# LeetCode Student Monitor

Monitors your students' LeetCode accounts daily and sends a Gmail warning if they haven't solved any new problems in 3+ days.

---

## Project Structure

```
leetcode-monitor/
├── monitor.py          # main script
├── requirements.txt
├── render.yaml         # Render cron job config
├── uname.txt           # student list (you edit this)
└── data/
    └── progress.json   # auto-created, persists between runs
```

---

## uname.txt Format

One student per line: `leetcode_username,email`

```
alice,alice@gmail.com
bob,bob@university.edu
charlie,charlie@outlook.com
```

Lines starting with `#` are ignored.

---

## Gmail Setup (App Password)

You must use a **Gmail App Password** (not your regular Gmail password):

1. Go to your Google Account → **Security**
2. Enable **2-Step Verification** (required)
3. Search for **"App Passwords"** → generate one for "Mail"
4. Copy the 16-character password — this is your `GMAIL_PASSWORD`

---

## Run Locally (for testing)

```bash
pip install -r requirements.txt

export GMAIL_USER="you@gmail.com"
export GMAIL_PASSWORD="xxxx xxxx xxxx xxxx"   # App Password
export WARN_DAYS=3

python monitor.py
```

---

## Deploy to Render (Cron Job)

1. Push this folder to a **GitHub repo**
2. Go to [render.com](https://render.com) → **New → Cron Job**
3. Connect your GitHub repo
4. Render auto-detects `render.yaml` — just confirm settings
5. In **Environment Variables**, set:
   - `GMAIL_USER` → your Gmail address
   - `GMAIL_PASSWORD` → your App Password
6. Add a **Disk** (under the cron job settings):
   - Mount path: `/opt/render/project/src/data`
   - Size: 1 GB (free tier works)
7. Deploy! The job runs every day at 09:00 UTC

> **Why a Disk?** Render cron jobs are stateless. The disk persists `data/progress.json` between daily runs so the script remembers previous solve counts.

---

## How It Works

| Step | What happens |
|------|-------------|
| 1 | Reads `uname.txt` for all students |
| 2 | Queries LeetCode's GraphQL API for each student's total solved count |
| 3 | Compares with the saved count in `data/progress.json` |
| 4 | If count **changed** → updates the record, resets warning flag |
| 5 | If count **unchanged for ≥ WARN_DAYS** → sends one warning email |
| 6 | Warning is only sent once per inactivity streak (no spam) |

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GMAIL_USER` | ✅ | — | Your Gmail address |
| `GMAIL_PASSWORD` | ✅ | — | Gmail App Password |
| `SENDER_NAME` | ❌ | `LeetCode Monitor` | Name shown in emails |
| `WARN_DAYS` | ❌ | `3` | Days of inactivity before warning |
| `UNAME_FILE` | ❌ | `uname.txt` | Path to student list |
| `DB_FILE` | ❌ | `data/progress.json` | Path to progress store |
