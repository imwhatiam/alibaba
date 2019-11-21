# -*- coding: utf-8 -*-
import json
import stat
import logging
import time
from collections import namedtuple
from datetime import timedelta, datetime

from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from django.db.models import Q
from django.utils import translation, timezone
from django.http import HttpResponse

from seaserv import seafile_api, ccnet_api

from seahub.api2.utils import api_error
from seahub.api2.throttling import UserRateThrottle
from seahub.api2.authentication import TokenAuthentication

from seahub.base.models import UserLastLogin
from seahub.base.accounts import User
from seahub.profile.models import DetailedProfile, Profile
from seahub.utils import is_valid_email, get_log_events_by_time, \
        gen_file_share_link
from seahub.utils.ms_excel import write_xls
from seahub.utils.timeutils import datetime_to_isoformat_timestr, \
        timestamp_to_isoformat_timestr, utc_datetime_to_isoformat_timestr
from seahub.views import check_folder_permission
from seahub.base.templatetags.seahub_tags import email2nickname

from seahub.share.models import ApprovalChain, approval_chain_str2list, \
    FileShare, UserApprovalChain, approval_chain_list2str, \
    is_valid_approval_chain_str, FileShareApprovalStatus, FileShareDownloads, \
    FileShareExtraInfo
from seahub.views.sysadmin_pingan import download_links_excel_report
from seahub.share.settings import PINGAN_SHARE_LINK_BACKUP_LIBRARIES, \
        PINGAN_SHARE_LINKS_REPORT_ADMIN, PINGAN_COMPANY_ID_NAME, \
        SHARE_LINK_BACKUP_LIBRARY
from seahub.share.pingan_utils import is_company_member, get_company_id, \
        get_company_security
from seahub.share.constants import STATUS_VERIFING, STATUS_PASS, STATUS_VETO, \
        STATUS_BLOCK_HIGH_RISK

logger = logging.getLogger(__name__)


class ApprovalChainView(APIView):
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (IsAdminUser, )
    throttle_classes = (UserRateThrottle, )

    def get(self, request):
        """List department approval chain.

        e.g.

        curl -v -H 'Authorization: Token 5f7435e5e585f935b84067bd0b6088cf8af9f6ac' -H 'Accept: application/json; indent=4' http://127.0.0.1:8000/api/v2.1/admin/approval-chain/

        """
        qs = ApprovalChain.objects.values_list('department',
                                               flat=True).distinct()

        return Response({'count': len(qs)})

    def put(self, request):
        """Add or update department approval chain.

        e.g.

        curl -X PUT -d "chain=测试部门1<->a@pingan.com.cn->b@pingan.com.cn->c@pingan.com.cn | d@pingan.com.cn&chain=测试部门2<->a@pingan.com.cn->b@pingan.com.cn->c@pingan.com.cn" -v -H 'Authorization: Token 5f7435e5e585f935b84067bd0b6088cf8af9f6ac' -H 'Accept: application/json; indent=4' http://127.0.0.1:8000/api/v2.1/admin/approval-chain/

        """
        chain_list = request.data.getlist('chain', None)
        if not chain_list:
            error_msg = 'chain invalid.'
            return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

        success = []
        failed = []
        for ele in chain_list:
            splits = ele.split('<->')
            if len(splits) != 2:
                failed.append(ele)
                continue

            dept = splits[0].strip()
            chain = splits[1].strip()
            if not dept or not chain:
                failed.append(ele)
                continue

            # remove duplicated records
            ApprovalChain.objects.filter(department=dept).delete()

            chain_list = approval_chain_str2list(chain)
            for e in chain_list:
                if isinstance(e, basestring):
                    if not is_valid_email(e):
                        failed.append(ele)
                        continue
                    try:
                        u = User.objects.get(email=e)
                        if not u.is_active:
                            failed.append(ele)
                            continue
                    except User.DoesNotExist:
                        failed.append(ele)
                        continue
                else:
                    for x in e[1:]:
                        if not is_valid_email(x):
                            failed.append(ele)
                            continue
                    try:
                        u = User.objects.get(email=x)
                        if not u.is_active:
                            failed.append(ele)
                            continue
                    except User.DoesNotExist:
                        failed.append(ele)
                        continue

            ApprovalChain.objects.create_chain(dept, chain_list)
            success.append(ele)

        result = {
            'success': success,
            'failed': failed,
        }
        return Response(result)


