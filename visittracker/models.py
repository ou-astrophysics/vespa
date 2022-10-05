from django.db import models


class TrackedVisit(models.Model):
    url = models.CharField(max_length=255)
    source = models.CharField(max_length=255, null=True)
    created = models.DateTimeField(auto_now_add=True)
