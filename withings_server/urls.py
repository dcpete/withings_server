"""
URL configuration for withings_server project.

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
from django.contrib import admin
from django.urls import path, include
from django.conf import settings

from withings import views as withingsviews
 
context_root = settings.WITHINGS_CONTEXT_ROOT + '/'

urlpatterns = [
    #path(context_root, include(router.urls)),
    path(context_root, withingsviews.oauth2),
    path(context_root + 'userinfo/', withingsviews.UserInfoViewSet.as_view({'get': 'list'}), name='userinfo'),
    path(context_root + 'device/', withingsviews.DeviceViewSet.as_view({'get': 'list'}), name='device'),
    path(context_root + 'experiment/', withingsviews.ExperimentViewSet.as_view({'get': 'list'}), name='experiment'),
    path(context_root + 'rawdatarecord/', withingsviews.RawdataRecordViewSet.as_view({'get': 'list'}), name='rawdatarecord'),
    path(context_root + 'admin/', admin.site.urls),
    path(context_root + 'api-auth/', include('rest_framework.urls', namespace='rest_framework')),    
    path(context_root + 'oauth2/', withingsviews.oauth2),
    path(context_root + 'callback/', withingsviews.callback2),
    path(context_root + 'getdevices/', withingsviews.getdevices),
    path(context_root + 'getrawdata/', withingsviews.get_rawdata),
    path(context_root + 'activate/', withingsviews.activate),
    path(context_root + 'experiments/', withingsviews.withings_experiments),
]
