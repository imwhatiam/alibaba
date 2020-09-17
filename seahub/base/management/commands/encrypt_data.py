# Copyright (c) 2012-2016 Seafile Ltd.
# encoding: utf-8

from django.core.management.base import BaseCommand

from seaserv import seafile_api


class Command(BaseCommand):

    def add_arguments(self, parser):

        # Named (optional) arguments
        parser.add_argument(
            '--data',
        )

    def handle(self, *args, **options):

        data = str(options['data'])
        print(seafile_api.seafile_encrypt(data))
