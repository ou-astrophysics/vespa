# Generated by Django 3.2.2 on 2021-05-18 14:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('starcatalogue', '0027_auto_20210513_1622'),
    ]

    operations = [
        migrations.AddField(
            model_name='star',
            name='_amplitude',
            field=models.FloatField(null=True),
        ),
    ]
