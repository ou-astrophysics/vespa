# This file consolidates the various constants, lists of
# params, etc. that define the export parameters. This makes
# it easier to add new fields, since they're all in one place.

import uuid

from django.db import models
from django.template import RequestContext

from humanize import naturalsize

from .models import export_upload_to


BASIC_EXPORT_PARAMS = (
    'min_period',
    'max_period',
    'min_magnitude',
    'max_magnitude',
    'certain_period',
    'search',
    'search_radius',
)
DISPLAYABLE_EXPORT_PARAMS = (
    'certain_period',
    'uncertain_period',
    'type_pulsator',
    'type_rotator',
    'type_ew',
    'type_eaeb',
    'type_unknown',
)
EXPORT_PARAMS = BASIC_EXPORT_PARAMS + DISPLAYABLE_EXPORT_PARAMS

def gen_export_params_dict(obj, displayable=False):
    if type(obj) == RequestContext:
        get_attr = lambda o, p: o.get(p)
        IS_CONTEXT = True
    else:
        get_attr = getattr
        IS_CONTEXT = False
    params = {param: get_attr(obj, param) for param in BASIC_EXPORT_PARAMS}
    if displayable and not IS_CONTEXT:
        displayable_params = {param: get_attr(obj, f"get_{param}_display")() for param in DISPLAYABLE_EXPORT_PARAMS}
    else:
        displayable_params = {param: get_attr(obj, param) for param in DISPLAYABLE_EXPORT_PARAMS}
    params.update(displayable_params)
    return params

class DataExport(models.Model):
    CHECKBOX_CHOICES = [
        (True, 'on'),
        (False, 'off'),
    ]
    CHECKBOX_CHOICES_DICT = dict([ (v, k) for (k, v) in CHECKBOX_CHOICES])

    EXPORT_FILE_NAME = 'superwasp-vespa-export.zip'

    STATUS_PENDING = 0
    STATUS_RUNNING = 1
    STATUS_COMPLETE = 2
    STATUS_FAILED = 3
    STATUS_CHOICES = (
        (STATUS_PENDING, 'Pending'),
        (STATUS_RUNNING, 'Running'),
        (STATUS_COMPLETE, 'Complete'),
        (STATUS_FAILED, 'Failed'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    min_period = models.FloatField(null=True)
    max_period = models.FloatField(null=True)
    min_magnitude = models.FloatField(null=True)
    max_magnitude = models.FloatField(null=True)
    certain_period = models.BooleanField(choices=CHECKBOX_CHOICES, default=True)
    uncertain_period = models.BooleanField(choices=CHECKBOX_CHOICES, default=True)
    type_pulsator = models.BooleanField(choices=CHECKBOX_CHOICES, default=True)
    type_rotator = models.BooleanField(choices=CHECKBOX_CHOICES, default=True)
    type_ew = models.BooleanField(choices=CHECKBOX_CHOICES, default=True)
    type_eaeb = models.BooleanField(choices=CHECKBOX_CHOICES, default=True)
    type_unknown = models.BooleanField(choices=CHECKBOX_CHOICES, default=True)
    search = models.TextField(null=True)
    search_radius = models.FloatField(null=True)

    data_version = models.FloatField()

    celery_task_id = models.UUIDField(null=True)
    export_status = models.IntegerField(choices=STATUS_CHOICES, default=STATUS_PENDING)
    export_file = models.FileField(
        upload_to=export_upload_to,
        null=True,
    )

    progress = models.FloatField(default=0.0)

    created = models.DateTimeField(auto_now_add=True)
    
    @property
    def queryset(self):
        return StarListView().get_queryset(params=self.queryset_params)

    @property
    def export_file_naturalsize(self):
        return naturalsize(self.export_file.size)

    @property
    def queryset_params(self):
        return gen_export_params_dict(self, displayable=True)


def gen_export_params_yaml_dict(export, total_records):
    params = {
        'data_version': export.data_version,
        'object_count': total_records,
    }
    params.update(gen_export_params_dict(export))
    return params


EXPORT_DATA_DESCRIPTION = {
    'SuperWASP ID': 'The unique identifier for the source',
    'Period Length': 'The period length in seconds',
    'RA': 'Right ascension in hours',
    'Dec': 'Declination in degrees',
    'Maximum magnitude': 'The brightest magnitude for this source',
    'Minimum magnitude': 'The least bright magnitude for this source',
    'Mean magnitude': 'The mean magnitude for this source',
    'Classification': 'The candidate variable star type',
    'Classification count': 'How many Zooniverse classifications this entry received',
    'Folding flag': 'Whether the correctness of this period is certain or uncertain (based on Zooniverse classifications)',
    'Sigma': 'Sigma error estimate from original period search',
    'Chi squared': 'Chi squared error estimate from original period search',
}

def gen_export_record_dict(record):
    return {
        'SuperWASP ID': record.star.superwasp_id,
        'Period Length': record.period_length,
        'RA': record.star.ra,
        'Dec': record.star.dec,
        'Maximum magnitude': record.star.max_magnitude,
        'Minimum magnitude': record.star.min_magnitude,
        'Mean magnitude': record.star.mean_magnitude,
        'Classification': record.get_classification_display(), 
        'Classification count': record.classification_count,
        'Folding flag': record.get_period_uncertainty_display(),
        'Sigma': record.sigma,
        'Chi squared': record.chi_squared,
    }

from .views import StarListView