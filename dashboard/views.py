from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from jobs.models import Job, ScrapeRun
from jobs.services.ingest import upsert_jobs
from scraper.selectors.indeed import scrape_indeed
from scraper.selectors.glassdoor import scrape_glassdoor
from scraper.selectors.linkedin import scrape_linkedin
from django.contrib import messages

SCRAPE_MAP = {
    "indeed": scrape_indeed,
    "glassdoor": scrape_glassdoor,
    "linkedin": scrape_linkedin,
}

def home(request):
    q = request.GET.get("q","")
    location = request.GET.get("location","")
    action = request.GET.get("action")
    source = request.GET.get("source","")   # NEW
    pages = request.GET.get("pages","1")    # NEW

    # On-demand scrape
    if action == "scrape" and q and source:
        try:
            pages_i = max(1, min(5, int(pages)))
        except: pages_i = 1

        items = []
        if source == "all":
            for _, fn in SCRAPE_MAP.items():
                items.extend(fn(q, location or "", pages=pages_i))
        else:
            fn = SCRAPE_MAP.get(source)
            if fn:
                items = fn(q, location or "", pages=pages_i)
            else:
                messages.error(request, f"Unknown source: {source}")

        if items:
            upsert_jobs(items)
            messages.success(request, f"Fetched {len(items)} job(s) from {source}.")
        else:
            messages.warning(request, f"No results fetched from {source}.")
        return redirect(f"{reverse('home')}?q={q}&location={location}&source={source}")

    # Filter existing jobs
    jobs = Job.objects.all().order_by("-created_at")
    if q:
        jobs = jobs.filter(title__icontains=q) | jobs.filter(company__icontains=q)
    if location:
        jobs = jobs.filter(location__icontains=location)
    if source and source != "all":
        jobs = jobs.filter(source=source)

    paginator = Paginator(jobs, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    last_run = ScrapeRun.objects.order_by("-started_at").first()

    return render(request, "dashboard/jobs_list.html", {
        "page_obj": page_obj, "q": q, "location": location,
        "source": source, "pages": pages, "last_run": last_run,
    })


def job_detail(request, pk: int):
    job = get_object_or_404(Job, pk=pk)
    return render(request, "dashboard/jobs_detail.html", {"job": job})
