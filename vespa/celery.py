import os
from decimal import Decimal

from celery import Celery

from panoptes_client import Panoptes

from django.conf import settings
from django.db.models import Q


# set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vespa.settings")

app = Celery("vespa")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()


@app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(
        settings.PERIODIC_TASK_INTERVAL,
        queue_image_generations.s(),
    )
    sender.add_periodic_task(
        settings.PERIODIC_TASK_INTERVAL,
        queue_json_generations.s(),
    )
    sender.add_periodic_task(settings.PERIODIC_TASK_INTERVAL, calculate_magnitudes.s())
    sender.add_periodic_task(settings.PERIODIC_TASK_INTERVAL, set_locations.s())
    sender.add_periodic_task(
        settings.PERIODIC_TASK_INTERVAL,
        set_zooniverse_metadata.s(),
    )


@app.on_after_fork.connect
@app.on_after_finalize.connect
def setup_zooniverse(sender, **kwargs):
    if settings.ZOONIVERSE_CLIENT_ID and settings.ZOONIVERSE_CLIENT_SECRET:
        Panoptes.connect(
            client_id=settings.ZOONIVERSE_CLIENT_ID,
            client_secret=settings.ZOONIVERSE_CLIENT_SECRET,
        )


@app.task
def queue_image_generations():
    from starcatalogue.models import Star, FoldedLightcurve

    for star in Star.objects.filter(
        fits_error_count__lt=settings.FITS_DOWNLOAD_ATTEMPTS
    ).filter(Q(image_version=None) | Q(image_version__lt=Star.CURRENT_IMAGE_VERSION))[
        :1000
    ]:
        star.get_image_location()

    for lightcurve in (
        FoldedLightcurve.objects.filter(
            star__fits_error_count__lt=settings.FITS_DOWNLOAD_ATTEMPTS
        )
        .filter(
            Q(image_version=None)
            | Q(image_version__lt=FoldedLightcurve.CURRENT_IMAGE_VERSION)
        )
        .filter(
            ~Q(sigma=Decimal("NaN"))
            & ~Q(chi_squared=Decimal("NaN"))
            & ~Q(period_length=Decimal("NaN"))
        )[:1000]
    ):
        lightcurve.get_image_location()


@app.task
def queue_json_generations():
    from starcatalogue.models import Star, FoldedLightcurve

    for star in Star.objects.filter(
        fits_error_count__lt=settings.FITS_DOWNLOAD_ATTEMPTS
    ).filter(Q(json_version=None) | Q(json_version__lt=Star.CURRENT_JSON_VERSION))[
        :1000
    ]:
        star.get_json_location()


@app.task
def calculate_magnitudes():
    from starcatalogue.models import Star

    for star in Star.objects.filter(
        fits_error_count__lt=settings.FITS_DOWNLOAD_ATTEMPTS
    ).filter(
        Q(fits_file__isnull=False)
        & (
            Q(_min_magnitude__isnull=True)
            | Q(_max_magnitude__isnull=True)
            | Q(_mean_magnitude__isnull=True)
            | Q(stats_version__lt=Star.CURRENT_STATS_VERSION)
            | Q(stats_version__isnull=True)
        )
    )[
        :1000
    ]:
        star.calculate_magnitudes()


@app.task
def set_locations():
    from starcatalogue.models import Star

    for star in Star.objects.filter(location=None)[:1000]:
        star.set_location()


@app.task
def set_zooniverse_metadata():
    from starcatalogue.models import ZooniverseSubject

    for subject in ZooniverseSubject.objects.exclude(
        lightcurve__cnn_junk_prediction=None
    ).filter(
        Q(metadata_version=None)
        | Q(metadata_version__lt=ZooniverseSubject.CURRENT_METADATA_VERSION)
    )[
        :10000
    ]:
        subject.save_metadata()
