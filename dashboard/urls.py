from django.urls import path
from .views import home, job_detail

urlpatterns = [
    path("", home, name="home"),
    path("jobs/<int:pk>/", job_detail, name="job_detail"),
]
