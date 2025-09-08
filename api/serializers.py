from rest_framework import serializers
from jobs.models import Job

class JobSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = [
            "id","source","external_id","title","company","location",
            "salary_min","salary_max","currency","salary_raw",
            "post_date","description","url","is_remote","created_at"
        ]
