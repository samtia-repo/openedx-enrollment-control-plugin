from django.urls import path
from .views import EnrollmentView, ManagedCourseView

app_name = "kkux_enrollment_control"
urlpatterns = [
    path("enrollments/", EnrollmentView.as_view(), name="enrollments"),
    path("managed-courses/<path:course_id>/", ManagedCourseView.as_view(), name="managed-course"),
]
