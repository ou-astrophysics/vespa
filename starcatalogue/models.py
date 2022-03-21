import datetime
import logging
import urllib

import numpy

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone

import astropy.io.fits as fits
from astropy import units
from astropy.coordinates import SkyCoord
from astropy.stats import sigma_clip
from astropy.timeseries import TimeSeries

from celery.result import AsyncResult
from humanize.time import naturaldelta
from humanize import naturalsize

from .fields import SPointField


OUTLIER_SIGMA_CLIP = 5
FLUX_MAX_CLIP = 2e5

logger = logging.getLogger(__name__)


def export_upload_to(instance, filename):
    return f"exports/{instance.id.hex[:3]}/{instance.id.hex}/{filename}"


def star_upload_to(instance, filename):
    return (
        f"sources/{instance.superwasp_id}/v{instance.CURRENT_IMAGE_VERSION}_{filename}"
    )


def star_json_upload_to(instance, filename):
    return (
        f"sources/{instance.superwasp_id}/v{instance.CURRENT_JSON_VERSION}_{filename}"
    )


def lightcurve_upload_to(instance, filename):
    return f"sources/{instance.star.superwasp_id}/v{instance.CURRENT_IMAGE_VERSION}_{filename}"


class ImageGenerator(object):
    def get_or_generate_image(self, image_attr, generation_task, default=None):
        image_not_present = not image_attr or not self.image_version
        image_outdated = (
            self.image_version and self.image_version < self.CURRENT_IMAGE_VERSION
        )
        if image_not_present or image_outdated:
            if (
                not self.images_celery_task_id
                or AsyncResult(self.images_celery_task_id).ready()
                or not self.image_celery_started
                or self.image_celery_started
                < (timezone.now() - datetime.timedelta(minutes=5))
            ):
                self.images_celery_task_id = generation_task.delay(self.id).id
                self.image_celery_started = timezone.now()
                self.save()
            if image_not_present:
                return default
        elif self.images_celery_task_id:
            AsyncResult(self.images_celery_task_id).forget()
        return image_attr.url


class JSONGenerator(object):
    def get_or_generate_json(self, json_attr, generation_task, default=None):
        json_not_present = not json_attr or not self.json_version
        json_outdated = (
            self.json_version and self.json_version < self.CURRENT_JSON_VERSION
        )
        if json_not_present or json_outdated:
            if (
                not self.json_files_celery_task_id
                or AsyncResult(self.json_files_celery_task_id).ready()
                or not self.json_celery_started
                or self.json_celery_started
                < (timezone.now() - datetime.timedelta(minutes=5))
            ):
                self.json_files_celery_task_id = generation_task.delay(self.id).id
                self.json_celery_started = timezone.now()
                self.save()
            if json_not_present:
                return default
        elif self.json_files_celery_task_id:
            AsyncResult(self.json_files_celery_task_id).forget()
        return json_attr.url


