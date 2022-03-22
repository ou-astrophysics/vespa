from itertools import chain
from django.contrib import admin

from starcatalogue.exports import DataExport
from starcatalogue.models import (
    Star,
    FoldedLightcurve,
    ZooniverseSubject,
    AggregatedClassification,
    DataRelease,
)


class DataExportAdmin(admin.ModelAdmin):
    date_hierarchy = "created"
    list_display = (
        "id",
        "created",
        "data_version",
        "export_status",
        "in_data_archive",
    )
    list_filter = ("in_data_archive", "export_status", "data_version")
    fields = (
        "in_data_archive",
        "doi",
        "data_version",
        "export_file",
        ("min_period", "max_period"),
        ("min_magnitude", "max_magnitude"),
        ("min_amplitude", "max_amplitude"),
        ("certain_period", "uncertain_period"),
        ("min_classifications", "max_classifications"),
        ("type_pulsator", "type_rotator", "type_ew", "type_eaeb", "type_unknown"),
        ("search", "search_radius"),
    )
    readonly_fields = fields[2:4] + tuple(f for f in chain.from_iterable(fields[4:]))
    ordering = ("-created",)


admin.site.register(DataExport, DataExportAdmin)


class FoldedLightcurveAdmin(admin.ModelAdmin):
    list_display = ("star", "period_number", "period_length", "sigma", "chi_squared")
    search_fields = ("star__superwasp_id",)
    fields = (
        ("star", "zooniversesubject"),
        ("period_number", "period_length"),
        ("sigma", "chi_squared"),
        ("image_file", "thumbnail_file", "image_version"),
    )
    readonly_fields = tuple(f for f in chain.from_iterable(fields))
    list_filter = ("image_version",)


admin.site.register(FoldedLightcurve, FoldedLightcurveAdmin)


class FoldedLightcurveInline(admin.StackedInline):
    model = FoldedLightcurve
    fields = FoldedLightcurveAdmin.fields[1:]
    readonly_fields = tuple(f for f in chain.from_iterable(fields))
    extra = 0
    max_num = 0
    can_delete = False
    show_change_link = True


class StarAdmin(admin.ModelAdmin):
    list_display = (
        "superwasp_id",
        "image_version",
        "json_version",
        "stats_version",
    )
    search_fields = ("superwasp_id",)
    fields = (
        "stats_version",
        ("_min_magnitude", "_mean_magnitude", "_max_magnitude", "_amplitude"),
        ("fits_file", "fits_error_count"),
        ("image_file", "image_version"),
        ("json_file", "json_version"),
    )
    readonly_fields = fields[0:1] + tuple(f for f in chain.from_iterable(fields[1:]))
    inlines = (FoldedLightcurveInline,)


admin.site.register(Star, StarAdmin)


class ZooniverseSubjectAdmin(admin.ModelAdmin):
    list_display = (
        "zooniverse_id",
        "lightcurve",
        "subject_set_id",
        "retired_at",
        "metadata_version",
    )
    search_fields = (
        "zooniverse_id",
        "lightcurve__star__superwasp_id",
        "subject_set_id",
    )
    list_filter = (
        "metadata_version",
        "subject_set_id",
    )
    fields = (
        "lightcurve",
        "subject_set_id",
        "retired_at",
        "image_location",
        "metadata_version",
        "talk_url",
    )
    readonly_fields = fields


admin.site.register(ZooniverseSubject, ZooniverseSubjectAdmin)


class DataReleaseAdmin(admin.ModelAdmin):
    list_display = (
        "version",
        "active",
        "created",
        "aggregation_finished",
        "pending_stars",
    )
    readonly_fields = ("aggregation_finished", "pending_stars")
    fields = (
        "version",
        "active",
        "active_at",
        "aggregation_finished",
        "pending_stars",
    )


admin.site.register(DataRelease, DataReleaseAdmin)


class AggregatedClassificationAdmin(admin.ModelAdmin):
    list_display = (
        "lightcurve",
        "data_release",
        "classification",
        "classification_count",
    )
    search_fields = ("lightcurve__star__superwasp_id",)
    list_filter = ("classification", "period_uncertainty", "data_release__version")
    fields = (
        "classification",
        "period_uncertainty",
        "classification_count",
    )
    readonly_fields = fields


admin.site.register(AggregatedClassification, AggregatedClassificationAdmin)
