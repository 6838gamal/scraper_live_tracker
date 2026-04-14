import requests
from bs4 import BeautifulSoup
import time
import json
import threading
import re
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

BASE_URL = "https://mostaql.com"
URL = f"{BASE_URL}/projects"

app = FastAPI()
templates = Jinja2Templates(directory="templates")

DATA_FILE = "data.json"

HEADERS = {"User-Agent": "Mozilla/5.0"}


# =========================
# أدوات مساعدة
# =========================
def clean_filename(text):
    return re.sub(r'[\\/*?:"<>|]', "", text)


def load_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# =========================
# جلب آخر مشروع (مختصر)
# =========================
def get_latest_project():
    try:
        res = requests.get(URL, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")

        project = soup.select_one("tr.project-row")
        if not project:
            return None

        a_tag = project.select_one("h2 a")
        time_tag = project.select_one("time")

        link = a_tag.get("href")

        if not link.startswith("http"):
            link = BASE_URL + link

        return {
            "title": a_tag.text.strip(),
            "link": link,
            "datetime": time_tag.get("datetime") if time_tag else None
        }

    except Exception as e:
        print("latest error:", e)
        return None


# =========================
# جلب الصفحة الكاملة
# =========================
def get_full_page(link):
    res = requests.get(link, headers=HEADERS, timeout=10)
    return res.text


# =========================
# استخراج البيانات (نفس سكربتك الثاني)
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

    # ===== STATUS =====
    status = soup.select_one(".label-prj-open")
    data["status"] = status.text.strip() if status else ""

    # ===== DATE =====
    publish_time = soup.select_one('time[itemprop="datePublished"]')
    data["publish_date"] = publish_time.get("datetime") if publish_time else ""

    # ===== BUDGET =====
    budget = soup.select_one('[data-type="project-budget_range"]')
    data["budget"] = budget.text.strip() if budget else ""

    # ===== DURATION =====
    data["duration"] = ""
    for row in soup.select(".meta-row"):
        label = row.select_one(".meta-label")
        value = row.select_one(".meta-value")

        if label and value and "مدة التنفيذ" in label.text:
            data["duration"] = value.text.strip()

    # ===== SKILLS (بدون تكرار) =====
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

    for row in soup.select(".table-meta tr"):
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
# المراقبة
# =========================
def monitor():
    print("🚀 Monitor Started...")

    data = load_data()
    seen = set(item["id"] for item in data if "id" in item)

    while True:
        try:
            latest = get_latest_project()

            if not latest:
                time.sleep(10)
                continue

            project_id = latest["link"].split("/")[-1].split("-")[0]

            if project_id not in seen:
                print("🆕 New Project:", latest["title"])

                html = get_full_page(latest["link"])
                full_data = extract_project_data(html)

                full_data["id"] = project_id
                full_data["scraped_at"] = datetime.now().isoformat()

                data.insert(0, full_data)
                data = data[:200]

                save_data(data)
                seen.add(project_id)

            time.sleep(8)

        except Exception as e:
            print("Monitor error:", e)
            time.sleep(10)


# =========================
# واجهة FastAPI
# =========================
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    data = load_data()

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"projects": data[:50]}
    )


# =========================
# تشغيل المراقبة
# =========================
@app.on_event("startup")
def startup():
    thread = threading.Thread(target=monitor, daemon=True)
    thread.start()