class Star(models.Model, ImageGenerator, JSONGenerator):
    CURRENT_IMAGE_VERSION = 0.92
    CURRENT_JSON_VERSION = 0.3
    CURRENT_STATS_VERSION = 0.4

    superwasp_id = models.CharField(unique=True, max_length=26)
    fits_file = models.FileField(null=True, upload_to=star_upload_to)
    fits_celery_task_id = models.UUIDField(null=True)
    fits_celery_started = models.DateTimeField(null=True)
    fits_error_count = models.IntegerField(default=0)

    image_file = models.ImageField(null=True, upload_to=star_upload_to)
    images_celery_task_id = models.UUIDField(null=True)
    image_version = models.FloatField(null=True)
    image_celery_started = models.DateTimeField(null=True)

    json_file = models.FileField(null=True, upload_to=star_json_upload_to)
    json_files_celery_task_id = models.UUIDField(null=True)
    json_version = models.FloatField(null=True)
    json_celery_started = models.DateTimeField(null=True)

    _min_magnitude = models.FloatField(null=True)
    _mean_magnitude = models.FloatField(null=True)
    _max_magnitude = models.FloatField(null=True)
    _amplitude = models.FloatField(null=True)
    stats_version = models.FloatField(null=True)

    location = SPointField(null=True)

    @classmethod
    def outlier_clip(cls, flux):
        return sigma_clip(
            numpy.ma.masked_greater(
                numpy.ma.masked_less(
                    flux,
                    -FLUX_MAX_CLIP,
                ),
                FLUX_MAX_CLIP,
            ),
            sigma=OUTLIER_SIGMA_CLIP,
        )

    def __str__(self):
        return self.superwasp_id

    def get_absolute_url(self):
        return reverse(
            "view_source",
            kwargs={
                "swasp_id": self.superwasp_id,
            },
        )

    @property
    def coords_str(self):
        return self.superwasp_id.replace("1SWASP", "")

    @property
    def coords(self):
        return SkyCoord(self.coords_str, unit=(units.hour, units.deg))

    @property
    def coords_quoted(self):
        return urllib.parse.quote(self.coords_str)

    @property
    def ra(self):
        return self.coords.ra.to_string(units.hour)

    @property
    def dec(self):
        return self.coords.dec

    @property
    def ra_quoted(self):
        coords = self.coords_str
        return urllib.parse.quote(f"{coords[1:3]}:{coords[3:5]}:{coords[5:10]}")

    @property
    def dec_quoted(self):
        coords = self.coords_str
        return urllib.parse.quote(f"{coords[10:13]}:{coords[13:15]}:{coords[15:]}")

    def set_location(self):
        coords = self.coords
        self.location = (coords.ra.to_value(), coords.dec.to_value())
        self.save()

    @property
    def lightcurve_classifications(self):
        return (
            AggregatedClassification.get_latest()
            .filter(lightcurve__star=self)
            .order_by("lightcurve__period_length")
        )

    @property
    def fits(self):
        if not self.fits_file and (
            not self.fits_celery_task_id
            or AsyncResult(self.fits_celery_task_id).ready()
            or not self.fits_celery_started
            or self.fits_celery_started
            < (timezone.now() - datetime.timedelta(minutes=5))
        ):
            self.fits_celery_task_id = download_fits.apply_async(
                (self.id,),
                expires=300,
            ).id
            self.fits_celery_started = timezone.now()
            self.save()
            return None

        if self.fits_celery_task_id:
            AsyncResult(self.fits_celery_task_id).forget()

        return self.fits_file

    @property
    def fits_file_naturalsize(self):
        return naturalsize(self.fits_file.size)

    @property
    def timeseries(self):
        if not self.fits:
            return

        try:
            with fits.open(self.fits.path) as fits_file:
                hjd_col = fits.Column(
                    name="HJD",
                    format="D",
                    array=fits_file[1].data["TMID"] / 86400 + 2453005.5,
                )
                lc_data = fits.BinTableHDU.from_columns(
                    fits_file[1].data.columns + fits.ColDefs([hjd_col])
                )
                return TimeSeries.read(lc_data, time_column="HJD", time_format="jd")
        except OSError as e:
            logger.warning(
                f"Could not read FITS file {self.fits.path} for star {self.id}"
            )
            logger.warning(str(e))
            self.fits_file = None
            self.fits_error_count += 1
            self.save()

    @property
    def image_location(self):
        return self.get_image_location()

    def get_image_location(self):
        return self.get_or_generate_image(self.image_file, generate_star_images)

    @property
    def json_location(self):
        return self.get_json_location()

    def get_json_location(self):
        return self.get_or_generate_json(self.json_file, generate_star_json_files)

    @property
    def cerit_url(self):
        return f"https://wasp.cerit-sc.cz/search?objid={self.coords_quoted}&radius=1&radiusUnit=deg&limit=10"

    @property
    def simbad_url(self):
        return f"http://simbad.u-strasbg.fr/simbad/sim-coo?Coord={self.ra_quoted}+{self.dec_quoted}&Radius=2&Radius.unit=arcmin&submit=submit+query"

    @property
    def asassn_url(self):
        return f"https://asas-sn.osu.edu/photometry?ra={self.ra_quoted}&dec={self.dec_quoted}&radius=2"

    def get_magnitude(self, attr_name="_mean_magnitude"):
        if (
            self.stats_version is None
            or self.stats_version < self.CURRENT_STATS_VERSION
            or getattr(self, attr_name) is None
        ):
            self.calculate_magnitudes()

        return getattr(self, attr_name)

    def calculate_magnitudes(self):
        agg_funcs = {
            "_mean_magnitude": lambda x: x.mean(),
            "_min_magnitude": lambda x: x.min(),
            "_max_magnitude": lambda x: x.max(),
        }
        timeseries = self.timeseries
        if not timeseries:
            return
        flux = Star.outlier_clip(timeseries["TAMFLUX2"])
        for attr_name, agg_func in agg_funcs.items():
            mag = 15 - 2.5 * numpy.log10(agg_func(flux))
            setattr(self, attr_name, mag)
        self._amplitude = self._min_magnitude - self._max_magnitude
        self.stats_version = self.CURRENT_STATS_VERSION
        self.save()

    @property
    def mean_magnitude(self):
        return self.get_magnitude("_mean_magnitude")

    @property
    def max_magnitude(self):
        return self.get_magnitude("_max_magnitude")

    @property
    def min_magnitude(self):
        return self.get_magnitude("_min_magnitude")

    @property
    def amplitude(self):
        return self.get_magnitude("_amplitude")


