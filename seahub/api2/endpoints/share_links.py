# Copyright (c) 2012-2016 Seafile Ltd.
# -*- coding: utf-8 -*-
import os
import stat
import logging
import posixpath
from constance import config
from dateutil.relativedelta import relativedelta

from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from django.utils import timezone
from django.utils.translation import ugettext as _
from django.utils.http import urlquote

from seaserv import seafile_api
from pysearpc import SearpcError

from seahub.api2.utils import api_error
from seahub.api2.authentication import TokenAuthentication
from seahub.api2.throttling import UserRateThrottle
from seahub.api2.permissions import CanGenerateShareLink, IsProVersion
from seahub.constants import PERMISSION_READ_WRITE
from seahub.share.models import FileShare, check_share_link_access
from seahub.utils import gen_shared_link, is_org_context, normalize_file_path, \
        normalize_dir_path, is_pro_version, get_file_type_and_ext, is_user_password_strong
from seahub.utils.file_op import if_locked_by_online_office
from seahub.utils.file_types import IMAGE, VIDEO, XMIND
from seahub.utils.timeutils import datetime_to_isoformat_timestr, \
        timestamp_to_isoformat_timestr
from seahub.utils.repo import parse_repo_perm
from seahub.thumbnail.utils import get_share_link_thumbnail_src
from seahub.settings import SHARE_LINK_EXPIRE_DAYS_MAX, \
        SHARE_LINK_EXPIRE_DAYS_MIN, SHARE_LINK_LOGIN_REQUIRED, \
        SHARE_LINK_EXPIRE_DAYS_DEFAULT, \
        ENABLE_SHARE_LINK_AUDIT, ENABLE_VIDEO_THUMBNAIL, \
        THUMBNAIL_ROOT
from seahub.wiki.models import Wiki

from seahub.share.settings import ENABLE_FILESHARE_CHECK
from seahub.share.signals import file_shared_link_created
from seahub.share.share_link_checking import check_share_link

logger = logging.getLogger(__name__)


def get_share_link_info(fileshare):
    data = {}
    token = fileshare.token

    repo_id = fileshare.repo_id
    try:
        repo = seafile_api.get_repo(repo_id)
    except Exception as e:
        logger.error(e)
        repo = None

    path = fileshare.path
    if path:
        obj_name = '/' if path == '/' else os.path.basename(path.rstrip('/'))
    else:
        obj_name = ''

    if fileshare.expire_date:
        expire_date = datetime_to_isoformat_timestr(fileshare.expire_date)
    else:
        expire_date = ''

    if fileshare.ctime:
        ctime = datetime_to_isoformat_timestr(fileshare.ctime)
    else:
        ctime = ''

    data['username'] = fileshare.username
    data['repo_id'] = repo_id
    data['repo_name'] = repo.repo_name if repo else ''

    data['path'] = path
    data['obj_name'] = obj_name
    data['is_dir'] = True if fileshare.s_type == 'd' else False

    data['token'] = token
    data['link'] = gen_shared_link(token, fileshare.s_type)
    data['view_cnt'] = fileshare.view_cnt
    data['ctime'] = ctime
    data['expire_date'] = expire_date
    data['is_expired'] = fileshare.is_expired()
    data['permissions'] = fileshare.get_permissions()
    data['password'] = fileshare.get_password()

    from seahub.share.models import FileShareExtraInfo
    if fileshare.pass_verify():
        data['status'] = 'pass'
        data['pass_time'] = fileshare.get_pass_time()
        extra_info = FileShareExtraInfo.objects.filter(share_link=fileshare)
        if len(extra_info) > 0:
            data['receivers'] = [x.sent_to for x in extra_info]
        else:
            data['receivers'] = []
    elif fileshare.is_verifing():
        data['status'] = 'verifing'
    elif fileshare.reject_verify():
        data['status'] = 'veto'
    else:
        data['status'] = ''

    data['verbose_status_str'] = fileshare.get_verbose_status_str()

    return data