class UserApprovalChainsView(APIView):
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (IsAdminUser, )
    throttle_classes = (UserRateThrottle, )

    def get(self, request):
        """Count user approval chains.

        e.g.

        curl -v -H 'Authorization: Token 5f7435e5e585f935b84067bd0b6088cf8af9f6ac' -H 'Accept: application/json; indent=4' http://127.0.0.1:8000/api/v2.1/admin/user-approval-chains/

        """
        qs = UserApprovalChain.objects.values_list('user',
                                                   flat=True).distinct()

        return Response({'count': len(qs)})

    def put(self, request):
        """Add or update user approval chain.

        e.g.

        curl -X PUT -d "chain=a@pingan.com.cn<->a@pingan.com.cn->b@pingan.com.cn->c@pingan.com.cn | d@pingan.com.cn&chain=b@pingan.com.cn<->a@pingan.com.cn->b@pingan.com.cn->c@pingan.com.cn" -v -H 'Authorization: Token 5f7435e5e585f935b84067bd0b6088cf8af9f6ac' -H 'Accept: application/json; indent=4' http://127.0.0.1:8000/api/v2.1/admin/user-approval-chains/

        """
        chain_list = request.data.getlist('chain', None)
        if not chain_list:
            error_msg = 'chain invalid.'
            return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

        success = []
        failed = []
        for ele in chain_list:
            # check whether chain string is valid
            if not is_valid_approval_chain_str(ele):
                failed.append(ele)
                continue

            splits = ele.split('<->')
            user = splits[0].strip()
            chain = splits[1].strip()
            chain_list = approval_chain_str2list(chain)

            # remove duplicated records
            UserApprovalChain.objects.filter(user=user).delete()

            UserApprovalChain.objects.create_chain(user, chain_list)
            success.append(ele)

        result = {
            'success': success,
            'failed': failed,
        }
        return Response(result)


class UserApprovalChainView(APIView):
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (IsAdminUser, )
    throttle_classes = (UserRateThrottle, )

    def get(self, request, user):
        """Get user approval chain.

        e.g.

        curl -v -H 'Authorization: Token 5f7435e5e585f935b84067bd0b6088cf8af9f6ac' -H 'Accept: application/json; indent=4' http://127.0.0.1:8000/api/v2.1/admin/user-approval-chains/a@pingan.com.cn/

        """
        if UserApprovalChain.objects.filter(user=user).count() == 0:
            return Response(status=404)

        chain_obj = namedtuple('ChainObj', ['user', 'chain', 'chain_raw'])
        chain = UserApprovalChain.objects.get_by_user(user)
        chain_str = approval_chain_list2str(chain)
        chain_raw = approval_chain_list2str(chain, with_nickname=False)
        chain_obj(user=user, chain=chain_str, chain_raw=chain_raw)

        return Response({'chain': chain_str})

    def delete(self, request, user):
        """Delete user approval chain.

        e.g.

        curl -X DELETE -v -H 'Authorization: Token 5f7435e5e585f935b84067bd0b6088cf8af9f6ac' -H 'Accept: application/json; indent=4' http://127.0.0.1:8000/api/v2.1/admin/user-approval-chains/a@pingan.com.cn/

        """
        if UserApprovalChain.objects.filter(user=user).count() == 0:
            return Response(status=404)

        UserApprovalChain.objects.filter(user=user).delete()
        return Response({'success': True})


