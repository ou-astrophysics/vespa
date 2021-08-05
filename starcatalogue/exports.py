# This file consolidates the various constants, lists of
# params, etc. that define the export parameters. This makes
# it easier to add new fields, since they're all in one place.

import uuid

from celery.result import AsyncResult

from django.conf import settings
from django.db import models
from django.http import HttpResponseRedirect, HttpResponseBadRequest
from django.template import RequestContext
from django.urls import reverse
from django.views import View

from humanize import naturalsize

from .models import export_upload_to


BASIC_EXPORT_PARAMS = (
    'min_period',
    'max_period',
    'min_magnitude',
    'max_magnitude',
    'min_amplitude',
    'max_amplitude',
    'certain_period',
    'search',
    'search_radius',
    'min_classifications',
    'max_classifications',
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
    min_amplitude = models.FloatField(null=True)
    max_amplitude = models.FloatField(null=True)
    certain_period = models.BooleanField(choices=CHECKBOX_CHOICES, default=True)
    uncertain_period = models.BooleanField(choices=CHECKBOX_CHOICES, default=True)
    min_classifications = models.IntegerField(null=True)
    max_classifications = models.IntegerField(null=True)
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
    'Amplitude': 'The absolute difference between max and min magnitude',
    'Classification': 'The candidate variable star type',
    'Classification count': 'How many Zooniverse classifications this entry received',
    'Folding flag': 'Whether the correctness of this period is certain or uncertain (based on Zooniverse classifications)',
    'Sigma': 'Sigma error estimate from original period search',
    'Chi squared': 'Chi squared error estimate from original period search',
    'FITS URL': 'The URL of the FITS file containing unfolded photometry data',
    'JSON URL': 'The URL of the JSON file containing unfolded photometry data',
    'Unfolded plot URL': 'The URL of the PNG plot of the unfolded light curve',
    'Folded plot URL': 'The URL of the PNG plot of the folded light curve',
}

def gen_export_record_dict(record):
    out = {
        'SuperWASP ID': record.star.superwasp_id,
        'Period Length': record.period_length,
        'RA': record.star.ra,
        'Dec': record.star.dec,
        'Maximum magnitude': record.star.max_magnitude,
        'Minimum magnitude': record.star.min_magnitude,
        'Mean magnitude': record.star.mean_magnitude,
        'Amplitude': record.star.amplitude,
        'Classification': record.get_classification_display(), 
        'Classification count': record.classification_count,
        'Folding flag': record.get_period_uncertainty_display(),
        'Sigma': record.sigma,
        'Chi squared': record.chi_squared,
        'FITS URL': '',
        'JSON URL': '',
        'Unfolded plot URL': '',
        'Folded plot URL': '',
    }
    if record.star.fits_file:
        out.update({
            'FITS URL': f'https://{settings.ALLOWED_HOSTS[0]}{record.star.fits_file.url}',
            'JSON URL': f'https://{settings.ALLOWED_HOSTS[0]}{record.star.json_file.url}',
            'Unfolded plot URL': f'https://{settings.ALLOWED_HOSTS[0]}{record.star.image_file.url}',
            'Folded plot URL': f'https://{settings.ALLOWED_HOSTS[0]}{record.image_file.url}',
        })

    return out

class GenerateExportView(View):
    def get(self, request):
        return HttpResponseRedirect(reverse('vespa'))

    def post(self, request):
        try:
            min_period = request.POST.get('min_period', None)
            if not min_period:
                min_period = None

            max_period = request.POST.get('max_period', None)
            if not max_period:
                max_period = None

            min_magnitude = request.POST.get('min_magnitude', None)
            if not min_magnitude:
                min_magnitude = None

            max_magnitude = request.POST.get('max_magnitude', None)
            if not max_magnitude:
                max_magnitude = None

            min_amplitude = request.POST.get('min_amplitude', None)
            if not min_amplitude:
                min_amplitude = None

            max_amplitude = request.POST.get('max_amplitude', None)
            if not max_amplitude:
                max_amplitude = None

            min_classifications = request.POST.get('min_classifications', None)
            if not min_classifications:
                min_classifications = None

            max_classifications = request.POST.get('max_classifications', None)
            if not max_classifications:
                max_classifications = None

            search_radius = request.POST.get('search_radius', None)
            if not search_radius:
                search_radius = None

            export, created = DataExport.objects.get_or_create(
                data_version=settings.DATA_VERSION,
                min_period = min_period,
                max_period = max_period,
                min_magnitude = min_magnitude,
                max_magnitude = max_magnitude,
                min_amplitude = min_amplitude,
                max_amplitude = max_amplitude,
                min_classifications = min_classifications,
                max_classifications = max_classifications,
                certain_period = DataExport.CHECKBOX_CHOICES_DICT[request.POST.get('certain_period', 'on')],
                uncertain_period = DataExport.CHECKBOX_CHOICES_DICT[request.POST.get('uncertain_period', 'on')],
                type_pulsator = DataExport.CHECKBOX_CHOICES_DICT[request.POST.get('type_pulsator', 'on')],
                type_eaeb = DataExport.CHECKBOX_CHOICES_DICT[request.POST.get('type_eaeb', 'on')],
                type_ew = DataExport.CHECKBOX_CHOICES_DICT[request.POST.get('type_ew', 'on')],
                type_rotator = DataExport.CHECKBOX_CHOICES_DICT[request.POST.get('type_rotator', 'on')],
                type_unknown = DataExport.CHECKBOX_CHOICES_DICT[request.POST.get('type_unknown', 'on')],
                search = request.POST.get('search', None),
                search_radius = search_radius,
            )
            if (
                export.export_status in (export.STATUS_PENDING, export.STATUS_FAILED) 
                or (export.export_status == export.STATUS_RUNNING and AsyncResult(export.celery_task_id).ready())
            ):
                export.celery_task_id = generate_export.delay(export.id).id
                export.save()
            return HttpResponseRedirect(reverse('view_export', kwargs={'pk': export.id.hex}))
        except (ValueError, TypeError):
            return HttpResponseBadRequest('Bad Request')

from .tasks import generate_export
from .views import StarListView