class FoldedLightcurve(models.Model, ImageGenerator):
    CURRENT_IMAGE_VERSION = 1.0

    star = models.ForeignKey(to=Star, on_delete=models.CASCADE)

    period_number = models.IntegerField()
    period_length = models.FloatField(null=True)
    sigma = models.FloatField(null=True)
    chi_squared = models.FloatField(null=True)

    image_file = models.ImageField(null=True, upload_to=lightcurve_upload_to)
    thumbnail_file = models.ImageField(null=True, upload_to=lightcurve_upload_to)
    images_celery_task_id = models.UUIDField(null=True)
    image_version = models.FloatField(null=True)
    image_celery_started = models.DateTimeField(null=True)

    def __str__(self):
        return f"{self.star.superwasp_id}@{self.period_length} sec"

    def get_absolute_url(self):
        return f"{self.star.get_absolute_url()}#lightcurve-{ self.pk }"

    def get_period_url(self):
        return f"{self.star.get_absolute_url()}#period-{ self.period_length }"

    @property
    def latest_aggregated_classification(self):
        return self.aggregatedclassification_set.filter(
            data_release=DataRelease.get_latest()
        ).first()

    @property
    def natural_period(self):
        return naturaldelta(self.period_length)

    @property
    def image_location(self):
        return self.get_image_location()

    def get_image_location(self):
        return self.get_or_generate_image(
            self.image_file,
            generate_lightcurve_images,
            self.zooniversesubject.image_location,
        )

    @property
    def thumbnail_location(self):
        return self.get_thumbnail_location()

    def get_thumbnail_location(self):
        return self.get_or_generate_image(
            self.thumbnail_file,
            generate_lightcurve_images,
            self.zooniversesubject.thumbnail_location,
        )

    @property
    def timeseries(self):
        if not self.star.timeseries:
            return
        return self.star.timeseries.fold(
            period=self.period_length * units.second,
        )


