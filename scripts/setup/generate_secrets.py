#!/usr/bin/env python
# This tools generates /etc/zulip/zulip-secrets.conf

from __future__ import print_function
import sys, os, os.path
from os.path import dirname, abspath
if False:
    from typing import Dict, Optional

BASE_DIR = dirname(dirname(dirname(abspath(__file__))))
sys.path.append(BASE_DIR)
import scripts.lib.setup_path_on_import

os.environ['DJANGO_SETTINGS_MODULE'] = 'zproject.settings'

from django.utils.crypto import get_random_string
from six import text_type
import six
import argparse
from zerver.lib.str_utils import force_str
from zerver.lib.utils import generate_random_token

os.chdir(os.path.join(os.path.dirname(__file__), '..', '..'))

CAMO_CONFIG_FILENAME = '/etc/default/camo'

AUTOGENERATED_SETTINGS = ['shared_secret', 'avatar_salt', 'rabbitmq_password', 'local_database_password',
                          'initial_password_salt']

# TODO: We can eliminate this function if we refactor the install
# script to run generate_secrets before zulip-puppet-apply.
def generate_camo_config_file(camo_key):
    # type: (text_type) -> None
    camo_config = """ENABLED=yes
PORT=9292
CAMO_KEY=%s
""" % (camo_key,)
    with open(CAMO_CONFIG_FILENAME, 'w') as camo_file:
        camo_file.write(camo_config)
    print("Generated Camo config file %s" % (CAMO_CONFIG_FILENAME,))

def generate_django_secretkey():
    # type: () -> text_type
    """Secret key generation taken from Django's startproject.py"""
    chars = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'
    return get_random_string(50, chars)

def get_old_conf(output_filename):
    # type: (text_type) -> Dict[str, text_type]
    if not os.path.exists(output_filename):
        return {}

    secrets_file = six.moves.configparser.RawConfigParser() # type: ignore # https://github.com/python/typeshed/issues/307
    secrets_file.read(output_filename)

    def get_secret(key):
        # type: (text_type) -> Optional[text_type]
        if secrets_file.has_option('secrets', key):
            return secrets_file.get('secrets', key)
        return None

    fields = AUTOGENERATED_SETTINGS + ['secret_key', 'camo_key']
    return {name: get_secret(name) for name in fields}

def generate_secrets(development=False):
    # type: (bool) -> None
    if development:
        OUTPUT_SETTINGS_FILENAME = "zproject/dev-secrets.conf"
    else:
        OUTPUT_SETTINGS_FILENAME = "/etc/zulip/zulip-secrets.conf"

    lines = [u'[secrets]\n']

    def config_line(var, value):
        # type: (text_type, text_type) -> text_type
        return "%s = %s\n" % (var, value)

    old_conf = get_old_conf(OUTPUT_SETTINGS_FILENAME)
    for name in AUTOGENERATED_SETTINGS:
        lines.append(config_line(name, old_conf.get(name, generate_random_token(64))))

    secret_key = old_conf.get('secret_key', generate_django_secretkey())
    lines.append(config_line('secret_key', secret_key))

    camo_key = old_conf.get('camo_key', get_random_string(64))
    lines.append(config_line('camo_key', camo_key))

    if not development:
        # Write the Camo config file directly
        generate_camo_config_file(camo_key)

    out = open(OUTPUT_SETTINGS_FILENAME, 'w')
    out.write(force_str("".join(lines)))
    out.close()

    print("Generated %s with auto-generated secrets!" % (OUTPUT_SETTINGS_FILENAME,))

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--development', action='store_true', dest='development', help='For setting up the developer env for zulip')
    group.add_argument('--production', action='store_false', dest='development', help='For setting up the production env for zulip')
    results = parser.parse_args()

    generate_secrets(results.development)
