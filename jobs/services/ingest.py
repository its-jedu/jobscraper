from typing import Iterable, Dict, Tuple
from django.db import transaction, IntegrityError
from jobs.models import Job

UPSERT_FIELDS = ["salary_min","salary_max","currency","salary_raw","description","post_date","is_remote"]

@transaction.atomic
def upsert_jobs(job_dicts: Iterable[Dict]) -> Tuple[int,int]:
    """Return (saved, duplicates) counts."""
    saved = dup = 0
    for data in job_dicts:
        try:
            obj, created = Job.objects.update_or_create(
                hash_key=data.get("hash_key"), defaults=data
            )
            saved += 1 if created else 0
            dup   += 0 if created else 1
        except IntegrityError:
            dup += 1
    return saved, dup
