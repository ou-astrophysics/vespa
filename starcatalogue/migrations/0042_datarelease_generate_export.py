# Generated by Django 4.0.3 on 2022-03-23 12:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('starcatalogue', '0041_aggregatedclassification_created_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='datarelease',
            name='generate_export',
            field=models.BooleanField(default=False),
        ),
    ]
