# Generated by Django 3.2.7 on 2021-09-22 12:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('starcatalogue', '0030_auto_20210713_1335'),
    ]

    operations = [
        migrations.AddField(
            model_name='dataexport',
            name='in_data_archive',
            field=models.BooleanField(default=False),
        ),
    ]
