# Copyright (c) 2012-2016 Seafile Ltd.
import logging
import json
import stat
import posixpath
import requests
import urllib
from datetime import datetime

from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from django.conf import settings
from django.http import HttpResponse
from django.utils.translation import ugettext as _
from django.core.urlresolvers import reverse

from seahub.api2.throttling import UserRateThrottle
from seahub.api2.authentication import TokenAuthentication
from seahub.api2.utils import api_error

from seahub.views import check_folder_permission
from seahub.views.file import send_file_access_msg
from seahub.utils import is_windows_operating_system
from seahub.utils.repo import parse_repo_perm

import seaserv
from seaserv import seafile_api

from seahub.alibaba.settings import ALIBABA_ENABLE_WATERMARK
if ALIBABA_ENABLE_WATERMARK:
    from seahub.alibaba.settings import ALIBABA_WATERMARK_IS_DOWNLOAD_SERVER
    from seahub.alibaba.settings import ALIBABA_WATERMARK_DOWNLOAD_SERVER_DOMAIN
    from seahub.alibaba.settings import ALIBABA_WATERMARK_USE_EXTRA_DOWNLOAD_SERVER
    from seahub.alibaba.settings import ALIBABA_WATERMARK_DOWNLOAD_FILE_TO_LOCAL
    from seahub.alibaba.settings import ALIBABA_WATERMARK_PATH_FOR_DOWNLOAD_FILE_TO_LOCAL
    from seahub.alibaba.views import alibaba_get_zip_download_url

logger = logging.getLogger(__name__)

