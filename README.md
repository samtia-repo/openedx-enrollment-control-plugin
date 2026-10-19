# Open edX KKUx Enrollment Control

Install this package into the LMS image, set `KKUX_ENROLLMENT_SERVICE_TOKEN`, and run LMS migrations.

The plugin provides:

- A trusted, idempotent enrol/unenrol API for the Node backend.
- A managed-course registry.
- Middleware for the supported Ulmo LMS UI `/change_enrollment`, MFE `/course_modes/choose/...`, and public REST `/api/enrollment/v1/...` mutation routes for managed course runs.
- Staff override only when enabled per managed course; each bypass is written to `EnrollmentOverrideEvent`.
- Configurable enrollment mode via `KKUX_ENROLLMENT_MODE` (default `audit`) and fail-closed behavior via `KKUX_ENROLLMENT_FAIL_CLOSED`.
- Idempotent successful replay, explicit 409 while processing, controlled retry of failed/stale requests, and attempt/correlation metadata.

The Node service must first mark each explicit offering target as managed using `PUT /api/kkux-registration/v1/managed-courses/{course_id}/`, then call `POST /api/kkux-registration/v1/enrollments/`.

Do not expose the service token to browsers. Configure the LMS and Node service with the same secret through Kubernetes Secrets.

## Runtime Compatibility and Tests

The locally available KKUx Ulmo image `jed.ocir.io/axle5qpxx8gk/kkux/ulmo/openedx:21.0.7-custom-0.1.2` reports Python 3.11.8, Django 5.2.11, and DRF 3.16.1. The declared requirements (`Python >=3.11`, `Django >=5.2,<6`, `DRF >=3.15,<4`) match those installed versions. Confirm the deployed image digest before promotion.

The LMS image does not include pytest. Tests use Django's built-in runner and an isolated SQLite test database; LMS CourseEnrollment calls are mocked, so these tests are not a substitute for a deployed LMS bypass test:

```bash
docker run --rm --platform linux/amd64 \
	-v "$PWD":/plugin:ro \
	-e PYTHONPATH=/plugin \
	-e PYTHONPYCACHEPREFIX=/tmp/pycache \
	--entrypoint python jed.ocir.io/axle5qpxx8gk/kkux/ulmo/openedx:21.0.7-custom-0.1.2 \
	-m django test tests --settings=tests.settings -v 1
```

The current suite covers idempotent replay, failed retry, stale PROCESSING recovery, payload conflict, middleware route blocking/unmanaged bypass, fail-closed/fail-open behavior, staff override audit, mode configuration, and correlation. Live MFE/LMS/API bypass tests and concurrent MySQL claim tests remain required.

## Identity Contract

The trusted endpoint currently looks up `user_id` as the configured Django user primary key. The Open edX JWT `sub` to Django primary-key mapping has not been verified against a production token contract. Do not enable end-to-end registration calls until the deployment confirms that mapping or an approved stable-identifier lookup is implemented.
