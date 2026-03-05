# import os
# import json
# import smtplib
# import requests
# import logging
# from datetime import datetime, timedelta
# from email.mime.text import MIMEText
# from email.mime.multipart import MIMEMultipart

# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s [%(levelname)s] %(message)s"
# )
# log = logging.getLogger(__name__)

# # ── Config from environment variables ──────────────────────────────────────────
# GMAIL_USER     = os.environ["GMAIL_USER"]       # your Gmail address
# GMAIL_PASSWORD = os.environ["GMAIL_PASSWORD"]   # Gmail App Password (not login pw)
# SENDER_NAME    = os.environ.get("SENDER_NAME", "LeetCode Monitor")
# WARN_DAYS      = int(os.environ.get("WARN_DAYS", "3"))  # days of inactivity → warn

# UNAME_FILE  = os.environ.get("UNAME_FILE", "uname.txt")
# DB_FILE     = os.environ.get("DB_FILE", "data/progress.json")

# LEETCODE_GQL = "https://leetcode.com/graphql"
# SOLVED_QUERY = """
# query userStats($username: String!) {
#   matchedUser(username: $username) {
#     submitStatsGlobal {
#       acSubmissionNum {
#         difficulty
#         count
#       }
#     }
#   }
# }
# """

# # ── Helpers ────────────────────────────────────────────────────────────────────

# def load_students(path: str) -> list[dict]:
#     """Parse uname.txt → list of {username, email}"""
#     students = []
#     with open(path) as f:
#         for raw in f:
#             line = raw.strip()
#             if not line or line.startswith("#"):
#                 continue
#             parts = [p.strip() for p in line.split(",")]
#             if len(parts) < 2:
#                 log.warning("Skipping malformed line: %s", raw.rstrip())
#                 continue
#             students.append({"username": parts[0], "email": parts[1]})
#     return students


# def load_db(path: str) -> dict:
#     os.makedirs(os.path.dirname(path), exist_ok=True)
#     if os.path.exists(path):
#         with open(path) as f:
#             return json.load(f)
#     return {}


# def save_db(path: str, db: dict):
#     os.makedirs(os.path.dirname(path), exist_ok=True)
#     with open(path, "w") as f:
#         json.dump(db, f, indent=2)


# def fetch_solved_count(username: str) -> int | None:
#     """Return total accepted submissions for a LeetCode user, or None on error."""
#     try:
#         resp = requests.post(
#             LEETCODE_GQL,
#             json={"query": SOLVED_QUERY, "variables": {"username": username}},
#             headers={"Content-Type": "application/json", "Referer": "https://leetcode.com"},
#             timeout=15,
#         )
#         resp.raise_for_status()
#         data = resp.json()
#         user = data.get("data", {}).get("matchedUser")
#         if user is None:
#             log.warning("User not found on LeetCode: %s", username)
#             return None
#         stats = user["submitStatsGlobal"]["acSubmissionNum"]
#         # sum all difficulties (Easy + Medium + Hard + All — pick 'All' entry)
#         for entry in stats:
#             if entry["difficulty"] == "All":
#                 return entry["count"]
#         # fallback: sum Easy+Medium+Hard
#         return sum(e["count"] for e in stats if e["difficulty"] != "All")
#     except Exception as exc:
#         log.error("Failed to fetch stats for %s: %s", username, exc)
#         return None


# def send_warning_email(to_email: str, username: str, days: int, count: int):
#     subject = f"⚠️ LeetCode Inactivity Alert – {username}"
#     body = f"""\
# Hi {username},

# This is a friendly reminder from your instructor.

# Your LeetCode account has shown no new solved problems in the past {days} day(s).

#   • Current solved count : {count}
#   • Last activity check  : {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

# Consistent practice is key to improvement. Please try to solve at least one problem today!

# If you believe this message was sent in error, feel free to reply to this email.

# Good luck and keep coding! 💪

# — {SENDER_NAME}
# """
#     msg = MIMEMultipart("alternative")
#     msg["Subject"] = subject
#     msg["From"]    = f"{SENDER_NAME} <{GMAIL_USER}>"
#     msg["To"]      = to_email
#     msg.attach(MIMEText(body, "plain"))

