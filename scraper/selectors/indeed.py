import time, hashlib, re
from typing import List, Dict
from urllib.parse import urlencode
from bs4 import BeautifulSoup
from django.conf import settings

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

SALARY_RE = re.compile(r"([\$€£₦])?[\s]*([\d,]+)")

def _headless_driver():
    opts = Options()
    if settings.SELENIUM_HEADLESS:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1366,900")
    return webdriver.Chrome(ChromeDriverManager().install(), options=opts)

def parse_salary(s: str):
    if not s: return None, None, None
    m = SALARY_RE.findall(s)
    if not m: return None, None, None
    currency = m[0][0] or None
    nums = [int(x[1].replace(",", "")) for x in m]
    if len(nums) == 1: return nums[0], None, currency
    return min(nums), max(nums), currency

def scrape_indeed(query: str, location: str, pages: int = None) -> List[Dict]:
    pages = pages or settings.SCRAPER_MAX_PAGES
    delay = settings.SCRAPER_DELAY_MS / 1000.0

    base = "https://www.indeed.com/jobs?"
    results: List[Dict] = []
    driver = _headless_driver()
    try:
        for page in range(pages):
            params = {"q": query, "l": location, "start": page * 10}
            url = base + urlencode(params)
            driver.get(url)
            time.sleep(delay)

            soup = BeautifulSoup(driver.page_source, "html.parser")
            cards = soup.select("div.job_seen_beacon") or soup.select("li[class*=result]")
            if not cards: break

            for c in cards:
                title_el = c.select_one("h2 a")
                company_el = c.select_one("span.companyName")
                loc_el = c.select_one("div.companyLocation")
                salary_el = c.select_one("div.metadata.salary-snippet-container, span.salary-snippet")
                desc_el = c.select_one("div.job-snippet")

                title = (title_el.get_text(strip=True) if title_el else None) or "Job"
                url_rel = title_el["href"] if title_el and title_el.has_attr("href") else None
                job_url = ("https://www.indeed.com" + url_rel) if url_rel and url_rel.startswith("/") else url_rel or ""
                company = company_el.get_text(strip=True) if company_el else None
                location_txt = loc_el.get_text(" ", strip=True) if loc_el else None
                salary_raw = salary_el.get_text(" ", strip=True) if salary_el else None
                desc = desc_el.get_text(" ", strip=True) if desc_el else None

                smin, smax, curr = parse_salary(salary_raw or "")
                basis = f"indeed|{job_url}|{title}|{company or ''}"
                hash_key = hashlib.sha256(basis.encode("utf-8")).hexdigest()

                results.append({
                    "source":"indeed",
                    "external_id": None,
                    "title": title,
                    "company": company,
                    "location": location_txt,
                    "salary_min": smin, "salary_max": smax, "currency": curr, "salary_raw": salary_raw,
                    "post_date": None,
                    "description": desc,
                    "url": job_url,
                    "is_remote": bool(location_txt and "remote" in location_txt.lower()),
                    "hash_key": hash_key,
                })
    finally:
        driver.quit()
    return results
