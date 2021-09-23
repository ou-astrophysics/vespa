from astropy.coordinates import SkyCoord
from astropy.coordinates.name_resolve import NameResolveError
from astropy import units as u

from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.views.generic.list import ListView
from django.views.generic import DetailView

from starcatalogue.models import Star, FoldedLightcurve
from starcatalogue.exports import DataExport
from starcatalogue.fields import Distance


class StarListView(ListView):
    paginate_by = 20

    def get_queryset(self, params=None):
        if params is None:
            params = self.request.GET

        qs = FoldedLightcurve.objects.all()

        try:
            self.min_period = float(params.get('min_period', None))
            if self.min_period:
                qs = qs.filter(period_length__gte=self.min_period)
            else:
                # To ensure it's None rather than ''
                self.min_period = None
        except (ValueError, TypeError):
            self.min_period = None
        
        try:
            self.max_period = float(params.get('max_period', None))
            if self.max_period:
                qs = qs.filter(period_length__lte=self.max_period)
            else:
                # To ensure it's None rather than ''
                self.max_period = None
        except (ValueError, TypeError):
            self.max_period = None

        self.certain_period = params.get('certain_period', 'off')
        self.uncertain_period = params.get('uncertain_period', 'off')

        uncertainty_map = {
            FoldedLightcurve.CERTAIN: self.certain_period,
            FoldedLightcurve.UNCERTAIN: self.uncertain_period,
        }

        enabled_uncertainties = [ k for k, v in uncertainty_map.items() if v == 'on']

        if not enabled_uncertainties:
            enabled_uncertainties = uncertainty_map.keys()
            self.certain_period = 'on'
            self.uncertain_period = 'on'

        qs = qs.filter(period_uncertainty__in=enabled_uncertainties)

        try:
            self.min_magnitude = float(params.get('min_magnitude', None))
            if self.min_magnitude:
                qs = qs.filter(star___mean_magnitude__gte=self.min_magnitude)
            else:
                # To ensure it's None rather than ''
                self.min_magnitude = None
        except (ValueError, TypeError):
            self.min_magnitude = None
        
        try:
            self.max_magnitude = float(params.get('max_magnitude', None))
            if self.max_magnitude:
                qs = qs.filter(star___mean_magnitude__lte=self.max_magnitude)
            else:
                # To ensure it's None rather than ''
                self.max_magnitude = None
        except (ValueError, TypeError):
            self.max_magnitude = None

        try:
            self.min_amplitude = float(params.get('min_amplitude', None))
            if self.min_amplitude:
                qs = qs.filter(star___amplitude__gte=self.min_amplitude)
            else:
                # To ensure it's None rather than ''
                self.min_amplitude = None
        except (ValueError, TypeError):
            self.min_amplitude = None
        
        try:
            self.max_amplitude = float(params.get('max_amplitude', None))
            if self.max_amplitude:
                qs = qs.filter(star___amplitude__lte=self.max_amplitude)
            else:
                # To ensure it's None rather than ''
                self.max_amplitude = None
        except (ValueError, TypeError):
            self.max_amplitude = None

        try:
            self.min_classifications = int(params.get('min_classifications', None))
            if self.min_classifications:
                qs = qs.filter(classification_count__gte=self.min_classifications)
            else:
                # To ensure it's None rather than ''
                self.min_classifications = None
        except (ValueError, TypeError):
            self.min_classifications = None
        
        try:
            self.max_classifications = int(params.get('max_classifications', None))
            if self.max_classifications:
                qs = qs.filter(classification_count__lte=self.max_classifications)
            else:
                # To ensure it's None rather than ''
                self.max_classifications = None
        except (ValueError, TypeError):
            self.max_classifications = None

        self.type_pulsator = params.get('type_pulsator', 'off')
        self.type_rotator = params.get('type_rotator', 'off')
        self.type_ew = params.get('type_ew', 'off')
        self.type_eaeb = params.get('type_eaeb', 'off')
        self.type_unknown = params.get('type_unknown', 'off')

        type_map = {
            FoldedLightcurve.PULSATOR: self.type_pulsator,
            FoldedLightcurve.EA_EB: self.type_eaeb,
            FoldedLightcurve.EW: self.type_ew,
            FoldedLightcurve.ROTATOR: self.type_rotator,
            FoldedLightcurve.UNKNOWN: self.type_unknown,
        }

        enabled_types = [ k for k, v in type_map.items() if v == 'on']

        # If nothing is enabled, enable everything
        # This works as a default, because why would anyone actually want to exclude all types?
        if not enabled_types:
            enabled_types = type_map.keys()
            self.type_pulsator = 'on'
            self.type_rotator = 'on'
            self.type_ew = 'on'
            self.type_eaeb = 'on'
            self.type_unknown = 'on'

        qs = qs.filter(classification__in=enabled_types)

        self.search = params.get('search', None)
        self.search_radius = params.get('search_radius', None)
        self.coords = None

        if self.search:
            try:
               self.search_radius = float(self.search_radius)
            except (ValueError, TypeError):
               self.search_radius = 0.1

            if self.search_radius < 0:
                self.search_radius = 0
            if self.search_radius > 90:
                self.search_radius = 90

            if self.search.startswith('1SWASP'):
                try:
                    self.coords = Star.objects.get(superwasp_id=self.search).coords
                except Star.DoesNotExist:
                    pass
            
            if self.coords is None:
                try:
                    self.coords = SkyCoord(self.search)
                except (ValueError, UnicodeDecodeError, u.UnitsError):
                    try:
                        self.coords = SkyCoord.from_name(self.search, parse=True)
                    except NameResolveError:
                        pass
                
            if self.coords is None:
                qs = qs.none()
            else:
                qs = qs.filter(Q(
                    star__location__inradius=(
                        (self.coords.ra.to_value(), self.coords.dec.to_value()),
                        self.search_radius
                    )
                ))

        sort_fields = (
            'distance',
            'star__superwasp_id',
            'period_length',
            'classification',
            'classification_count',
            'star___mean_magnitude',
            'star___max_magnitude',
            'star___min_magnitude',
            'star___amplitude',
        )
        self.sort = params.get('sort', None)
        if self.sort not in sort_fields:
            self.sort = sort_fields[0]

        self.order = params.get('order', None)
        if self.order == 'desc':
            order_prefix = '-'
        else:
            order_prefix = ''
            self.order = 'asc' # To ditch any invalid values
        
        if not self.search and self.coords is None:
            self.coords = SkyCoord(0, 0, unit=u.deg)

        if self.coords is not None:
            qs = qs.annotate(
                distance=Distance('star__location', (
                    self.coords.ra.to_value(), self.coords.dec.to_value(),
                )),
            ).order_by('{}{}'.format(order_prefix, self.sort))

        self.result_count = qs.count()

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['min_period'] = self.min_period
        context['max_period'] = self.max_period
        context['min_magnitude'] = self.min_magnitude
        context['max_magnitude'] = self.max_magnitude
        context['min_amplitude'] = self.min_amplitude
        context['max_amplitude'] = self.max_amplitude
        context['certain_period'] = self.certain_period
        context['uncertain_period'] = self.uncertain_period
        context['min_classifications'] = self.min_classifications
        context['max_classifications'] = self.max_classifications
        context['type_pulsator'] = self.type_pulsator
        context['type_eaeb'] = self.type_eaeb
        context['type_ew'] = self.type_ew
        context['type_rotator'] = self.type_rotator
        context['type_unknown'] = self.type_unknown
        context['search'] = self.search
        context['search_radius'] = self.search_radius
        context['coords'] = self.coords
        context['sort'] = self.sort
        context['order'] = self.order
        context['result_count'] = self.result_count

        return context


class SourceView(DetailView):
    model = Star

    def get_object(self, queryset=None):
        return get_object_or_404(self.model, superwasp_id=self.kwargs['swasp_id'])

from .exports import GenerateExportView