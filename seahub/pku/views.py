# -*- coding: utf-8 -*-

import logging
import hashlib
import requests

from django.shortcuts import render
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext as _

from seahub.api2.utils import get_api_token
from seahub import auth
from seahub.profile.models import Profile
from seahub.utils import render_error, get_service_url

from seahub.pku.settings import PKU_IAAA_APPID, \
        PKU_IAAA_APPNAME, PKU_IAAA_MSGABS_KEY, PKU_IAAA_OAUTH_URL

logger = logging.getLogger(__name__)

def pku_iaaa_login(request):

    return render(request, 'pku/iaaa-login.html', {
        'app_id': PKU_IAAA_APPID,
        'app_name': PKU_IAAA_APPNAME,
        'iaaa_oauth_url': PKU_IAAA_OAUTH_URL,
        'redirect_url': get_service_url().rstrip('/') + reverse('pku_iaaa_callback'),
        'redirect_logon_url': get_service_url().rstrip('/') + reverse('auth_login')
    })

def pku_iaaa_callback(request):

    token = request.GET.get('token', '')
    client_ip = request.META.get('HTTP_X_FORWARDED_FOR', '115.27.161.11')

    param_str = "appId=%s&remoteAddr=%s&token=%s" % (PKU_IAAA_APPID, client_ip, token)
    src_str = param_str + PKU_IAAA_MSGABS_KEY

    md5 = hashlib.md5()
    md5.update(src_str)
    msg_abs = md5.hexdigest()

    validate_url ='https://iaaa.pku.edu.cn/iaaa/svc/token/validate.do?appId=%s&remoteAddr=%s&token=%s&msgAbs=%s' % \
            (PKU_IAAA_APPID, client_ip, token, msg_abs)
    user_info_resp = requests.get(validate_url)
    resp_json = user_info_resp.json()
    if not resp_json['success']:
        logger.error(validate_url)
        logger.error(resp_json)
        return render_error(request, _('Error, please contact administrator.'))

    user_info = resp_json.get('userInfo', '')
    if not user_info or 'identityId' not in user_info:
        logger.error('Response invalid.')
        logger.error(resp_json)
        return render_error(request, _('Error, please contact administrator.'))

    email = user_info['identityId'] + '@pku.edu.cn'
    user = auth.authenticate(remote_user=email)
    if not user:
        return render_error(request, _('Error, please contact administrator.'))
    if not user.is_active:
        return render_error(request, _(u'Please contact administrator to active.'))

    # User is valid.  Set request.user and persist user in the session
    # by logging the user in.
    request.user = user
    auth.login(request, user)

    # update user's profile
    profile = Profile.objects.get_profile_by_user(email)
    if not profile:
        profile = Profile(user=email)

    profile.contact_email = email
    profile.save()

    name = user_info['name'] if user_info.has_key('name') else ''
    if name:
        profile.nickname = name.strip()
        profile.save()

    # generate auth token for Seafile client
    api_token = get_api_token(request)

    # redirect user to home page
    response = HttpResponseRedirect('/')
    response.set_cookie('seahub_auth', email + '@' + api_token.key)
    return response
