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
# جلب المشاريع
# =========================
def get_projects(page=1):
    url = f"{BASE_URL}/projects?page={page}"

    res = requests.get(url, headers=HEADERS, timeout=10)
    soup = BeautifulSoup(res.text, "html.parser")

    links = soup.select("a[href*='/project/']")

    projects = []
    seen = set()

    for a in links:
        href = a.get("href")

        if not href:
            continue

        # فلترة روابط غير مهمة
        if "create" in href or "similar" in href:
            continue

        if "/project/" not in href:
            continue

        # إصلاح الرابط
        if href.startswith("http"):
            full_link = href
        else:
            full_link = BASE_URL + href

        if full_link in seen:
            continue

        seen.add(full_link)

        title = a.get_text(strip=True)

        if len(title) < 10:
            continue

        projects.append({
            "title": title,
            "link": full_link
        })

    return projects


# =========================
# تفاصيل المشروع
# =========================
def get_project_details(url):
    res = requests.get(url, headers=HEADERS, timeout=10)
    soup = BeautifulSoup(res.text, "html.parser")

    desc = soup.select_one("div[class*=description]")
    budget = soup.select_one("div[class*=budget]")

    skills = [s.get_text(strip=True) for s in soup.select("a[href*='/skills/']")]

    return {
        "description": desc.get_text(strip=True) if desc else "",
        "budget": budget.get_text(strip=True) if budget else "",
        "skills": skills
    }


# =========================
# حفظ صفحة مستقلة
# =========================
def save_page(data, page):
    os.makedirs("output", exist_ok=True)

    filename = f"output/projects_page_{page}.json"

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"💾 تم حفظ الصفحة {page} في {filename}")


# =========================
# التشغيل الرئيسي
# =========================
def main():
    page = 1

    while True:
        print(f"\n📄 الصفحة {page}")

        projects = get_projects(page)

        if not projects:
            print("⚠️ لا توجد مشاريع في هذه الصفحة")
            break

        page_data = []

        for project in projects:
            print("🔍", project["title"])

            details = get_project_details(project["link"])

            page_data.append({
                "title": project["title"],
                "link": project["link"],
                **details
            })

            time.sleep(1)

        # حفظ كل صفحة لوحدها
        save_page(page_data, page)

        # =========================
        # سؤال المستخدم
        # =========================
        choice = input("\n➡️ هل ترغب في متابعة الصفحة التالية؟ (y/n): ").strip().lower()

        if choice != "y":
            print("🛑 تم إيقاف السكربت")
            break

        page += 1
        time.sleep(1)


if __name__ == "__main__":
    main()