def check_permissions_arg(request):
    permissions = request.data.get('permissions', None)
    if permissions is not None:
        if isinstance(permissions, dict):
            perm_dict = permissions
        elif isinstance(permissions, basestring):
            import json
            try:
                perm_dict = json.loads(permissions)
            except ValueError:
                error_msg = 'permissions invalid: %s' % permissions
                return api_error(status.HTTP_400_BAD_REQUEST, error_msg)
        else:
            error_msg = 'permissions invalid: %s' % permissions
            return api_error(status.HTTP_400_BAD_REQUEST, error_msg)
    else:
        perm_dict = None

    can_download = True
    can_edit = False

    if perm_dict is not None:
        can_download = perm_dict.get('can_download', True)
        can_edit = perm_dict.get('can_edit', False)

    if not can_edit and can_download:
        perm = FileShare.PERM_VIEW_DL

    if not can_edit and not can_download:
        perm = FileShare.PERM_VIEW_ONLY

    if can_edit and can_download:
        perm = FileShare.PERM_EDIT_DL

    if can_edit and not can_download:
        perm = FileShare.PERM_EDIT_ONLY

    return perm

class ShareLinks(APIView):

    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated, CanGenerateShareLink)
    throttle_classes = (UserRateThrottle,)

    def _generate_obj_id_and_type_by_path(self, repo_id, path):

        file_id = seafile_api.get_file_id_by_path(repo_id, path)
        if file_id:
            return (file_id, 'f')

        dir_id = seafile_api.get_dir_id_by_path(repo_id, path)
        if dir_id:
            return (dir_id, 'd')

        return (None, None)

    def get(self, request):
        """ Get all share links of a user.

        Permission checking:
        1. default(NOT guest) user;
        """

        # get all share links
        username = request.user.username
        fileshares = FileShare.objects.filter(username=username)

        repo_id = request.GET.get('repo_id', None)
        if repo_id:
            repo = seafile_api.get_repo(repo_id)
            if not repo:
                error_msg = 'Library %s not found.' % repo_id
                return api_error(status.HTTP_404_NOT_FOUND, error_msg)

            # filter share links by repo
            fileshares = filter(lambda fs: fs.repo_id == repo_id, fileshares)

            path = request.GET.get('path', None)
            if path:
                try:
                    obj_id, s_type = self._generate_obj_id_and_type_by_path(repo_id, path)
                except SearpcError as e:
                    logger.error(e)
                    error_msg = 'Internal Server Error'
                    return api_error(status.HTTP_500_INTERNAL_SERVER_ERROR, error_msg)

                if not obj_id:
                    if s_type == 'f':
                        error_msg = 'file %s not found.' % path
                    elif s_type == 'd':
                        error_msg = 'folder %s not found.' % path
                    else:
                        error_msg = 'path %s not found.' % path

                    return api_error(status.HTTP_404_NOT_FOUND, error_msg)

                # if path invalid, filter share links by repo
                if s_type == 'd' and path[-1] != '/':
                    path = path + '/'

                fileshares = filter(lambda fs: fs.path == path, fileshares)

        links_info = []
        for fs in fileshares:
            link_info = get_share_link_info(fs)
            links_info.append(link_info)

        if len(links_info) == 1:
            result = links_info
        else:
            dir_list = filter(lambda x: x['is_dir'], links_info)
            file_list = filter(lambda x: not x['is_dir'], links_info)

            dir_list.sort(lambda x, y: cmp(x['obj_name'], y['obj_name']))
            file_list.sort(lambda x, y: cmp(x['obj_name'], y['obj_name']))

            result = dir_list + file_list

        return Response(result)

    def post(self, request):
        """ Create share link.

        Permission checking:
        1. default(NOT guest) user;
        """

        # argument check
        repo_id = request.data.get('repo_id', None)
        if not repo_id:
            error_msg = 'repo_id invalid.'
            return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

        path = request.data.get('path', None)
        if not path:
            error_msg = 'path invalid.'
            return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

        password = request.data.get('password', None)
        if password:
            if len(password) < config.SHARE_LINK_PASSWORD_MIN_LENGTH:
                error_msg = _('Password is too short.')
                return api_error(status.HTTP_400_BAD_REQUEST, error_msg)
            if not is_user_password_strong(password):
                error_msg = _('Password is too week.')
                return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

        try:
            expire_days = int(request.data.get('expire_days', 0))
        except ValueError:
            error_msg = 'expire_days invalid.'
            return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

        if expire_days <= 0:
            if SHARE_LINK_EXPIRE_DAYS_DEFAULT > 0:
                expire_days = SHARE_LINK_EXPIRE_DAYS_DEFAULT

        if SHARE_LINK_EXPIRE_DAYS_MIN > 0:
            if expire_days < SHARE_LINK_EXPIRE_DAYS_MIN:
                error_msg = _('Expire days should be greater or equal to %s') % \
                        SHARE_LINK_EXPIRE_DAYS_MIN
                return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

        if SHARE_LINK_EXPIRE_DAYS_MAX > 0:
            if expire_days > SHARE_LINK_EXPIRE_DAYS_MAX:
                error_msg = _('Expire days should be less than or equal to %s') % \
                        SHARE_LINK_EXPIRE_DAYS_MAX
                return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

        if expire_days <= 0:
            expire_date = None
        else:
            expire_date = timezone.now() + relativedelta(days=expire_days)

        sent_to = request.data.get('sent_to', '').split(',')
        sent_emails = [x.strip() for x in sent_to if x.strip()]
        if len(sent_emails) == 0:
            error_msg = _("Please enter the recipient's email.")
            return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

        from seahub.utils import is_valid_email
        for e in sent_emails:
            if not is_valid_email(e):
                error_msg = u"非法邮箱地址：%s" % e
                return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

        note = request.data.get('note', '').strip()
        if not note:
            error_msg = _('Please enter note.')
            return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

        perm = check_permissions_arg(request)

        # resource check
        repo = seafile_api.get_repo(repo_id)
        if not repo:
            error_msg = 'Library %s not found.' % repo_id
            return api_error(status.HTTP_404_NOT_FOUND, error_msg)

        if repo.encrypted:
            error_msg = 'Permission denied.'
            return api_error(status.HTTP_403_FORBIDDEN, error_msg)

        try:
            obj_id, s_type = self._generate_obj_id_and_type_by_path(repo_id, path)
        except SearpcError as e:
            logger.error(e)
            error_msg = 'Internal Server Error'
            return api_error(status.HTTP_500_INTERNAL_SERVER_ERROR, error_msg)

        if not obj_id:
            if s_type == 'f':
                error_msg = 'file %s not found.' % path
            elif s_type == 'd':
                error_msg = 'folder %s not found.' % path
            else:
                error_msg = 'path %s not found.' % path

            return api_error(status.HTTP_404_NOT_FOUND, error_msg)

        username = request.user.username
        permission_by_path = seafile_api.check_permission_by_path(repo_id, path, username)
        if parse_repo_perm(permission_by_path).can_generate_share_link is False:
            error_msg = 'Permission denied.'
            return api_error(status.HTTP_403_FORBIDDEN, error_msg)

        org_id = request.user.org.org_id if is_org_context(request) else None
        if s_type == 'f':
            fs = FileShare.objects.get_file_link_by_path(username, repo_id, path)
            if fs:
                error_msg = _(u'Share link %s already exists.' % fs.token)
                return api_error(status.HTTP_400_BAD_REQUEST, error_msg)
            fs = FileShare.objects.create_file_link(username, repo_id, path,
                                                    password, expire_date,
                                                    permission=perm, org_id=org_id)

            if ENABLE_FILESHARE_CHECK:
                file_shared_link_created.send(
                    sender=fs, sent_to=sent_emails, note=note)
                check_share_link(request, fs, repo)

        elif s_type == 'd':
            fs = FileShare.objects.get_dir_link_by_path(username, repo_id, path)
            if fs:
                error_msg = _(u'Share link %s already exists.' % fs.token)
                return api_error(status.HTTP_400_BAD_REQUEST, error_msg)
            fs = FileShare.objects.create_dir_link(username, repo_id, path,
                                                    password, expire_date,
                                                    permission=perm, org_id=org_id)

        link_info = get_share_link_info(fs)
        return Response(link_info)

