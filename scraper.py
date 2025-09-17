import os, re, json, base64
from datetime import datetime, timezone
import requests
from bs4 import BeautifulSoup

REPO = "SimplifyJobs/New-Grad-Positions"
PATH = "README.md"
GITHUB_API_URL = f"https://api.github.com/repos/{REPO}/contents/{PATH}"

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
NOTION_DB_ID = os.environ["NOTION_DB_ID"]
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")
GITHUB_TOKEN = os.environ.get("GH_PAT")  # optional, helps with rate limits

NYC_PATTERNS = [
    r"\bNYC\b",
    r"\bNY\b",
    r"\nyc\b",
    r"\bNew York\b",
    r"\bNew York[, ]+NY\b",
    r"\bManhattan\b",
    r"\bBrooklyn\b",
    r"\bQueens\b",
    r"\bBronx\b",
    r"\bStaten Island\b",
]

SECTION_MARKERS = [
    "## 💻 Software Engineering New Grad Roles",
    "## 📱 Product Management New Grad Roles",
    "## 🤖 Data Science, AI & Machine Learning New Grad Roles",
]

def http_get_json(url, headers):
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()

def fetch_readme_markdown():
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    data = http_get_json(GITHUB_API_URL, headers=headers)
    content_b64 = data["content"]
    return base64.b64decode(content_b64).decode("utf-8")

def slice_sections(md_text):
    out = []
    for marker in SECTION_MARKERS:
        start = md_text.find(marker)
        if start == -1:
            continue
        next_idx = md_text.find("\n## ", start + 3)
        section = md_text[start:] if next_idx == -1 else md_text[start:next_idx]
        out.append(section)
    return "\n\n".join(out)

def normalize_whitespace(s):
    return re.sub(r"\s+", " ", s or "").strip()

def td_text(td):
    for br in td.find_all("br"):
        br.replace_with(" | ")
    return normalize_whitespace(td.get_text(" ", strip=True))

def first_href(td):
    a = td.find("a", href=True)
    return a["href"].strip() if a else None

def looks_like_nyc(text):
    if not text:
        return False
    for pat in NYC_PATTERNS:
        if re.search(pat, text, flags=re.I):
            return True
    return False

def parse_age_to_days(age_str):
    """
    Convert age like '0d', '12d', '1mo', '2mo', '7d', '3mo', '1w', '12h'
    into a standardized days format like '0d', '12d', '30d', '60d', '7d', '90d', '7d', '0d'
    """
    if not age_str:
        return "0d"
    
    s = age_str.strip().lower()
    # Remove non-alphanumerics (e.g., emojis)
    s = re.sub(r"[^\dA-Za-z]", "", s)

    # Normalize common variants
    s = s.replace("months", "mo").replace("month", "mo")
    s = s.replace("weeks", "w").replace("week", "w")
    s = s.replace("days", "d").replace("day", "d")
    s = s.replace("hours", "h").replace("hour", "h").replace("hrs", "h").replace("hr", "h")

    m = re.match(r"^(\d+)(mo|w|d|h)$", s)
    if not m:
        return "0d"
    
    qty = int(m.group(1))
    unit = m.group(2)

    if unit == "h":
        # Hours: round down to 0 days for anything less than 24h
        days = 0
    elif unit == "d":
        # Days: keep as is
        days = qty
    elif unit == "w":
        # Weeks: convert to days (7 days per week)
        days = qty * 7
    elif unit == "mo":  # 'mo' → months: convert to days (30 days per month)
        days = qty * 30

    return f"{days}d"


def load_seen():
    if os.path.exists("seen.json"):
        with open("seen.json", "r") as f:
            return set(json.load(f))
    return set()

def save_seen(seen):
    with open("seen.json", "w") as f:
        json.dump(sorted(list(seen)), f)

def extract_active_tables(section_md):
    soup = BeautifulSoup(section_md, "html.parser")
    tables = []
    for table in soup.find_all("table"):
        inside_details = any(parent.name == "details" for parent in table.parents)
        if not inside_details:
            tables.append(table)
    return tables

def extract_jobs_from_tables(section_md):
    jobs = []
    for table in extract_active_tables(section_md):
        tbody = table.find("tbody")
        if not tbody:
            continue
        for tr in tbody.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) < 5:
                continue

            company_cell, role_cell, loc_cell, app_cell, age_cell = tds[:5]
            company = td_text(company_cell).replace("↳", "").strip()
            role = td_text(role_cell)
            location = td_text(loc_cell).replace("|", ",")
            apply_link = first_href(app_cell)
            age = td_text(age_cell)

            jobs.append({
                "company": company,
                "title": role,
                "url": apply_link,
                "location": location,
                "age": age,
                "age_days": parse_age_to_days(age)
            })
    return jobs

def notion_create_page(job):
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    props = {
        "Job Title": {"title": [{"text": {"content": job["title"][:100]}}]},
        "Company": {"rich_text": [{"text": {"content": (job.get("company") or "")[:200]}}]},
        "Source Link": {"url": job["url"]},
        "Age": {"rich_text": [{"text": {"content": (job.get("age") or "")}}]},
        "Age": {"rich_text": [{"text": {"content": (job.get("age_days") or "0d")}}]},
        "Location": {"rich_text": [{"text": {"content": (job.get("location") or "")}}]},
    }

    body = {
        "parent": {"database_id": NOTION_DB_ID},
        "properties": props,
    }
    r = requests.post("https://api.notion.com/v1/pages", headers=headers, json=body, timeout=30)
    if r.status_code >= 400:
        print("Notion error:", r.status_code, r.text)
    r.raise_for_status()
    return r.json()

def notify(text):
    if not SLACK_WEBHOOK_URL:
        return
    try:
        requests.post(SLACK_WEBHOOK_URL, json={"text": text}, timeout=10)
    except Exception:
        pass

def main():
    seen = load_seen()
    md = fetch_readme_markdown()
    md_subset = slice_sections(md)

    jobs_all = extract_jobs_from_tables(md_subset)

    new_items = []
    for job in jobs_all:
        # Skip jobs without URLs (can't track them)
        if not job.get("url"):
            continue
        # Use URL as the stable identifier
        if job["url"] in seen or "Phd" in job["title"] or "🎓" in job["title"]:
            continue
        if looks_like_nyc(job.get("location") or ""):
            new_items.append(job)

    created = 0
    for job in new_items:
        notion_create_page(job)
        notify(f"NYC job added: {job['title']} | {job.get('company') or ''} | {job['url']} | Age={job.get('age')} | Location={job.get('location')}")
        seen.add(job["url"])
        created += 1

    # Always save seen.json to persist the baseline
    save_seen(seen)
    print(f"Checked {len(jobs_all)} rows across SWE/PM/DS-AI, added {created} NYC items.")

if __name__ == "__main__":
    main()
