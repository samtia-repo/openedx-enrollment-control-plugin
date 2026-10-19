from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("kkux_enrollment_control", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="enrollmentrequest",
            name="attempt_count",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="enrollmentrequest",
            name="last_attempt_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]