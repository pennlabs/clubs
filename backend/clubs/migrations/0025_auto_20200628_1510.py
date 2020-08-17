# Generated by Django 3.0.7 on 2020-06-28 19:10

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("clubs", "0024_auto_20200628_1445"),
    ]

    operations = [
        migrations.AddField(
            model_name="questionanswer",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="questionanswer",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
    ]
