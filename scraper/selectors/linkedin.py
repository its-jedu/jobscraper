# scraper/selectors/linkedin.py
import re, time, random, hashlib
from typing import List, Dict, Optional
from urllib.parse import urlencode, urljoin

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

try:
    from django.conf import settings
except Exception:
    class _S:
        SELENIUM_HEADLESS = False
        SCRAPER_DELAY_MS = 1200
    settings = _S()

LI_BASE = "https://www.linkedin.com"
SEARCH_BASE = f"{LI_BASE}/jobs/search/"

# ---------------------------
# Driver (attach to Chrome at 9222)
# ---------------------------
def _driver():
    opts = Options()
    opts.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    opts.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)

# ---------------------------
# Helpers
# ---------------------------
def _dismiss_overlays(d):
    for sel in (
        "button[aria-label='Accept cookies']",
        "button[data-control-name='ga-cookie-consent-accept']",
        "button[aria-label='Dismiss']",
        "button[aria-label='Close']",
    ):
        try:
            WebDriverWait(d, 3).until(EC.element_to_be_clickable((By.CSS_SELECTOR, sel))).click()
            time.sleep(0.2)
        except Exception:
            pass

def _captcha_guard(d, where: str = "", wait_seconds: int = 90):
    def has_wall() -> bool:
        html = d.page_source.lower()
        return ("captcha" in html or "verify" in html) and "jobs-search" not in html
    if has_wall():
        print(f"[linkedin] CAPTCHA/verify at {where or d.current_url} — solve it in Chrome…")
        for _ in range(wait_seconds):
            time.sleep(1)
            if not has_wall():
                print("[linkedin] Wall cleared.")
                return
        raise RuntimeError("LinkedIn verification not cleared")

def _wait_results(d, timeout=25):
    _dismiss_overlays(d)
    _captcha_guard(d, "before results")
    WebDriverWait(d, timeout).until(
        EC.any_of(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.job-card-container[data-job-id]")),
            EC.presence_of_element_located((By.CSS_SELECTOR, "ul.jobs-search__results-list li")),
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.base-card")),
        )
    )
    _captcha_guard(d, "after results")

def _abs(href: str) -> str:
    if not href:
        return ""
    return href if href.startswith("http") else urljoin(LI_BASE, href)

# ---------------------------
# Parsing (list card)
# ---------------------------
def _parse_card_basic(html: str) -> Optional[Dict]:
    s = BeautifulSoup(html, "html.parser")

    # Prefer explicit job id
    root = s.select_one("div.job-card-container[data-job-id]")
    external_id = root.get("data-job-id").strip() if root else None

    # Fallback from link
    a = (s.select_one("a.job-card-container__link")
         or s.select_one("a.base-card__full-link")
         or s.select_one("a[href*='/jobs/view/']")
         or s.select_one("a"))
    if not external_id and a:
        href = (a.get("href", "") or "").split("?")[0].strip()
        m = re.search(r"/jobs/view/(\d+)", href)
        external_id = m.group(1) if m else None
    if not external_id:
        return None

    url = f"https://www.linkedin.com/jobs/view/{external_id}/"

    # ---- robust title extraction on the CARD ----
    title_el = (s.select_one(".job-card-list__title")
                or s.select_one(".job-card-container__title")
                or s.select_one(".base-search-card__title")
                or s.select_one("h3"))
    # Try multiple fallbacks, including anchor attributes
    title = None
    if title_el:
        title = title_el.get_text(strip=True)
    if (not title) and a:
        title = (a.get_text(strip=True) or a.get("aria-label") or a.get("title"))
    if not title:
        # sometimes the inner span has the text
        inner = s.select_one(".job-card-list__title span, .job-card-container__title span")
        if inner:
            title = inner.get_text(strip=True)

    comp_el = (s.select_one(".job-card-container__company-name")
               or s.select_one(".base-search-card__subtitle")
               or s.select_one("h4"))
    loc_el  = (s.select_one(".job-card-container__metadata-item")
               or s.select_one(".job-search-card__location")
               or s.select_one("[data-test-location]"))

    company = comp_el.get_text(strip=True) if comp_el else None
    location = loc_el.get_text(" ", strip=True) if loc_el else None

    # last resort so it still saves (but with better chance above)
    if not title:
        title = f"LinkedIn Job {external_id}"

    hk = hashlib.sha256(f"linkedin|{external_id}".encode()).hexdigest()

    return {
        "source": "linkedin",
        "external_id": external_id,
        "title": title,
        "company": company,
        "location": location,
        "salary_min": None,
        "salary_max": None,
        "currency": None,
        "salary_raw": None,
        "post_date": None,
        "description": None,
        "url": url,
        "is_remote": "remote" in (location or "").lower(),
        "hash_key": hk,
    }

