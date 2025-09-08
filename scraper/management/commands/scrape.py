from django.core.management.base import BaseCommand
from scraper.tasks import scrape_source_task

class Command(BaseCommand):
    help = "Run a scrape for a given source"

    def add_arguments(self, parser):
        parser.add_argument("--source", required=True, choices=["indeed","glassdoor","linkedin"])
        parser.add_argument("--q", required=True, help="query/role")
        parser.add_argument("--loc", required=True, help="location")
        parser.add_argument("--pages", type=int, default=1)

    def handle(self, *args, **opts):
        source = opts["source"]
        q = opts["q"]
        loc = opts["loc"]
        pages = opts["pages"]
        # Run synchronously for CLI UX (Celery is used in prod schedules)
        res = scrape_source_task.apply(kwargs={"source": source, "query": q, "location": loc, "pages": pages})
        self.stdout.write(self.style.SUCCESS(f"Scrape finished: {res.state}"))
