# -*- coding: utf-8 -*-

import logging
from django.shortcuts import render, get_object_or_404

from seahub.utils import render_error, redirect_to_login
from seahub.utils.ip import get_remote_ip

from seahub.share.constants import STATUS_VETO, STATUS_BLOCK_HIGH_RISK
from seahub.share.models import FileShare, set_share_link_access, \
        check_share_link_access, FileShareExtraInfo, FileShareApprovalStatus
from seahub.share.forms import SharedLinkPasswordForm, CaptchaSharedLinkPasswordForm
from seahub.share.utils import incr_share_link_decrypt_failed_attempts, \
        clear_share_link_decrypt_failed_attempts, \
        show_captcha_share_link_password_form, enable_share_link_verify_code, \
        get_unusable_verify_code
from seahub.share.signals import file_shared_link_decrypted
from seahub.share.pingan_utils import user_in_chain, get_dlp_approval_status, \
        ita_get_all_event_detail
from seahub.share.settings import PINGAN_IS_DMZ_SERVER

logger = logging.getLogger(__name__)

def share_link_approval_for_pingan(func):
    """Decorator for share link approval test for PingAn Group.
    When a share link does not pass verify, only verifier can view the link,
    no mater encrypted or expired.
    """
    def _decorated(request, token, *args, **kwargs):

        fileshare = get_object_or_404(FileShare, token=token)

        if PINGAN_IS_DMZ_SERVER:
            skip_encrypted = False

            event_code = ''
            status_list = FileShareApprovalStatus.objects.filter(share_link_id=fileshare.id)
            for status in status_list:
                msg = status.msg
                if msg and msg.startswith('R'):
                    event_code = msg

            if event_code:
                try:
                    resp_json = ita_get_all_event_detail(fileshare.username, event_code)
                except Exception as e:
                    logger.error(e)
                    return render_error(request, u'服务器内部错误，请联系管理员解决。')

                if not resp_json.get('success', False) or not resp_json.get('value', []):
                    logger.error(resp_json)
                    return render_error(request, resp_json.get('errorMsg', '服务器内部错误，请联系管理员解决。'))

                ita_status = resp_json['value'][0]['status']
                if ita_status in ('A', 'B', 'C'):
                    return render_error(request, u'未审核通过，你无法访问该文件。')
            else:
                if not fileshare.pass_verify():
                    return render_error(request, u'未审核通过，你无法访问该文件。')
        else:
            skip_encrypted = True

            if not request.user.is_authenticated():
                return redirect_to_login(request)

            username = request.user.username
            chain = fileshare.get_approval_chain()
            if not user_in_chain(username, chain):
                return render_error(request, u'权限不足，你无法访问该文件。')

            extra_info = FileShareExtraInfo.objects.filter(share_link=fileshare)
            note = extra_info[0].note if extra_info else ''
            sent_to_emails = ', '.join([e.sent_to for e in extra_info]) if extra_info else ''

            dlp_msg_dict = {}
            show_dlp_veto_msg = False
            dlp_approval_status = get_dlp_approval_status(fileshare)
            if dlp_approval_status:
                show_dlp_veto_msg = get_dlp_approval_status(fileshare).status in (STATUS_VETO,
                        STATUS_BLOCK_HIGH_RISK)
                dlp_msg_dict = fileshare.get_dlp_msg()

            kwargs.update({
                'skip_encrypted': skip_encrypted,
                'share_to': sent_to_emails,
                'note': note,
                'show_dlp_veto_msg': show_dlp_veto_msg,
                'download_cnt': fileshare.get_download_cnt(),
                'policy_categories': dlp_msg_dict['policy_categories'] if 'policy_categories' in dlp_msg_dict else '',
                'breach_content': dlp_msg_dict['breach_content'] if 'breach_content' in dlp_msg_dict else '',
                'total_matches': dlp_msg_dict['total_matches'] if 'total_matches' in dlp_msg_dict else '',
            })

        return func(request, fileshare, *args, **kwargs)

    return _decorated

def share_link_passwd_check_for_pingan(func):
    """Decorator for share link password check, show captcah if too many
    failed attempts.

    Also show email verify code if `ENABLE_SHARE_LINK_VERIFY_CODE = True`
    """
    def _decorated(request, fileshare, *args, **kwargs):
        token = fileshare.token
        skip_encrypted = kwargs.get('skip_encrypted', False)
        if skip_encrypted or not fileshare.is_encrypted() or \
           check_share_link_access(request, token) is True:
            # no check for un-encrypt shared link, or if `skip_encrypted` in
            # keyword arguments or password is already stored in session
            return func(request, fileshare, *args, **kwargs)

        d = {'token': token, 'view_name': func.__name__,
             'enable_share_link_verify_code': enable_share_link_verify_code()}
        ip = get_remote_ip(request)
        validation_tmpl = 'share_access_validation_for_pingan.html'
        if request.method == 'POST':
            post_values = request.POST.copy()
            post_values['enc_password'] = fileshare.password
            post_values['token'] = token
            if not enable_share_link_verify_code():
                # set verify code to random string to make form validation
                # pass
                post_values['verify_code'] = get_unusable_verify_code()

            if show_captcha_share_link_password_form(ip):
                form = CaptchaSharedLinkPasswordForm(post_values)
            else:
                form = SharedLinkPasswordForm(post_values)
            d['form'] = form
            if form.is_valid():
                file_shared_link_decrypted.send(sender=None, fileshare=fileshare,
                                                request=request, success=True)
                set_share_link_access(request, token)
                clear_share_link_decrypt_failed_attempts(ip)

                return func(request, fileshare, *args, **kwargs)
            else:
                file_shared_link_decrypted.send(sender=None, fileshare=fileshare,
                                                request=request, success=False)

                incr_share_link_decrypt_failed_attempts(ip)
                d.update({'password': request.POST.get('password', ''),
                          'verify_code': request.POST.get('verify_code', '')})
                return render(request, validation_tmpl, d)
        else:
            if show_captcha_share_link_password_form(ip):
                d.update({'form': CaptchaSharedLinkPasswordForm})
            return render(request, validation_tmpl, d)
    return _decorated
