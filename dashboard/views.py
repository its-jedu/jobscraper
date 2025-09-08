from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404
from jobs.models import Job, ScrapeRun

def home(request):
    q = request.GET.get("q","")
    location = request.GET.get("location","")
    source = request.GET.get("source","")
    remote = request.GET.get("remote","")

    jobs = Job.objects.all().order_by("-created_at")
    if q:
        jobs = jobs.filter(title__icontains=q) | jobs.filter(company__icontains=q)
    if location:
        jobs = jobs.filter(location__icontains=location)
    if source:
        jobs = jobs.filter(source=source)
    if remote == "true":
        jobs = jobs.filter(is_remote=True)

    paginator = Paginator(jobs, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    last_run = ScrapeRun.objects.order_by("-started_at").first()

    return render(request, "dashboard/jobs_list.html", {
        "page_obj": page_obj,
        "q": q, "location": location, "source": source, "remote": remote,
        "last_run": last_run,
    })

def job_detail(request, pk: int):
    job = get_object_or_404(Job, pk=pk)
    return render(request, "dashboard/jobs_detail.html", {"job": job})
