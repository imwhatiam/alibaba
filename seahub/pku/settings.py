from django.conf import settings

ENABLE_PKU_IAAA = getattr(settings, 'ENABLE_PKU_IAAA', '')
PKU_IAAA_APPID = getattr(settings, 'PKU_IAAA_APPID', '')
PKU_IAAA_APPNAME = getattr(settings, 'PKU_IAAA_APPNAME', '')
PKU_IAAA_MSGABS_KEY = getattr(settings, 'PKU_IAAA_MSGABS_KEY', '')
PKU_IAAA_CHECK_OTP_URL = getattr(settings, 'PKU_IAAA_CHECK_OTP_URL', 'https://iaaa.pku.edu.cn/iaaa/svc/mobileAuthen/checkOtpLogon.do')
PKU_IAAA_OAUTH_URL = getattr(settings, 'PKU_IAAA_OAUTH_URL', 'https://iaaa.pku.edu.cn/iaaa/oauth.jsp')