class SysDownloadLinksReport(APIView):
    """List download links.

    e.g.

    curl -v -H 'Authorization: Token afef525019166d0e29bfe126cf6163c8c5bc82a5' -H 'Accept: application/json; indent=4' http://seacloud.docker:8000/api/v2.1/admin/download-link-excel/?start=2018-06-07T14:50:00&end=2018-06-07T14:55:00
    """
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated, )
    throttle_classes = (UserRateThrottle, )

    def get(self, request):
        translation.activate('zh-cn')

        end_date = timezone.now()
        start_date = end_date - timedelta(days=60)

        start_date_str = request.GET.get('start', '')
        end_date_str = request.GET.get('end', '')
        if start_date_str and end_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%dT%H:%M:%S')
                end_date = datetime.strptime(end_date_str, '%Y-%m-%dT%H:%M:%S')
            except Exception:
                pass

        download_links = FileShare.objects.filter(s_type='f').filter(
            ctime__lte=end_date).filter(ctime__gte=start_date)


        head, data_list = download_links_excel_report(download_links)

        ret = {
            'data': [],
            'start_time': start_date_str,
            'end_time': end_date_str,
        }
        for e in data_list:
            d = {}
            d['filename'] = e[0]
            d['from_user'] = e[1]

            try:
                d_p = DetailedProfile.objects.get(user=e[1])
                d['department'] = d_p.department
                d['company'] = d_p.company
            except DetailedProfile.DoesNotExist:
                d['department'] = ''
                d['company'] = ''

            d['send_to'] = e[2]
            d['statue'] = e[3]
            d['created_at'] = e[4]
            d['first_download_time'] = e[5]
            d['downlods'] = e[6]
            d['expiration'] = e[7]
            d['link'] = e[8]

            d['dlp_status'] = e[9]
            d['dlp_time'] = e[10]

            d['human'] = e[11:]

            ret['data'].append(d)

        return Response(ret)


# new pinga api
def get_share_link_info(share_links, export_excel=False):

    api_result = []
    excel_data_list = []

    # get share link receivers
    receiver_dict = {}
    extra_infos = FileShareExtraInfo.objects.filter(share_link__in=share_links)
    for extra_info in extra_infos:
        share_link_id = extra_info.share_link.id
        if share_link_id not in receiver_dict:
            receiver_dict[share_link_id] = [extra_info.sent_to]
        else:
            receiver_dict[share_link_id].append(extra_info.sent_to)

    # get company and department info
    company_id_dict = {}
    department_name_dict = {}
    user_emails = [x.username for x in share_links]
    detailed_profiles = DetailedProfile.objects.filter(user__in=user_emails)
    for profile in detailed_profiles:
        if profile.user not in department_name_dict:
            department_name_dict[profile.user] = profile.department
        if profile.user not in company_id_dict:
            company_id_dict[profile.user] = profile.company.lower()

    for share_link in share_links:

        if share_link.s_type != 'f':
            continue

        info = {}

        # basic info
        info['filename'] = share_link.get_name()
        info['from_user'] = share_link.username
        info['created_at'] = datetime_to_isoformat_timestr(share_link.ctime)
        info['expiration'] = share_link.expire_date.strftime('%Y-%m-%d') if share_link.expire_date else ''
        info['share_link_url'] = share_link.get_full_url()
        info['share_link_token'] = share_link.token

        try:
            dirent = seafile_api.get_dirent_by_path(share_link.repo_id, share_link.path)
            info['size'] = dirent.size if dirent else ''
        except Exception:
            info['size'] = ''

        # company and department info
        company_id = company_id_dict.get(share_link.username, '')
        info['company'] = PINGAN_COMPANY_ID_NAME.get(company_id, '')
        info['department'] = department_name_dict.get(share_link.username, '')
        info['sent_to'] = receiver_dict.get(share_link.id, [])

        api_result.append(info)

        if export_excel:

            approval_info = get_share_link_approval_info(share_link)

            dlp_approval_info = approval_info.get('dlp_approval_info', {})
            dlp_approval_msg = dlp_approval_info.get('dlp_msg', {})
            dlp_approval_status = dlp_approval_info.get('dlp_status', '')

            detailed_approval_info = approval_info.get('detailed_approval_info', [])

            final_approval_status = 0
            if len(detailed_approval_info) > 0:
                if len(detailed_approval_info[-1]) > 0:
                    final_approval_status = detailed_approval_info[-1][0]

            status_dict = {
                STATUS_VERIFING: '正在审核',
                STATUS_PASS: '通过',
                STATUS_VETO: '否决',
                STATUS_BLOCK_HIGH_RISK: '高敏',
            }

            formated_approval_info = ''
            for sub_approval_info in detailed_approval_info:
                formated_approval_info += str(sub_approval_info[1]) + '; '

            excel_row = [info['filename'], info['size'], info['from_user'], info['company'],
                    info['department'], ','.join(info['sent_to']), info['created_at'],
                    info['expiration'], info['share_link_url'],
                    status_dict.get(final_approval_status, ''),
                    status_dict.get(dlp_approval_status, ''),
                    dlp_approval_info.get('dlp_vtime', ''),
                    dlp_approval_msg.get('policy_categories', ''),
                    dlp_approval_msg.get('breach_content', ''),
                    dlp_approval_msg.get('total_matches', ''),
                    formated_approval_info
                    ]

            excel_data_list.append(excel_row)

    return api_result, excel_data_list


