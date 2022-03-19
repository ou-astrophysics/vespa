from django.db.models.signals import post_save
from django.dispatch import receiver

from starcatalogue.exports import DataExport
from starcatalogue.models import DataRelease
from starcatalogue.tasks import prepare_data_release

import datetime


@receiver(post_save, sender=DataRelease)
def queue_prepare_data_release(sender, instance, created, **kwargs):
    if created:
        prepare_data_release.delay(instance.id)


@receiver(post_save, sender=DataRelease)
def generate_data_release_full_export(sender, instance, created, **kwargs):
    if instance.active and not instance.active_at:
        DataExport.objects.create(
            data_release=instance,
            data_version=instance.version,
            in_data_archive=True,
        )
        instance.active_at = datetime.datetime.now()
        instance.save()