class ShareLink(APIView):

    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated, CanGenerateShareLink)
    throttle_classes = (UserRateThrottle,)

    def get(self, request, token):
        """ Get a special share link info.

        Permission checking:
        1. default(NOT guest) user;
        """

        try:
            fs = FileShare.objects.get(token=token)
        except FileShare.DoesNotExist:
            error_msg = 'token %s not found.' % token
            return api_error(status.HTTP_404_NOT_FOUND, error_msg)

        link_info = get_share_link_info(fs)
        return Response(link_info)

    def put(self, request, token):
        """ Update share link, currently only available for permission.

        Permission checking:
        share link creater
        """

        try:
            fs = FileShare.objects.get(token=token)
        except FileShare.DoesNotExist:
            error_msg = 'token %s not found.' % token
            return api_error(status.HTTP_404_NOT_FOUND, error_msg)

        username = request.user.username
        if not fs.is_owner(username):
            error_msg = 'Permission denied.'
            return api_error(status.HTTP_403_FORBIDDEN, error_msg)

        permissions = request.data.get('permissions', None)
        if permissions:
            perm = check_permissions_arg(request)
            fs.permission = perm
            fs.save()

        link_info = get_share_link_info(fs)
        return Response(link_info)

    def delete(self, request, token):
        """ Delete share link.

        Permission checking:
        1. default(NOT guest) user;
        2. link owner;
        """

        try:
            fs = FileShare.objects.get(token=token)
        except FileShare.DoesNotExist:
            return Response({'success': True})

        has_published_library = False
        if fs.path == '/':
            try:
                Wiki.objects.get(repo_id=fs.repo_id)
                has_published_library = True
            except Wiki.DoesNotExist:
                pass

        username = request.user.username
        if not fs.is_owner(username):
            error_msg = 'Permission denied.'
            return api_error(status.HTTP_403_FORBIDDEN, error_msg)

        if has_published_library:
            error_msg = 'There is an associated published library.'
            return api_error(status.HTTP_403_FORBIDDEN, error_msg)

        try:
            fs.delete()
        except Exception as e:
            logger.error(e)
            error_msg = 'Internal Server Error'
            return api_error(status.HTTP_500_INTERNAL_SERVER_ERROR, error_msg)

        return Response({'success': True})


