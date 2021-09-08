from django.contrib import admin

from blog.models import Article


class ArticleAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("title",)}
    date_hierarchy = 'date_created'
    list_display = ('title', 'date_created', 'date_updated', 'author')

    def save_model(self, request, obj, form, change):
        obj.author = request.user
        super().save_model(request, obj, form, change)

admin.site.register(Article, ArticleAdmin)