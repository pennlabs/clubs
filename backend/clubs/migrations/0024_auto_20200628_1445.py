# Generated by Django 3.0.7 on 2020-06-28 18:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("clubs", "0023_questionanswer"),
    ]

    operations = [
        migrations.AddField(
            model_name="questionanswer", name="approved", field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name="questionanswer",
            name="is_anonymous",
            field=models.BooleanField(default=False),
        ),
    ]