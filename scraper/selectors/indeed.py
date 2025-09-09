# scraper/selectors/indeed.py
import os
import time
import random
import hashlib
from urllib.parse import urlencode, quote_plus, urljoin

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

try:
    from django.conf import settings
except Exception:  # fallback if not in Django
    class _S:
        SELENIUM_HEADLESS = False
        SCRAPER_DELAY_MS = 1200
    settings = _S()

INDEED_BASE = os.getenv("INDEED_BASE", "https://ng.indeed.com")


# ---------------------------
# Driver (attach to Chrome)
# ---------------------------

def _driver():
    opts = Options()
    # attach to running Chrome started with --remote-debugging-port=9222
    opts.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    opts.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)


# ---------------------------
# Helpers
# ---------------------------

def _abs(href: str) -> str:
    if not href:
        return ""
    if href.startswith("http"):
        return href
    return urljoin(INDEED_BASE, href)


def _desktop_search_url(q: str, l: str, page: int) -> str:
    params = {"hl": "en"}
    if q:
        params["q"] = q
    if l:
        params["l"] = l
    if page:
        params["start"] = page * 10
    return f"{INDEED_BASE}/jobs?{urlencode(params)}"


def _mobile_url(q: str, l: str, page: int) -> str:
    params = {}
    if q:
        params["q"] = q
    if l:
        params["l"] = l
    if page:
        params["start"] = page * 10
    return f"{INDEED_BASE}/m/jobs" + ("?" + urlencode(params) if params else "")


def _safe_text(el):
    return el.text.strip() if el is not None else None


def _dismiss_overlays(d):
    for sel in (
        "#onetrust-accept-btn-handler",
        "[data-testid='cookie-accept-button']",
        "button[aria-label='Accept All']",
        "#onetrust-banner-sdk button",
    ):
        try:
            btn = WebDriverWait(d, 3).until(EC.element_to_be_clickable((By.CSS_SELECTOR, sel)))
            btn.click()
            time.sleep(0.3)
            break
        except Exception:
            pass


def _captcha_guard(d, where: str = "", wait_seconds: int = 120):
    """If a CAPTCHA wall is present, give you time to solve it in the attached Chrome."""
    def has_captcha() -> bool:
        html = d.page_source.lower()
        if "recaptcha" in html or "captcha" in html:
            return True
        # common iframe/widget
        return bool(d.find_elements(By.CSS_SELECTOR, 'iframe[src*="recaptcha"], div#g-recaptcha'))
    if has_captcha():
        print(f"[indeed] CAPTCHA at {where or d.current_url} — solve it in the attached Chrome window…")
        for _ in range(wait_seconds):
            time.sleep(1)
            if not has_captcha():
                print("[indeed] CAPTCHA cleared.")
                return
        raise RuntimeError(f"CAPTCHA still present after waiting at {where or d.current_url}")


def _wait_for_results(d, timeout=25):
    _dismiss_overlays(d)
    _captcha_guard(d, "results wait (before)")
    WebDriverWait(d, timeout).until(
        EC.any_of(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='resultsList'] [data-testid='jobCard']")),
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.cardOutline.tapItem")),
            EC.presence_of_element_located((By.CSS_SELECTOR, "a.tapItem")),
            EC.presence_of_element_located((By.CSS_SELECTOR, ".jobsearch-NoResult-message, #no_results")),
        )
    )
    _captcha_guard(d, "results wait (after)")


# ---------------------------
# Parsing
# ---------------------------

def _parse_card(card_html: str):
    c = BeautifulSoup(card_html, "html.parser")
    link = c.select_one("a.jcs-JobTitle") or c.select_one("a.tapItem") or c.select_one("a.jobLink")
    href = link.get("href") if link else None
    job_url = _abs(href)

    title_el = c.select_one("h2.jobTitle span[title]") or c.select_one("h2.jobTitle span")
    title = title_el.get_text(strip=True) if title_el else None
    if not title and link:
        title = link.get("aria-label") or link.get("title")

    company = _safe_text(c.select_one("span.companyName") or c.select_one(".company"))
    location = _safe_text(c.select_one("div.companyLocation") or c.select_one(".location"))
    salary = _safe_text(c.select_one(".salary-snippet, .salary-snippet-container"))

    hk = hashlib.sha256(f"indeed|{job_url}|{title or ''}|{company or ''}".encode()).hexdigest()
    return {
        "source": "indeed",
        "title": title,
        "company": company,
        "location": location,
        "salary_raw": salary,
        "description": None,
        "url": job_url,
        "is_remote": "remote" in (location or "").lower(),
        "hash_key": hk,
    }


# ---------------------------
# Scraper (list-only parse)
# ---------------------------

def scrape_indeed(query: str = "", location: str = "Nigeria", pages: int = 1):
    pages = max(1, int(pages or 1))
    items = []

    base_delay = max(1.0, int(getattr(settings, "SCRAPER_DELAY_MS", 1200)) / 1000.0)

    d = _driver()
    try:
        for p in range(pages):
            url = _desktop_search_url(query.strip(), location.strip() or "Nigeria", p)
            d.get(url)
            _wait_for_results(d, timeout=25)
            time.sleep(base_delay + random.uniform(0.3, 0.7))

            # nudge lazy loading
            d.execute_script("window.scrollBy(0, 600);"); time.sleep(0.2)
            d.execute_script("window.scrollBy(0, 1200);"); time.sleep(0.2)

            cards = d.find_elements(
                By.CSS_SELECTOR,
                "[data-testid='resultsList'] [data-testid='jobCard'], div.cardOutline.tapItem, a.tapItem"
            )

            if not cards:
                # Mobile fallback
                d.get(_mobile_url(query, location, p))
                _captcha_guard(d, "mobile page")
                time.sleep(base_delay)
                mobile_cards = d.find_elements(By.CSS_SELECTOR, "a.jobLink, li.job a")
                for mc in mobile_cards:
                    items.append(_parse_card(mc.get_attribute("outerHTML")))
                continue

            for card in cards:
                items.append(_parse_card(card.get_attribute("outerHTML")))
                time.sleep(random.uniform(0.05, 0.15))

    finally:
        d.quit()

    return items
