# Generated by Django 4.1.1 on 2022-10-05 14:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('visittracker', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='trackedvisit',
            name='source',
            field=models.CharField(max_length=255, null=True),
        ),
    ]