class ZipTaskView(APIView):

    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)
    throttle_classes = (UserRateThrottle,)

    def get(self, request, repo_id, format=None):
        """ Deprecated.

        Sometimes when user download too many files in one request,
        Nginx will return 414-Request-URI Too Large error.

        So, use the following POST request instead.
        Put all parameters in request body.
        """

        # argument check
        parent_dir = request.GET.get('parent_dir', None)
        if not parent_dir:
            error_msg = 'parent_dir invalid.'
            return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

        dirent_name_list = request.GET.getlist('dirents', None)
        if not dirent_name_list:
            error_msg = 'dirents invalid.'
            return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

        if len(dirent_name_list) == 1:
            download_type = 'download-dir'
        elif len(dirent_name_list) > 1:
            download_type = 'download-multi'
        else:
            error_msg = 'dirents invalid.'
            return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

        # recourse check
        repo = seafile_api.get_repo(repo_id)
        if not repo:
            error_msg = 'Library %s not found.' % repo_id
            return api_error(status.HTTP_404_NOT_FOUND, error_msg)

        if not seafile_api.get_dir_id_by_path(repo_id, parent_dir):
            error_msg = 'Folder %s not found.' % parent_dir
            return api_error(status.HTTP_404_NOT_FOUND, error_msg)

        # permission check
        if not check_folder_permission(request, repo_id, parent_dir):
            error_msg = 'Permission denied.'
            return api_error(status.HTTP_403_FORBIDDEN, error_msg)

        # get file server access token
        is_windows = 0
        if is_windows_operating_system(request):
            is_windows = 1

        if download_type == 'download-dir':
            dir_name = dirent_name_list[0].strip('/')
            full_dir_path = posixpath.join(parent_dir, dir_name)

            dir_id = seafile_api.get_dir_id_by_path(repo_id, full_dir_path)
            if not dir_id:
                error_msg = 'Folder %s not found.' % full_dir_path
                return api_error(status.HTTP_404_NOT_FOUND, error_msg)

            dir_size = 0

            if dir_size > seaserv.MAX_DOWNLOAD_DIR_SIZE:
                error_msg = _('Unable to download directory "%s": size is too large.') % dir_name
                return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

            fake_obj_id = {
                'obj_id': dir_id,
                'dir_name': dir_name,
                'is_windows': is_windows
            }

        if download_type == 'download-multi':
            dirent_list = []
            total_size = 0
            for dirent_name in dirent_name_list:
                dirent_name = dirent_name.strip('/')
                dirent_list.append(dirent_name)

                full_dirent_path = posixpath.join(parent_dir, dirent_name)
                current_dirent = seafile_api.get_dirent_by_path(repo_id, full_dirent_path)
                if not current_dirent:
                    continue

                if stat.S_ISDIR(current_dirent.mode):
                    total_size += 0
                else:
                    total_size += current_dirent.size

            if total_size > seaserv.MAX_DOWNLOAD_DIR_SIZE:
                error_msg = _('Total size exceeds limit.')
                return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

            fake_obj_id = {
                'parent_dir': parent_dir,
                'file_list': dirent_list,
                'is_windows': is_windows
            }

        username = request.user.username
        try:
            zip_token = seafile_api.get_fileserver_access_token(
                repo_id, json.dumps(fake_obj_id), download_type, username,
                use_onetime=settings.FILESERVER_TOKEN_ONCE_ONLY
            )
        except Exception as e:
            logger.error(e)
            error_msg = 'Internal Server Error'
            return api_error(status.HTTP_500_INTERNAL_SERVER_ERROR, error_msg)

        if not zip_token:
            error_msg = 'Internal Server Error'
            return api_error(status.HTTP_500_INTERNAL_SERVER_ERROR, error_msg)

        if len(dirent_name_list) > 10:
            send_file_access_msg(request, repo, parent_dir, 'web')
        else:
            for dirent_name in dirent_name_list:
                full_dirent_path = posixpath.join(parent_dir, dirent_name)
                send_file_access_msg(request, repo, full_dirent_path, 'web')

        if not ALIBABA_ENABLE_WATERMARK:
            return Response({'zip_token': zip_token})

        result = {}
        alibbaba_resp = alibaba_get_zip_download_url(username, repo_id, parent_dir,
                dirent_name_list, zip_token)
        if alibbaba_resp['success']:
            zip_download_url = alibbaba_resp['url']
            result['download_url'] = zip_download_url
        else:
            zip_token = seafile_api.get_fileserver_access_token(
                repo_id, json.dumps(fake_obj_id), download_type, username,
                use_onetime=settings.FILESERVER_TOKEN_ONCE_ONLY
            )
            result['zip_token'] = zip_token

        return Response(result)

    def post(self, request, repo_id, format=None):
        """ Get file server token for download-dir and download-multi.

        Permission checking:
        1. user with 'r' or 'rw' permission;
        """

        # argument check
        parent_dir = request.data.get('parent_dir', None)
        if not parent_dir:
            error_msg = 'parent_dir invalid.'
            return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

        dirent_name_list = request.data.getlist('dirents', None)
        if not dirent_name_list:
            error_msg = 'dirents invalid.'
            return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

        if len(dirent_name_list) == 1:
            download_type = 'download-dir'
        elif len(dirent_name_list) > 1:
            download_type = 'download-multi'
        else:
            error_msg = 'dirents invalid.'
            return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

        # recourse check
        repo = seafile_api.get_repo(repo_id)
        if not repo:
            error_msg = 'Library %s not found.' % repo_id
            return api_error(status.HTTP_404_NOT_FOUND, error_msg)

        if not seafile_api.get_dir_id_by_path(repo_id, parent_dir):
            error_msg = 'Folder %s not found.' % parent_dir
            return api_error(status.HTTP_404_NOT_FOUND, error_msg)

        # permission check
        if parse_repo_perm(check_folder_permission(request, repo_id, parent_dir)).can_download is False:
            error_msg = 'Permission denied.'
            return api_error(status.HTTP_403_FORBIDDEN, error_msg)

        if ALIBABA_ENABLE_WATERMARK and \
                ALIBABA_WATERMARK_USE_EXTRA_DOWNLOAD_SERVER and \
                not ALIBABA_WATERMARK_IS_DOWNLOAD_SERVER:
            params = '?parent_dir=%s' % urllib.quote(parent_dir.encode('utf-8'))
            for dirent_name in dirent_name_list:
                params += '&dirents=%s' % urllib.quote(dirent_name.encode('utf-8'))
            zip_task_url = reverse('api-v2.1-zip-task', args=[repo_id]) + params
            download_server_domain = ALIBABA_WATERMARK_DOWNLOAD_SERVER_DOMAIN.strip('/')
            full_zip_task_url= download_server_domain + zip_task_url
            resp = requests.get(full_zip_task_url, cookies=request.COOKIES)

            resp_json = resp.json()
            status_code = resp.status_code
            if status_code == 400:
                return api_error(status.HTTP_400_BAD_REQUEST, resp_json['error_msg'])
            if status_code == 403:
                return api_error(status.HTTP_403_FORBIDDEN, resp_json['error_msg'])
            if status_code == 404:
                return api_error(status.HTTP_404_NOT_FOUND, resp_json['error_msg'])
            if status_code == 500:
                return api_error(status.HTTP_500_INTERNAL_SERVER_ERROR, resp_json['error_msg'])

            return Response(resp.json())

        # get file server access token
        is_windows = 0
        if is_windows_operating_system(request):
            is_windows = 1

        if download_type == 'download-dir':
            dir_name = dirent_name_list[0].strip('/')
            full_dir_path = posixpath.join(parent_dir, dir_name)

            dir_id = seafile_api.get_dir_id_by_path(repo_id, full_dir_path)
            if not dir_id:
                error_msg = 'Folder %s not found.' % full_dir_path
                return api_error(status.HTTP_404_NOT_FOUND, error_msg)

            dir_size = 0

            if dir_size > seaserv.MAX_DOWNLOAD_DIR_SIZE:
                error_msg = 'Unable to download directory "%s": size is too large.' % dir_name
                return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

            fake_obj_id = {
                'obj_id': dir_id,
                'dir_name': dir_name,
                'is_windows': is_windows
            }

        if download_type == 'download-multi':
            dirent_list = []
            total_size = 0
            for dirent_name in dirent_name_list:
                dirent_name = dirent_name.strip('/')
                dirent_list.append(dirent_name)

                full_dirent_path = posixpath.join(parent_dir, dirent_name)
                current_dirent = seafile_api.get_dirent_by_path(repo_id, full_dirent_path)
                if not current_dirent:
                    continue

                if stat.S_ISDIR(current_dirent.mode):
                    total_size += 0
                else:
                    total_size += current_dirent.size

            if total_size > seaserv.MAX_DOWNLOAD_DIR_SIZE:
                error_msg = _('Total size exceeds limit.')
                return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

            fake_obj_id = {
                'parent_dir': parent_dir,
                'file_list': dirent_list,
                'is_windows': is_windows
            }

        username = request.user.username
        try:
            zip_token = seafile_api.get_fileserver_access_token(
                repo_id, json.dumps(fake_obj_id), download_type, username,
                use_onetime=settings.FILESERVER_TOKEN_ONCE_ONLY
            )
        except Exception as e:
            logger.error(e)
            error_msg = 'Internal Server Error'
            return api_error(status.HTTP_500_INTERNAL_SERVER_ERROR, error_msg)

        if not zip_token:
            error_msg = 'Internal Server Error'
            return api_error(status.HTTP_500_INTERNAL_SERVER_ERROR, error_msg)

        if len(dirent_name_list) > 10:
            send_file_access_msg(request, repo, parent_dir, 'web')
        else:
            for dirent_name in dirent_name_list:
                full_dirent_path = posixpath.join(parent_dir, dirent_name)
                send_file_access_msg(request, repo, full_dirent_path, 'web')

        if not ALIBABA_ENABLE_WATERMARK:
            return Response({'zip_token': zip_token})

        result = {}
        alibbaba_resp = alibaba_get_zip_download_url(username, repo_id, parent_dir,
                dirent_name_list, zip_token)
        if alibbaba_resp['success']:
            zip_download_url = alibbaba_resp['url']

#            if ALIBABA_WATERMARK_DOWNLOAD_FILE_TO_LOCAL and \
#                    ALIBABA_WATERMARK_PATH_FOR_DOWNLOAD_FILE_TO_LOCAL != '':
#                from seahub.alibaba.views import alibaba_download_file_to_local
#                try:
#                    local_filename = alibaba_download_file_to_local(username,
#                            repo_id, parent_dir, zip_download_url)
#                except Exception as e:
#                    logger.error(e)
#                else:
#                    response = HttpResponse(open(local_filename, "rb").read())
#                    zip_file_name = 'documents-export-%s' % datetime.now().strftime('%Y-%m-%d')
#                    content_disposition = "attachment; filename*=UTF-8''" + zip_file_name
#                    response['Content-Disposition'] = content_disposition
#                    return response

            result['download_url'] = zip_download_url
        else:
            zip_token = seafile_api.get_fileserver_access_token(
                repo_id, json.dumps(fake_obj_id), download_type, username,
                use_onetime=settings.FILESERVER_TOKEN_ONCE_ONLY
            )
            result['zip_token'] = zip_token

        return Response(result)
