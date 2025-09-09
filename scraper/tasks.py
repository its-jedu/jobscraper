import traceback
from django.utils import timezone
from django.conf import settings

from jobs.models import ScrapeRun
from jobs.services.ingest import upsert_jobs

from scraper.selectors.indeed import scrape_indeed
from scraper.selectors.glassdoor import scrape_glassdoor
from scraper.selectors.linkedin import scrape_linkedin


SCRAPERS = {
    "indeed": scrape_indeed,
    "glassdoor": scrape_glassdoor,
    "linkedin": scrape_linkedin,
}


def run_scrape(source: str, query: str, location: str, pages: int | None = None) -> ScrapeRun:
    """
    Run a scrape for a given source.
    Creates a ScrapeRun row, executes the scraper, and stores results.

    :param source: "indeed", "glassdoor", "linkedin", or "all"
    :param query: search query string
    :param location: job location string
    :param pages: number of pages to scrape (defaults to SCRAPER_MAX_PAGES)
    """
    pages = pages or getattr(settings, "SCRAPER_MAX_PAGES", 2)

    run = ScrapeRun.objects.create(
        source=source,
        query=f"{query} @ {location}",
        status="PENDING",
    )

    try:
        items = []

        if source == "all":
            for name, fn in SCRAPERS.items():
                try:
                    sub_items = fn(query, location or "", pages)
                    items.extend(sub_items)
                    print(f"[{name}] scraped {len(sub_items)} jobs")
                except RuntimeError as e:
                    # special handling for CAPTCHA / block detection
                    msg = f"[{name}] BLOCKED: {e}"
                    print(msg)
                    continue
                except Exception as e:
                    # log per-source failure but continue others
                    msg = f"[{name}] ERROR: {e}"
                    print(msg)
                    continue
        else:
            fn = SCRAPERS.get(source)
            if not fn:
                raise ValueError(f"Unknown source: {source}")
            items = fn(query, location or "", pages)

        # Save results
        run.total_found = len(items)
        saved, _dups = upsert_jobs(items)
        run.total_saved = saved

        if not items:
            run.status = "EMPTY"  # ran successfully but found nothing
        else:
            run.status = "SUCCESS"

        return run

    except RuntimeError as e:
        # Handle CAPTCHA / blocks distinctly
        run.status = "BLOCKED"
        run.error_log = str(e)[:4000]
        raise

    except Exception as e:
        # Generic failure
        run.status = "FAIL"
        run.error_log = "".join(
            traceback.format_exception_only(type(e), e)
        )[:4000]
        raise

    finally:
        run.finished_at = timezone.now()
        run.save()
