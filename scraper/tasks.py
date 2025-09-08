from celery import shared_task
from django.utils import timezone
from jobs.models import ScrapeRun
from jobs.services.ingest import upsert_jobs
from django.conf import settings
from .selectors.indeed import scrape_indeed

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def scrape_source_task(self, source: str, query: str, location: str, pages: int = None):
    run = ScrapeRun.objects.create(source=source, query=f"{query} @ {location}", status="PENDING")
    try:
        if source == "indeed":
            items = scrape_indeed(query, location, pages or settings.SCRAPER_MAX_PAGES)
        else:
            items = []  # placeholders for other sources
        run.total_found = len(items)
        saved, dup = upsert_jobs(items)
        run.total_saved = saved
        run.status = "SUCCESS"
    except Exception as e:
        run.status = "FAIL"
        run.error_log = str(e)[:4000]
        raise
    finally:
        run.finished_at = timezone.now()
        run.save()
