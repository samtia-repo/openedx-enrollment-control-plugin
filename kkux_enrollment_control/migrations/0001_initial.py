from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(name="ManagedCourseRun", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("course_id", models.CharField(db_index=True, max_length=255, unique=True)), ("enabled", models.BooleanField(default=True)), ("allow_staff_override", models.BooleanField(default=True)), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True))]),
        migrations.CreateModel(name="EnrollmentRequest", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("idempotency_key", models.CharField(max_length=255, unique=True)), ("registration_id", models.CharField(db_index=True, max_length=255)), ("course_id", models.CharField(max_length=255)), ("action", models.CharField(max_length=20)), ("status", models.CharField(max_length=20)), ("error", models.TextField(blank=True)), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)), ("user", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL))]),
    ]
