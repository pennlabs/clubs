# Generated by Django 3.1.4 on 2021-01-02 23:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("clubs", "0067_profile_show_profile"),
    ]

    operations = [
        migrations.AddField(
            model_name="clubvisit",
            name="ip",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
