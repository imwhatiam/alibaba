# Copyright (c) 2012-2018 Seafile Ltd.
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import os
import stat
import json
import csv
import logging
import chardet
import StringIO
import hmac
import time
import random
import requests
import posixpath
import urllib

import hashlib
from datetime import datetime

from django.db.models import Q
from django.shortcuts import render
from django.utils.translation import ugettext as _
from django.http import HttpResponseRedirect

from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from seaserv import seafile_api, ccnet_api

from seahub.api2.throttling import UserRateThrottle
from seahub.api2.authentication import TokenAuthentication
from seahub.api2.utils import api_error

from seahub.utils import normalize_file_path, gen_file_get_url, \
        get_fileserver_root
from seahub.views import check_folder_permission
from seahub.auth.decorators import login_required
from seahub.group.utils import is_group_member, is_group_admin_or_owner
from seahub.group.signals import add_user_to_group
from seahub.share.models import FileShare
from seahub.avatar.util import get_alibaba_user_avatar_url
from seahub.base.templatetags.seahub_tags import email2nickname
from seahub.tags.models import FileUUIDMap

from seahub.alibaba.models import AlibabaProfile, AlibabaUserEditFile

from seahub.alibaba.settings import ALIBABA_WATERMARK_KEY_ID, \
        ALIBABA_WATERMARK_SECRET, ALIBABA_WATERMARK_SERVER_NAME, \
        ALIBABA_WATERMARK_BASE_URL, ALIBABA_WATERMARK_MARK_MODE, \
        ALIBABA_WATERMARK_VISIBLE_TEXT, ALIBABA_WATERMARK_EXTEND_PARAMS, \
        ALIBABA_WATERMARK_FILE_SIZE_LIMIT

from seahub.alibaba.settings import WINDOWS_CLIENT_PUBLIC_DOWNLOAD_URL, \
        WINDOWS_CLIENT_VERSION, APPLE_CLIENT_PUBLIC_DOWNLOAD_URL, \
        APPLE_CLIENT_VERSION, WINDOWS_CLIENT_PUBLIC_DOWNLOAD_URL_EN, \
        WINDOWS_CLIENT_VERSION_EN, APPLE_CLIENT_PUBLIC_DOWNLOAD_URL_EN, \
        APPLE_CLIENT_VERSION_EN, ALIBABA_ENABLE_CITRIX, ALIBABA_CITRIX_ICA_URL, \
        ALIBABA_WATERMARK_PATH_FOR_DOWNLOAD_FILE_TO_LOCAL

logger = logging.getLogger(__name__)

### utils ###

def get_dir_file_recursively(username, repo_id, path, all_dirs):
    dir_id = seafile_api.get_dir_id_by_path(repo_id, path)
    if not dir_id:
        return [{'parent_dir': '/', 'name': os.path.basename(path)}]

    dirs = seafile_api.list_dir_with_perm(repo_id, path,
            dir_id, username, -1, -1)

    for dirent in dirs:
        entry = {}
        if not stat.S_ISDIR(dirent.mode):
            entry["parent_dir"] = path
            entry["name"] = dirent.obj_name
            all_dirs.append(entry)

        if stat.S_ISDIR(dirent.mode):
            sub_path = posixpath.join(path, dirent.obj_name)
            get_dir_file_recursively(username, repo_id, sub_path, all_dirs)

    return all_dirs