#     with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
#         server.login(GMAIL_USER, GMAIL_PASSWORD)
#         server.sendmail(GMAIL_USER, to_email, msg.as_string())
#     log.info("Warning email sent → %s (%s)", username, to_email)


# # ── Main logic ─────────────────────────────────────────────────────────────────

# def run():
#     students = load_students(UNAME_FILE)
#     log.info("Loaded %d student(s) from %s", len(students), UNAME_FILE)

#     db = load_db(DB_FILE)
#     now = datetime.utcnow()
#     now_str = now.isoformat()

#     for student in students:
#         uname = student["username"]
#         email = student["email"]

#         current_count = fetch_solved_count(uname)
#         if current_count is None:
#             continue  # skip – network/username error, don't penalise student

#         record = db.get(uname, {})
#         last_count     = record.get("count", -1)
#         last_change_at = record.get("last_change_at", now_str)
#         warned_at      = record.get("warned_at")

#         # Detect progress
#         if current_count != last_count:
#             log.info("%s: count changed %d → %d", uname, last_count, current_count)
#             db[uname] = {
#                 "count": current_count,
#                 "last_change_at": now_str,
#                 "warned_at": None,          # reset warning flag on progress
#                 "email": email,
#             }
#             save_db(DB_FILE, db)
#             continue

#         # No change – check how long
#         last_change_dt = datetime.fromisoformat(last_change_at)
#         inactive_days  = (now - last_change_dt).days

#         log.info(
#             "%s: no change (count=%d, inactive %d day(s))",
#             uname, current_count, inactive_days
#         )

#         if inactive_days >= WARN_DAYS:
#             # Don't spam: only send one warning per inactivity streak
#             already_warned = warned_at is not None
#             if not already_warned:
#                 try:
#                     send_warning_email(email, uname, inactive_days, current_count)
#                     db[uname] = {**record, "warned_at": now_str, "email": email}
#                     save_db(DB_FILE, db)
#                 except Exception as exc:
#                     log.error("Email failed for %s: %s", uname, exc)
#             else:
#                 log.info("%s already warned on %s, skipping email", uname, warned_at)
#         else:
#             # Update email in case it changed; keep last_change_at intact
#             db[uname] = {**record, "email": email, "count": current_count}
#             save_db(DB_FILE, db)

#     log.info("Run complete.")


# if __name__ == "__main__":
#     run()

import os
import json
import smtplib
import requests
import logging
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# ── Config ─────────────────────────────────────────────────────────────────────
GMAIL_USER     = os.environ["GMAIL_USER"]
GMAIL_PASSWORD = os.environ["GMAIL_PASSWORD"]
SENDER_NAME    = os.environ.get("SENDER_NAME", "LeetCode Monitor")
WARN_DAYS      = int(os.environ.get("WARN_DAYS", "3"))
TEACHER_EMAIL  = os.environ.get("TEACHER_EMAIL", GMAIL_USER)  # summary sent here

UNAME_FILE = os.environ.get("UNAME_FILE", "uname.txt")
DB_FILE    = os.environ.get("DB_FILE", "data/progress.json")

LEETCODE_GQL = "https://leetcode.com/graphql"
SOLVED_QUERY = """
query userStats($username: String!) {
  matchedUser(username: $username) {
    submitStatsGlobal {
      acSubmissionNum {
        difficulty
        count
      }
    }
  }
}
"""

# ── Helpers ────────────────────────────────────────────────────────────────────

def load_students(path: str) -> list[dict]:
    students = []
    with open(path) as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 2:
                log.warning("Skipping malformed line: %s", raw.rstrip())
                continue
            students.append({"username": parts[0], "email": parts[1]})
    return students


def load_db(path: str) -> dict:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


def save_db(path: str, db: dict):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        json.dump(db, f, indent=2)


