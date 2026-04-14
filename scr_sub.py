import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime

URL = "https://mostaql.com/projects"
HEADERS = {"User-Agent": "Mozilla/5.0"}


# تنظيف اسم الملف
def clean_filename(text):
    return re.sub(r'[\\/*?:"<>|]', "", text)


# =========================
# جلب آخر مشروع
# =========================
def get_latest_project():
    res = requests.get(URL, headers=HEADERS)
    soup = BeautifulSoup(res.text, "html.parser")

    project = soup.select_one("tr.project-row")
    if not project:
        return None

    a_tag = project.select_one("h2 a")
    time_tag = project.select_one("time")

    return {
        "title": a_tag.text.strip(),
        "link": a_tag.get("href"),
        "datetime": time_tag.get("datetime") if time_tag else None
    }


# =========================
# جلب الصفحة كاملة
# =========================
def get_full_page(link):
    res = requests.get(link, headers=HEADERS)
    return res.text


# =========================
# استخراج البيانات المنظمة
# =========================
def extract_project_data(html):
    soup = BeautifulSoup(html, "html.parser")

    data = {}

    # ===== HEAD =====
    data["title"] = soup.select_one("title").text.strip() if soup.select_one("title") else ""

    meta_desc = soup.select_one('meta[name="description"]')
    data["description_meta"] = meta_desc.get("content") if meta_desc else ""

    canonical = soup.select_one('link[rel="canonical"]')
    data["url"] = canonical.get("href") if canonical else ""

    # ===== PROJECT META =====
    status = soup.select_one(".label-prj-open")
    data["status"] = status.text.strip() if status else ""

    publish_time = soup.select_one('time[itemprop="datePublished"]')
    data["publish_date"] = publish_time.get("datetime") if publish_time else ""

    budget = soup.select_one('[data-type="project-budget_range"]')
    data["budget"] = budget.text.strip() if budget else ""

    # مدة التنفيذ
    data["duration"] = ""
    for row in soup.select(".meta-row"):
        label = row.select_one(".meta-label")
        value = row.select_one(".meta-value")

        if not label or not value:
            continue

        if "مدة التنفيذ" in label.text:
            data["duration"] = value.text.strip()

    # ===== SKILLS (بدون تكرار + ترتيب محفوظ) =====
    skills_elements = soup.select(".skills__item bdi")

    skills = []
    seen = set()

    for s in skills_elements:
        skill = s.text.strip()

        if skill and skill not in seen:
            seen.add(skill)
            skills.append(skill)

    data["skills"] = skills

    # ===== DETAILS =====
    details = soup.select_one("#projectDetailsTab .text-wrapper-div")
    data["details"] = details.text.strip() if details else ""

    # ===== CLIENT =====
    client = {}

    name = soup.select_one(".profile__name bdi")
    client["name"] = name.text.strip() if name else ""

    job = soup.select_one(".meta_items li a")
    client["job"] = job.text.strip() if job else ""

    rows = soup.select(".table-meta tr")

    for row in rows:
        cols = row.find_all("td")
        if len(cols) != 2:
            continue

        key = cols[0].text.strip()
        value = cols[1].text.strip()

        if "تاريخ التسجيل" in key:
            client["registration_date"] = value
        elif "معدل التوظيف" in key:
            client["hire_rate"] = value
        elif "المشاريع المفتوحة" in key:
            client["open_projects"] = value
        elif "مشاريع قيد التنفيذ" in key:
            client["active_projects"] = value
        elif "التواصلات الجارية" in key:
            client["messages"] = value

    data["client"] = client

    return data


# =========================
# حفظ الملفات
# =========================
def save_files(project, html, data):
    title = clean_filename(project["title"])

    if project["datetime"]:
        dt = project["datetime"].replace(":", "-").replace(" ", "_")
    else:
        dt = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    filename = f"{title}_{dt}"

    # JSON
    with open(f"{filename}.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    # HTML كامل
    with open(f"{filename}.html", "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✅ تم حفظ: {filename}")


# =========================
# التشغيل
# =========================
def run():
    project = get_latest_project()

    if not project:
        print("❌ لا يوجد مشروع")
        return

    print("📌", project["title"])

    html = get_full_page(project["link"])

    data = extract_project_data(html)

    save_files(project, html, data)


if __name__ == "__main__":
    run()