class ShareLinkOnlineOfficeLock(APIView):

    permission_classes = (IsProVersion,)
    throttle_classes = (UserRateThrottle,)

    def put(self, request, token):
        """ This api only used for refresh OnlineOffice lock
        when user edit office file via share link.

        Permission checking:
        1, If enable SHARE_LINK_LOGIN_REQUIRED, user must have been authenticated.
        2, Share link should have can_edit permission.
        3, File must have been locked by OnlineOffice.
        """

        if SHARE_LINK_LOGIN_REQUIRED and \
                not request.user.is_authenticated():
            error_msg = 'Permission denied.'
            return api_error(status.HTTP_403_FORBIDDEN, error_msg)

        try:
            share_link = FileShare.objects.get(token=token)
        except FileShare.DoesNotExist:
            error_msg = 'Share link %s not found.' % token
            return api_error(status.HTTP_404_NOT_FOUND, error_msg)

        if share_link.is_expired():
            error_msg = 'Share link %s is expired.' % token
            return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

        shared_by = share_link.username
        repo_id = share_link.repo_id
        path = normalize_file_path(share_link.path)
        parent_dir = os.path.dirname(path)
        if seafile_api.check_permission_by_path(repo_id,
                parent_dir, shared_by) != PERMISSION_READ_WRITE:
            error_msg = 'Permission denied.'
            return api_error(status.HTTP_403_FORBIDDEN, error_msg)

        permissions = share_link.get_permissions()
        can_edit = permissions['can_edit']
        if not can_edit:
            error_msg = 'Share link %s has no edit permission.' % token
            return api_error(status.HTTP_403_FORBIDDEN, error_msg)

        locked_by_online_office = if_locked_by_online_office(repo_id, path)
        if locked_by_online_office:
            # refresh lock file
            try:
                seafile_api.refresh_file_lock(repo_id, path)
            except SearpcError, e:
                logger.error(e)
                error_msg = 'Internal Server Error'
                return api_error(status.HTTP_500_INTERNAL_SERVER_ERROR, error_msg)
        else:
            error_msg = _("You can not refresh this file's lock.")
            return api_error(status.HTTP_403_FORBIDDEN, error_msg)

        return Response({'success': True})


