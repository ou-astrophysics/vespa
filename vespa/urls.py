"""vespa URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from typing import List
from django.contrib import admin
from django.urls import path
from django.views.generic.base import TemplateView
from django.views.generic.list import ListView
from django.views.generic import DetailView
from django.views.generic.dates import ArchiveIndexView, YearArchiveView, MonthArchiveView, DayArchiveView, DateDetailView

from django.conf import settings
from django.conf.urls.static import static

import blog.models
import blog.views
import starcatalogue.models
import starcatalogue.views
import waspstatic.views

blog_context = {
    'categories': blog.models.Category.objects.all(),
    'years': blog.models.Article.objects.all().datetimes('date_created', 'year')
}

urlpatterns = [
    path('', TemplateView.as_view(template_name='index.html'), name='index'),

    path('about/', waspstatic.views.AboutView.as_view(), name='about'),
    path('exoplanets/', TemplateView.as_view(template_name='waspstatic/exoplanets.html'), name='exoplanets'),
    path('black-hole-hunters/', TemplateView.as_view(template_name='waspstatic/black-hole-hunters.html'), name='black-hole-hunters'),

    path('vespa/', starcatalogue.views.StarListView.as_view(template_name = 'starcatalogue/index.html'), name='vespa'),
    path('vespa/browse/', starcatalogue.views.StarListView.as_view(), name='browse'),
    path('vespa/data-releases/', ListView.as_view(
        queryset=starcatalogue.exports.DataExport.objects.filter(in_data_archive=True).order_by('-created'),
        template_name='starcatalogue/data_releases.html'
    ), name='data_releases'),
    path('vespa/export/', starcatalogue.views.GenerateExportView.as_view(), name='generate_export'),
    path('vespa/export/<str:pk>/', DetailView.as_view(model=starcatalogue.models.DataExport), name='view_export'),
    path('vespa/source/<str:swasp_id>/', starcatalogue.views.SourceView.as_view(), name='view_source'),

    path('blog/', ArchiveIndexView.as_view(
        model=blog.models.Article,
        paginate_by=10,
        date_field="date_created",
        extra_context=blog_context,
    ), name='blog'),
    path('blog/<int:year>/', YearArchiveView.as_view(
        model=blog.models.Article,
        paginate_by=10,
        date_field="date_created",
        make_object_list=True,
        extra_context=blog_context,
    ), name='blog'),
    path('blog/<int:year>/<str:month>/', MonthArchiveView.as_view(
        model=blog.models.Article,
        paginate_by=10,
        date_field="date_created",
        extra_context=blog_context,
    ), name='blog'),
    path('blog/<int:year>/<str:month>/<int:day>/', DayArchiveView.as_view(
        model=blog.models.Article,
        paginate_by=10,
        date_field="date_created",
        extra_context=blog_context,
    ), name='blog'),
    path('blog/<int:year>/<str:month>/<int:day>/<str:slug>/', DateDetailView.as_view(
        model=blog.models.Article,
        date_field="date_created",
        allow_future=True,
        extra_context=blog_context,
    ), name='blog_article_detail'),
        path('blog/<str:category>/', blog.views.CategoryListView.as_view(
        paginate_by=10,
        extra_context=blog_context,
    ), name='blog'),

    path('admin/', admin.site.urls),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
