import json
import re
from urllib.parse import unquote
from django.conf import settings
from django.http import JsonResponse
from .models import EnrollmentOverrideEvent, ManagedCourseRun


class ManagedEnrollmentMiddleware:
    """Reject learner self-enrolment for explicitly managed course runs.

    This is an enforcement layer for common LMS mutation routes. The trusted
    plugin API is excluded. Staff override remains configurable per course.
    """
    MUTATION_PATHS = (
        re.compile(r"^/change_enrollment/?$"),
        re.compile(r"^/course_modes/choose(?:/[^/]+){1,3}/?$"),
        re.compile(r"^/api/enrollment/v1/(?:enrollment(?:/.*)?|enrollments/?|unenroll/?)$"),
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == "POST" and self._is_enrollment_mutation(request.path):
            course_id = self._course_id(request)
            try:
                managed = ManagedCourseRun.objects.filter(course_id=course_id, enabled=True).first() if course_id else None
            except Exception:
                if getattr(settings, "KKUX_ENROLLMENT_FAIL_CLOSED", True):
                    return JsonResponse({"error": {"code": "enrollment_control_unavailable", "message": "Enrollment is temporarily unavailable."}}, status=503)
                return self.get_response(request)
            staff_override = bool(managed and managed.allow_staff_override and getattr(request.user, "is_staff", False))
            if staff_override:
                try:
                    EnrollmentOverrideEvent.objects.create(user=request.user, course_id=managed.course_id, request_path=request.path[:500], correlation_id=request.headers.get("X-Correlation-ID", "")[:128])
                except Exception:
                    if getattr(settings, "KKUX_ENROLLMENT_FAIL_CLOSED", True):
                        return JsonResponse({"error": {"code": "enrollment_control_unavailable", "message": "Enrollment is temporarily unavailable."}}, status=503)
            if managed and not staff_override:
                return JsonResponse({"error": {"code": "managed_enrollment_required", "message": "Enrollment for this course is managed by the KKUx registration service."}}, status=403)
        return self.get_response(request)

    @classmethod
    def _is_enrollment_mutation(cls, path):
        if path.startswith("/api/kkux-registration/v1/"):
            return False
        return any(pattern.fullmatch(path) for pattern in cls.MUTATION_PATHS)

    @staticmethod
    def _course_id(request):
        value = request.POST.get("course_id") or request.GET.get("course_id")
        if value:
            return str(value)
        if request.content_type == "application/json":
            try:
                body = json.loads(request.body or b"{}")
                details = body.get("course_details") or {}
                return str(body.get("course_id") or details.get("course_id") or "")
            except (ValueError, TypeError):
                return ""
        course_path = re.match(r"^/course_modes/choose/(.+?)/?$", request.path)
        if course_path:
            return unquote(course_path.group(1)).replace("/", "+")
        api_path = re.match(r"^/api/enrollment/v1/enrollment/(.+?)/?$", request.path)
        if api_path:
            course = unquote(api_path.group(1))
            return course.rsplit(",", 1)[-1]
        return ""
