from typing import Iterable, Dict, Tuple
from django.db import transaction, IntegrityError
from jobs.models import Job

ALLOWED_FIELDS = {
    "source", "external_id", "title", "company", "location",
    "salary_min", "salary_max", "currency", "salary_raw",
    "post_date", "description", "url", "is_remote", "hash_key",
}

@transaction.atomic
def upsert_jobs(job_dicts: Iterable[Dict]) -> Tuple[int, int]:
    """Return (saved, duplicates) counts."""
    saved = dup = 0
    for raw in job_dicts:
        data = {k: raw.get(k) for k in ALLOWED_FIELDS}
        if not data.get("hash_key") or not data.get("url") or not data.get("title"):
            # minimal validation
            dup += 1
            continue
        try:
            obj, created = Job.objects.update_or_create(
                hash_key=data["hash_key"],
                defaults=data,
            )
            if created:
                saved += 1
            else:
                dup += 1
        except IntegrityError:
            dup += 1
    return saved, dup
