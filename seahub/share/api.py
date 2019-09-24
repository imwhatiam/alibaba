# -*- coding: utf-8 -*-
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

from seaserv import seafile_api

from seahub.api2.utils import api_error
from seahub.api2.throttling import UserRateThrottle
from seahub.api2.authentication import TokenAuthentication
from seahub.api2.endpoints.utils import get_log_events_by_type_and_time

from seahub.base.accounts import User
from seahub.profile.models import DetailedProfile
from seahub.utils import is_valid_email, get_log_events_by_time
from seahub.utils.ms_excel import write_xls
from seahub.utils.timeutils import datetime_to_isoformat_timestr
from seahub.views import check_folder_permission

from seahub.share.constants import STATUS_VERIFING, STATUS_PASS, STATUS_VETO, \
        STATUS_BLOCK_HIGH_RISK
from seahub.share.models import ApprovalChain, approval_chain_str2list, \
    FileShare, UserApprovalChain, approval_chain_list2str, \
    is_valid_approval_chain_str, FileShareApprovalStatus, FileShareDownloads
from seahub.views.sysadmin_pingan import download_links_excel_report
from seahub.share.settings import PINGAN_SHARE_LINK_BACKUP_LIBRARIES, \
        PINGAN_SHARE_LINKS_REPORT_ADMIN
from seahub.share.pingan_utils import is_company_member, get_company, \
        get_company_name

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

def get_share_link_approve_info(share_links):

    api_result = []
    excel_data_list = []

    status_dict = {
        STATUS_VERIFING: '正在审核',
        STATUS_PASS: '通过',
        STATUS_VETO: '否决',
        STATUS_BLOCK_HIGH_RISK: '高敏',
    }

    for share_link in share_links:

        dlp_status = ''
        dlp_vtime = ''
        chain_status = FileShareApprovalStatus.objects.get_chain_status_by_share_link(share_link)
        if chain_status:
            dlp_status = status_dict.get(chain_status[0].status, '')
            if chain_status[0].vtime:
                dlp_vtime = chain_status[0].vtime.strftime('%Y-%m-%d %H:%M:%S')

        detailed_profile = DetailedProfile.objects.filter(user=share_link.username)

        info = {}
        info['filename'] = share_link.get_name()
        info['from_user'] = share_link.username
        info['company'] = get_company_name(share_link.username)
        info['department'] = detailed_profile[0].department if detailed_profile else ''
        info['send_to'] = ','.join(share_link.get_receivers())
        info['created_at'] = share_link.ctime.strftime('%Y-%m-%d')
        info['expiration'] = share_link.expire_date.strftime('%Y-%m-%d') if share_link.expire_date else ''
        info['share_link_url'] = share_link.get_full_url()
        info['share_link_token'] = share_link.token
        info['approve_status'] = share_link.get_short_status_str()
        info['dlp_status'] = dlp_status
        info['dlp_vtime'] = dlp_vtime
        info['detailed_approve_status'] = str(share_link.get_verbose_status())

        api_result.append(info)

        excel_row = [info['filename'], info['from_user'], info['company'],
                info['department'], info['send_to'], info['created_at'],
                info['expiration'], info['share_link_url'], info['approve_status'],
                info['dlp_status'], info['dlp_vtime'], info['detailed_approve_status']]
        excel_data_list.append(excel_row)

    return api_result, excel_data_list


class PinganAdminShareLinksReport(APIView):

    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)
    throttle_classes = (UserRateThrottle,)

    def get(self, request):

        if not request.user.is_staff or \
                request.user.username not in PINGAN_SHARE_LINKS_REPORT_ADMIN:
            error_msg = 'Permission denied.'
            return api_error(status.HTTP_403_FORBIDDEN, error_msg)

        start_date_str = request.GET.get('start', '')
        end_date_str = request.GET.get('end', '')
        if start_date_str and end_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            except Exception:
                error_msg = "date invalid."
                return api_error(status.HTTP_400_BAD_REQUEST, error_msg)
        else:
            end_date = timezone.now()
            start_date = end_date - timedelta(days=60)

        share_links = FileShare.objects.filter(s_type='f') \
                .filter(ctime__lte=end_date) \
                .filter(ctime__gte=start_date)
        api_result, excel_data_list = get_share_link_approve_info(share_links)
        ret = {
            'data': api_result,
            'start_time': start_date.strftime("%Y-%m-%d"),
            'end_time': end_date.strftime("%Y-%m-%d"),
        }

        export_excel = request.GET.get('excel', 'false')
        if export_excel.lower() != 'true':
            return Response(ret)

        response = HttpResponse(content_type='application/ms-excel')
        response['Content-Disposition'] = 'attachment; filename=download-links.xls'

        head = ["文件名", "发送人", "发送人公司", "发送人部门", "接收对象",
                "创建时间", "链接过期时间", "下载链接", "最终审核状态",
                "DLP审核状态", "DLP审核时间", "详细审核状态"]

        wb = write_xls(u'共享链接', head, excel_data_list)
        wb.save(response)
        return response


