import time, hashlib
from urllib.parse import urlencode
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from django.conf import settings

def _driver():
    o = Options()
    if settings.SELENIUM_HEADLESS:
        o.add_argument("--headless=new")
    o.add_argument("--no-sandbox"); o.add_argument("--disable-dev-shm-usage")
    o.add_argument("--disable-gpu"); o.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=o)

def scrape_indeed(query: str | None = "", location: str | None = "", pages: int = 1):
    base = "https://www.indeed.com/jobs"
    delay = settings.SCRAPER_DELAY_MS / 1000.0
    items = []
    d = _driver()
    try:
        for p in range(pages):
            params = {}
            if (query or "").strip():    params["q"] = query
            if (location or "").strip(): params["l"] = location
            if p: params["start"] = p * 10
            url = "https://www.indeed.com/jobs" + ("?" + urlencode(params) if params else (f"?start={p*10}" if p else ""))

            d.get(url); time.sleep(delay)
            soup = BeautifulSoup(d.page_source, "html.parser")
            cards = soup.select("div.job_seen_beacon")
            if not cards: 
                if p == 0:  # no results even on first page → stop
                    break
                continue

            for c in cards:
                t = c.select_one("h2.jobTitle span")
                comp = c.select_one("span.companyName")
                loc = c.select_one("div.companyLocation")
                sal = c.select_one("div.metadata.salary-snippet-container")
                link = c.select_one("a[href*='/pagead/'], a[href^='/rc/'], a.jcs-JobTitle")

                title = t.get_text(strip=True) if t else None
                company = comp.get_text(strip=True) if comp else None
                location_txt = loc.get_text(" ", strip=True) if loc else None
                salary_raw = sal.get_text(" ", strip=True) if sal else None
                href = link["href"] if link and link.has_attr("href") else ""
                job_url = ("https://www.indeed.com" + href) if href.startswith("/") else href

                hk = hashlib.sha256(f"indeed|{job_url}|{title or ''}|{company or ''}".encode()).hexdigest()
                items.append({
                    "source":"indeed","external_id":None,
                    "title":title,"company":company,"location":location_txt,
                    "salary_min":None,"salary_max":None,"currency":None,"salary_raw":salary_raw,
                    "post_date":None,"description":None,"url":job_url,
                    "is_remote": bool((location_txt or "").lower().find("remote") >= 0),
                    "hash_key":hk,
                })
    finally:
        d.quit()
    return items
