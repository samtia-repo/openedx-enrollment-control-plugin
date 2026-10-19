import json
from types import SimpleNamespace
from unittest.mock import patch
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase as DjangoTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from kkux_enrollment_control.middleware import ManagedEnrollmentMiddleware
from kkux_enrollment_control.models import EnrollmentOverrideEvent, EnrollmentRequest, ManagedCourseRun


class EnrollmentApiTests(DjangoTestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="learner", email="learner@example.org")
        self.course_id = "course-v1:KKUx+TEST+2026"
        ManagedCourseRun.objects.create(course_id=self.course_id, enabled=True)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION="Bearer test-service-token")
        self.payload = {
            "user_id": self.user.pk,
            "email": "learner@example.org",
            "course_id": self.course_id,
            "registration_id": "registration-1",
            "action": "enroll",
        }

    @patch("kkux_enrollment_control.views.CourseEnrollment.enroll")
    def test_success_replay_does_not_repeat_lms_operation(self, enroll):
        headers = {"HTTP_IDEMPOTENCY_KEY": "registration-1-course-1", "HTTP_X_CORRELATION_ID": "corr-1"}
        first = self.client.post("/api/kkux-registration/v1/enrollments/", self.payload, format="json", **headers)
        second = self.client.post("/api/kkux-registration/v1/enrollments/", self.payload, format="json", **headers)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json()["status"], "SUCCEEDED")
        self.assertEqual(second.json()["enrollment_id"], first.json()["enrollment_id"])
        self.assertEqual(second.json()["correlation_id"], "corr-1")
        self.assertEqual(enroll.call_count, 1)

    @patch("kkux_enrollment_control.views.CourseEnrollment.enroll")
    def test_failed_request_can_retry_with_same_key(self, enroll):
        enroll.side_effect = [RuntimeError("temporary LMS failure"), None]
        headers = {"HTTP_IDEMPOTENCY_KEY": "retryable-key"}
        first = self.client.post("/api/kkux-registration/v1/enrollments/", self.payload, format="json", **headers)
        second = self.client.post("/api/kkux-registration/v1/enrollments/", self.payload, format="json", **headers)
        self.assertEqual(first.status_code, 502)
        self.assertEqual(second.status_code, 200)
        row = EnrollmentRequest.objects.get(idempotency_key="retryable-key")
        self.assertEqual(row.status, "SUCCEEDED")
        self.assertEqual(row.attempt_count, 2)
        self.assertIsNotNone(row.last_attempt_at)
        self.assertEqual(enroll.call_count, 2)

    def test_processing_conflict_and_idempotency_key_payload_conflict(self):
        row = EnrollmentRequest.objects.create(
            idempotency_key="processing-key", registration_id="registration-1", course_id=self.course_id,
            user=self.user, action="enroll", status="PROCESSING", attempt_count=1, last_attempt_at=timezone.now(),
        )
        headers = {"HTTP_IDEMPOTENCY_KEY": "processing-key"}
        response = self.client.post("/api/kkux-registration/v1/enrollments/", self.payload, format="json", **headers)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["status"], "PROCESSING")
        changed = dict(self.payload, course_id="course-v1:KKUx+OTHER+2026")
        conflict = self.client.post("/api/kkux-registration/v1/enrollments/", changed, format="json", **headers)
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(row.status, "PROCESSING")

    def test_request_without_idempotency_key_is_rejected(self):
        response = self.client.post("/api/kkux-registration/v1/enrollments/", self.payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "idempotency_key_required")

    @patch("kkux_enrollment_control.views.CourseEnrollment.enroll")
    def test_stale_processing_request_is_recovered_after_timeout(self, enroll):
        EnrollmentRequest.objects.create(
            idempotency_key="stale-processing", registration_id="registration-1", course_id=self.course_id,
            user=self.user, action="enroll", status="PROCESSING", attempt_count=1,
            last_attempt_at=timezone.now() - timedelta(seconds=1200),
        )
        response = self.client.post("/api/kkux-registration/v1/enrollments/", self.payload, format="json", HTTP_IDEMPOTENCY_KEY="stale-processing")
        self.assertEqual(response.status_code, 200)
        row = EnrollmentRequest.objects.get(idempotency_key="stale-processing")
        self.assertEqual(row.status, "SUCCEEDED")
        self.assertEqual(row.attempt_count, 2)
        enroll.assert_called_once()

    @override_settings(KKUX_ENROLLMENT_MODE="verified")
    @patch("kkux_enrollment_control.views.CourseEnrollment.enroll")
    def test_enrollment_mode_is_configurable(self, enroll):
        response = self.client.post("/api/kkux-registration/v1/enrollments/", self.payload, format="json", HTTP_IDEMPOTENCY_KEY="mode-key")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(enroll.call_args.kwargs["mode"], "verified")


