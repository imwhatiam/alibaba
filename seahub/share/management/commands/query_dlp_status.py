# -*- coding: utf-8 -*-
import os
import base64
import json
import requests
from datetime import datetime
from pprint import pprint

from django.utils import translation
from django.core.management.base import BaseCommand

from seaserv import seafile_api

from seahub.profile.models import Profile, DetailedProfile
from seahub.base.templatetags.seahub_tags import email2nickname

from seahub.share.models import UserApprovalChain, FileShareApprovalStatus, \
        FileShareExtraInfo
from seahub.share.constants import STATUS_VERIFING, STATUS_PASS, STATUS_VETO, \
        STATUS_BLOCK_HIGH_RISK
from seahub.share.signals import file_shared_link_verify
from seahub.share.share_link_checking import email_reviser, email_verify_result
from seahub.share.pingan_utils import get_company_security, has_security_in_chain_list
from seahub.share.settings import DLP_SCAN_POINT, SHARE_LINK_BACKUP_LIBRARY, \
        PINGAN_SHARE_LINK_BACKUP_LIBRARIES, PINGAN_ITA_AUTHKEY, PINGAN_ITA_CHANNELID, \
        PINGAN_ITA_CHANNELNAME, PINGAN_ITA_EVENTNAME, PINGAN_ITA_FLOWFLAG, PINGAN_ITA_REPORTTYPE, \
        PINGAN_ITA_AFFECTRANGE, PINGAN_ITA_AFFECTLEVEL, PINGAN_ITA_REPORTEVENTAPI, \
        PINGAN_FULL_APPROVE_CHAIN_COMPANY

