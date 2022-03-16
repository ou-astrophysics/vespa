from django.apps import AppConfig


class StarcatalogueConfig(AppConfig):
    name = "starcatalogue"

    def ready(self):
        from . import signals