class PinganCompanySecurityShareLinksReport(APIView):
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)
    throttle_classes = (UserRateThrottle,)

    def get(self, request):

        username = request.user.username

        # check if company backup library exist
        company = get_company(username)
        backup_repo_id = PINGAN_SHARE_LINK_BACKUP_LIBRARIES.get(company, '')
        if not backup_repo_id:
            error_msg = "%s's backup library not found." % company
            return api_error(status.HTTP_404_NOT_FOUND, error_msg)

        # check permission
        if not is_company_member(username) or \
                not check_folder_permission(request, backup_repo_id, '/'):
            error_msg = 'Permission denied.'
            return api_error(status.HTTP_403_FORBIDDEN, error_msg)

        # handle date parameters
        start_date_str = request.GET.get('start', '')
        end_date_str = request.GET.get('end', '')
        if start_date_str and end_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
                end_date = end_date + timedelta(days=1)
            except Exception:
                error_msg = "date invalid."
                return api_error(status.HTTP_400_BAD_REQUEST, error_msg)
        else:
            end_date = timezone.now()
            start_date = end_date - timedelta(days=60)

        # get all filename in root folder of backup library
        dir_id = seafile_api.get_dir_id_by_path(backup_repo_id, '/')
        dirent_list = seafile_api.list_dir_with_perm(backup_repo_id,
                '/', dir_id, username, -1, -1)
        filename_list = [d.obj_name for d in dirent_list if not stat.S_ISDIR(d.mode)]

        # get share links
        share_link_token_list = []
        for filename in filename_list:
            share_link_token_list.append(filename.split('.')[-1])
        share_links = FileShare.objects.filter(Q(token__in=share_link_token_list)) \
                .filter(ctime__lte=end_date).filter(ctime__gte=start_date)

        # search by filename
        filename = request.GET.get('filename', '')
        if filename:
            share_links = filter(lambda link: filename in link.get_name(), share_links)

        # search by share link creator
        from_user = request.GET.get('from_user', '')
        if from_user:
            share_links = filter(lambda link: from_user in link.username, share_links)

        api_result, excel_data_list = get_share_link_approve_info(share_links)
        ret = {
            'data': api_result,
            'start_time': start_date.strftime("%Y-%m-%d"),
            'end_time': end_date.strftime("%Y-%m-%d"),
        }

        export_excel = request.GET.get('excel', 'false')
        if export_excel.lower() != 'true':
            return Response(ret)

        response = HttpResponse(content_type='application/ms-excel')
        response['Content-Disposition'] = 'attachment; filename=download-links.xls'

        head = ["文件名", "发送人", "发送人公司", "发送人部门", "接收对象",
                "创建时间", "链接过期时间", "下载链接", "最终审核状态",
                "DLP审核状态", "DLP审核时间", "详细审核状态"]

        wb = write_xls(u'共享链接', head, excel_data_list)
        wb.save(response)
        return response


class PinganCompanySecurityShareLinkDownloadInfo(APIView):

    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)
    throttle_classes = (UserRateThrottle,)

    def get(self, request):

        username = request.user.username
        if not is_company_member(username) and \
                not request.user.is_staff and \
                username not in PINGAN_SHARE_LINKS_REPORT_ADMIN:
            error_msg = 'Permission denied.'
            return api_error(status.HTTP_403_FORBIDDEN, error_msg)

        # check the date format, should be like '2015-10-10'
        start_date_str = request.GET.get('start', '')
        end_date_str = request.GET.get('end', '')
        if start_date_str and end_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
                end_date = end_date + timedelta(days=1)
            except Exception:
                error_msg = "date invalid."
                return api_error(status.HTTP_400_BAD_REQUEST, error_msg)
        else:
            end_date = timezone.now()
            start_date = end_date - timedelta(days=60)

        share_link_token = request.GET.get('share_link_token', None)
        if not share_link_token:
            error_msg = 'share_link_token invalid.'
            return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

        try:
            share_link = FileShare.objects.get(token=share_link_token)
        except FileShare.DoesNotExist:
            error_msg = 'token %s not found.' % share_link_token
            return api_error(status.HTTP_404_NOT_FOUND, error_msg)

        try:
            start_timestamp = time.mktime(start_date.timetuple())
            end_timestamp = time.mktime(end_date.timetuple())
            events = get_log_events_by_time('file_audit', start_timestamp, end_timestamp)
            events = events if events else []
        except Exception as e:
            logger.error(e)
            error_msg = 'Internal Server Error'
            return api_error(status.HTTP_500_INTERNAL_SERVER_ERROR, error_msg)

        result = {
            'data': [],
            'first_download_time': FileShareDownloads.objects.get_first_download_time(share_link),
            'download_count': share_link.get_download_cnt(),
        }

        for ev in events:
            result['data'].append({
                'user': ev.user,
                'ip': ev.ip,
                'device': ev.device,
                'time': datetime_to_isoformat_timestr(ev.timestamp),
            })

        return Response(result)