def alibaba_get_zip_download_url(username, repo_id, parent_path,
        dirent_name_list, zip_token):

    # generate zip file name
    now = datetime.now()
    now_date = now.strftime('%Y-%m-%d')
    filename = 'documents-export-%s.zip' % now_date

    # query zip progress
    zipped = 0
    total = 1
    while zipped < total:
        time.sleep(1)
        progress = seafile_api.query_zip_progress(zip_token)
        json_resp = json.loads(progress)
        zipped = json_resp['zipped']
        total = json_resp['total']

    # get zip_packet_size field after finish zip
    progress = seafile_api.query_zip_progress(zip_token)
    json_resp = json.loads(progress)

    # generate zip download url
    fileserver_root = get_fileserver_root()
    fileserver_root = fileserver_root.rstrip('/')
    download_url = '%s/zip/%s' % (fileserver_root, zip_token)

    # check if size exceed limit
    if 'zip_packet_size' not in json_resp:
        logger.error('zip_packet_size field not returned.')
        logger.error(json_resp)
        return {'success': True, 'url': download_url}

    if 'zip_packet_size' in json_resp:
        file_size = json_resp['zip_packet_size']
        if file_size > ALIBABA_WATERMARK_FILE_SIZE_LIMIT * 1024 * 1024:
            return {'success': True, 'url': download_url}

    profile = AlibabaProfile.objects.get_profile(username)

    sub_item_path_list = []
    for dirent_name in dirent_name_list:
        dirent_name = dirent_name.strip('/')
        sub_item_list = get_dir_file_recursively(username, repo_id,
                posixpath.join(parent_path, dirent_name), [])

        for item in sub_item_list:
            sub_item_path_list.append(posixpath.join(item['parent_dir'], item['name']))

    invisible_text = {
        "operatorId": profile.work_no or '',
        "operatorType": "aliempid",
        "operatorName": profile.emp_name or '',
        "operatorNick": profile.nick_name or '',
        "labelInfo": {
            "businessInfo": {
                "repo_owner": seafile_api.get_repo_owner(repo_id),
                "repo_id": repo_id,
                "parent_path": parent_path,
                "sub_item_path_list": sub_item_path_list,
            },
            "fileInfo": {
                "fileId": '%s_%s' % (repo_id, parent_path),
                "fileName": filename,
                "fileSize": file_size,
                "fileType": filename.split('.')[-1],
            },
        }
    }

    extend_params = ALIBABA_WATERMARK_EXTEND_PARAMS
    extend_params.update({
        "Content-Disposition":"attachment;filename=%s" % filename
        })

    # make watermark
    body = json.dumps({
        'carrierLink': download_url,
        'markMode': 'waterm_document_1',
        'scene': 'datasec',
        'invisibleText': json.dumps(invisible_text),
        'visibleText': ALIBABA_WATERMARK_VISIBLE_TEXT,
        'extendParams': extend_params
    })

    ts = str(int(time.time() * 1000))
    nonce = str(random.randint(1000, 9999))
    hmac_key = ALIBABA_WATERMARK_SECRET + ts + nonce
    sign = hmac.new(key=bytes(hmac_key), msg=bytes(body), digestmod=hashlib.md5).hexdigest()
    headers = {
        'time': ts,
        'nonce': nonce,
        'sign': sign,
        'Content-Type': 'application/json; charset=utf-8'
    }
    url = '%s/%s?key=%s' % (ALIBABA_WATERMARK_BASE_URL,
            ALIBABA_WATERMARK_SERVER_NAME, ALIBABA_WATERMARK_KEY_ID)

    try:
        resp = requests.post(url, data=body, headers=headers)
        json_resp = json.loads(resp.content)
        return {'success': True, 'url': json_resp['data']['carrierLink']}
    except Exception as e:
        logger.error(e)
        logger.error(json_resp)
        return {'success': False, 'error_msg': json_resp['msg']}