class MiddlewareTests(DjangoTestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="staff", email="staff@example.org", is_staff=True)
        self.course_id = "course-v1:KKUx+MANAGED+2026"
        ManagedCourseRun.objects.create(course_id=self.course_id, enabled=True, allow_staff_override=True)
        self.factory = RequestFactory()

    def test_supported_lms_enrollment_route_is_blocked_for_managed_learner(self):
        request = self.factory.post("/change_enrollment", {"course_id": self.course_id})
        request.user = SimpleNamespace(is_staff=False)
        middleware = ManagedEnrollmentMiddleware(lambda req: None)
        response = middleware(request)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(json.loads(response.content)["error"]["code"], "managed_enrollment_required")

    def test_course_modes_route_is_blocked_and_unmanaged_route_is_not(self):
        request = self.factory.post("/course_modes/choose/course-v1:KKUx+MANAGED+2026/", {"course_id": self.course_id})
        request.user = SimpleNamespace(is_staff=False)
        middleware = ManagedEnrollmentMiddleware(lambda req: None)
        self.assertEqual(middleware(request).status_code, 403)
        enrollment_api = self.factory.post("/api/enrollment/v1/enrollment/", {"course_id": self.course_id})
        enrollment_api.user = SimpleNamespace(is_staff=False)
        self.assertEqual(middleware(enrollment_api).status_code, 403)
        unmanaged = self.factory.post("/api/enrollment/v1/enrollment/", {"course_id": "course-v1:KKUx+UNMANAGED+2026"})
        unmanaged.user = SimpleNamespace(is_staff=False)
        self.assertIsNone(middleware(unmanaged))

    @override_settings(KKUX_ENROLLMENT_FAIL_CLOSED=True)
    def test_database_error_fails_closed_on_known_mutation_route(self):
        request = self.factory.post("/change_enrollment", {"course_id": self.course_id})
        request.user = SimpleNamespace(is_staff=False)
        middleware = ManagedEnrollmentMiddleware(lambda req: None)
        with patch("kkux_enrollment_control.middleware.ManagedCourseRun.objects.filter", side_effect=RuntimeError("database unavailable")):
            response = middleware(request)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(json.loads(response.content)["error"]["code"], "enrollment_control_unavailable")

    def test_service_plugin_api_is_not_blocked(self):
        request = self.factory.post("/api/kkux-registration/v1/enrollments/", {"course_id": self.course_id})
        request.user = SimpleNamespace(is_staff=False)
        response = object()
        middleware = ManagedEnrollmentMiddleware(lambda req: response)
        self.assertIs(middleware(request), response)

    def test_staff_override_is_audited(self):
        request = self.factory.post("/change_enrollment", {"course_id": self.course_id}, HTTP_X_CORRELATION_ID="corr-1")
        request.user = self.user
        middleware = ManagedEnrollmentMiddleware(lambda req: None)
        self.assertIsNone(middleware(request))
        audit = EnrollmentOverrideEvent.objects.get(course_id=self.course_id)
        self.assertEqual(audit.correlation_id, "corr-1")
        self.assertEqual(audit.user_id, self.user.pk)

    @override_settings(KKUX_ENROLLMENT_FAIL_CLOSED=False)
    def test_database_failure_can_be_configured_to_fail_open(self):
        request = self.factory.post("/change_enrollment", {"course_id": self.course_id})
        request.user = SimpleNamespace(is_staff=False)
        expected = object()
        middleware = ManagedEnrollmentMiddleware(lambda req: expected)
        with patch("kkux_enrollment_control.middleware.ManagedCourseRun.objects.filter", side_effect=RuntimeError("database unavailable")):
            self.assertIs(middleware(request), expected)
