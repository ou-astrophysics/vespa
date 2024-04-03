# Based on django-pgsphere https://github.com/akorotkov/pgsphere

from django.db import models
from django.db.models.expressions import Func
from ast import literal_eval as make_tuple
from django.core.exceptions import ValidationError
import collections
import math


def to_tuple(inval):
    if isinstance(inval, list):
        return tuple(inval)
    try:
        val = make_tuple(inval)
    except (ValueError, SyntaxError):
        raise ValidationError('Invalid input: "{0}"'.format(inval))
    if not isinstance(val, collections.abc.Iterable):
        raise ValidationError("Value must be a tuple")
    return val


def parse_spoint(point, to_deg):
    if not isinstance(point, tuple):
        point = to_tuple(point)
    if len(point) != 2:
        raise ValidationError("Point has exactly two values: (ra, dec)")
    if to_deg:
        return tuple(math.degrees(i) for i in point)
    else:
        return tuple(math.radians(i) for i in point)


class SPointField(models.Field):
    description = "A pgsphere spoint as a tuple (ra, dec) in degrees"

    def db_type(self, connection):
        return "spoint"

    def to_python(self, value):
        if value is None:
            return value
        return str(value)

    def from_db_value(self, value, expression, connection, context=None):
        if value is None:
            return value
        return parse_spoint(value, to_deg=True)

    def get_db_prep_value(self, value, connection, prepared=True):
        if value is None:
            return value
        return str(parse_spoint(value, to_deg=False))

    def get_prep_lookup(self, lookup_type, value):
        if lookup_type == "inradius":
            # value will be a tuple ((ra, dec), radius)
            point, radius = value
            return "<{0}, {1}>".format(
                tuple(math.radians(x) for x in point), math.radians(radius)
            )
        else:
            raise TypeError("Lookup type %r not supported." % lookup_type)


@SPointField.register_lookup
class SPointIn(models.Lookup):
    lookup_name = "inradius"

    def as_sql(self, compiler, connection):
        lhs, params = self.process_lhs(compiler, connection)
        rhs, rhs_params = self.process_rhs(compiler, connection)
        params.extend(rhs_params)
        return "%s @ scircle %s" % (lhs, rhs), params

    def process_rhs(self, compiler, connection):
        _, (((ra, dec), radius),) = super().process_rhs(compiler, connection)
        ra, dec = parse_spoint((ra, dec), to_deg=False)
        radius = math.radians(radius)
        return ("(spoint(%s, %s), %s)", (ra, dec, radius))


class Distance(Func):
    template = "%(expressions)s"
    arg_joiner = "<->"
    arity = 2
    output_field = models.FloatField()

    def as_sql(
        self,
        compiler,
        connection,
        function=None,
        template=None,
        arg_joiner=None,
        **extra_context,
    ):
        sql, ((ra, dec),) = super().as_sql(
            compiler,
            connection,
            function,
            template,
            arg_joiner,
            **extra_context,
        )

        lhs, rhs = sql.split(self.arg_joiner)
        rhs = "spoint(%s, %s)"
        sql = self.arg_joiner.join((lhs, rhs))

        ra, dec = parse_spoint((ra, dec), to_deg=False)

        return sql, (ra, dec)
