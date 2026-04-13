import requests
from bs4 import BeautifulSoup
import time
import json
import os
import re
from datetime import datetime

BASE_URL = "https://mostaql.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "ar,en-US;q=0.9"
}

SEEN_FILE = "seen.json"
OUTPUT_DIR = "live_data"


# =========================
# أدوات مساعدة
# =========================
def slugify(text, max_len=40):
    text = text.strip()
    text = re.sub(r'\s+', '-', text)
    text = re.sub(r'[^\w\u0600-\u06FF\-]', '', text)
    text = re.sub(r'-+', '-', text)
    return text[:max_len].strip("-")


def get_timestamp():
    return datetime.now().strftime("%Y-%m-%d-%H%M")


# =========================
# حفظ ومعالجة التكرار
# =========================
def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def save_seen(seen):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(list(seen), f, ensure_ascii=False, indent=2)


# =========================
# استخراج مشروع واحد (مطابق للهيكل)
# =========================
def parse_project(row):

    # ===== العنوان =====
    title_tag = row.select_one("h2 a")
    title = title_tag.get_text(strip=True) if title_tag else ""

    link = title_tag.get("href") if title_tag else ""
    if link and not link.startswith("http"):
        link = BASE_URL + link

    # ===== الوصف (IMPORTANT) =====
    brief_tag = row.select_one("p.project__brief a.details-url")
    brief = brief_tag.get_text(strip=True) if brief_tag else ""

    # ===== صاحب المشروع =====
    owner_tag = row.select_one("ul.project__meta li bdi")
    owner = owner_tag.get_text(strip=True) if owner_tag else ""

    # ===== الوقت =====
    time_tag = row.select_one("ul.project__meta time")
    time_text = time_tag.get_text(strip=True) if time_tag else ""
    time_raw = time_tag.get("datetime") if time_tag else ""

    # ===== عدد العروض =====
    bids_tag = row.select_one("ul.project__meta li span")
    bids = bids_tag.get_text(strip=True) if bids_tag else ""

    # ===== ID =====
    project_id = link.split("/")[-1].split("-")[0] if link else ""

    return {
        "id": project_id,
        "title": title,
        "link": link,
        "brief": brief,
        "owner": owner,
        "bids": bids,
        "time_text": time_text,
        "time_raw": time_raw
    }


# =========================
# جلب أحدث مشروع فقط
# =========================
def get_latest_project():
    url = f"{BASE_URL}/projects"

    res = requests.get(url, headers=HEADERS, timeout=10)
    soup = BeautifulSoup(res.text, "html.parser")

    row = soup.select_one("tr.project-row")

    if not row:
        return None

    return parse_project(row)


# =========================
# حفظ المشروع
# =========================
def save_project(project):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    safe_title = slugify(project["title"])
    timestamp = get_timestamp()

    file_path = f"{OUTPUT_DIR}/{project['id']}-{safe_title}-{timestamp}.json"

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(project, f, ensure_ascii=False, indent=2)

    print("💾 تم حفظ:", project["title"])


# =========================
# المراقبة اللحظية
# =========================
def monitor():
    seen = load_seen()

    print("🚀 بدء مراقبة أحدث المشاريع...")

    while True:
        try:
            project = get_latest_project()

            if not project:
                print("⚠️ لا يوجد بيانات")
                time.sleep(10)
                continue

            if project["id"] in seen:
                print("⏳ لا يوجد جديد...")
                time.sleep(10)
                continue

            print("🆕 مشروع جديد:", project["title"])
            print("📝 الوصف:", project["brief"][:80], "...")

            save_project(project)

            seen.add(project["id"])
            save_seen(seen)

            time.sleep(10)

        except Exception as e:
            print("❌ خطأ:", e)
            time.sleep(10)


if __name__ == "__main__":
    monitor()
