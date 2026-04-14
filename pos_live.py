import requests
from bs4 import BeautifulSoup
import time
import threading
from datetime import datetime
import os

import psycopg2
from psycopg2.extras import Json

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


# =========================
# CONFIG
# =========================
BASE_URL = "https://mostaql.com"
URL = f"{BASE_URL}/projects"

HEADERS = {"User-Agent": "Mozilla/5.0"}

# مهم: من Render Environment
DATABASE_URL = os.environ.get("DATABASE_URL")

app = FastAPI()
templates = Jinja2Templates(directory="templates")


# =========================
# DB CONNECTION
# =========================
def get_conn():
    return psycopg2.connect(DATABASE_URL, sslmode="require", connect_timeout=10)


# =========================
# INIT DB
# =========================
def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        id TEXT PRIMARY KEY,
        title TEXT,
        link TEXT,
        status TEXT,
        budget TEXT,
        duration TEXT,
        publish_date TEXT,
        skills JSONB,
        details TEXT,
        client JSONB,
        scraped_at TIMESTAMP DEFAULT NOW()
    );
    """)

    conn.commit()
    cur.close()
    conn.close()


# =========================
# GET LATEST PROJECT
# =========================
def get_latest_project():
    try:
        res = requests.get(URL, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")

        project = soup.select_one("tr.project-row")
        if not project:
            return None

        a_tag = project.select_one("h2 a")
        if not a_tag:
            return None

        link = a_tag.get("href", "")
        if not link.startswith("http"):
            link = BASE_URL + link

        project_id = link.rstrip("/").split("/")[-1].split("-")[0]

        return {
            "id": project_id,
            "title": a_tag.text.strip(),
            "link": link
        }

    except Exception as e:
        print("latest error:", e)
        return None


# =========================
# FULL PAGE
# =========================
def get_full_page(link):
    res = requests.get(link, headers=HEADERS, timeout=10)
    return res.text


# =========================
# EXTRACT DATA
# =========================
def extract_project_data(html, base_link):
    soup = BeautifulSoup(html, "html.parser")

    data = {}

    data["title"] = soup.select_one("title").text.strip() if soup.select_one("title") else ""

    status = soup.select_one(".label-prj-open")
    data["status"] = status.text.strip() if status else ""

    budget = soup.select_one('[data-type="project-budget_range"]')
    data["budget"] = budget.text.strip() if budget else ""

    time_tag = soup.select_one('time[itemprop="datePublished"]')
    data["publish_date"] = time_tag.get("datetime") if time_tag else ""

    # duration
    data["duration"] = ""
    for row in soup.select(".meta-row"):
        label = row.select_one(".meta-label")
        value = row.select_one(".meta-value")
        if label and value and "مدة التنفيذ" in label.text:
            data["duration"] = value.text.strip()

    # skills
    skills = []
    seen = set()
    for s in soup.select(".skills__item bdi"):
        skill = s.text.strip()
        if skill and skill not in seen:
            seen.add(skill)
            skills.append(skill)

    data["skills"] = skills

    # details
    details = soup.select_one("#projectDetailsTab .text-wrapper-div")
    data["details"] = details.text.strip() if details else ""

    # client
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

        if "معدل التوظيف" in key:
            client["hire_rate"] = value

    data["client"] = client
    data["link"] = base_link

    return data


# =========================
# SAVE PROJECT
# =========================
def save_project(project):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO projects (
            id, title, link, status, budget,
            duration, publish_date, skills,
            details, client, scraped_at
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW())
        ON CONFLICT (id) DO NOTHING;
    """, (
        project["id"],
        project.get("title"),
        project.get("link"),
        project.get("status"),
        project.get("budget"),
        project.get("duration"),
        project.get("publish_date"),
        Json(project.get("skills", [])),
        project.get("details"),
        Json(project.get("client", {}))
    ))

    conn.commit()
    cur.close()
    conn.close()


# =========================
# LOAD DATA
# =========================
def load_data(limit=50):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, title, link, status, budget,
               duration, publish_date, skills,
               details, client, scraped_at
        FROM projects
        ORDER BY scraped_at DESC
        LIMIT %s
    """, (limit,))

    rows = cur.fetchall()

    cur.close()
    conn.close()

    data = []
    for r in rows:
        data.append({
            "id": r[0],
            "title": r[1],
            "url": r[2],
            "status": r[3],
            "budget": r[4],
            "duration": r[5],
            "publish_date": r[6],
            "skills": r[7],
            "details": r[8],
            "client": r[9],
            "scraped_at": str(r[10])
        })

    return data


# =========================
# MONITOR
# =========================
def monitor():
    print("🚀 Monitor started...")

    seen = set()

    while True:
        try:
            latest = get_latest_project()

            if not latest:
                time.sleep(10)
                continue

            if latest["id"] in seen:
                time.sleep(8)
                continue

            print("🆕 New:", latest["title"])

            html = get_full_page(latest["link"])
            full = extract_project_data(html, latest["link"])

            full["id"] = latest["id"]

            save_project(full)

            seen.add(latest["id"])

            time.sleep(8)

        except Exception as e:
            print("monitor error:", e)
            time.sleep(10)


# =========================
# API
# =========================
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    data = load_data()

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"projects": data}
    )


# اختبار الاتصال
@app.get("/db-check")
def db_check():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT NOW();")
    result = cur.fetchone()
    conn.close()

    return {"status": "OK", "time": str(result[0])}


# =========================
# STARTUP
# =========================
@app.on_event("startup")
def startup():
    init_db()

    thread = threading.Thread(target=monitor, daemon=True)
    thread.start()
