import sys
from types import ModuleType

common = ModuleType("common")
common.__path__ = []
djangoapps = ModuleType("common.djangoapps")
djangoapps.__path__ = []
student = ModuleType("common.djangoapps.student")
student.__path__ = []
student_models = ModuleType("common.djangoapps.student.models")


class CourseEnrollment:
    @classmethod
    def enroll(cls, user, course_key, mode=None):
        return None

    @classmethod
    def unenroll(cls, user, course_key):
        return None


student_models.CourseEnrollment = CourseEnrollment
sys.modules.setdefault("common", common)
sys.modules.setdefault("common.djangoapps", djangoapps)
sys.modules.setdefault("common.djangoapps.student", student)
sys.modules.setdefault("common.djangoapps.student.models", student_models)

SECRET_KEY = "test-only-key"
DEBUG = True
USE_TZ = True
ROOT_URLCONF = "tests.urls"
ALLOWED_HOSTS = ["testserver", "localhost"]
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "rest_framework",
    "kkux_enrollment_control",
]
MIDDLEWARE = []
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
KKUX_ENROLLMENT_SERVICE_TOKEN = "test-service-token"
KKUX_ENROLLMENT_FAIL_CLOSED = True
KKUX_ENROLLMENT_MODE = "audit"
KKUX_ENROLLMENT_PROCESSING_TIMEOUT_SECONDS = 900
REST_FRAMEWORK = {"UNAUTHENTICATED_USER": None}