def alibaba_get_file_download_url(username, repo_id, file_path, file_id, access_token):

    repo = seafile_api.get_repo(repo_id)
    if repo.is_virtual:
        repo_id = repo.origin_repo_id
        file_path = posixpath.join(repo.origin_path, file_path.strip('/'))

    file_path = normalize_file_path(file_path)
    parent_dir = os.path.dirname(file_path)
    filename = os.path.basename(file_path)
    file_uuid_map = FileUUIDMap.objects.get_or_create_fileuuidmap(repo_id,
                    parent_dir, filename, False)
    file_uuid = file_uuid_map.uuid.hex

    download_url = gen_file_get_url(access_token, filename)

    profile = AlibabaProfile.objects.get_profile(username)
    dirent = seafile_api.get_dirent_by_path(repo_id, file_path)
    invisible_text = {
        "operatorId": profile.work_no or '',
        "operatorType": "aliempid",
        "operatorName": profile.emp_name or '',
        "operatorNick": profile.nick_name or '',
        "labelInfo": {
            "businessInfo": {
                "repo_owner": seafile_api.get_repo_owner(repo_id),
                "repo_id": repo_id,
                "file_path": file_path,
            },
            "fileInfo": {
                "fileId": file_uuid,
                "fileName": filename,
                "fileSize": dirent.size if dirent else '',
                "fileType": filename.split('.')[-1],
            },
        }
    }

    extend_params = ALIBABA_WATERMARK_EXTEND_PARAMS

    from django.utils.http import urlquote
    content_disposition = "attachment; filename*=UTF-8''" + urlquote(filename)
    extend_params.update({
        "Content-Disposition": content_disposition
        })

    # make watermark
    body = json.dumps({
        'carrierLink': download_url,
        'markMode': ALIBABA_WATERMARK_MARK_MODE[filename.split('.')[-1].lower()],
        'scene': 'datasec',
        'invisibleText': json.dumps(invisible_text),
        'visibleText': ALIBABA_WATERMARK_VISIBLE_TEXT,
        'extendParams': extend_params
    })

    ts = str(int(time.time() * 1000))
    nonce = str(random.randint(1000, 9999))
    hmac_key = ALIBABA_WATERMARK_SECRET + ts + nonce
    sign = hmac.new(key=bytes(hmac_key), msg=bytes(body), digestmod=hashlib.md5).hexdigest()
    headers = {
        'time': ts,
        'nonce': nonce,
        'sign': sign,
        'Content-Type': 'application/json; charset=utf-8'
    }
    url = '%s/%s?key=%s' % (ALIBABA_WATERMARK_BASE_URL,
            ALIBABA_WATERMARK_SERVER_NAME, ALIBABA_WATERMARK_KEY_ID)

    try:
        resp = requests.post(url, data=body, headers=headers)
        json_resp = json.loads(resp.content)
        return {'success': True, 'url': json_resp['data']['carrierLink']}
    except Exception as e:
        logger.error(e)
        logger.error(json_resp)
        return {'success': False, 'error_msg': json_resp['msg']}

def alibaba_download_file_to_local(username, repo_id, file_path, download_url):

    file_path = file_path.replace('/', '%2F')
    local_filename = "%s_%s_%s_%s" % (username, repo_id, file_path,
            datetime.now().strftime('%Y-%m-%dT%H:%M:%S'))
    local_filename = posixpath.join(ALIBABA_WATERMARK_PATH_FOR_DOWNLOAD_FILE_TO_LOCAL,
            local_filename)

    with requests.get(download_url, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=10240):
                if chunk: # filter out keep-alive new chunks
                    f.write(chunk)

    return local_filename

def alibaba_err_msg_when_unable_to_view_file(request, repo_id):

    repo_owner = seafile_api.get_repo_owner(repo_id)
    if request.LANGUAGE_CODE in ('zh-cn', 'zh-tw'):
        return "您没有权限查看此文件，请联系 %s 添加权限" % email2nickname(repo_owner)
    else:
        return "You don't have permission to view this file, \
                please contact %s to add permission" % email2nickname(repo_owner)

### page view ###
@login_required
def alibaba_client_download_view(request):

    return render(request, 'alibaba_client_download.html', {
            'windows_client_public_download_url': WINDOWS_CLIENT_PUBLIC_DOWNLOAD_URL,
            'windows_client_version': WINDOWS_CLIENT_VERSION,
            'apple_client_public_download_url': APPLE_CLIENT_PUBLIC_DOWNLOAD_URL,
            'apple_client_version': APPLE_CLIENT_VERSION,
            'windows_client_public_download_url_en': WINDOWS_CLIENT_PUBLIC_DOWNLOAD_URL_EN,
            'windows_client_version_en': WINDOWS_CLIENT_VERSION_EN,
            'apple_client_public_download_url_en': APPLE_CLIENT_PUBLIC_DOWNLOAD_URL_EN,
            'apple_client_version_en': APPLE_CLIENT_VERSION_EN,
        })

