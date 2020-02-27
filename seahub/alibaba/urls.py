# Copyright (c) 2012-2018 Seafile Ltd.

from django.conf.urls import url
from seahub.alibaba.views import AlibabaUserEditFileView, \
        AlibabaImportGroupMembers, alibaba_citrix

urlpatterns = [
    url(r'^api/user-edit-file/$', AlibabaUserEditFileView.as_view(), name="alibaba-api-user-edit-file"),
    url(r'^api/groups/(?P<group_id>\d+)/members/import/$', AlibabaImportGroupMembers.as_view(), name="alibaba-import-group-members"),
    url(r'^citrix/$', alibaba_citrix, name="alibaba-citrix"),
]
