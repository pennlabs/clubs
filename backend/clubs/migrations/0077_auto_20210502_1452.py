# Generated by Django 3.1.2 on 2021-05-02 18:52

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("clubs", "0076_auto_20210214_1305"),
    ]

    operations = [
        migrations.RemoveField(model_name="club", name="target_majors",),
        migrations.RemoveField(model_name="club", name="target_schools",),
        migrations.RemoveField(model_name="club", name="target_years",),
        migrations.AddField(
            model_name="club",
            name="archived",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="club",
            name="archived_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="archived_clubs",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="club",
            name="archived_on",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="historicalclub",
            name="archived",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="historicalclub",
            name="archived_by",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="historicalclub",
            name="archived_on",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name="TargetYear",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("program", models.CharField(blank=True, max_length=255, null=True)),
                (
                    "club",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="clubs.club"
                    ),
                ),
                (
                    "target_years",
                    models.ForeignKey(
                        blank=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="clubs.year",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="TargetSchool",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("program", models.CharField(blank=True, max_length=255, null=True)),
                (
                    "club",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="clubs.club"
                    ),
                ),
                (
                    "target_schools",
                    models.ForeignKey(
                        blank=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="clubs.school",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="TargetMajor",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("program", models.CharField(blank=True, max_length=255, null=True)),
                (
                    "club",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="clubs.club"
                    ),
                ),
                (
                    "target_majors",
                    models.ForeignKey(
                        blank=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="clubs.major",
                    ),
                ),
            ],
        ),
    ]
