# Generated by Django 5.1.5 on 2025-02-27 11:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('starcatalogue', '0045_foldedlightcurve_cnn_junk_prediction'),
    ]

    operations = [
        migrations.AddField(
            model_name='dataexport',
            name='_object_count',
            field=models.IntegerField(null=True),
        ),
    ]
