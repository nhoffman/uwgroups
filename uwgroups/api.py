from __future__ import print_function
import logging
import httplib
from os import path
import xml.etree.ElementTree as ET
import subprocess

from jinja2 import Environment, PackageLoader

from uwgroups import package_data
from uwgroups.utils import reconcile

log = logging.getLogger(__name__)


GWS_HOST = 'iam-ws.u.washington.edu'
GWS_PORT = 7443
API_PATH = '/group_sws/v2'

# https://certs.cac.washington.edu/?req=svpem
UWCA_ROOT = package_data('root.cert')


def get_admins(cert):
    """Returns (dns_user, uwnetid_user) given data in cert

    """

    output = subprocess.check_output(
        ['openssl', 'x509', '-in', cert, '-noout', '-subject'])
    log.debug(output)
    data = {k: v.strip() or None for k, v in [e.split('=') for e in output.split('/')]}

    dns_user = User(uwnetid=data['CN'], type='dns')
    uwnetid_user = User(uwnetid=data['emailAddress'].split('@')[0], type='uwnetid')

    return (dns_user, uwnetid_user)


class User(object):
    user_types = {'uwnetid', 'group', 'dns', 'eppn'}

    def __init__(self, uwnetid, type):
        if type not in self.user_types:
            raise ValueError('user_type must be in {}'.format(self.user_types))

        self.uwnetid = uwnetid
        self.type = type

    def __repr__(self):
        return 'User(uwnetid={}, type={})'.format(self.uwnetid, self.type)


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

        self.j2env = Environment(loader=PackageLoader('uwgroups', 'templates'))

        self.admins = get_admins(cert)
        log.info(self.admins)

    def __enter__(self):
        return self

    def __exit__(self, type, value, tback):
        self.close()

    def close(self):
        self.connection.close()

    def raw_request(self, method, endpoint, headers=None, body=None,
                    expect_status=200):
        methods = {'GET', 'PUT', 'DELETE'}
        if method not in methods:
            raise ValueError('method must be one of {}'.format(', '.join(methods)))

        url = path.join(API_PATH, endpoint)
        log.info(url)

        args = {}
        if headers:
            args['headers'] = headers
        if body:
            args['body'] = body

        self.connection.request(method, url, **args)
        response = self.connection.getresponse()
        log.info('{} {}'.format(response.status, response.reason))

        if response.status != expect_status:
            raise ValueError('{}: {}'.format(url, response.reason))

        body = response.read()
        return body

    def get_members(self, group_name):
        endpoint = 'group/{group_name}/member'.format(group_name=group_name)
        response = self.raw_request('GET', endpoint, headers={'accept': 'text/xml'})
        root = ET.fromstring(response)
        members = [member.text for member in root.iter('member')]
        return members

    def add_members(self, group_name, members):
        if not isinstance(members, list):
            raise TypeError('"members" must be a list of uwnetids')

        endpoint = 'group/{group_name}/member/{members}'.format(
            group_name=group_name, members=','.join(members))

        response = self.raw_request('PUT', endpoint)
        return response

    def delete_members(self, group_name, members):
        if not isinstance(members, list):
            raise TypeError('"members" must be a list of uwnetids')

        endpoint = 'group/{group_name}/member/{members}'.format(
            group_name=group_name, members=','.join(members))

        response = self.raw_request('DELETE', endpoint)
        return response

    def create_group(self, group_name, admins=None):
        extra_admins = admins or []
        for admin in extra_admins:
            if not isinstance(admin, User):
                raise TypeError('admins must be User instances')

        template = self.j2env.get_template('create_group.xml')
        body = template.render(
            group_name=group_name,
            admins=self.admins + extra_admins)
        log.debug(body)
        endpoint = 'group/{group_name}'.format(group_name=group_name)
        response = self.raw_request(
            'PUT', endpoint,
            headers={"Accept": "text/xml", "Content-Type": "text/xml"},
            body=body,
            expect_status=201)
        return response

    def delete_group(self, group_name):
        endpoint = 'group/{group_name}'.format(group_name=group_name)
        response = self.raw_request('DELETE', endpoint)
        return response

    def sync_group(self, group_name, members, dry_run=False):
        """Define members for group_name, adding and removing users as
        necessary.

        """

        desired_members = set(members)
        current_members = set(self.get_members(group_name))
        to_add, to_delete = reconcile(current_members, desired_members)

        log.info('{} add: {}'.format(group_name, ','.join(to_add)))
        log.info('{} del: {}'.format(group_name, ','.join(to_delete)))

        if not dry_run:
            self.add_members(group_name, to_add)
            self.delete_members(group_name, to_delete)
