from django.contrib import admin

from visittracker.models import TrackedVisit


class TrackedVisitAdmin(admin.ModelAdmin):
    date_hierarchy = "created"
    list_display = (
        "url",
        "created",
    )
    search_fields = ("url",)
    list_filter = ("url",)


admin.site.register(TrackedVisit, TrackedVisitAdmin)