@login_required
def alibaba_edit_profile(request):
    """
    Show and edit user profile.
    """
    username = request.user.username
    profile = AlibabaProfile.objects.get_profile(username)
    init_dict = {}
    if profile:
        init_dict['personal_photo_url'] = get_alibaba_user_avatar_url(username)
        init_dict['emp_name'] = profile.emp_name or ''
        init_dict['nick_name'] = profile.nick_name or ''
        init_dict['post_name'] = profile.post_name or ''
        init_dict['post_name_en'] = profile.post_name_en or ''
        init_dict['dept_name'] = profile.dept_name or ''
        init_dict['dept_name_en'] = profile.dept_name_en or ''

    return render(request, 'alibaba/set_profile.html', init_dict)

@login_required
def alibaba_user_profile(request, username):

    profile = AlibabaProfile.objects.get_profile(username)
    init_dict = {}
    if profile:
        init_dict['personal_photo_url'] = get_alibaba_user_avatar_url(username)
        init_dict['emp_name'] = profile.emp_name or ''
        init_dict['nick_name'] = profile.nick_name or ''
        init_dict['work_no'] = profile.work_no or ''
        init_dict['post_name'] = profile.post_name or ''
        init_dict['post_name_en'] = profile.post_name_en or ''
        init_dict['dept_name'] = profile.dept_name or ''
        init_dict['dept_name_en'] = profile.dept_name_en or ''

    return render(request, 'alibaba/user_profile.html', init_dict)

### alibaba api ###
class AlibabaImportGroupMembers(APIView):
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)
    throttle_classes = (UserRateThrottle,)

    def post(self, request, group_id, format=None):
        """Import users to group.

        Permission checking:
        1. Only group admin/owner can add import group members
        """

        result = {}
        username = request.user.username

        # argument check
        uploaded_file = request.FILES['file']
        if not uploaded_file:
            error_msg = 'file invalid.'
            return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

        # recourse check
        group_id = int(group_id)
        group = ccnet_api.get_group(group_id)
        if not group:
            error_msg = _('Group does not exist')
            return api_error(status.HTTP_404_NOT_FOUND, error_msg)

        # check permission
        if not is_group_admin_or_owner(group_id, username):
            error_msg = 'permission denied.'
            return api_error(status.HTTP_403_FORBIDDEN, error_msg)

        # prepare work no list from uploaded file
        try:
            content = uploaded_file.read()
            encoding = chardet.detect(content)['encoding']
            if encoding != 'utf-8':
                content = content.decode(encoding, 'replace').encode('utf-8')

            filestream = StringIO.StringIO(content)
            reader = csv.reader(filestream)
        except Exception as e:
            logger.error(e)
            error_msg = 'Internal Server Error'
            return api_error(status.HTTP_500_INTERNAL_SERVER_ERROR, error_msg)

        work_no_list = []
        for row in reader:
            if not row:
                continue
            work_no = row[0].strip().lower()
            work_no_list.append(work_no)

        def alibaba_get_group_member_info(group_id, alibaba_profile):
            emp_name = alibaba_profile.emp_name
            nick_name = alibaba_profile.nick_name
            if nick_name:
                emp_nick_name = '%s(%s)' % (emp_name, nick_name)
            else:
                emp_nick_name = emp_name

            member_info = {
                'group_id': group_id,
                "name": emp_nick_name,
                'email': alibaba_profile.uid,
                "avatar_url": get_alibaba_user_avatar_url(alibaba_profile.uid),
            }
            return member_info

        is_cn = request.LANGUAGE_CODE in ('zh-cn', 'zh-tw')

        result = {}
        result['failed'] = []
        result['success'] = []

        # check work_no validation
        for work_no in work_no_list:

            # only digit in work_no string
            if len(work_no) < 6 and work_no.isdigit():
                work_no = '000000'[:6 - len(work_no)] + work_no

            alibaba_profile = AlibabaProfile.objects.get_profile_by_work_no(work_no)
            if not alibaba_profile or not alibaba_profile.uid:
                result['failed'].append({
                    'email': work_no,
                    'error_msg': '工号没找到。' if is_cn else 'Employee ID not found.'
                    })
                continue

            ccnet_email = alibaba_profile.uid
            if is_group_member(group_id, ccnet_email, in_structure=False):
                result['failed'].append({
                    'email': work_no,
                    'error_msg': '已经是群组成员。' if is_cn else 'Is already a group member.'
                    })
                continue

            try:
                ccnet_api.group_add_member(group_id, username, ccnet_email)
                member_info = alibaba_get_group_member_info(group_id,
                        alibaba_profile)
                result['success'].append(member_info)
            except Exception as e:
                logger.error(e)
                result['failed'].append({
                    'email': work_no,
                    'error_msg': _('Internal Server Error')
                    })

            add_user_to_group.send(sender=None,
                                group_staff=username,
                                group_id=group_id,
                                added_user=ccnet_email)

        return Response(result)


