# Generated by Django 3.1.5 on 2021-01-20 17:08

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("clubs", "0073_event_pinned"),
    ]

    operations = [
        migrations.AlterField(
            model_name="zoommeetingvisit",
            name="event",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, related_name="visits", to="clubs.event"
            ),
        ),
        migrations.AlterField(
            model_name="zoommeetingvisit",
            name="person",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="visits",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
