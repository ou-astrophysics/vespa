# Generated by Django 3.1.7 on 2021-03-05 16:06

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('starcatalogue', '0004_auto_20201027_1525'),
    ]

    operations = [
        migrations.CreateModel(
            name='DataExport',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('min_period', models.FloatField(null=True)),
                ('max_period', models.FloatField(null=True)),
                ('type_pulsator', models.BooleanField(choices=[(True, 'on'), (False, 'off')], default=True)),
                ('type_rotator', models.BooleanField(choices=[(True, 'on'), (False, 'off')], default=True)),
                ('type_ew', models.BooleanField(choices=[(True, 'on'), (False, 'off')], default=True)),
                ('type_eaeb', models.BooleanField(choices=[(True, 'on'), (False, 'off')], default=True)),
                ('type_unknown', models.BooleanField(choices=[(True, 'on'), (False, 'off')], default=True)),
                ('search', models.TextField(null=True)),
                ('sort', models.CharField(max_length=18, null=True)),
                ('order', models.IntegerField(choices=[(0, 'asc'), (1, 'desc')], null=True)),
                ('data_version', models.FloatField()),
                ('created', models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]