class AlibabaSearchUser(APIView):
    """ Search user from alibaba profile
    """
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)
    throttle_classes = (UserRateThrottle,)

    def get(self, request, format=None):

        q = request.GET.get('q', None)
        if not q:
            error_msg = 'q invalid.'
            return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

        # only digit in q string
        # search by work no
        if len(q) < 6 and q.isdigit():
            q = '000000'[:6 - len(q)] + q

        if '@' in q:
            q = q.split('@')[0]

        sorted_users = []
        username = request.user.username
        current_user_profile = AlibabaProfile.objects.get_profile(username)
        if not current_user_profile:
            # users.query
            users = AlibabaProfile.objects.filter(work_status='A').filter(
                    Q(emp_name__icontains=q) | Q(pinyin_name=q) | Q(work_no=q) |
                    Q(uid__startswith=q) | Q(emp_name_en__icontains=q) |
                    Q(nick_name__icontains=q) | Q(pinyin_nick=q)).order_by('dept_name')[:50]

            sorted_users = sorted(users,
                    key=lambda user: len(user.dept_name.split('-')), reverse=True)
        else:
            users = AlibabaProfile.objects.filter(work_status='A').filter(
                    Q(emp_name__icontains=q) | Q(pinyin_name=q) | Q(work_no=q) |
                    Q(uid__startswith=q) | Q(emp_name_en__icontains=q) |
                    Q(nick_name__icontains=q) | Q(pinyin_nick=q))[:50]

            # current user's dept is "A-B-C-D"
            current_user_dept_name = current_user_profile.dept_name

            # [u'A', u'A-B', u'A-B-C', u'A-B-C-D']
            current_user_dept_name_structure = []
            for idx, val in enumerate(current_user_dept_name.split('-')):
                if idx == 0:
                    current_user_dept_name_structure.append(val)
                else:
                    current_user_dept_name_structure.append(
                            current_user_dept_name_structure[-1] + '-' + val)

            for item in reversed(current_user_dept_name_structure):

                dept_match_list = []
                for user in users:
                    if user in sorted_users:
                        continue

                    user_dept_name = user.dept_name
                    if user_dept_name.startswith(item):
                        dept_match_list.append(user)

                dept_match_list = sorted(dept_match_list,
                        key=lambda user: len(user.dept_name.split('-')))

                sorted_users.extend(dept_match_list)

            dept_unmatch_list = []
            for user in users:
                if user not in sorted_users:
                    dept_unmatch_list.append(user)

            dept_unmatch_list = sorted(dept_unmatch_list,
                    key=lambda user: len(user.dept_name.split('-')))
            sorted_users.extend(dept_unmatch_list)

        result = []
        for user in sorted_users:

            if user.uid == username:
                continue

            user_info = {}
            user_info['uid'] = user.uid
            user_info['personal_photo_url'] = get_alibaba_user_avatar_url(user.uid)
            user_info['emp_name'] = user.emp_name or ''
            user_info['nick_name'] = user.nick_name or ''
            user_info['work_no'] = user.work_no or ''

            if request.LANGUAGE_CODE == 'zh-cn':
                user_info['post_name'] = user.post_name or ''
                user_info['dept_name'] = user.dept_name or ''
            else:
                user_info['post_name'] = user.post_name_en or ''
                user_info['dept_name'] = user.dept_name_en or ''

            result.append(user_info)

        return Response({"users": result})


