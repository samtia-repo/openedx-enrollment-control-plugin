from django.conf import settings
from django.db import models


class ManagedCourseRun(models.Model):
    course_id = models.CharField(max_length=255, unique=True, db_index=True)
    enabled = models.BooleanField(default=True)
    allow_staff_override = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.course_id


class EnrollmentRequest(models.Model):
    idempotency_key = models.CharField(max_length=255, unique=True)
    registration_id = models.CharField(max_length=255, db_index=True)
    course_id = models.CharField(max_length=255)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    action = models.CharField(max_length=20)
    status = models.CharField(max_length=20)
    error = models.TextField(blank=True)
    attempt_count = models.PositiveIntegerField(default=0)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    correlation_id = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class EnrollmentOverrideEvent(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    course_id = models.CharField(max_length=255, db_index=True)
    request_path = models.CharField(max_length=500)
    correlation_id = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user_id}:{self.course_id}:{self.created_at}"
