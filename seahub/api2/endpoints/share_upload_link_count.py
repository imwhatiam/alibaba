# Copyright (c) 2012-2016 Seafile Ltd.
import logging

from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from seahub.api2.authentication import TokenAuthentication
from seahub.api2.throttling import UserRateThrottle

from seahub.share.models import FileShare, UploadLinkShare

logger = logging.getLogger(__name__)

def get_share_upload_link_count(username):
    share_link_count = FileShare.objects.filter(username=username).count()
    upload_link_count = UploadLinkShare.objects.filter(username=username).count()
    return share_link_count + upload_link_count


class ShareUploadLinkCount(APIView):

    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)
    throttle_classes = (UserRateThrottle,)

    def get(self, request):
        """ Get link count of both share-link and upload-link.
        """

        username = request.user.username
        result = {}
        result['count'] = get_share_upload_link_count(username)

        return Response(result)
