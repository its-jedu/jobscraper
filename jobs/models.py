import hashlib
from django.conf import settings
from django.db import models

class Job(models.Model):
    SOURCE_CHOICES = (("indeed","Indeed"),("glassdoor","Glassdoor"),("linkedin","LinkedIn"))
    source = models.CharField(max_length=32, choices=SOURCE_CHOICES)
    external_id = models.CharField(max_length=255, blank=True, null=True)  # site-specific job id if available
    title = models.CharField(max_length=255)
    company = models.CharField(max_length=255, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)

    salary_min = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    salary_max = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    currency = models.CharField(max_length=8, blank=True, null=True)
    salary_raw = models.CharField(max_length=255, blank=True, null=True)

    post_date = models.DateTimeField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    url = models.URLField(max_length=1000)
    is_remote = models.BooleanField(default=False)

    hash_key = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.hash_key:
            basis = f"{self.source}|{self.external_id or ''}|{self.url or ''}|{self.title}|{self.company or ''}"
            self.hash_key = hashlib.sha256(basis.encode("utf-8")).hexdigest()
        return super().save(*args, **kwargs)

    def __str__(self): return f"{self.title} @ {self.company or 'N/A'} ({self.source})"

class ScrapeRun(models.Model):
    STATUS = (("PENDING","PENDING"),("SUCCESS","SUCCESS"),("FAIL","FAIL"),)
    source = models.CharField(max_length=32)
    query = models.CharField(max_length=255)
    status = models.CharField(max_length=16, choices=STATUS, default="PENDING")
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(blank=True, null=True)
    total_found = models.PositiveIntegerField(default=0)
    total_saved = models.PositiveIntegerField(default=0)
    error_log = models.TextField(blank=True, null=True)

    def __str__(self): return f"{self.source} {self.query} [{self.status}]"

class SavedJob(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="saves")
    is_favorite = models.BooleanField(default=False)
    note = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user","job")