def fetch_solved_count(username: str) -> int | None:
    try:
        resp = requests.post(
            LEETCODE_GQL,
            json={"query": SOLVED_QUERY, "variables": {"username": username}},
            headers={"Content-Type": "application/json", "Referer": "https://leetcode.com"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        user = data.get("data", {}).get("matchedUser")
        if user is None:
            log.warning("User not found on LeetCode: %s", username)
            return None
        stats = user["submitStatsGlobal"]["acSubmissionNum"]
        for entry in stats:
            if entry["difficulty"] == "All":
                return entry["count"]
        return sum(e["count"] for e in stats if e["difficulty"] != "All")
    except Exception as exc:
        log.error("Failed to fetch stats for %s: %s", username, exc)
        return None


def send_email(to_email: str, subject: str, body: str):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"{SENDER_NAME} <{GMAIL_USER}>"
    msg["To"]      = to_email
    msg.attach(MIMEText(body, "plain"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        server.sendmail(GMAIL_USER, to_email, msg.as_string())


def send_warning_email(to_email: str, username: str, days: int, count: int):
    subject = f"⚠️ LeetCode Inactivity Alert – {username}"
    body = f"""\
Hi {username},

This is a reminder from your instructor.

Your LeetCode account has shown NO new solved problems in the past {days} day(s).

  • Current solved count : {count}
  • Checked at           : {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

Consistent practice is key to improvement. Please solve at least one problem today!

— {SENDER_NAME}
"""
    send_email(to_email, subject, body)
    log.info("Warning email sent → %s (%s)", username, to_email)


def send_summary_email(results: list[dict]):
    """Send a daily summary of all students' solve counts to the teacher."""
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    subject = f"📊 LeetCode Daily Summary – {datetime.utcnow().strftime('%Y-%m-%d')}"

    rows = ""
    for r in results:
        change = f"+{r['count'] - r['prev_count']}" if r['changed'] else "—"
        status = "✅ Active" if r['changed'] else f"⚠️  Inactive {r['inactive_days']}d"
        rows += f"  {r['username']:<20} {r['count']:<10} {change:<10} {status}\n"

    body = f"""\
LeetCode Daily Summary
Checked at: {now_str}

  {"Username":<20} {"Solved":<10} {"Change":<10} Status
  {"─" * 58}
{rows}
  Total students   : {len(results)}
  Active today     : {sum(1 for r in results if r['changed'])}
  Inactive (≥{WARN_DAYS}d)  : {sum(1 for r in results if r['inactive_days'] >= WARN_DAYS)}

— {SENDER_NAME}
"""
    send_email(TEACHER_EMAIL, subject, body)
    log.info("Summary email sent → %s", TEACHER_EMAIL)


# ── Main ───────────────────────────────────────────────────────────────────────

def run():
    students = load_students(UNAME_FILE)
    log.info("Loaded %d student(s) from %s", len(students), UNAME_FILE)

    db     = load_db(DB_FILE)
    now    = datetime.utcnow()
    now_str = now.isoformat()
    results = []

    for student in students:
        uname = student["username"]
        email = student["email"]

        current_count = fetch_solved_count(uname)
        if current_count is None:
            continue

        record         = db.get(uname, {})
        last_count     = record.get("count", -1)
        last_change_at = record.get("last_change_at", now_str)
        warned_at      = record.get("warned_at")

        last_change_dt = datetime.fromisoformat(last_change_at)
        inactive_days  = (now - last_change_dt).days
        changed        = current_count != last_count

        results.append({
            "username":      uname,
            "count":         current_count,
            "prev_count":    last_count if last_count != -1 else current_count,
            "changed":       changed,
            "inactive_days": 0 if changed else inactive_days,
        })

        if changed:
            log.info("%s: count changed %d → %d", uname, last_count, current_count)
            db[uname] = {
                "count":          current_count,
                "last_change_at": now_str,
                "warned_at":      None,
                "email":          email,
            }
        else:
            log.info("%s: no change (count=%d, inactive %d day(s))", uname, current_count, inactive_days)
            if inactive_days >= WARN_DAYS and not warned_at:
                try:
                    send_warning_email(email, uname, inactive_days, current_count)
                    db[uname] = {**record, "warned_at": now_str, "email": email}
                except Exception as exc:
                    log.error("Warning email failed for %s: %s", uname, exc)
            else:
                db[uname] = {**record, "email": email, "count": current_count}

        save_db(DB_FILE, db)

    # Daily summary to teacher
    if results:
        try:
            send_summary_email(results)
        except Exception as exc:
            log.error("Summary email failed: %s", exc)

    log.info("Run complete.")


if __name__ == "__main__":
    run()