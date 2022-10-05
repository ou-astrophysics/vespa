from django.contrib import admin

from visittracker.models import TrackedVisit


class TrackedVisitAdmin(admin.ModelAdmin):
    date_hierarchy = "created"
    list_display = (
        "url",
        "source",
        "created",
    )
    search_fields = ("url",)
    list_filter = (
        "source",
        "url",
    )


admin.site.register(TrackedVisit, TrackedVisitAdmin)