class Command(BaseCommand):

    label = "share_query_dlp_status"

    def handle(self, *args, **kwargs):

        query_list = []

        fs_verifies = FileShareApprovalStatus.objects.get_dlp_status()
        for fs_verify in fs_verifies:
            if fs_verify.status != STATUS_VERIFING:
                continue

            repo_id = fs_verify.share_link.repo_id
            repo = seafile_api.get_repo(repo_id)
            if not repo:
                continue

            path = fs_verify.share_link.path
            obj_id = seafile_api.get_file_id_by_path(repo_id, path.rstrip('/'))
            if not obj_id:
                continue

            try:
                file_size = seafile_api.get_file_size(repo.store_id, repo.version, obj_id)
                real_path = repo.origin_path + path if repo.origin_path else path
                dirent = seafile_api.get_dirent_by_path(repo.store_id, real_path)
                mtime = dirent.mtime
            except Exception as e:
                print(e)
                file_size = 0
                mtime = 0

            username = fs_verify.share_link.username
            detailed_profile = DetailedProfile.objects.get_detailed_profile_by_user(username)
            if detailed_profile and detailed_profile.company:
                company = base64.b64encode(detailed_profile.company.encode('utf-8'))
                partial_path = os.path.join(company, username,
                        repo.id + '_' + repo.name, path.lstrip('/'))
            else:
                partial_path = os.path.join(username,
                        repo.id + '_' + repo.name, path.lstrip('/'))

            query_list.append((partial_path, fs_verify, file_size, mtime))

        self.do_query(query_list)

    def do_query(self, query_list):

        for e in query_list:

            status, message = self.query_dlp_status(e[0], e[2], [3])
            if status == 0:
                continue

            if status == 1:
                e[1].status = STATUS_PASS
            elif status == 2:
                e[1].status = STATUS_VETO
            else:
                e[1].status = STATUS_BLOCK_HIGH_RISK
                e[1].msg = message

            e[1].vtime = datetime.now()
            e[1].save()

            share_link = e[1].share_link

            try:
                local_file_path = os.path.join(DLP_SCAN_POINT, e[0])
                os.remove(local_file_path)
            except Exception as excp:
                print('Failed to remove %s' % local_file_path)
                print(excp)

            try:
                self.do_backup(share_link)
            except Exception as excp:
                print('Failed to backup share link file %s' % share_link.token)
                print(excp)

            try:
                self.email_revisers(share_link)
                email_verify_result(share_link, share_link.username,
                        source='DLP', result_code=str(status))
            except Exception as excp:
                print('Failed to send email')
                print(excp)

            # submit to ita
            dlp_vtime = e[1].vtime
            dlp_status = e[1].status

            username = share_link.username
            chain_list = UserApprovalChain.objects.get_by_user(username)
            if not chain_list:
                continue

            try:
                resp_json = self.ita_submit(share_link, chain_list, dlp_vtime, dlp_status)
            except Exception as excp:
                print('Failed to submit to ita')
                print(excp)
                continue

            if not resp_json.get('success', False) or not resp_json.get('value', ''):
                print('Error returned when submit to ita')
                pprint(resp_json)
                continue

            event_code = resp_json['value']
            for email in resp_json['post_chain_emails']:
                FileShareApprovalStatus.objects.set_status(share_link, 0,
                        email, msg=event_code)

    def ita_submit(self, share_link, chain_list, dlp_vtime, dlp_status):
        post_chain_emails = []
        username = share_link.username
        company_security_list = get_company_security(username)
        if has_security_in_chain_list(chain_list, company_security_list):
            manager_chain_list = chain_list[:-1]
        else:
            manager_chain_list = chain_list

        audit_flow_detail = []
        for index, sub_chain in enumerate(manager_chain_list):
            info = {}
            if not isinstance(sub_chain, tuple):
                reviser = sub_chain

                reviser_name = email2nickname(reviser)
                if '(' in reviser_name:
                    reviser_name = reviser_name.split('(')[0]
                elif '（' in reviser_name:
                    reviser_name = reviser_name.split('（')[0]

                post_chain_emails.append(reviser)
                info["auditUserVo"] = [
                    {
                        "auditUser": reviser.split('@')[0], # 审批人的um账号
                        "auditUserName": reviser_name, # 审批人的姓名
                        "isOtype": ""
                    }
                ]
                info["stepName"] = "直线领导"
                info["stepOrder"] = index + 1
                info["stepType"] = "U"
                info["typeFlag"] = "O"
                audit_flow_detail.append(info)
            else:
                info["auditUserVo"] = []
                for reviser in sub_chain[1:]:

                    reviser_name = email2nickname(reviser)
                    if '(' in reviser_name:
                        reviser_name = reviser_name.split('(')[0]
                    elif '（' in reviser_name:
                        reviser_name = reviser_name.split('（')[0]

                    post_chain_emails.append(reviser)
                    info["auditUserVo"].append(
                        {
                            "auditUser": reviser.split('@')[0],
                            "auditUserName": reviser_name,
                            "isOtype": ""
                        }
                    )
                info["stepName"] = "直线领导"
                info["stepOrder"] = index + 1
                info["stepType"] = "U"
                info["typeFlag"] = "S"
                audit_flow_detail.append(info)

        add_security_to_chain = False
        if company_security_list:
            d_profile = DetailedProfile.objects.get_detailed_profile_by_user(username)
            if d_profile and d_profile.company and \
                    d_profile.company.lower() in PINGAN_FULL_APPROVE_CHAIN_COMPANY:
                add_security_to_chain = True

            if dlp_status == 3:
                add_security_to_chain = True

        if add_security_to_chain:
            info = {}
            info["auditUserVo"] = []
            for reviser in company_security_list:

                reviser_name = email2nickname(reviser)
                if '(' in reviser_name:
                    reviser_name = reviser_name.split('(')[0]
                elif '（' in reviser_name:
                    reviser_name = reviser_name.split('（')[0]

                post_chain_emails.append(reviser)
                info["auditUserVo"].append(
                    {
                        "auditUser": reviser.split('@')[0],
                        "auditUserName": reviser_name,
                        "isOtype": ""
                    }
                )
            info["stepName"] = "信息安全员"
            info["stepOrder"] = len(manager_chain_list)+1
            info["stepType"] = "U"
            info["typeFlag"] = "O" if len(company_security_list) == 1 else "S"
            audit_flow_detail.append(info)

        extra_info = FileShareExtraInfo.objects.filter(share_link=share_link)
        note = extra_info[0].note if extra_info else ''
        sent_to_emails = ', '.join([e.sent_to for e in extra_info]) if extra_info else ''

        dlp_status_dict = {
            1: '同意',
            2: '否决',
            3: '高敏',
        }

        payload = {
            "password": "password-not-used",
            "um": username.split('@')[0], # sunruili267
            "authKey": PINGAN_ITA_AUTHKEY,
            "channelId": PINGAN_ITA_CHANNELID,
            "channelName": PINGAN_ITA_CHANNELNAME,
            "eventName": PINGAN_ITA_EVENTNAME,
            "flowFlag": PINGAN_ITA_FLOWFLAG,
            "reportType": PINGAN_ITA_REPORTTYPE,
            "affectRange": PINGAN_ITA_AFFECTRANGE,
            "affectLevel": PINGAN_ITA_AFFECTLEVEL,
            "auditFlowDetail": audit_flow_detail,
            "inputors": [
                {
                    "inputorName": "fileName",
                    "selectorType": "class",
                    "values": share_link.get_name() # "具体的文件名"
                },
                {
                    "inputorName": "submitUM",
                    "selectorType": "class",
                    "values": username.split('@')[0] # sunruili267
                },
                {
                    "inputorName": "DLPStatus",
                    "selectorType": "class",
                    "values": dlp_status_dict.get(dlp_status, '') # "具体的DLP审核状态"
                },
                {
                    "inputorName": "DLPTime",
                    "selectorType": "class",
                    "values": dlp_vtime.strftime("%Y-%m-%d %H:%M:%S") # "dlp审核时间"
                },
                {
                    "inputorName": "outURLCreateTime",
                    "selectorType": "class",
                    "values": share_link.ctime.strftime("%Y-%m-%d %H:%M:%S") # "外链创建时间"
                },
                {
                    "inputorName": "outURLGetUM",
                    "selectorType": "class",
                    "values": sent_to_emails # "外链接收人"
                },
                {
                    "inputorName": "outURL",
                    "selectorType": "class",
                    "values": share_link.get_full_url() # "外链"
                },
                {
                    "inputorName": "case",
                    "selectorType": "class",
                    "values": note # "外发原因"
                },
            ]
        }
        resp = requests.post(PINGAN_ITA_REPORTEVENTAPI, data=json.dumps(payload))
        resp_json = resp.json()
        resp_json['post_data'] = payload
        resp_json['post_chain_emails'] = post_chain_emails
        return resp_json

    def query_dlp_status(self, partial_path, file_size, mtime):
        """Return 0 if there is no DLP record, 1 if pass DLP check, else failed.
        """
        from .checkdlp import MSSQL
        ms = MSSQL()
        result, message = ms.CheckDLP(partial_path, file_size, mtime)
        return result, message

    def get_user_language(self, username):
        return Profile.objects.get_user_language(username)

    def do_backup(self, fileshare):

        if SHARE_LINK_BACKUP_LIBRARY is None:
            print('SHARE_LINK_BACKUP_LIBRARY is None, please create a backup library.')
            return

        if PINGAN_SHARE_LINK_BACKUP_LIBRARIES is None:
            print('PINGAN_SHARE_LINK_BACKUP_LIBRARIES is None, please create backup libraries.')
            return

        company_backup_repo_ip = ''
        username = fileshare.username
        detailed_profile = DetailedProfile.objects.get_detailed_profile_by_user(username)
        if detailed_profile and detailed_profile.company:
            company_id = detailed_profile.company.lower()
            if company_id in PINGAN_SHARE_LINK_BACKUP_LIBRARIES:
                company_backup_repo_ip = PINGAN_SHARE_LINK_BACKUP_LIBRARIES[company_id]

        new_file = '%s-%s-%s.%s' % (username, datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                os.path.basename(fileshare.path), fileshare.token)

        admin_backup_repo_ip = SHARE_LINK_BACKUP_LIBRARY
        seafile_api.copy_file(fileshare.repo_id, os.path.dirname(fileshare.path),
                os.path.basename(fileshare.path), admin_backup_repo_ip, '/',
                new_file, '', need_progress=0)

        if company_backup_repo_ip:
            seafile_api.copy_file(fileshare.repo_id, os.path.dirname(fileshare.path),
                    os.path.basename(fileshare.path), company_backup_repo_ip, '/',
                    new_file, '', need_progress=0)

    def email_revisers(self, fileshare):
        chain = fileshare.get_approval_chain()
        if len(chain) == 0:
            print('Failed to send email, no reviser info found for user: %s' % fileshare.username)
            return

        for ele in chain:
            if not isinstance(ele, tuple):
                emails = [ele]
            else:
                emails = ele[1:]

            for email in emails:

                # send notice first
                file_shared_link_verify.send(sender=None,
                        from_user=fileshare.username, to_user=email, token=fileshare.token)

                # save current language
                cur_language = translation.get_language()

                # get and active user language
                user_language = self.get_user_language(email)
                translation.activate(user_language)

                email_reviser(fileshare, email)

                # restore current language
                translation.activate(cur_language)
