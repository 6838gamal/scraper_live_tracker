import requests
from bs4 import BeautifulSoup
import time
import json
import os

BASE_URL = "https://mostaql.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "ar,en-US;q=0.9"
}


# =========================
# جلب المشاريع من صفحة
# =========================
def get_projects(page=1):
    url = f"{BASE_URL}/projects?page={page}"

    res = requests.get(url, headers=HEADERS, timeout=10)
    soup = BeautifulSoup(res.text, "html.parser")

    rows = soup.select("tr.project-row")

    projects = []

    for row in rows:

        title_tag = row.select_one("h2 a")
        if not title_tag:
            continue

        title = title_tag.get_text(strip=True)
        link = title_tag.get("href")

        if link.startswith("http"):
            full_link = link
        else:
            full_link = BASE_URL + link

        brief_tag = row.select_one("p.project__brief a")
        brief = brief_tag.get_text(strip=True) if brief_tag else ""

        owner_tag = row.select_one("ul.project__meta li bdi")
        owner = owner_tag.get_text(strip=True) if owner_tag else ""

        bids_tag = row.select_one("ul.project__meta li span")
        bids = bids_tag.get_text(strip=True) if bids_tag else ""

        time_tag = row.select_one("time")
        time_text = time_tag.get_text(strip=True) if time_tag else ""

        projects.append({
            "title": title,
            "link": full_link,
            "brief": brief,
            "owner": owner,
            "bids": bids,
            "time": time_text
        })

    return projects


# =========================
# حفظ كل صفحة لوحدها
# =========================
def save_page(data, page):
    os.makedirs("output", exist_ok=True)

    file_path = f"output/page_{page}.json"

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"💾 تم حفظ الصفحة {page}")


# =========================
# التشغيل التفاعلي
# =========================
def main():
    page = 1

    while True:
        print(f"\n📄 الصفحة {page}")

        projects = get_projects(page)

        if not projects:
            print("⚠️ لا توجد بيانات في هذه الصفحة")
            break

        for p in projects:
            print("🔍", p["title"])

        # حفظ الصفحة
        save_page(projects, page)

        # =========================
        # سؤال المستخدم
        # =========================
        choice = input("\n➡️ هل ترغب في الانتقال للصفحة التالية؟ (y/n): ").strip().lower()

        if choice != "y":
            print("🛑 تم إيقاف السكربت")
            break

        page += 1
        time.sleep(1)


if __name__ == "__main__":
    main()
