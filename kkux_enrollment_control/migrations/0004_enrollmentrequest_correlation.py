from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("kkux_enrollment_control", "0003_enrollmentoverrideevent"),
    ]

    operations = [
        migrations.AddField(
            model_name="enrollmentrequest",
            name="correlation_id",
            field=models.CharField(blank=True, max_length=128),
        ),
    ]