# ---------------------------
# Enrichment (right pane)
# ---------------------------
def _enrich_from_pane(d, current: Dict) -> Dict:
    """Pull true title/company/location/description from the right pane after click."""
    try:
        WebDriverWait(d, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, ".jobs-unified-top-card__job-title, .jobs-unified-top-card__company-name")
            )
        )
    except Exception:
        return current

    soup = BeautifulSoup(d.page_source, "html.parser")

    title_el = soup.select_one(".jobs-unified-top-card__job-title")
    if not title_el:
        # older/newer variants
        title_el = soup.select_one("h1.top-card-layout__title, h1")

    comp_el = (soup.select_one(".jobs-unified-top-card__company-name a")
               or soup.select_one(".jobs-unified-top-card__company-name"))
    if not comp_el:
        comp_el = soup.select_one(".topcard__org-name-link, .topcard__flavor")

    loc_el = (soup.select_one(".jobs-unified-top-card__primary-description")
              or soup.select_one(".topcard__flavor--bullet"))

    desc_el = soup.select_one("#job-details, .jobs-description__content, #job-details-container")

    title = title_el.get_text(strip=True) if title_el else None
    company = comp_el.get_text(strip=True) if comp_el else None

    location = None
    if loc_el:
        raw = loc_el.get_text(" ", strip=True)
        parts = [p.strip() for p in raw.split("·")]
        location = parts[-1] if parts else raw

    description = desc_el.get_text("\n", strip=True) if desc_el else None

    if title: current["title"] = title
    if company: current["company"] = company
    if location: current["location"] = location
    if description: current["description"] = description
    current["is_remote"] = "remote" in (current.get("location") or "").lower()
    return current

# ---------------------------
# URL composer (3 days)
# ---------------------------
def _build_search_url(q: str, loc: str, start: int) -> str:
    # Last 3 days filter: f_TPR=r259200
    params = {
        "keywords": q or "",
        "location": loc or "",
        "start": max(0, start),
        "refresh": "true",
        "f_TPR": "r259200",
    }
    return f"{SEARCH_BASE}?{urlencode(params)}"

# ---------------------------
# Scraper (click & enrich)
# ---------------------------
def scrape_linkedin(query: str, location: str, pages: int = 1) -> List[Dict]:
    results: List[Dict] = []
    delay = max(1.0, int(getattr(settings, "SCRAPER_DELAY_MS", 1200)) / 1000.0)

    d = _driver()
    try:
        for p in range(max(1, int(pages or 1))):
            url = _build_search_url(query, location, start=p * 25)
            d.get(url)
            _wait_results(d, timeout=25)
            time.sleep(delay + random.uniform(0.3, 0.8))

            # Lazy-load nudge
            for _ in range(3):
                d.execute_script("window.scrollBy(0, 900);")
                time.sleep(0.25)

            cards = d.find_elements(
                By.CSS_SELECTOR,
                "div.job-card-container[data-job-id], ul.jobs-search__results-list li, div.base-card"
            )
            print(f"[linkedin] raw cards on page {p}: {len(cards)}")
            if not cards:
                break

            for idx, c in enumerate(cards):
                # parse basic info from list card HTML
                base = _parse_card_basic(c.get_attribute("outerHTML"))
                if not base:
                    continue

                # try clicking to load the right pane, then enrich
                try:
                    d.execute_script("arguments[0].scrollIntoView({block:'center'});", c)
                    time.sleep(0.15)
                    try:
                        c.click()
                    except Exception:
                        d.execute_script("arguments[0].click();", c)
                    time.sleep(0.4)
                    base = _enrich_from_pane(d, base)
                except Exception:
                    pass

                results.append(base)
                time.sleep(random.uniform(0.05, 0.12))
    finally:
        d.quit()

    return results