def get_share_link_approval_info(share_link):

    # get dlp message
    dlp_approval = FileShareApprovalStatus.objects.get_dlp_status_by_share_link(share_link)
    try:
        dlp_msg = json.loads(dlp_approval.msg)
    except Exception as e:
        logger.error(e)
        dlp_msg = {}

    dlp_approval_dict = {}
    dlp_approval_dict['dlp_msg'] = dlp_msg
    dlp_approval_dict['dlp_status'] = dlp_approval.status
    dlp_approval_dict['dlp_vtime'] = datetime_to_isoformat_timestr(dlp_approval.vtime)

    # get detailed approval message
    result = {
        'dlp_approval_info': dlp_approval_dict,
        'detailed_approval_info': share_link.get_verbose_status()
    }

    return result


class PinganAdminShareLinksReport(APIView):

    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)
    throttle_classes = (UserRateThrottle,)

    def get(self, request):

        # parameter check
        start_date_str = request.GET.get('start', '')
        end_date_str = request.GET.get('end', '')
        if start_date_str and end_date_str:

            if len(start_date_str) == 10:
                start_date_str += 'T00:00:00'

            if len(end_date_str) == 10:
                end_date_str += 'T23:59:59'

            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%dT%H:%M:%S')
                end_date = datetime.strptime(end_date_str, '%Y-%m-%dT%H:%M:%S')
            except Exception:
                error_msg = "date invalid."
                return api_error(status.HTTP_400_BAD_REQUEST, error_msg)
        else:
            end_date = timezone.now()
            start_date = end_date - timedelta(days=7)

        # permission check
        if not request.user.is_staff and \
                request.user.username not in PINGAN_SHARE_LINKS_REPORT_ADMIN:
            error_msg = 'Permission denied.'
            return api_error(status.HTTP_403_FORBIDDEN, error_msg)

        # get all filename in root folder of backup library
        backup_repo_id = SHARE_LINK_BACKUP_LIBRARY
        dir_id = seafile_api.get_dir_id_by_path(backup_repo_id, '/')
        dirent_list = seafile_api.list_dir_with_perm(backup_repo_id,
                '/', dir_id, request.user.username, -1, -1)
        filename_list = [d.obj_name for d in dirent_list if not stat.S_ISDIR(d.mode)]

        # get share links by dirent name
        share_link_token_2_source_obj_name = {}
        share_link_token_list = []
        for filename in filename_list:
            share_link_token_list.append(filename.split('.')[-1])
            share_link_token_2_source_obj_name[share_link_token_list[-1]] = filename

        # get share link approval link info
        share_links = FileShare.objects.filter(s_type='f') \
                .filter(ctime__lte=end_date) \
                .filter(ctime__gte=start_date)

        # search by filename
        filename = request.GET.get('filename', '').lower().strip()
        if filename:
            share_links = filter(lambda link: filename in link.get_name().lower().strip(), share_links)

        # search by share link creator
        from_user = request.GET.get('from_user', '').lower().strip()
        if from_user:
            share_links = filter(lambda link: from_user in link.username.lower().strip(), share_links)

        export_excel = request.GET.get('excel', 'false').lower() == 'true'
        api_result, excel_data_list = get_share_link_info(share_links, export_excel)

        if not export_excel:
            for result in api_result:
                result['source_obj_name'] = share_link_token_2_source_obj_name.get(result['share_link_token'], '')

            ret = {
                'data': api_result,
                'start_time': datetime_to_isoformat_timestr(start_date),
                'end_time': datetime_to_isoformat_timestr(end_date),
                'backup_repo_id': SHARE_LINK_BACKUP_LIBRARY,
            }
            return Response(ret)

        response = HttpResponse(content_type='application/ms-excel')
        response['Content-Disposition'] = 'attachment; filename=download-link-report.xlsx'

        head = ["文件名", "文件大小", "发送人", "发送人公司", "发送人部门", "接收对象",
                "创建时间", "链接过期时间", "下载链接", "最终审核状态",
                "DLP审核状态", "DLP审核时间", "策略类型", "命中信息", "总计",
                "详细审核状态"]

        wb = write_xls(u'链接审核信息', head, excel_data_list)
        wb.save(response)
        return response


