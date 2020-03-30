# -*- coding: utf-8 -*-
from django.conf import settings

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

##########
# share link visit limit
PINGAN_SHARE_LINK_SEND_TO_VISITS_LIMIT_BASE = getattr(settings, 'PINGAN_SHARE_LINK_SEND_TO_VISITS_LIMIT_BASE', 2)
PINGAN_SHARE_LINK_REVISER_VISITS_LIMIT_BASE= getattr(settings, 'PINGAN_SHARE_LINK_REVISER_VISITS_LIMIT_BASE', 1)

# share link approve
PINGAN_COMPANY_ID_NAME = getattr(settings, 'PINGAN_COMPANY_ID_NAME', {})
PINGAN_COMPANY_SEAFILE_DEPT_MAP = getattr(settings, 'PINGAN_COMPANY_SEAFILE_DEPT_MAP', {})
PINGAN_FULL_APPROVE_CHAIN_COMPANY = getattr(settings, 'PINGAN_FULL_APPROVE_CHAIN_COMPANY', [])
PINGAN_SHARE_LINKS_REPORT_ADMIN = getattr(settings, 'PINGAN_SHARE_LINKS_REPORT_ADMIN', [])

# pingan email
PINGAN_EMAIL_URL = getattr(settings, 'PINGAN_EMAIL_URL', 'http://pecp-mngt-api-super.paic.com.cn/pecp-mngt/appsvr/public/smg/sendEmail')

# DMZ
PINGAN_DMZ_DOMAIN = getattr(settings, 'PINGAN_DMZ_DOMAIN', 'https://pafile2.pingan.com.cn')
PINGAN_IS_DMZ_SERVER = getattr(settings, 'PINGAN_IS_DMZ_SERVER', False)

# side panel
PINGAN_FAQ_URL = getattr(settings, 'PINGAN_FAQ_URL', '#')
PINGAN_HELP_URL = getattr(settings, 'PINGAN_HELP_URL', 'http://fcloud.paic.com.cn/f/470c7c10bd/?raw=1')
PINGAN_PERMISSION_HELP_URL = getattr(settings, 'PINGAN_PERMISSION_HELP_URL', 'http://fcloud.paic.com.cn/f/e176568aa7/?raw=1')

# DLP
PINGAN_DLP_DATABASE_CONF = getattr(settings, 'PINGAN_DLP_DATABASE_CONF', '/wls/seafile/check-dlp/mssql.conf')
PINGAN_DLP_DB_CONNECT_TIMEOUT = getattr(settings, 'PINGAN_DLP_DB_CONNECT_TIMEOUT', 50)
PINGAN_DLP_DB_LOGIN_CONNECT_TIMEOUT = getattr(settings, 'PINGAN_DLP_DB_LOGIN_CONNECT_TIMEOUT', 50)

# ITA
# 测试：http://30.12.59.63:80
# 生产：http://30.16.97.197:80

# 测试、生产一样
PINGAN_ITA_AUTHKEY = getattr(settings, 'PINGAN_ITA_AUTHKEY', "af7c205e-6bb7-4434-9c51-c89d2ddcd8d9")
PINGAN_ITA_REPORTEVENTAPI = getattr(settings, 'PINGAN_ITA_REPORTEVENTAPI', "http://30.16.97.197:80/api/reportEventAPI")
PINGAN_ITA_GETALLEVENTDETAIL = getattr(settings, 'PINGAN_ITA_GETALLEVENTDETAIL', 'http://30.16.97.197:80/api/getAllEventDetail')
PINGAN_ITA_HASEOAAUTH = getattr(settings, 'PINGAN_ITA_HASEOAAUTH', 'http://30.16.97.197:80/api/hasEoaAuth')

# ITA事件取消的authkey: fc1789bd-8d69-4e31-a3fd-dc38c9ff0898
PINGAN_ITA_AUTHKEY_FOR_CANCEL_EVENT = getattr(settings, 'PINGAN_ITA_AUTHKEY_FOR_CANCEL_EVENT', 'fc1789bd-8d69-4e31-a3fd-dc38c9ff0898')
PINGAN_ITA_CANCELEVENTAPI = getattr(settings, 'PINGAN_ITA_CANCELEVENTAPI', 'http://30.16.97.197:80/api/cancelEventAPI')

PINGAN_ITA_CHANNELID = getattr(settings, 'PINGAN_ITA_CHANNELID', 1402) # 测试是2169
PINGAN_ITA_AFFECTRANGE = getattr(settings, 'PINGAN_ITA_AFFECTRANGE', "SLA_002_1_1") # 测试是SLA_050_2_1
PINGAN_ITA_AFFECTLEVEL = getattr(settings, 'PINGAN_ITA_AFFECTLEVEL', "SLA_002_2_1") # 测试是SLA_050_1_1

PINGAN_ITA_CHANNELNAME = getattr(settings, 'PINGAN_ITA_CHANNELNAME', "大文件外发系统文件外发申请")
PINGAN_ITA_EVENTNAME = getattr(settings, 'PINGAN_ITA_EVENTNAME', "大文件外发系统文件外发申请")
PINGAN_ITA_FLOWFLAG = getattr(settings, 'PINGAN_ITA_FLOWFLAG', "Y")
PINGAN_ITA_REPORTTYPE = getattr(settings, 'PINGAN_ITA_REPORTTYPE', 0)

PINGAN_AUTH_TOKEN_USER_LIMIT = getattr(settings, 'PINGAN_AUTH_TOKEN_USER_LIMIT', [])
PINGAN_AUTH_TOKEN_SYSTEM_TOKEN_LIMIT = getattr(settings, 'PINGAN_AUTH_TOKEN_SYSTEM_TOKEN_LIMIT', [])

# default 10 Mb, if user"s quota less than 10 Mb, he/she can not create share link
PINGAN_USER_SPACE_QUOTA_LIMIT = getattr(settings, 'PINGAN_USER_SPACE_QUOTA_LIMIT', 10)
