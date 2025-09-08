import time, hashlib
from typing import List, Dict
from urllib.parse import urlencode
from bs4 import BeautifulSoup
from django.conf import settings
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# NOTE: LinkedIn aggressively changes DOM & rate-limits. This MVP targets public job search pages.
def _driver():
    o = Options()
    if settings.SELENIUM_HEADLESS:
        o.add_argument("--headless=new")
    o.add_argument("--no-sandbox"); o.add_argument("--disable-dev-shm-usage"); o.add_argument("--window-size=1366,900")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=o)

def scrape_linkedin(query: str, location: str, pages: int = 1) -> List[Dict]:
    base = "https://www.linkedin.com/jobs/search/?"
    results: List[Dict] = []
    d = _driver()
    delay = settings.SCRAPER_DELAY_MS / 1000.0
    try:
        for p in range(pages):
            params = {"keywords": query, "location": location or "", "start": p * 25}
            url = base + urlencode(params)
            d.get(url); time.sleep(delay)

            soup = BeautifulSoup(d.page_source, "html.parser")
            cards = soup.select("ul.jobs-search__results-list li") or soup.select("div.base-card")
            if not cards: break

            for c in cards:
                t = c.select_one("h3") or c.select_one(".base-search-card__title")
                comp = c.select_one("h4") or c.select_one(".base-search-card__subtitle")
                loc = c.select_one(".job-search-card__location")
                href = (c.select_one("a.base-card__full-link") or c.select_one("a")).get("href", "") if c.select_one("a") else ""
                title = t.get_text(strip=True) if t else "Job"
                company = comp.get_text(strip=True) if comp else None
                location_txt = loc.get_text(" ", strip=True) if loc else location or None

                hk = hashlib.sha256(f"linkedin|{href}|{title}|{company or ''}".encode()).hexdigest()
                results.append({
                    "source":"linkedin","external_id":None,"title":title,"company":company,"location":location_txt,
                    "salary_min":None,"salary_max":None,"currency":None,"salary_raw":None,"post_date":None,
                    "description":None, "url":href, "is_remote": bool(location_txt and "remote" in location_txt.lower()),
                    "hash_key": hk,
                })
    finally:
        d.quit()
    return results
