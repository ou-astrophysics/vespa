# Generated by Django 3.2.2 on 2021-05-18 14:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('starcatalogue', '0028_star__amplitude'),
    ]

    operations = [
        migrations.AddField(
            model_name='dataexport',
            name='max_amplitude',
            field=models.FloatField(null=True),
        ),
        migrations.AddField(
            model_name='dataexport',
            name='min_amplitude',
            field=models.FloatField(null=True),
        ),
    ]
