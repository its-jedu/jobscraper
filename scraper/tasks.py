from django.utils import timezone
from jobs.models import ScrapeRun
from jobs.services.ingest import upsert_jobs
from scraper.selectors.indeed import scrape_indeed
from scraper.selectors.glassdoor import scrape_glassdoor
from scraper.selectors.linkedin import scrape_linkedin
from django.conf import settings

SCRAPERS = {
    "indeed": scrape_indeed,
    "glassdoor": scrape_glassdoor,
    "linkedin": scrape_linkedin,
}

def run_scrape(source: str, query: str, location: str, pages: int | None = None) -> ScrapeRun:
    pages = pages or getattr(settings, "SCRAPER_MAX_PAGES", 2)
    run = ScrapeRun.objects.create(source=source, query=f"{query} @ {location}", status="PENDING")
    try:
        items = []
        if source == "all":
            for _, fn in SCRAPERS.items():
                items.extend(fn(query, location or "", pages))
        else:
            fn = SCRAPERS.get(source)
            if not fn:
                raise ValueError(f"Unknown source: {source}")
            items = fn(query, location or "", pages)

        run.total_found = len(items)
        saved, _dups = upsert_jobs(items)
        run.total_saved = saved
        run.status = "SUCCESS"
        return run
    except Exception as e:
        run.status = "FAIL"
        run.error_log = str(e)[:4000]
        raise
    finally:
        run.finished_at = timezone.now()
        run.save()