class AlibabaUserEditFileView(APIView):

    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated, )
    throttle_classes = (UserRateThrottle, )

    def post(self, request):

        # argument check
        repo_id = request.data.get('repo_id', None)
        path = request.data.get('path', None)
        unique_id = request.data.get('unique_id', None)

        if not repo_id:
            error_msg = 'repo_id invalid.'
            return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

        if not path:
            error_msg = 'path invalid.'
            return api_error(status.HTTP_400_BAD_REQUEST, error_msg)
        path = normalize_file_path(path)

        if not unique_id:
            error_msg = 'unique_id invalid.'
            return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

        # resource check
        repo = seafile_api.get_repo(repo_id)
        if not repo:
            error_msg = 'Library %s not found.' % repo_id
            return api_error(status.HTTP_404_NOT_FOUND, error_msg)

        file_id = seafile_api.get_file_id_by_path(repo_id, path)
        if not file_id:
            error_msg = 'File %s not found.' % path
            return api_error(status.HTTP_404_NOT_FOUND, error_msg)

        # permission check
        if not check_folder_permission(request, repo_id, '/'):
            # if not has repo permisson, then check share link permisson
            share_link_token = request.data.get('share_link_token', None)
            if not share_link_token:
                error_msg = 'permission denied.'
                return api_error(status.HTTP_403_FORBIDDEN, error_msg)

            try:
                share_link = FileShare.objects.get(token=share_link_token)
            except FileShare.DoesNotExist:
                error_msg = 'permission denied.'
                return api_error(status.HTTP_403_FORBIDDEN, error_msg)

            share_link_repo_id = share_link.repo_id
            share_link_path = normalize_file_path(share_link.path)
            if repo_id != share_link_repo_id or path != share_link_path:
                log_error_info = 'request info (%s, %s) not equal to share link database info (%s, %s)' % \
                        (repo_id, path, share_link_repo_id, share_link_path)
                logger.error(log_error_info)
                error_msg = 'permission denied.'
                return api_error(status.HTTP_403_FORBIDDEN, error_msg)

            # check share link creator's repo permission to current file
            share_link_creator = share_link.username
            if not seafile_api.check_permission_by_path(repo_id, '/', share_link_creator):
                log_error_info = 'share link creator has no permission for (%s, %s)' % (repo_id, path)
                logger.error(log_error_info)
                error_msg = 'permission denied.'
                return api_error(status.HTTP_403_FORBIDDEN, error_msg)

        # add user view/edit file start time info
        username = request.user.username
        try:
            AlibabaUserEditFile.objects.add_start_edit_info(username, repo_id,
                    path, unique_id)
        except Exception as e:
            logger.error(e)
            error_msg = 'Internal Server Error'
            return api_error(status.HTTP_500_INTERNAL_SERVER_ERROR, error_msg)

        return Response({'success': True})

    def put(self, request):

        unique_id = request.data.get('unique_id', None)
        if not unique_id:
            error_msg = 'unique_id invalid.'
            return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

        info = AlibabaUserEditFile.objects.get_edit_info_by_unique_id(unique_id)
        if not info:
            error_msg = 'User view/edit file info %s not found.' % unique_id
            return api_error(status.HTTP_404_NOT_FOUND, error_msg)

        # permission check
        repo_id = info.repo_id
        path = normalize_file_path(info.path)
        if not check_folder_permission(request, repo_id, '/'):

            share_link_token = request.data.get('share_link_token', None)
            if not share_link_token:
                error_msg = 'permission denied.'
                return api_error(status.HTTP_403_FORBIDDEN, error_msg)

            try:
                share_link = FileShare.objects.get(token=share_link_token)
            except FileShare.DoesNotExist:
                error_msg = 'permission denied.'
                return api_error(status.HTTP_403_FORBIDDEN, error_msg)

            share_link_repo_id = share_link.repo_id
            share_link_path = normalize_file_path(share_link.path)
            if repo_id != share_link_repo_id or path != share_link_path:
                log_error_info = 'request info (%s, %s) not equal to share link database info (%s, %s)' % \
                        (repo_id, path, share_link_repo_id, share_link_path)
                logger.error(log_error_info)
                error_msg = 'permission denied.'
                return api_error(status.HTTP_403_FORBIDDEN, error_msg)

            # check share link creator's repo permission to current file
            share_link_creator = share_link.username
            if not seafile_api.check_permission_by_path(repo_id, '/', share_link_creator):
                log_error_info = 'share link creator has no permission for (%s, %s)' % (repo_id, path)
                logger.error(log_error_info)
                error_msg = 'permission denied.'
                return api_error(status.HTTP_403_FORBIDDEN, error_msg)

        try:
            AlibabaUserEditFile.objects.complete_end_edit_info(unique_id)
        except Exception as e:
            logger.error(e)
            error_msg = 'Internal Server Error'
            return api_error(status.HTTP_500_INTERNAL_SERVER_ERROR, error_msg)

        return Response({'success': True})


