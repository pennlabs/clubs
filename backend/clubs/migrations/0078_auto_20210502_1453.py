# Generated by Django 3.1.2 on 2021-05-02 18:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clubs', '0077_auto_20210502_1452'),
    ]

    operations = [
        migrations.AddField(
            model_name='club',
            name='target_majors',
            field=models.ManyToManyField(through='clubs.TargetMajor', to='clubs.Major'),
        ),
        migrations.AddField(
            model_name='club',
            name='target_schools',
            field=models.ManyToManyField(through='clubs.TargetSchool', to='clubs.School'),
        ),
        migrations.AddField(
            model_name='club',
            name='target_years',
            field=models.ManyToManyField(through='clubs.TargetYear', to='clubs.Year'),
        ),
    ]