class PinganCompanySecurityShareLinksReport(APIView):

    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)
    throttle_classes = (UserRateThrottle,)

    def get(self, request):

        # parameter check
        start_date_str = request.GET.get('start', '')
        end_date_str = request.GET.get('end', '')
        if start_date_str and end_date_str:

            if len(start_date_str) == 10:
                start_date_str += 'T00:00:00'

            if len(end_date_str) == 10:
                end_date_str += 'T23:59:59'

            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%dT%H:%M:%S')
                end_date = datetime.strptime(end_date_str, '%Y-%m-%dT%H:%M:%S')
            except Exception:
                error_msg = "date invalid."
                return api_error(status.HTTP_400_BAD_REQUEST, error_msg)
        else:
            end_date = timezone.now()
            start_date = end_date - timedelta(days=7)

        # permission check
        username = request.user.username
        company_id = get_company_id(username)
        backup_repo_id = PINGAN_SHARE_LINK_BACKUP_LIBRARIES.get(company_id, '')
        if not backup_repo_id:
            error_msg = "%s's backup library not found." % company_id
            return api_error(status.HTTP_404_NOT_FOUND, error_msg)

        if not is_company_member(username) or \
                not check_folder_permission(request, backup_repo_id, '/'):
            error_msg = 'Permission denied.'
            return api_error(status.HTTP_403_FORBIDDEN, error_msg)

        # get all filename in root folder of backup library
        dir_id = seafile_api.get_dir_id_by_path(backup_repo_id, '/')
        dirent_list = seafile_api.list_dir_with_perm(backup_repo_id,
                '/', dir_id, username, -1, -1)
        filename_list = [d.obj_name for d in dirent_list if not stat.S_ISDIR(d.mode)]

        # get share links by dirent name
        share_link_token_2_source_obj_name = {}
        share_link_token_list = []
        for filename in filename_list:
            share_link_token_list.append(filename.split('.')[-1])
            share_link_token_2_source_obj_name[share_link_token_list[-1]] = filename
        share_links = FileShare.objects.filter(Q(token__in=share_link_token_list)) \
                .filter(ctime__lte=end_date).filter(ctime__gte=start_date)

        # search by filename
        filename = request.GET.get('filename', '').lower().strip()
        if filename:
            share_links = filter(lambda link: filename in link.get_name().lower().strip(), share_links)

        # search by share link creator
        from_user = request.GET.get('from_user', '').lower().strip()
        if from_user:
            share_links = filter(lambda link: from_user in link.username.lower().strip(), share_links)

        export_excel = request.GET.get('excel', 'false').lower() == 'true'
        api_result, excel_data_list = get_share_link_info(share_links, export_excel)

        if not export_excel:
            for result in api_result:
                result['source_obj_name'] = share_link_token_2_source_obj_name.get(result['share_link_token'], '')
            ret = {
                'data': api_result,
                'start_time': datetime_to_isoformat_timestr(start_date),
                'end_time': datetime_to_isoformat_timestr(end_date),
                'backup_repo_id': backup_repo_id,
            }
            return Response(ret)

        response = HttpResponse(content_type='application/ms-excel')
        response['Content-Disposition'] = 'attachment; filename=download-link-report.xlsx'

        head = ["文件名", "文件大小", "发送人", "发送人公司", "发送人部门", "接收对象",
                "创建时间", "链接过期时间", "下载链接", "最终审核状态",
                "DLP审核状态", "DLP审核时间", "策略类型", "命中信息", "总计",
                "详细审核状态"]

        wb = write_xls(u'链接审核信息', head, excel_data_list)
        wb.save(response)
        return response