class ShareLinkDirents(APIView):

    throttle_classes = (UserRateThrottle,)

    def get(self, request, token):
        """ Only used for get dirents in a folder share link.

        Permission checking:
        1, If enable SHARE_LINK_LOGIN_REQUIRED, user must have been authenticated.
        2, If enable ENABLE_SHARE_LINK_AUDIT, user must have been authenticated, or have been audited.
        3, If share link is encrypted, share link password must have been checked.
        """

        # argument check
        thumbnail_size = request.GET.get('thumbnail_size', 48)
        try:
            thumbnail_size = int(thumbnail_size)
        except ValueError:
            error_msg = 'thumbnail_size invalid.'
            return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

        # permission check

        # check if login required
        if SHARE_LINK_LOGIN_REQUIRED and \
                not request.user.is_authenticated():
            error_msg = 'Permission denied.'
            return api_error(status.HTTP_403_FORBIDDEN, error_msg)

        # check share link audit
        if is_pro_version() and ENABLE_SHARE_LINK_AUDIT and \
                not request.user.is_authenticated() and \
                not request.session.get('anonymous_email'):
            error_msg = 'Permission denied.'
            return api_error(status.HTTP_403_FORBIDDEN, error_msg)

        # resource check
        try:
            share_link= FileShare.objects.get(token=token)
        except FileShare.DoesNotExist:
            error_msg = 'Share link %s not found.' % token
            return api_error(status.HTTP_404_NOT_FOUND, error_msg)

        # check share link password
        if share_link.is_encrypted() and not check_share_link_access(request, token):
            error_msg = 'Permission denied.'
            return api_error(status.HTTP_403_FORBIDDEN, error_msg)

        if share_link.s_type != 'd':
            error_msg = 'Share link %s is not a folder share link.' % token
            return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

        repo_id = share_link.repo_id
        repo = seafile_api.get_repo(repo_id)
        if not repo:
            error_msg = 'Library %s not found.' % repo_id
            return api_error(status.HTTP_404_NOT_FOUND, error_msg)

        share_link_path = share_link.path
        request_path = request.GET.get('path', '/')
        if request_path == '/':
            path = share_link_path
        else:
            path = posixpath.join(share_link_path, request_path.strip('/'))

        path = normalize_dir_path(path)
        dir_id = seafile_api.get_dir_id_by_path(repo_id, path)
        if not dir_id:
            error_msg = 'Folder %s not found.' % request_path
            return api_error(status.HTTP_404_NOT_FOUND, error_msg)

        try:
            current_commit = seafile_api.get_commit_list(repo_id, 0, 1)[0]
            dirent_list = seafile_api.list_dir_by_commit_and_path(repo_id,
                    current_commit.id, path, -1, -1)
        except Exception as e:
            logger.error(e)
            error_msg = 'Internal Server Error'
            return api_error(status.HTTP_500_INTERNAL_SERVER_ERROR, error_msg)

        result = []
        for dirent in dirent_list:

            # don't return parent folder(share link path) info to user
            # so use request_path here
            dirent_path = posixpath.join(request_path, dirent.obj_name)

            dirent_info = {}
            dirent_info['size'] = dirent.size
            dirent_info['last_modified'] = timestamp_to_isoformat_timestr(dirent.mtime)

            if stat.S_ISDIR(dirent.mode):
                dirent_info['is_dir'] = True
                dirent_info['folder_path'] = normalize_dir_path(dirent_path)
                dirent_info['folder_name'] = dirent.obj_name
            else:
                dirent_info['is_dir'] = False
                dirent_info['file_path'] = normalize_file_path(dirent_path)
                dirent_info['file_name'] = dirent.obj_name

                file_type, file_ext = get_file_type_and_ext(dirent.obj_name)
                if file_type in (IMAGE, XMIND) or \
                        file_type == VIDEO and ENABLE_VIDEO_THUMBNAIL:

                    if os.path.exists(os.path.join(THUMBNAIL_ROOT, str(thumbnail_size), dirent.obj_id)):
                        req_image_path = posixpath.join(request_path, dirent.obj_name)
                        src = get_share_link_thumbnail_src(token, thumbnail_size, req_image_path)
                        dirent_info['encoded_thumbnail_src'] = urlquote(src)

            result.append(dirent_info)

        return Response({'dirent_list': result})


