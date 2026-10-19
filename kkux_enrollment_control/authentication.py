import secrets
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed


class ServiceTokenAuthentication(BaseAuthentication):
    def authenticate(self, request):
        expected = str(getattr(settings, "KKUX_ENROLLMENT_SERVICE_TOKEN", ""))
        header = request.headers.get("Authorization", "")
        supplied = header.removeprefix("Bearer ").strip() if header.startswith("Bearer ") else ""
        if not expected or not supplied or not secrets.compare_digest(expected, supplied):
            raise AuthenticationFailed("Invalid KKUx enrollment service token.")
        return (None, "kkux-registration-backend")
