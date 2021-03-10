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
from django.contrib import admin
from django.urls import path
from django.views.generic.base import TemplateView

import starcatalogue.views
import waspstatic.views

urlpatterns = [
    path('', TemplateView.as_view(template_name='index.html'), name='index'),
    path('exoplanets/', TemplateView.as_view(template_name='waspstatic/exoplanets.html'), name='exoplanets'),
    path('vespa/', starcatalogue.views.IndexListView.as_view(), name='vespa'),
    path('vespa/browse/', starcatalogue.views.StarListView.as_view(), name='browse'),
    path('vespa/download/', starcatalogue.views.DownloadView.as_view(), name='download'),
    path('vespa/export/', starcatalogue.views.GenerateExportView.as_view(), name='generate_export'),
    path('vespa/export/<str:pk>/', starcatalogue.views.DataExportview.as_view(), name='view_export'),
    path('about/', waspstatic.views.AboutView.as_view(), name='about'),
    path('admin/', admin.site.urls),
]
