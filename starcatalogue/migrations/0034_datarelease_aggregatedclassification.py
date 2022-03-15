# Generated by Django 4.0.3 on 2022-03-08 11:33

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('starcatalogue', '0033_zooniversesubject_metadata_version'),
    ]

    operations = [
        migrations.CreateModel(
            name='DataRelease',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('version', models.FloatField()),
                ('active', models.BooleanField(default=False)),
                ('created', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='AggregatedClassification',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('classification', models.IntegerField(choices=[(1, 'Pulsator'), (2, 'EA/EB'), (3, 'EW'), (4, 'Rotator'), (5, 'Unknown'), (6, 'Junk')])),
                ('period_uncertainty', models.IntegerField(choices=[(0, 'Certain'), (1, 'Uncertain')])),
                ('classification_count', models.IntegerField()),
                ('data_release', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='starcatalogue.datarelease')),
                ('lightcurve', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='starcatalogue.foldedlightcurve')),
            ],
        ),
    ]