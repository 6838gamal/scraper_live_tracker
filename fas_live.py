import requests
from bs4 import BeautifulSoup
import time
import json
import threading
from datetime import datetime
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request

BASE_URL = "https://mostaql.com"

app = FastAPI()

templates = Jinja2Templates(directory="templates")

DATA_FILE = "data.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


# =========================
# تحميل البيانات
# =========================
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
# استخراج أحدث مشروع
# =========================
def get_latest_project():
    url = f"{BASE_URL}/projects"
    res = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(res.text, "html.parser")

    row = soup.select_one("tr.project-row")
    if not row:
        return None

    title = row.select_one("h2 a").get_text(strip=True)
    link = row.select_one("h2 a")["href"]

    if not link.startswith("http"):
        link = BASE_URL + link

    brief_tag = row.select_one("p.project__brief a.details-url")
    brief = brief_tag.get_text(strip=True) if brief_tag else ""

    time_tag = row.select_one("time")
    time_text = time_tag.get_text(strip=True) if time_tag else ""

    project_id = link.split("/")[-1].split("-")[0]

    return {
        "id": project_id,
        "title": title,
        "link": link,
        "brief": brief,
        "time": time_text,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


# =========================
# المراقبة اللحظية
# =========================
def monitor():
    seen = set()
    data = load_data()

    print("🚀 Live Monitor Started...")

    while True:
        try:
            project = get_latest_project()

            if project and project["id"] not in seen:
                print("🆕 New:", project["title"])

                data.insert(0, project)  # أحدث في الأعلى
                save_data(data)

                seen.add(project["id"])

            time.sleep(10)

        except Exception as e:
            print("❌ Error:", e)
            time.sleep(10)


# =========================
# API - عرض البيانات
# =========================
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    data = load_data()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "projects": data[:50]
    })


# =========================
# تشغيل المراقبة مع السيرفر
# =========================
@app.on_event("startup")
def start_monitor():
    thread = threading.Thread(target=monitor)
    thread.daemon = True
    thread.start()
