from django.core.management.base import BaseCommand, CommandError
from scraper.tasks import run_scrape

class Command(BaseCommand):
    help = "Scrape jobs synchronously (no Celery)."

    def add_arguments(self, parser):
        parser.add_argument("--source", required=True,
                            choices=["indeed", "glassdoor", "linkedin", "all"])
        parser.add_argument("--q", default="")
        parser.add_argument("--loc", default="")
        parser.add_argument("--pages", type=int, default=1)

    def handle(self, *args, **opts):
        # ensure pages is at least 1
        pages = max(1, int(opts.get("pages") or 1))

        sources = [opts["source"]]
        if opts["source"] == "all":
            sources = ["indeed", "glassdoor", "linkedin"]

        totals_found = 0
        totals_saved = 0

        for src in sources:
            run = run_scrape(src, opts["q"], opts["loc"], pages)

            msg = f"[{src}] status={run.status} found={run.total_found} saved={run.total_saved}"
            if run.status == "FAIL":
                self.stderr.write(self.style.ERROR(msg))
                if getattr(run, "error_log", None):
                    self.stderr.write(run.error_log)
                # exit with non-zero so CI/scripts can detect failure
                raise CommandError(f"Scrape failed for {src}")
            else:
                self.stdout.write(self.style.SUCCESS(msg))
                totals_found += int(run.total_found or 0)
                totals_saved += int(run.total_saved or 0)

        # overall summary
        if len(sources) > 1:
            self.stdout.write(self.style.SUCCESS(
                f"All sources completed | total_found={totals_found} total_saved={totals_saved}"
            ))
