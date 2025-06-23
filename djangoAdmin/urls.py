"""
URL configuration for djangoAdmin project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
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

# from django.contrib import admin
from django.urls import path, include, re_path
from django.views.static import serve

from djangoAdmin import settings
from djangoAdmin.utils.views import StatisticsView, ImageUploadView

urlpatterns = [
    #    path("admin/", admin.site.urls),
    path('api/user/', include('apps.user.urls')),
    path('api/role/', include('apps.role.urls')),
    path('api/menu/', include('apps.menu.urls')),
    path('api/blog/', include('apps.blog.urls')),
    path('api/statistics/', StatisticsView.as_view(), name='statistics'),
    path('api/upload-image/', ImageUploadView.as_view(), name='upload-image'),

    re_path('api/media/(?P<path>.*)', serve, {'document_root': settings.MEDIA_ROOT}, name='media')
]
