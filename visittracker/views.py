from django.views.generic.base import RedirectView

from visittracker.models import TrackedVisit


class TrackedRedirectView(RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        out_url = super().get_redirect_url(*args, **kwargs)
        TrackedVisit.objects.create(url=out_url)
        return out_url
