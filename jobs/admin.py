from django.contrib import admin
from .models import Job, ScrapeRun, SavedJob

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ("title","company","source","location","created_at")
    list_filter = ("source","is_remote","company")
    search_fields = ("title","company","location","description","url")

@admin.register(ScrapeRun)
class ScrapeRunAdmin(admin.ModelAdmin):
    list_display = ("source","query","status","started_at","finished_at","total_found","total_saved")
    list_filter = ("source","status")
    search_fields = ("query",)

@admin.register(SavedJob)
class SavedJobAdmin(admin.ModelAdmin):
    list_display = ("user","job","is_favorite","created_at")
    list_filter = ("is_favorite",)