class PinganAdminShareLinkApprovalInfo(APIView):

    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)
    throttle_classes = (UserRateThrottle,)

    def get(self, request):

        # parameter check
        share_link_token = request.GET.get('share_link_token', '')
        if not share_link_token:
            error_msg = 'share_link_token invalid.'
            return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

        # permission check
        if not request.user.is_staff and \
                request.user.username not in PINGAN_SHARE_LINKS_REPORT_ADMIN:
            error_msg = 'Permission denied.'
            return api_error(status.HTTP_403_FORBIDDEN, error_msg)

        # resource check
        try:
            share_link = FileShare.objects.get(token=share_link_token)
        except FileShare.DoesNotExist:
            error_msg = 'Share link %s not fount.' % share_link_token
            return api_error(status.HTTP_404_NOT_FOUND, error_msg)

        approval_info = get_share_link_approval_info(share_link)
        return Response(approval_info)


class PinganCompanySecurityShareLinkApprovalInfo(APIView):

    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)
    throttle_classes = (UserRateThrottle,)

    def get(self, request):

        # parameter check
        share_link_token = request.GET.get('share_link_token', '')
        if not share_link_token:
            error_msg = 'share_link_token invalid.'
            return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

        # permission check
        username = request.user.username
        if not is_company_member(username):
            error_msg = 'Permission denied.'
            return api_error(status.HTTP_403_FORBIDDEN, error_msg)

        # resource check
        try:
            share_link = FileShare.objects.get(token=share_link_token)
        except FileShare.DoesNotExist:
            error_msg = 'Share link %s not fount.' % share_link_token
            return api_error(status.HTTP_404_NOT_FOUND, error_msg)

        approval_info = get_share_link_approval_info(share_link)
        return Response(approval_info)


def get_share_link_download_info(share_links, events):

    api_result = []
    excel_data_list = []

    download_count_dict = {}
    first_download_time_dict = {}
    share_link_downloads = FileShareDownloads.objects.filter(share_link__in=share_links)
    for download in share_link_downloads:
        share_link_id = download.share_link.id
        # get download count
        if share_link_id not in download_count_dict:
            download_count_dict[share_link_id] = 1
        else:
            download_count_dict[share_link_id] += 1

        # get first download time
        if download.is_first_download:
            if share_link_id not in first_download_time_dict:
                first_download_time_dict[share_link_id] = download.download_time

    for share_link in share_links:
        download_count = download_count_dict.get(share_link.id, 0)
        first_download_time = first_download_time_dict.get(share_link.id, '')
        share_link_info = {
            'download_count': download_count,
            'first_download_time': datetime_to_isoformat_timestr(first_download_time),
            'data': [],
        }

        share_link_repo_id_path = share_link.repo_id + share_link.path
        for event in events:

            event_repo_id_path = event.repo_id + event.file_path
            if share_link_repo_id_path != event_repo_id_path:
                continue

            event_data = {
                'user': event.user,
                'ip': event.ip,
                'device': event.device,
                'time': utc_datetime_to_isoformat_timestr(event.timestamp),

            }
            share_link_info['data'].append(event_data)

            excel_row = [share_link.get_name(), gen_file_share_link(share_link.token),
                    first_download_time, download_count,
                    event.user, event.ip, event.device,
                    datetime_to_isoformat_timestr(event.timestamp)]

            excel_data_list.append(excel_row)

        api_result.append(share_link_info)

    return api_result, excel_data_list


