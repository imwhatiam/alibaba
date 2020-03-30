# -*- coding: utf-8 -*-
import logging
from pprint import pprint

from django.utils import timezone
from django.utils.encoding import smart_text
from django.core.management.base import BaseCommand

from seahub.base.templatetags.seahub_tags import email2nickname
from seahub.share.models import FileShareApprovalStatus, FileShareDownloads
from seahub.share.share_link_checking import email_verify_result
from seahub.share.pingan_utils import ita_get_all_event_detail

# Get an instance of a logger
logger = logging.getLogger(__name__)

class Command(BaseCommand):

    label = "share_query_ita_status"

    def handle(self, *args, **kwargs):

        approval_status_list = FileShareApprovalStatus.objects. \
                filter(msg__startswith="R").filter(status=0)

        need_get_ita_status = []
        for approval_status in approval_status_list:
            if approval_status not in need_get_ita_status and \
                    approval_status.share_link.is_verifing():
                need_get_ita_status.append(approval_status)

        has_get_ita_status = {}
        for approval_status in need_get_ita_status:

            event_code = approval_status.msg
            if event_code not in has_get_ita_status.keys():

                share_link_creator = approval_status.share_link.username
                try:
                    resp_json = ita_get_all_event_detail(share_link_creator, event_code)
                except Exception as e:
                    print('Failed to get ita status')
                    print(e)
                    continue

                if not resp_json.get('success', False) or not resp_json.get('value', []):
                    print('Error returned when get ita status')
                    pprint(resp_json)
                    continue

                has_get_ita_status[event_code] = resp_json['value'][0]['flowAuditDetails']

            reviser = approval_status.email
            for item in has_get_ita_status[event_code]:
                if item['auditUser'].lower() in reviser and item['auditResult'].lower() in ('y', 'n'):
                    status = '1' if item['auditResult'].lower() == 'y' else '2'
                    approval_status.status = status
                    approval_status.vtime = item['auditTime']
                    approval_status.save()

                    try:
                        email_verify_result(approval_status.share_link, share_link_creator,
                                source="%s (%s)" % (smart_text(email2nickname(reviser)), reviser),
                                result_code=status)
                    except Exception as e:
                        print('Failed to send email to link owner')
                        print(e)

        has_email_receivers = []
        for approval_status in need_get_ita_status:

            share_link = approval_status.share_link
            if share_link not in has_email_receivers and \
                    share_link.pass_verify():

                new_expire_date = timezone.now() + (share_link.expire_date - share_link.ctime)
                share_link.expire_date = new_expire_date
                share_link.save()

                FileShareDownloads.objects.filter(share_link=share_link).delete()

                try:
                    share_link.email_receivers()
                except Exception as e:
                    print('Failed to send email to reververs')
                    print(e)

                has_email_receivers.append(share_link)
