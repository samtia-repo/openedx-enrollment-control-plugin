import os


def _boolean(name, default):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def plugin_settings(settings):
    settings.KKUX_ENROLLMENT_SERVICE_TOKEN = os.getenv(
        "KKUX_ENROLLMENT_SERVICE_TOKEN",
        getattr(settings, "KKUX_ENROLLMENT_SERVICE_TOKEN", ""),
    )
    settings.KKUX_ENROLLMENT_FAIL_CLOSED = _boolean(
        "KKUX_ENROLLMENT_FAIL_CLOSED",
        getattr(settings, "KKUX_ENROLLMENT_FAIL_CLOSED", True),
    )
    settings.KKUX_ENROLLMENT_MODE = os.getenv(
        "KKUX_ENROLLMENT_MODE",
        getattr(settings, "KKUX_ENROLLMENT_MODE", "audit"),
    )
    settings.KKUX_ENROLLMENT_PROCESSING_TIMEOUT_SECONDS = int(os.getenv(
        "KKUX_ENROLLMENT_PROCESSING_TIMEOUT_SECONDS",
        str(getattr(settings, "KKUX_ENROLLMENT_PROCESSING_TIMEOUT_SECONDS", 900)),
    ))
    middleware = "kkux_enrollment_control.middleware.ManagedEnrollmentMiddleware"
    if middleware not in settings.MIDDLEWARE:
        settings.MIDDLEWARE.append(middleware)
