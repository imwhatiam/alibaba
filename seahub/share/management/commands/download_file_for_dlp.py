# -*- coding: utf-8 -*-
import os
import shutil
import base64
import logging
import requests

from django.core.management.base import BaseCommand

from seaserv import seafile_api

from seahub.profile.models import DetailedProfile
from seahub.share.models import FileShareApprovalStatus
from seahub.share.constants import STATUS_VERIFING

from seahub.utils import normalize_file_path, gen_inner_file_get_url

logger = logging.getLogger(__name__)

class Command(BaseCommand):

    label = "download_file_for_dlp"

    def handle(self, *args, **kwargs):

        fs_verifies = FileShareApprovalStatus.objects.get_dlp_status()
        for fs_verify in fs_verifies:

            # uncomment the following two lines for test
            # if 'sunruili' not in username:
            #     continue

            if fs_verify.status != STATUS_VERIFING:
                continue

            repo_id = fs_verify.share_link.repo_id
            repo = seafile_api.get_repo(repo_id)
            if not repo:
                continue

            path = fs_verify.share_link.path
            path = normalize_file_path(path)
            obj_id = seafile_api.get_file_id_by_path(repo_id, path)
            if not obj_id:
                continue

            username = fs_verify.share_link.username
            d_p = DetailedProfile.objects.get_detailed_profile_by_user(username)

            # generate file path
            if d_p and d_p.company:
                company = base64.b64encode(d_p.company.encode('utf-8'))
                path_for_dlp = os.path.join(company, username,
                        repo.id + '_' + repo.name, path.strip('/'))
            else:
                path_for_dlp = os.path.join(username,
                        repo.id + '_' + repo.name, path.strip('/'))

            # check if symlink or file exist
            full_path_for_dlp = os.path.join('/wls/nfs_mount/dlp/', path_for_dlp.strip('/'))
            try:
                if os.path.islink(full_path_for_dlp):
                    print('unlink: %s' % full_path_for_dlp)
                    os.unlink(full_path_for_dlp)
            except Exception as e:
                print(e)
                continue

            if os.path.exists(full_path_for_dlp):
                continue

            # download and move file
            file_name = os.path.basename(path)
            try:
                access_token = seafile_api.get_fileserver_access_token(repo_id,
                        obj_id, 'view', '', use_onetime = False)
                inner_url = gen_inner_file_get_url(access_token, file_name)
                resp = requests.get(inner_url)
            except Exception as e:
                print(e)
                continue

            tmp_path_for_dlp = os.path.join('/wls/nfs_mount/tmp/', path_for_dlp.strip('/'))
            tmp_parent_dir = os.path.dirname(tmp_path_for_dlp)
            if not os.path.exists(tmp_parent_dir):
                os.makedirs(tmp_parent_dir)

            print('\ndownload file to: %s' % tmp_path_for_dlp)
            with open(tmp_path_for_dlp, 'wb') as f:
                f.write(resp.content)

            full_parent_dir = os.path.dirname(full_path_for_dlp)
            if not os.path.exists(full_parent_dir):
                os.makedirs(full_parent_dir)
            print('\nmove file to: %s' % full_parent_dir)
            shutil.move(tmp_path_for_dlp, full_parent_dir)

        print('\nDone')
