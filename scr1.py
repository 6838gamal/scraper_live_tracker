import requests
from bs4 import BeautifulSoup
import time
import json

BASE_URL = "https://mostaql.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "ar,en-US;q=0.9"
}


# =========================
# جلب المشاريع من الصفحة
# =========================
def get_projects(page=1):
    url = f"{BASE_URL}/projects?page={page}"

    res = requests.get(url, headers=HEADERS, timeout=10)
    soup = BeautifulSoup(res.text, "html.parser")

    projects = []
    seen = set()

    rows = soup.select("tr.project-row")

    for row in rows:

        # ===== العنوان والرابط =====
        title_tag = row.select_one("h2 a")

        if not title_tag:
            continue

        title = title_tag.get_text(strip=True)
        link = title_tag.get("href")

        if not link:
            continue

        # إصلاح الرابط
        if link.startswith("http"):
            full_link = link
        else:
            full_link = BASE_URL + link

        if full_link in seen:
            continue

        seen.add(full_link)

        # ===== الوصف المختصر =====
        brief_tag = row.select_one("p.project__brief a")
        brief = brief_tag.get_text(strip=True) if brief_tag else ""

        # ===== اسم صاحب المشروع =====
        owner_tag = row.select_one("ul.project__meta li bdi")
        owner = owner_tag.get_text(strip=True) if owner_tag else ""

        # ===== عدد العروض =====
        bids_tag = row.select_one("ul.project__meta li span")
        bids = bids_tag.get_text(strip=True) if bids_tag else ""

        # ===== الوقت =====
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
# التشغيل
# =========================
def main():
    all_data = []

    pages = 2  # عدل عدد الصفحات

    for page in range(1, pages + 1):
        print(f"\n📄 الصفحة {page}")

        projects = get_projects(page)

        if not projects:
            print("⚠️ لا توجد بيانات")
            continue

        for p in projects:
            print("🔍", p["title"])

            all_data.append(p)

            time.sleep(0.5)

    # حفظ
    with open("mostaql_projects.json", "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)

    print("\n✅ تم الحفظ في mostaql_projects.json")


if __name__ == "__main__":
    main()
