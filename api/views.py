from rest_framework import viewsets, filters
from rest_framework.pagination import PageNumberPagination
from jobs.models import Job
from .serializers import JobSerializer
from django.utils.timezone import now, timedelta

class JobPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 50

class JobViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Job.objects.all().order_by("-created_at")
    serializer_class = JobSerializer
    pagination_class = JobPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title","company","location","description"]
    ordering_fields = ["created_at","salary_min","salary_max","title","company"]

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.query_params
        if company := q.get("company"):
            qs = qs.filter(company__icontains=company)
        if location := q.get("location"):
            qs = qs.filter(location__icontains=location)
        if src := q.get("source"):
            qs = qs.filter(source=src)
        if q.get("remote") == "true":
            qs = qs.filter(is_remote=True)
        if min_sal := q.get("min_salary"):
            qs = qs.filter(salary_min__gte=min_sal)
        if max_age := q.get("max_age_days"):
            try:
                days = int(max_age)
                qs = qs.filter(created_at__gte=now() - timedelta(days=days))
            except: pass
        return qs
