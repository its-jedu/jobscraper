from django.core.management.base import BaseCommand
from scraper.tasks import run_scrape

class Command(BaseCommand):
    help = "Scrape jobs synchronously (no Celery)."

    def add_arguments(self, parser):
        parser.add_argument("--source", required=True, choices=["indeed","glassdoor","linkedin","all"])
        parser.add_argument("--q", default="")
        parser.add_argument("--loc", default="")
        parser.add_argument("--pages", type=int, default=1)

    def handle(self, *args, **opts):
        run = run_scrape(opts["source"], opts["q"], opts["loc"], opts["pages"])
        self.stdout.write(self.style.SUCCESS(
            f"Scrape finished: {run.status} | found={run.total_found} saved={run.total_saved}"
        ))
        if run.status == "FAIL":
            self.stdout.write(self.style.ERROR(run.error_log or ""))
