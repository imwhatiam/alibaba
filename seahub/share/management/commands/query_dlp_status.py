# -*- coding: utf-8 -*-
import base64
from datetime import datetime
import logging
import os, sys
reload(sys)
sys.setdefaultencoding("utf-8")

from django.core.management.base import BaseCommand
from django.utils import translation
from django.utils.translation import ugettext as _
from seaserv import seafile_api

from seahub.profile.models import Profile, DetailedProfile
from seahub.share.models import FileShareApprovalStatus
from seahub.share.constants import STATUS_VERIFING, STATUS_PASS, STATUS_VETO, STATUS_BLOCK_HIGH_RISK
from seahub.share.signals import file_shared_link_verify
from seahub.share.settings import DLP_SCAN_POINT, SHARE_LINK_BACKUP_LIBRARY, \
        PINGAN_SHARE_LINK_BACKUP_LIBRARIES
from seahub.share.share_link_checking import (
    email_reviser, email_verify_result)
from seahub.utils import get_service_url, send_html_email

# Get an instance of a logger
logger = logging.getLogger(__name__)

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

            username = fs_verify.share_link.username
            path = fs_verify.share_link.path

            try:
                obj_id = seafile_api.get_file_id_by_path(repo_id,
                                                         path.rstrip('/'))
                if not obj_id:      # file is deleted
                    continue

                file_size = seafile_api.get_file_size(repo.store_id,
                                                      repo.version, obj_id)
                real_path = repo.origin_path + path if repo.origin_path else path
                dirent = seafile_api.get_dirent_by_path(repo.store_id, real_path)
                mtime = dirent.mtime
            except Exception as e:
                logger.error(e)
                file_size = 0
                mtime = 0

            # 5Lit5paH/pengjq@pingan.com.cn/d867f107-ad54-4093-8f0e-5b8ad670a70e_我的资料库/b.txt
            d_p = DetailedProfile.objects.get_detailed_profile_by_user(username)
            if d_p and d_p.company:
                company = base64.b64encode(d_p.company.encode('utf-8'))
                partial_path = os.path.join(company, username,
                                            repo.id + '_' + repo.name,
                                            path.lstrip('/'))
            else:
                partial_path = os.path.join(username,
                                            repo.id + '_' + repo.name,
                                            path.lstrip('/'))

            query_list.append((partial_path, fs_verify, file_size, mtime))
            logger.info('Add %s::%s::%s to DLP query list.' % (partial_path,
                                                               file_size, mtime))
            print 'Add %s::%s::%s to DLP query list.' % (partial_path,
                                                         file_size, mtime)

        self.do_query(query_list)

    def do_query(self, query_list):
        for e in query_list:
            status, message = self.query_dlp_status(e[0], e[2], [3])
            if status == 0:
                # do nothing
                pass
            else:
                if status == 1:
                    # set dlp status to pass
                    e[1].status = STATUS_PASS
                    print '%s pass dlp test' % e[0]
                elif status == 2:
                    # set dlp status to veto
                    e[1].status = STATUS_VETO
                    print '%s failed to pass dlp test' % e[0]
                else:
                    # set dlp status to veto
                    e[1].status = STATUS_BLOCK_HIGH_RISK
                    e[1].msg = message
                    print '%s dlp block high risk' % e[0]

                e[1].vtime = datetime.now()
                e[1].save()

                # remove symbol link
                symbol_link = os.path.join(DLP_SCAN_POINT, e[0])
                try:
                    os.remove(symbol_link)
                except (OSError, Exception) as exc:
                    logger.error('Failed to remove %s' % symbol_link)
                    logger.error(exc)

                if e[1].share_link.is_verifing():
                    # Send emails to revisers for huamn check no matter DLP
                    # pass or veto.
                    self.email_revisers(e[1].share_link)

                # save file to later review
                self.do_backup(e[1].share_link)

                # email DLP verify result to shared link owner
                email_verify_result(e[1].share_link, e[1].share_link.username,
                                    source='DLP', result_code=str(status))

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
            logger.error('SHARE_LINK_BACKUP_LIBRARY is None, please create a backup library.')
            return

        if PINGAN_SHARE_LINK_BACKUP_LIBRARIES is None:
            logger.error('PINGAN_SHARE_LINK_BACKUP_LIBRARIES is None, please create backup libraries.')
            return

        username = fileshare.username
        d_profile = DetailedProfile.objects.get_detailed_profile_by_user(username)
        if d_profile and d_profile.company:
            company_id = d_profile.company.lower()
            if company_id in PINGAN_SHARE_LINK_BACKUP_LIBRARIES:
                company_backup_repo_ip = PINGAN_SHARE_LINK_BACKUP_LIBRARIES[company_id]
            else:
                company_backup_repo_ip = ''

        new_file = '%s-%s-%s.%s' % (username,
                                 datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                 os.path.basename(fileshare.path),
                                 fileshare.token
        )

        try:
            admin_backup_repo_ip = SHARE_LINK_BACKUP_LIBRARY
            seafile_api.copy_file(
                fileshare.repo_id, os.path.dirname(fileshare.path),
                os.path.basename(fileshare.path), admin_backup_repo_ip, '/',
                new_file, '', need_progress=0)
            print 'Backup to %s successfuly, name is %s.' % (admin_backup_repo_ip, new_file)

            if company_backup_repo_ip:
                seafile_api.copy_file(
                    fileshare.repo_id, os.path.dirname(fileshare.path),
                    os.path.basename(fileshare.path), company_backup_repo_ip, '/',
                    new_file, '', need_progress=0)
                print 'Backup to %s successfuly, name is %s.' % (company_backup_repo_ip, new_file)
        except Exception as e:
            logger.error('Failed to backup, %s' % e)

    def email_revisers(self, fileshare):
        chain = fileshare.get_approval_chain()
        if len(chain) == 0:
            logger.error('Failed to send email, no reviser info found for user: %s' % fileshare.username)
            return

        ele = chain[0]
        if isinstance(ele, basestring):
            emails = [ele]
        else:
            emails = ele[1:]

        for email in emails:
            # add default approval status
            FileShareApprovalStatus.objects.set_status(
                fileshare, status=STATUS_VERIFING, username=email)

            # send notice first
            file_shared_link_verify.send(sender=None,
                                         from_user=fileshare.username,
                                         to_user=email,
                                         token=fileshare.token)

            # save current language
            cur_language = translation.get_language()

            # get and active user language
            user_language = self.get_user_language(email)
            translation.activate(user_language)

            email_reviser(fileshare, email)

            # restore current language
            translation.activate(cur_language)
