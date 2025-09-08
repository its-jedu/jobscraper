import time, hashlib
from typing import List, Dict
from urllib.parse import urlencode
from bs4 import BeautifulSoup
from django.conf import settings
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

def _driver():
    o = Options()
    if settings.SELENIUM_HEADLESS:
        o.add_argument("--headless=new")
    o.add_argument("--no-sandbox"); o.add_argument("--disable-dev-shm-usage"); o.add_argument("--window-size=1366,900")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=o)

def scrape_glassdoor(query: str, location: str, pages: int = 1) -> List[Dict]:
    """MVP parser for Glassdoor search results (public listings)."""
    base = "https://www.glassdoor.com/Job/jobs.htm?"
    results: List[Dict] = []
    d = _driver()
    delay = settings.SCRAPER_DELAY_MS / 1000.0
    try:
        for p in range(pages):
            params = {"sc.keyword": query, "locT": "C", "locId": "", "locKeyword": location or "", "p": p+1}
            url = base + urlencode(params)
            d.get(url); time.sleep(delay)

            soup = BeautifulSoup(d.page_source, "html.parser")
            cards = soup.select("li.react-job-listing") or soup.select("div.JobCard_jobCard")
            if not cards: break

            for c in cards:
                t = c.select_one("[data-test='job-title']") or c.select_one("a.jobLink")
                comp = c.select_one("[data-test='job-company-name']") or c.select_one(".jobInfoItem.jobEmpolyerName")
                loc = c.select_one("[data-test='job-location']") or c.select_one(".jobLoc")
                sal = c.select_one("[data-test='detailSalary']") or c.select_one(".salary-estimate")
                desc = c.select_one("[data-test='job-description']") or c.select_one(".job-snippet")
                href = t.get("href") if t else None
                url_abs = ("https://www.glassdoor.com" + href) if href and href.startswith("/") else (href or "")

                title = t.get_text(strip=True) if t else "Job"
                company = comp.get_text(strip=True) if comp else None
                location_txt = loc.get_text(" ", strip=True) if loc else location or None
                salary_raw = sal.get_text(" ", strip=True) if sal else None
                description = desc.get_text(" ", strip=True) if desc else None

                hk = hashlib.sha256(f"glassdoor|{url_abs}|{title}|{company or ''}".encode()).hexdigest()
                results.append({
                    "source":"glassdoor","external_id":None,"title":title,"company":company,"location":location_txt,
                    "salary_min":None,"salary_max":None,"currency":None,"salary_raw":salary_raw,"post_date":None,
                    "description":description,"url":url_abs,"is_remote": bool(location_txt and "remote" in location_txt.lower()),
                    "hash_key": hk,
                })
    finally:
        d.quit()
    return results