class VerifyShareLinks(APIView):

    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)
    throttle_classes = (UserRateThrottle,)

    def get(self, request):
        """List file links that need verify.
        列出审批员“待审批的外链”／“已审批的外链”：

        1. 从审批链（部门－部门长－稽核）里得到当前用户能审批的部门列表；--> dept_list
        2. 得到所有属于(dept_list)的成员（注意：精确到部门即可，基础架构部项目组和基础架构步系统组同属一个审批链）；--> users
        3. 得到所有 users 的外链；--> fileshares
        4. 遍历每条外链（fileshare）,
            如果外链状态为审核通过／否决，则加入“已审批”列表；（待审核的外链，我有可能已经审核完毕，等待其他人审核）
            否则得到该外链的审批人员的邮箱列表，
              如果当前用户属于这个列表，并且“通过”或“否决”该外链，则加入“已审批”列表；
              否则，加入“待审批”列表。
        """
        username = request.user.username
        from seahub.share.views_pingan import get_verify_link_by_user
        from seahub.share.constants import STATUS_VERIFING, STATUS_PASS
        verifing_links, verified_links = get_verify_link_by_user(username)
        cmp_func = lambda x, y: cmp(y.ctime, x.ctime)
        verifing_links = sorted(verifing_links, cmp=cmp_func)
        verified_links = sorted(verified_links, cmp=cmp_func)

        status = request.GET.get('status', '')
        if status == str(STATUS_VERIFING):
            links = verifing_links
        elif status == str(STATUS_PASS):
            links = verified_links
        else:
            links = verified_links + verifing_links

        links_info = []
        for link in links:
            link_info = get_share_link_info(link)
            link_info['verbose_status_str'] = link.get_verbose_status_str()
            link_info['short_status_str'] = link.get_short_status_str()
            link_info['first_download_time'] = link.first_dl_time
            links_info.append(link_info)

        return Response({'data': links_info})


class VerifyShareLink(APIView):
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)
    throttle_classes = (UserRateThrottle,)

    def delete(self, request, token):
        try:
            fs = FileShare.objects.get(token=token)
        except FileShare.DoesNotExist:
            error_msg = 'Share link %s not found.' % token
            return api_error(status.HTTP_404_NOT_FOUND, error_msg)

        username = request.user.username
        from seahub.share.models import FileShareApprovalStatus
        from seahub.share.constants import STATUS_VERIFING
        fs_s = FileShareApprovalStatus.objects.filter(share_link=fs, email=username)
        for ele in fs_s:
            if ele.status != STATUS_VERIFING:
                continue
            ele.delete()

        return Response({'success': True})
