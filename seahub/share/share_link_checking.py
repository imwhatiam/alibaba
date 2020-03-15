# -*- coding: utf-8 -*-
"""Utility functions used for share link verify in PingAn Group.
"""
import base64
import os
import logging
import string

from django.utils import translation
from django.utils.translation import ugettext as _

from .settings import (FUSE_MOUNT_POINT, DLP_SCAN_POINT,
                       ENABLE_FILESHARE_DLP_CHECK)
from seahub.profile.models import Profile, DetailedProfile
from seahub.share.constants import STATUS_PASS, STATUS_VETO
from seahub.share.models import (FileShareApprovalChain, ApprovalChain,
                                 UserApprovalChain, FileShareApprovalStatus)
from seahub.utils import get_service_url, send_html_email

# Get an instance of a logger
logger = logging.getLogger(__name__)

def check_share_link(request, fileshare, repo):
    """DLP and huamn check share link when create share link.
    """
    # record share link approval info
    FileShareApprovalChain.objects.create_fs_approval_chain(fileshare)

    # set default DLP status
    fs_v = FileShareApprovalStatus(share_link=fileshare,
                                   email=FileShareApprovalStatus.DLP_EMAIL)

    if not ENABLE_FILESHARE_DLP_CHECK:
        # dlp is disabled, pass
        # TODO: notify next revisers ?
        fs_v.DLP_status = STATUS_PASS

    fs_v.save()

def is_file_link_reviser(username):
    """Check whether a user is a reviser.
    """
    all_revisers = ApprovalChain.objects.get_emails()
    all_revisers += UserApprovalChain.objects.get_emails()
    all_revisers += FileShareApprovalChain.objects.values_list('email',
                                                               flat=True)

    return True if username in set(map(string.lower, all_revisers)) else False


def email_reviser(fileshare, reviser_email):
    """Send email to revisers to verify shared link.
    If DLP veto, show veto message to revisers.
    """
    subject = '请审核新创建的共享外链。'

    app_status = FileShareApprovalStatus.objects.get_dlp_status_by_share_link(fileshare)
    if app_status is not None:
        show_dlp_veto_msg = app_status == STATUS_VETO
    else:
        show_dlp_veto_msg = False

    c = {
        'email': fileshare.username,
        'file_name': fileshare.get_name(),
        'file_shared_link': fileshare.get_full_url(),
        'service_url': get_service_url(),
        'show_dlp_veto_msg': show_dlp_veto_msg,
    }
    try:
        send_html_email(subject, 'share/share_link_verify_email.html',
                        c, None, [reviser_email])
        logger.info('Send email to %s, link: %s' % (reviser_email,
                                                    fileshare.get_full_url()))
    except Exception as e:
        logger.error('Faied to send email to %s, please check email settings.' % reviser_email)
        logger.error(e)

def email_verify_result(fileshare, email_to, source='DLP', result_code=1):
    """Send email to `email_to` about shared link verify result.
    """
    # save current language
    cur_language = translation.get_language()

    # get and active user language
    user_language = Profile.objects.get_user_language(email_to)
    translation.activate(user_language)

    c = {
        'source': source,
        'result_code': result_code,
        'file_name': fileshare.get_name(),
        'service_url': get_service_url().rstrip('/'),
    }
    subject = '您共享外链的审核状态。'
    try:
        send_html_email(subject, 'share/share_link_verify_result_email.html',
                        c, None, [email_to])
        logger.info('Send verify result email to %s, link: %s' % (
            email_to, fileshare.get_full_url()))
    except Exception as e:
        logger.error('Faied to send verify result email to %s' % email_to)
        logger.error(e)

    # restore current language
    translation.activate(cur_language)