class PinganAdminShareLinkDownloadInfo(APIView):

    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)
    throttle_classes = (UserRateThrottle,)

    def get(self, request):

        # parameter check
        start_date_str = request.GET.get('start', '')
        end_date_str = request.GET.get('end', '')
        if not start_date_str and not end_date_str:
            end_date = timezone.now()
            start_date = end_date - timedelta(days=30)
        else:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%dT%H:%M:%S')
                end_date = datetime.strptime(end_date_str, '%Y-%m-%dT%H:%M:%S')
            except Exception:
                error_msg = "date invalid."
                return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

        # permission check
        username = request.user.username
        if not request.user.is_staff and \
                username not in PINGAN_SHARE_LINKS_REPORT_ADMIN:
            error_msg = 'Permission denied.'
            return api_error(status.HTTP_403_FORBIDDEN, error_msg)

        # get share_links
        share_link_token_list = request.GET.getlist('share_link_token', '')
        if not share_link_token_list:
            error_msg = "share_link_token invalid."
            return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

        share_links = FileShare.objects.filter(token__in=share_link_token_list)

        # get download info
        try:
            start_timestamp = time.mktime(start_date.timetuple())
            end_timestamp = time.mktime(end_date.timetuple())
            events = get_log_events_by_time('file_audit', start_timestamp, end_timestamp)
            events = events if events else []
        except Exception as e:
            logger.error(e)
            error_msg = 'Internal Server Error'
            return api_error(status.HTTP_500_INTERNAL_SERVER_ERROR, error_msg)

        events = filter(lambda e: e.etype=='file-download-share-link', events)
        events.sort(key=lambda e: e.timestamp, reverse=True)

        api_result, excel_data_list = get_share_link_download_info(share_links, events)

        export_excel = request.GET.get('excel', 'false').lower() == 'true'
        if not export_excel:
            return Response(api_result)

        response = HttpResponse(content_type='application/ms-excel')
        response['Content-Disposition'] = 'attachment; filename=link-download-info.xlsx'

        head = ["文件名", "下载链接", "首次下载时间", "下载次数", "用户", "IP", "设备名", "时间"]
        wb = write_xls(u'链接下载信息', head, excel_data_list)
        wb.save(response)
        return response


class PinganCompanySecurityShareLinkDownloadInfo(APIView):

    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)
    throttle_classes = (UserRateThrottle,)

    def get(self, request):

        # parameter check
        start_date_str = request.GET.get('start', '')
        end_date_str = request.GET.get('end', '')
        if not start_date_str and not end_date_str:
            end_date = timezone.now()
            start_date = end_date - timedelta(days=30)
        else:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%dT%H:%M:%S')
                end_date = datetime.strptime(end_date_str, '%Y-%m-%dT%H:%M:%S')
            except Exception:
                error_msg = "date invalid."
                return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

        # permission check
        username = request.user.username
        if not is_company_member(username):
            error_msg = 'Permission denied.'
            return api_error(status.HTTP_403_FORBIDDEN, error_msg)

        # get share_links
        share_link_token_list = request.GET.getlist('share_link_token', None)
        if not share_link_token_list:
            error_msg = 'share_link_token invalid.'
            return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

        share_links = FileShare.objects.filter(token__in=share_link_token_list)

        # get download info
        try:
            start_timestamp = time.mktime(start_date.timetuple())
            end_timestamp = time.mktime(end_date.timetuple())
            events = get_log_events_by_time('file_audit', start_timestamp, end_timestamp)
            events = events if events else []
        except Exception as e:
            logger.error(e)
            error_msg = 'Internal Server Error'
            return api_error(status.HTTP_500_INTERNAL_SERVER_ERROR, error_msg)

        events = filter(lambda e: e.etype=='file-download-share-link', events)
        events.sort(key=lambda e: e.timestamp, reverse=True)

        api_result, excel_data_list = get_share_link_download_info(share_links, events)

        export_excel = request.GET.get('excel', 'false').lower() == 'true'
        if not export_excel:
            return Response(api_result)

        response = HttpResponse(content_type='application/ms-excel')
        response['Content-Disposition'] = 'attachment; filename=link-download-info.xlsx'

        head = ["文件名", "下载链接", "首次下载时间", "下载次数", "用户", "IP", "设备名", "时间"]
        wb = write_xls(u'链接下载信息', head, excel_data_list)
        wb.save(response)
        return response