class ZooniverseSubject(models.Model):
    CURRENT_METADATA_VERSION = 1.0

    zooniverse_id = models.IntegerField(unique=True)
    lightcurve = models.OneToOneField(to=FoldedLightcurve, on_delete=models.CASCADE)

    subject_set_id = models.IntegerField(null=True)
    retired_at = models.DateTimeField(null=True)
    image_location = models.URLField(null=True)

    metadata_version = models.FloatField(null=True)

    def __str__(self):
        return f"Subject {self.zooniverse_id}"

    @property
    def thumbnail_location(self):
        if self.image_location:
            return "https://thumbnails.zooniverse.org/100x80/{}".format(
                self.image_location.replace("https://", ""),
            )

    @property
    def subject_metadata(self):
        coords = self.lightcurve.star.superwasp_id.replace("1SWASP", "")
        coords_quoted = urllib.parse.quote(coords)
        ra = urllib.parse.quote(f"{coords[1:3]}:{coords[3:5]}:{coords[5:10]}")
        dec = urllib.parse.quote(f"{coords[10:13]}:{coords[13:15]}:{coords[15:]}")

        return {
            "!CERiT": f"https://wasp.cerit-sc.cz/search?objid={coords_quoted}&radius=1&radiusUnit=deg&limit=10",
            "!Simbad": f"http://simbad.u-strasbg.fr/simbad/sim-coo?Coord={ra}+{dec}&Radius=2&Radius.unit=arcmin&submit=submit+query",
            "!ASAS-SN Photometry": f"https://asas-sn.osu.edu/photometry?ra={ra}&dec={dec}&radius=2",
            "!VeSPA": f"https://{settings.ALLOWED_HOSTS[0]}{self.lightcurve.get_period_url()}",
        }

    @property
    def talk_url(self):
        return f"https://www.zooniverse.org/projects/ajnorton/superwasp-variable-stars/talk/subjects/{ self.zooniverse_id }"

    def save_metadata(self):
        save_zooniverse_metadata.delay(self.id)


def get_next_data_release_version():
    return DataRelease.get_latest().version + 1


class DataRelease(models.Model):
    version = models.FloatField(default=get_next_data_release_version)

    active = models.BooleanField(default=False)

    created = models.DateTimeField(auto_now_add=True)
    aggregation_finished = models.DateTimeField(null=True)
    active_at = models.DateTimeField(null=True, blank=True)

    @classmethod
    def get_latest(cls, active=True):
        result = cls.objects
        if active:
            result = result.filter(active=True)
        result = result.order_by("-version")
        return result.first()

    @property
    def full_export(self):
        return self.dataexport_set.filter(in_data_archive=True).first()

    def pending_stars(self):
        return (
            self.aggregatedclassification_set.filter(
                lightcurve__star__fits_error_count__lt=settings.FITS_DOWNLOAD_ATTEMPTS
            )
            .filter(lightcurve__star__stats_version=None)
            .count()
        )

    def __str__(self):
        return f"Data release {self.version}"


class AggregatedClassification(models.Model):
    PULSATOR = 1
    EA_EB = 2
    EW = 3
    ROTATOR = 4
    UNKNOWN = 5
    JUNK = 6
    CLASSIFICATION_CHOICES = [
        (PULSATOR, "Pulsator"),
        (EA_EB, "EA/EB"),
        (EW, "EW"),
        (ROTATOR, "Rotator"),
        (UNKNOWN, "Unknown"),
        (JUNK, "Junk"),
    ]

    CERTAIN = 0
    UNCERTAIN = 1
    PERIOD_UNCERTAINTY_CHOICES = [
        (CERTAIN, "Certain"),
        (UNCERTAIN, "Uncertain"),
    ]

    data_release = models.ForeignKey(DataRelease, on_delete=models.CASCADE)
    lightcurve = models.ForeignKey(FoldedLightcurve, on_delete=models.CASCADE)

    classification = models.IntegerField(choices=CLASSIFICATION_CHOICES)
    period_uncertainty = models.IntegerField(choices=PERIOD_UNCERTAINTY_CHOICES)
    classification_count = models.IntegerField()

    @classmethod
    def get_latest(cls, active=True):
        return cls.objects.filter(data_release=DataRelease.get_latest(active=active))


from .tasks import (
    download_fits,
    generate_lightcurve_images,
    generate_star_images,
    generate_star_json_files,
    save_zooniverse_metadata,
)
from .exports import DataExport
