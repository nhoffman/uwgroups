from __future__ import print_function
import logging
import httplib
from os import path

import xml.etree.ElementTree as ET

from uwgroups import package_data

log = logging.getLogger(__name__)


GWS_HOST = 'iam-ws.u.washington.edu'
GWS_PORT = 7443
API_PATH = '/group_sws/v2'

KEY_FILE = 'newkey-decrypted.pem'
CERT_FILE = 'elmira.pem'

# https://certs.cac.washington.edu/?req=svpem
UWCA_ROOT = package_data('root.cert')


class UWGroups(object):
    def __init__(self, key, cert):
        """Initialize the connection. key and cert are paths to the key and
        certificate files, respectively.

        """
        if not key or not path.exists(key):
            raise ValueError("'key' must be defined and must specify a readable file")

        if not cert or not path.exists(cert):
            raise ValueError("'cert' must be defined and must specify a readable file")

        context = httplib.ssl.create_default_context()
        context.load_verify_locations(UWCA_ROOT)
        self.connection = httplib.HTTPSConnection(
            GWS_HOST, GWS_PORT, key, cert, context=context)
        log.info('connected to {}:{}'.format(GWS_HOST, GWS_PORT))

    def close(self):
        self.connection.close()

    def raw_request(self, method, endpoint, headers={'accept': 'text/xml'}):
        methods = {'GET', 'PUT', 'DELETE'}
        if method not in methods:
            raise ValueError('method must be one of {}'.format(', '.join(methods)))

        url = path.join(API_PATH, endpoint)

        self.connection.request(method, url, headers=headers)
        response = self.connection.getresponse()

        if response.status != 200:
            raise ValueError('{}: {}'.format(url, response.reason))

        body = response.read()
        return body

    def get_members(self, group_name):
        endpoint = 'group/{group_name}/member'.format(group_name=group_name)
        response = self.raw_request('GET', endpoint)
        root = ET.fromstring(response)
        members = [member.text for member in root.iter('member')]
        return members

    def delete_members(self, group_name, members):
        if not isinstance(members, list):
            raise TypeError('members must be a list')

        endpoint = 'group/{group_name}/member/{members}'.format(
            group_name=group_name, members=','.join(members))

        response = self.raw_request('DELETE', endpoint)
        print(response)
