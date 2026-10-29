from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView
from opaque_keys.edx.keys import CourseKey
from common.djangoapps.student.models import CourseEnrollment

from .authentication import ServiceTokenAuthentication
from .models import EnrollmentRequest, ManagedCourseRun


class EnrollmentView(APIView):
    authentication_classes = [ServiceTokenAuthentication]
    permission_classes = []

    def post(self, request):
        key = request.headers.get("Idempotency-Key", "").strip()
        if not key:
            return Response({"error": {"code": "idempotency_key_required", "message": "Idempotency-Key is required."}}, status=400)
        course_id = str(request.data.get("course_id", "")).strip()
        registration_id = str(request.data.get("registration_id", "")).strip()
        correlation_id = str(request.headers.get("X-Correlation-ID", "")).strip()[:128]
        action = str(request.data.get("action", "enroll")).lower()
        user_id = str(request.data.get("user_id", "")).strip()
        email = str(request.data.get("email", "")).strip().lower()

        if (
            not course_id
            or not registration_id
            or not user_id
            or not email
            or action not in {"enroll", "unenroll"}
        ):
            return Response(
                {
                    "error": {
                        "code": "invalid_request",
                        "message": (
                            "course_id, registration_id, user_id, email "
                            "and a valid action are required."
                        ),
                    }
                },
                status=400,
            )
        if not ManagedCourseRun.objects.filter(course_id=course_id, enabled=True).exists():
            return Response({"error": {"code": "course_not_managed", "message": "Course run is not managed by KKUx registration."}}, status=409)
        User = get_user_model()

        user = None

        # Some Open edX JWTs use the numeric Django user ID as `sub`.
        if user_id.isdigit():
            user = User.objects.filter(
                id=int(user_id),
                email__iexact=email,
                is_active=True,
            ).first()

        # KKUx JWT `sub` is currently an opaque identifier, so resolve the
        # authenticated learner using the verified JWT email sent by the backend.
        if user is None:
            matching_users = User.objects.filter(
                email__iexact=email,
                is_active=True,
            )

            if matching_users.count() > 1:
                return Response(
                    {
                        "error": {
                            "code": "learner_identity_ambiguous",
                            "message": "Multiple active Open edX users use this email.",
                        }
                    },
                    status=409,
                )

            user = matching_users.first()

        if user is None:
            return Response(
                {
                    "error": {
                        "code": "user_not_found",
                        "message": "The active Open edX learner was not found.",
                    }
                },
                status=404,
            )
        try:
            with transaction.atomic():
                record, created = EnrollmentRequest.objects.get_or_create(
                    idempotency_key=key,
                    defaults={
                        "registration_id": registration_id,
                        "course_id": course_id,
                        "user": user,
                        "action": action,
                        "status": "PROCESSING",
                        "attempt_count": 1,
                        "last_attempt_at": timezone.now(),
                        "correlation_id": correlation_id,
                    },
                )
                if not created:
                    record = EnrollmentRequest.objects.select_for_update().get(pk=record.pk)
                    if (record.registration_id, record.course_id, record.user_id, record.action) != (registration_id, course_id, user.id, action):
                        return Response({"error": {"code": "idempotency_key_conflict", "message": "This idempotency key was already used for a different operation."}}, status=409)
                    if record.status == "SUCCEEDED":
                        return Response(self._payload(record), status=200)
                    if record.status == "PROCESSING":
                        timeout = max(30, int(getattr(settings, "KKUX_ENROLLMENT_PROCESSING_TIMEOUT_SECONDS", 900)))
                        last_attempt = record.last_attempt_at
                        if last_attempt and (timezone.now() - last_attempt).total_seconds() < timeout:
                            return Response({"error": {"code": "enrollment_in_progress", "message": "An operation with this idempotency key is already processing."}, "status": "PROCESSING"}, status=409)
                    record.status = "PROCESSING"
                    record.error = ""
                    record.attempt_count += 1
                    record.last_attempt_at = timezone.now()
                    record.correlation_id = correlation_id
                    record.save(update_fields=["status", "error", "attempt_count", "last_attempt_at", "correlation_id", "updated_at"])
        except IntegrityError:
            record = EnrollmentRequest.objects.filter(idempotency_key=key).first()
            if record and record.status == "SUCCEEDED":
                return Response(self._payload(record), status=200)
            return Response({"error": {"code": "enrollment_in_progress", "message": "An operation with this idempotency key is already processing."}, "status": "PROCESSING"}, status=409)
        try:
            course_key = CourseKey.from_string(course_id)
            mode = getattr(settings, "KKUX_ENROLLMENT_MODE", "audit")
            if action == "enroll":
                CourseEnrollment.enroll(user, course_key, mode=mode)
            else:
                CourseEnrollment.unenroll(user, course_key)
            record.status = "SUCCEEDED"
            record.save(update_fields=["status", "updated_at"])
            return Response(self._payload(record), status=200)
        except Exception as exc:
            record.status = "FAILED"
            record.error = str(exc)
            record.save(update_fields=["status", "error", "updated_at"])
            return Response({"error": {"code": "enrollment_failed", "message": "Open edX enrollment operation failed.", "details": {"request_id": record.id}}}, status=502)

    @staticmethod
    def _payload(record):
        return {"enrollment_id": record.id, "registration_id": record.registration_id, "course_id": record.course_id, "user_id": record.user_id, "action": record.action, "status": record.status, "attempt_count": record.attempt_count, "last_attempt_at": record.last_attempt_at, "correlation_id": record.correlation_id}


class ManagedCourseView(APIView):
    authentication_classes = [ServiceTokenAuthentication]
    permission_classes = []

    def put(self, request, course_id):
        course, _ = ManagedCourseRun.objects.update_or_create(course_id=course_id, defaults={"enabled": bool(request.data.get("enabled", True)), "allow_staff_override": bool(request.data.get("allow_staff_override", True))})
        return Response({"course_id": course.course_id, "enabled": course.enabled, "allow_staff_override": course.allow_staff_override})
