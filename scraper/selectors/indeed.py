import os, time, hashlib
from urllib.parse import urlencode
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from django.conf import settings

INDEED_BASE = os.getenv("INDEED_BASE", "https://ng.indeed.com")
SEARCH_URL = INDEED_BASE + "/jobs"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")

def _driver():
    opts = Options()
    if getattr(settings, "SELENIUM_HEADLESS", True):
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument(f"--user-agent={UA}")
    opts.add_argument("--lang=en-US,en;q=0.9")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)

def _results_url(query: str, location: str, page: int) -> str:
    # If both are empty, force a broad location so Indeed returns listings
    if not query and not location:
        location = "Nigeria"
    params = {}
    if query:
        params["q"] = query
    if location:
        params["l"] = location
    if page:
        params["start"] = page * 10
    # force English to avoid odd layouts
    params["hl"] = "en"
    return SEARCH_URL + ("?" + urlencode(params) if params else "")

def _maybe_accept_consent(d):
    # Common consent buttons
    selectors = [
        "#onetrust-accept-btn-handler",
        "button#onetrust-accept-btn-handler",
        "button[aria-label='Accept all']",
        "button:has(#onetrust-pc-btn-handler)",
    ]
    for sel in selectors:
        try:
            btn = WebDriverWait(d, 2).until(EC.element_to_be_clickable((By.CSS_SELECTOR, sel)))
            btn.click()
            time.sleep(0.5)
            return True
        except Exception:
            pass
    return False

def scrape_indeed(query: str | None = "", location: str | None = "", pages: int = 1):
    delay = max(0.8, int(getattr(settings, "SCRAPER_DELAY_MS", 1200)) / 1000.0)
    items = []
    d = _driver()
    try:
        for p in range(pages):
            url = _results_url((query or "").strip(), (location or "").strip(), p)
            print(f"[indeed] GET {url}")
            d.get(url)

            _maybe_accept_consent(d)

            # Wait up to 10s for job cards or a no-results element
            try:
                WebDriverWait(d, 10).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "a.tapItem")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='jobCard']")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".jobsearch-NoResult-message, #no_results"))
                    )
                )
            except Exception:
                pass

            time.sleep(delay)
            soup = BeautifulSoup(d.page_source, "html.parser")

            cards = soup.select("a.tapItem")
            if not cards:
                cards = soup.select("[data-testid='jobCard'], div.cardOutline")

            print(f"[indeed] page {p} cards={len(cards)}")
            if not cards and p == 0:
                # Likely still on a landing/region page; stop to avoid looping
                break

            for c in cards:
                # Title
                t = c.select_one("h2.jobTitle span[title]") or c.select_one("h2.jobTitle span")
                title = (t.get_text(strip=True) if t else None) or c.get("aria-label")

                # Company / Location / Salary
                comp = c.select_one("span.companyName")
                loc = c.select_one("div.companyLocation")
                sal = c.select_one("div.metadata.salary-snippet-container, div.salary-snippet-container, span.salary-snippet")

                company = comp.get_text(strip=True) if comp else None
                location_txt = loc.get_text(" ", strip=True) if loc else None
                salary_raw = sal.get_text(" ", strip=True) if sal else None

                # Link → ensure absolute
                href = c.get("href") or ""
                job_url = (INDEED_BASE + href) if href.startswith("/") else href

                hk = hashlib.sha256(f"indeed|{job_url}|{title or ''}|{company or ''}".encode()).hexdigest()
                items.append({
                    "source": "indeed",
                    "external_id": None,
                    "title": title,
                    "company": company,
                    "location": location_txt,
                    "salary_min": None,
                    "salary_max": None,
                    "currency": None,
                    "salary_raw": salary_raw,
                    "post_date": None,
                    "description": None,
                    "url": job_url,
                    "is_remote": bool((location_txt or "").lower().find("remote") >= 0),
                    "hash_key": hk,
                })
    finally:
        d.quit()

    return items
