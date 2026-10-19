from django.contrib import admin
from .models import EnrollmentRequest, ManagedCourseRun


@admin.register(ManagedCourseRun)
class ManagedCourseRunAdmin(admin.ModelAdmin):
    list_display = ("course_id", "enabled", "allow_staff_override", "updated_at")
    search_fields = ("course_id",)
    list_filter = ("enabled",)


@admin.register(EnrollmentRequest)
class EnrollmentRequestAdmin(admin.ModelAdmin):
    list_display = ("registration_id", "course_id", "user", "action", "status", "created_at")
    search_fields = ("registration_id", "course_id", "user__username", "user__email", "idempotency_key")
    readonly_fields = tuple(field.name for field in EnrollmentRequest._meta.fields)
