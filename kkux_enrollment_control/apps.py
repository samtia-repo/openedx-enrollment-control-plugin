from django.apps import AppConfig


class KkuxEnrollmentControlConfig(AppConfig):
    name = "kkux_enrollment_control"
    verbose_name = "KKUx Enrollment Control"

    plugin_app = {
        "url_config": {
            "lms.djangoapp": {
                "namespace": "kkux_enrollment_control",
                "regex": r"^api/kkux-registration/v1/",
                "relative_path": "urls",
            }
        },
        "settings_config": {
            "lms.djangoapp": {"common": {"relative_path": "settings"}}
        },
    }
