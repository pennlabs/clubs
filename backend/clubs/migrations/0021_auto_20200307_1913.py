# Generated by Django 3.0.3 on 2020-03-08 00:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("clubs", "0020_auto_20200228_1651"),
    ]

    operations = [
        migrations.AlterField(
            model_name="event", name="code", field=models.SlugField(max_length=255),
        ),
    ]