@login_required
def alibaba_citrix(request):

    if not ALIBABA_ENABLE_CITRIX:
        error_msg = 'Citrix feature not enabled.'
        return api_error(status.HTTP_403_FORBIDDEN, error_msg)

    # parameter check
    repo_id = request.GET.get('repo_id', '')
    if not repo_id:
        error_msg = 'repo_id invalid.'
        return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

    path = request.GET.get('path', '')
    if not path:
        error_msg = 'repo_id invalid.'
        return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

    # resource check
    repo = seafile_api.get_repo(repo_id)
    if not repo:
        error_msg = 'Library %s not found.' % repo_id
        return api_error(status.HTTP_404_NOT_FOUND, error_msg)

    try:
        dirent = seafile_api.get_dirent_by_path(repo_id, path)
    except Exception as e:
        logger.error(e)
        error_msg = 'Internal Server Error'
        return api_error(status.HTTP_500_INTERNAL_SERVER_ERROR, error_msg)

    if not dirent:
        error_msg = 'Dirent %s not found.' % path
        return api_error(status.HTTP_404_NOT_FOUND, error_msg)

    # permission check
    if not check_folder_permission(request, repo_id, '/'):
        error_msg = 'permission denied.'
        return api_error(status.HTTP_403_FORBIDDEN, error_msg)

    username = request.user.username

    def get_repo_type(username, repo_id):

        owned_repos = seafile_api.get_owned_repo_list(username)
        if repo_id in [r.id for r in owned_repos]:
            return 'owned'

        shared_repos = seafile_api.get_share_in_repo_list(username, -1, -1)
        if repo_id in [r.id for r in shared_repos]:
            return 'shared'

        group_repos = seafile_api.get_group_repos_by_user(username)
        if repo_id in [r.id for r in group_repos]:
            return 'group'

        if seafile_api.is_inner_pub_repo(repo_id):
            return 'public'

    repo_type = get_repo_type(username, repo_id)
    parameters = {
        'username': username.split('@')[0],
        'repoType': repo_type,
        'file': path,
        'repoName': repo.repo_name,
    }
    encoded_parameters = urllib.urlencode(parameters)
    url = '%s?%s' % (ALIBABA_CITRIX_ICA_URL, encoded_parameters)
    return HttpResponseRedirect(url)
