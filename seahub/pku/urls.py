# Copyright (c) 2012-2016 Seafile Ltd.

from django.conf.urls import url
from seahub.pku.views import pku_iaaa_login, pku_iaaa_callback

urlpatterns = [
    url(r'iaaa-login/$', pku_iaaa_login, name='pku_iaaa_login'),
    url(r'iaaa-callback/$', pku_iaaa_callback, name='pku_iaaa_callback'),
]
