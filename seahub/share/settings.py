# -*- coding: utf-8 -*-
from django.conf import settings

######################### Start PingAn Group related ########################
ENABLE_FILESHARE_CHECK = getattr(settings, 'ENABLE_FILESHARE_CHECK', False)
FUSE_MOUNT_POINT = getattr(settings, 'FUSE_MOUNT_POINT', '/tmp/seafile_fuse')
ENABLE_FILESHARE_DLP_CHECK = getattr(settings, 'ENABLE_FILESHARE_DLP_CHECK', True)
DLP_SCAN_POINT = getattr(settings, 'DLP_SCAN_POINT', '/tmp/dlp_scan')
SHARE_LINK_BACKUP_LIBRARY = getattr(settings, 'SHARE_LINK_BACKUP_LIBRARY', None)
PINGAN_SHARE_LINK_BACKUP_LIBRARIES = getattr(settings, 'PINGAN_SHARE_LINK_BACKUP_LIBRARIES', {})

SHARE_LINK_REMEMBER_PASSWORD = getattr(settings, 'SHARE_LINK_REMEMBER_PASSWORD', True)
SHARE_LINK_DECRYPT_ATTEMPT_LIMIT = getattr(settings, 'SHARE_LINK_ATTEMPT_LIMIT', 3)
SHARE_LINK_DECRYPT_ATTEMPT_TIMEOUT = getattr(settings, 'SHARE_LINK_DECRYPT_ATTEMPT_TIMEOUT', 15 * 60)
ENABLE_SHARE_LINK_VERIFY_CODE = getattr(settings, 'ENABLE_SHARE_LINK_VERIFY_CODE', True)
PA_EMAIL_PATTERN_LIST = getattr(settings, 'PA_EMAIL_PATTERN_LIST', ['*@pingan.com.cn', ])
PA_STRONG_PASSWORD_PATT = getattr(settings, 'PA_STRONG_PASSWORD_PATT', ())
SHARE_LINK_MIN_FILE_SIZE = getattr(settings, 'SHARE_LINK_MIN_FILE_SIZE', 15)  # Mb


PINGAN_SHARE_LINK_SEND_TO_VISITS_LIMIT_BASE = getattr(settings,
        'PINGAN_SHARE_LINK_SEND_TO_VISITS_LIMIT_BASE', 2)
PINGAN_SHARE_LINK_REVISER_VISITS_LIMIT_BASE= getattr(settings,
        'PINGAN_SHARE_LINK_REVISER_VISITS_LIMIT_BASE', 1)

PINGAN_FULL_APPROVE_CHAIN_COMPANY = getattr(settings,
        'PINGAN_FULL_APPROVE_CHAIN_COMPANY', [])

PINGAN_COMPANY_SEAFILE_DEPT_MAP = getattr(settings,
        'PINGAN_COMPANY_SEAFILE_DEPT_MAP', {})

PINGAN_COMPANY_ID_NAME = getattr(settings,
        'PINGAN_COMPANY_ID_NAME', {})

PINGAN_SHARE_LINKS_REPORT_ADMIN = getattr(settings,
        'PINGAN_SHARE_LINKS_REPORT_ADMIN', [])

PINGAN_EMAIL_URL = getattr(settings,
        'PINGAN_EMAIL_URL', 'http://pecp-mngt-api-super.paic.com.cn/pecp-mngt/appsvr/public/smg/sendEmail')

PINGAN_DMZ_DOMAIN = getattr(settings,
        'PINGAN_DMZ_DOMAIN', 'https://pafile2.pingan.com.cn')

PINGAN_FAQ_URL = getattr(settings,
        'PINGAN_FAQ_URL', '#')

PINGAN_HELP_URL = getattr(settings,
        'PINGAN_HELP_URL', 'http://fcloud.paic.com.cn/f/470c7c10bd/?raw=1')

PINGAN_PERMISSION_HELP_URL = getattr(settings,
        'PINGAN_PERMISSION_HELP_URL', 'http://fcloud.paic.com.cn/f/e176568aa7/?raw=1')
######################### End PingAn Group related ##########################
