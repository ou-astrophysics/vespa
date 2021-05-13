import math

from astropy.coordinates import Angle
from astropy import units as u

from django import template
from django.utils.html import format_html_join

from ..exports import BASIC_EXPORT_PARAMS, DISPLAYABLE_EXPORT_PARAMS, gen_export_params_dict

register = template.Library()


@register.simple_tag()
def degrees(distance):   
    return Angle(distance, u.rad).to_string(u.deg)


@register.simple_tag()
def hours(coord):   
    return coord.to_string(u.hour)


@register.filter('isnan')
def isnan(x):
    return math.isnan(x)


# From https://www.caktusgroup.com/blog/2018/10/18/filtering-and-pagination-django/
@register.simple_tag(takes_context=True)
def param_replace(context, **kwargs):
    """
    Return encoded URL parameters that are the same as the current
    request's parameters, only with the specified GET parameters added or changed.

    It also removes any empty parameters to keep things neat,
    so you can remove a parm by setting it to ``""``.

    For example, if you're on the page ``/things/?with_frosting=true&page=5``,
    then

    <a href="/things/?{% param_replace page=3 %}">Page 3</a>

    would expand to

    <a href="/things/?with_frosting=true&page=3">Page 3</a>

    Based on
    https://stackoverflow.com/questions/22734695/next-and-before-links-for-a-django-paginated-query/22735278#22735278
    """
    d = context['request'].GET.copy()
    for k, v in kwargs.items():
        d[k] = v
    for k in [k for k, v in d.items() if not v]:
        del d[k]
    return d.urlencode()


@register.filter('startswith')
def startswith(text, starts):
    if isinstance(text, str):
        return text.startswith(starts)
    return False

@register.simple_tag(takes_context=True)
def export_hidden_inputs(context, obj=None):
    if obj is None:
        obj = context
    out = [(param, value) for param, value in gen_export_params_dict(obj, True).items() if value is not None]
    return format_html_join('\n', '<input type="hidden" name="{}" value="{}">', out)