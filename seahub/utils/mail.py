# Copyright (c) 2012-2016 Seafile Ltd.
import os
import logging

from django.template import Context, loader
from post_office import mail
from post_office.models import PRIORITY
from constance import config

from seahub.utils import get_site_scheme_and_netloc, get_site_name
from seahub.settings import MEDIA_URL, LOGO_PATH, \
        MEDIA_ROOT, CUSTOM_LOGO_PATH, SITE_NAME
try:
    from seahub.settings import PAFILE_EMAIL_DEBUG
except ImportError:
    PAFILE_EMAIL_DEBUG = False

MAIL_PRIORITY = PRIORITY        # 'low medium high now'

def send_html_email_with_dj_template(recipients, subject, dj_template,
                                     context={}, sender=None, template=None,
                                     message='', headers=None,
                                     priority=None, backend=''):
    """

    Arguments:
    - `recipients`:
    - `subject`:
    - `sender`:
    - `template`:
    - `context`:

    """

    # get logo path
    logo_path = LOGO_PATH
    custom_logo_file = os.path.join(MEDIA_ROOT, CUSTOM_LOGO_PATH)
    if os.path.exists(custom_logo_file):
        logo_path = CUSTOM_LOGO_PATH

    base_context = {
        'url_base': get_site_scheme_and_netloc(),
        'site_name': get_site_name(),
        'media_url': MEDIA_URL,
        'logo_path': logo_path,
    }
    context.update(base_context)
    t = loader.get_template(dj_template)
    html_message = t.render(context)

    return mail.send(recipients, sender=sender, template=template, context=context,
              subject=subject, message=message,
              html_message=html_message, headers=headers, priority=priority,
              backend=backend)

######################### Start PingAn Group related ########################
from seahub.utils.pafile_email_api import PAFileEmailApi
def send_pafile_html_email_with_dj_template(recipients, subject, dj_template,
                                            context={}, sender=None,
                                            template=None, message=''):
    base_context = {
        'url_base': get_site_scheme_and_netloc(),
        'site_name': SITE_NAME,
        'media_url': MEDIA_URL,
        'logo_path': LOGO_PATH,
    }
    context.update(base_context)
    t = loader.get_template(dj_template)
    html_message = t.render(context)

    email_api = PAFileEmailApi()
    for r in recipients:
        if PAFILE_EMAIL_DEBUG:
            # Get an instance of a logger
            logger = logging.getLogger(__name__)
            logger.info('PAFile Email send to: %s' % r)
            logger.info('PAFile Email subject: %s' % subject)
            logger.info('PAFile Email body: %s' % html_message)

        email_api.send_email(r, subject, html_message)
######################### End PingAn Group related ##########################
