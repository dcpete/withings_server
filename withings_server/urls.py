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

from rest_framework import routers

from withings import views as withingsviews
 
router = routers.DefaultRouter()

deploy_path = settings.WITHINGS_DEPLOY_PATH + '/'

router.register(r'userinfo', withingsviews.UserInfoViewSet)
router.register(r'device', withingsviews.DeviceViewSet)
router.register(r'experiment', withingsviews.ExperimentViewSet)
router.register(r'rawdatarecord', withingsviews.RawdataRecordViewSet)

urlpatterns = [
    path(deploy_path, include(router.urls)),
    path(deploy_path + 'admin/', admin.site.urls),
    path(deploy_path + 'api-auth/', include('rest_framework.urls', namespace='rest_framework')),    
    path(deploy_path + 'oauth2/', withingsviews.oauth2),
    path(deploy_path + 'callback/', withingsviews.callback2),
    path(deploy_path + 'getdevices/', withingsviews.getdevices),
    path(deploy_path + 'getrawdata/', withingsviews.get_rawdata),
    path(deploy_path + 'activate/', withingsviews.activate),
    path(deploy_path + 'experiments/', withingsviews.withings_experiments),
]
