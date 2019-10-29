import logging
import hashlib
import requests

from django.conf import settings

from seahub.base.accounts import User, AuthBackend
from seahub.pku.settings import PKU_IAAA_APPID, PKU_IAAA_MSGABS_KEY, \
        PKU_IAAA_CHECK_OTP_URL

logger = logging.getLogger(__name__)


class PkuIaaaAuthUserBackend(AuthBackend):

    # Create a User object if not already in the database?
    create_unknown_user = getattr(settings,
            'PKU_IAAA_AUTH_CREATE_UNKNOWN_USER', True)

    # Create active user by default.
    auto_activate = getattr(settings,
            'PKU_IAAA_AUTH_ACTIVATE_USER_AFTER_CREATION', False)

    def authenticate(self, remote_user=None):
        if not remote_user:
            return None

        username = self.clean_username(remote_user)

        # get user from ccnet
        user = self.get_user(username)
        if not user:
            # when user doesn't exist
            if not self.create_unknown_user:
                return None

            try:
                user = User.objects.create_user(email=username,
                        is_active=self.auto_activate)
            except Exception as e:
                logger.error(e)
                return None

        # get user again with updated extra info after configure
        return self.get_user(username)

    def clean_username(self, username):
        """
        Performs any cleaning on the "username" prior to using it to get or
        create the user object.  Returns the cleaned username.

        By default, returns the username unchanged.
        """
        return username.strip()


class PkuIaaaOTPBackend(AuthBackend):

    def authenticate(self, username=None, password=None, client_ip=''):
        identity_id = username
        otp_token = password
        if not identity_id or not otp_token:
            return None

        param_str = "appId=%s&remoteAddr=%s&userCode=%s&userName=%s" % \
                (PKU_IAAA_APPID, client_ip, otp_token, identity_id)
        src_str = param_str + PKU_IAAA_MSGABS_KEY

        md5 = hashlib.md5()
        md5.update(src_str)
        msg_abs = md5.hexdigest()

        validate_url = PKU_IAAA_CHECK_OTP_URL + '?appId=%s&remoteAddr=%s&userCode=%s&userName=%s&msgAbs=%s' % \
                (PKU_IAAA_APPID, client_ip, otp_token, username, msg_abs)

        user_info_resp = requests.get(validate_url)
        resp_json = user_info_resp.json()
        if not resp_json['success']:
            logger.error(validate_url)
            logger.error(resp_json)
            return None

        # get user from ccnet
        return self.get_user(identity_id + '@pku.edu.cn')