class PinganAdminUsers(APIView):

    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)
    throttle_classes = (UserRateThrottle,)

    def get(self, request):

        if not request.user.is_staff and \
                request.user.username not in PINGAN_SHARE_LINKS_REPORT_ADMIN:
            error_msg = 'Permission denied.'
            return api_error(status.HTTP_403_FORBIDDEN, error_msg)

        try:
            page = int(request.GET.get('page', '1'))
            per_page = int(request.GET.get('per_page', '25'))
        except ValueError:
            page = 1
            per_page = 25

        source = request.GET.get('source', 'db')
        source = source.lower()
        if source not in ('db', 'ldapimport'):
            error_msg = 'source invalid.'
            return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

        start = (page - 1) * per_page
        if source == 'db':
            users = ccnet_api.get_emailusers('DB', start, per_page)
            total_count = ccnet_api.count_emailusers('DB')
        else:
            users = ccnet_api.get_emailusers('LDAPImport', start, per_page)
            total_count = ccnet_api.count_emailusers('LDAP')

        user_emails = [x.email for x in users]
        last_logins = UserLastLogin.objects.filter(username__in=user_emails)
        last_login_dict = {}
        for last_login in last_logins:
            if last_login.username not in last_login_dict:
                last_login_dict[last_login.username] = datetime_to_isoformat_timestr(last_login.last_login)

        profiles = Profile.objects.filter(user__in=user_emails)
        login_id_dict = {}
        for profile in profiles:
            if profile.user not in login_id_dict:
                login_id_dict[profile.user] = profile.login_id

        detailed_profiles = DetailedProfile.objects.filter(user__in=user_emails)
        company_id_dict = {}
        department_name_dict = {}
        for profile in detailed_profiles:
            if profile.user not in department_name_dict:
                department_name_dict[profile.user] = profile.department

            if profile.user not in company_id_dict:
                company_id_dict[profile.user] = profile.company.lower()

        data = []
        for user in users:

            email = user.email
            quota = seafile_api.get_user_quota(email)
            company_id = company_id_dict.get(email, '')

            info = {}
            info['email'] = email
            info['account'] = login_id_dict.get(email, '')
            info['displayname'] = email2nickname(email)
            info['company'] = PINGAN_COMPANY_ID_NAME.get(company_id, '')
            info['department'] = department_name_dict.get(email, '')
            info['usedsize'] = seafile_api.get_user_self_usage(email)
            info['last_login'] = last_login_dict.get(email, '')
            info['create_time'] = timestamp_to_isoformat_timestr(user.ctime)
            info['security'] = '外发权限' if quota > 15000000 else '审核权限'
            info['is_active'] = user.is_active
            info['quota'] = quota
            data.append(info)

        return Response({'data': data, 'total_count': total_count})


class PinganAdminUserApprovalChain(APIView):

    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)
    throttle_classes = (UserRateThrottle,)

    def get(self, request, email):
        """Get user approval chain.
        """
        username = request.user.username
        if not request.user.is_staff and \
                username not in PINGAN_SHARE_LINKS_REPORT_ADMIN:
            error_msg = 'Permission denied.'
            return api_error(status.HTTP_403_FORBIDDEN, error_msg)

        if UserApprovalChain.objects.filter(user=email).count() == 0:
            error_msg = 'Chain not fount.'
            return api_error(status.HTTP_404_NOT_FOUND, error_msg)

        chain = UserApprovalChain.objects.get_by_user(email)
        return Response({'chain': chain})

    def post(self, request, email):
        """Create  user approval chain.

        parameters:
        chain: 'a@pingan.com.cn->b@pingan.com.cn|c@pingan.com.cn->d@pingan.com.cn'
        """
        username = request.user.username
        if not request.user.is_staff and \
                username not in PINGAN_SHARE_LINKS_REPORT_ADMIN:
            error_msg = 'Permission denied.'
            return api_error(status.HTTP_403_FORBIDDEN, error_msg)

        chain = request.data.get('chain', '').strip()
        if not chain:
            error_msg = "chain invalid."
            return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

        chain_list = approval_chain_str2list(chain)
        company_security_list = get_company_security(email)
        if company_security_list:
            company_security_list.insert(0, 'op_or')
            chain_list.append(company_security_list)

        UserApprovalChain.objects.filter(user=email).delete()
        UserApprovalChain.objects.create_chain(email, chain_list)
        chain = UserApprovalChain.objects.get_by_user(email)
        return Response({'chain': chain})
