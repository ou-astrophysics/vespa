# Generated by Django 4.0.3 on 2022-03-19 16:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('starcatalogue', '0036_remove_foldedlightcurve_classification_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='datarelease',
            name='aggregation_finished',
            field=models.DateTimeField(null=True),
        ),
    ]
