from django.urls import include, path

urlpatterns = [path("api/kkux-registration/v1/", include("kkux_enrollment_control.urls"))]
