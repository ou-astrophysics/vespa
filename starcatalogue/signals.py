from django.db.models.signals import post_save
from django.dispatch import receiver

from starcatalogue.models import DataRelease
from starcatalogue.tasks import prepare_data_release


@receiver(post_save, sender=DataRelease)
def queue_prepare_data_release(sender, instance, created, **kwargs):
    if created:
        prepare_data_release.delay(instance.id)
