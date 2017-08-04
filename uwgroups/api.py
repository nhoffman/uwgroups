from __future__ import print_function
import logging
import httplib
from os import path
import xml.etree.ElementTree as ET
import subprocess
from functools import wraps

from jinja2 import Environment, PackageLoader

from uwgroups import package_data
from uwgroups.utils import reconcile, prettify, grouper

log = logging.getLogger(__name__)

GWS_HOST = 'iam-ws.u.washington.edu'
GWS_PORT = 7443
API_PATH = '/group_sws/v2'

# https://certs.cac.washington.edu/?req=svpem
UWCA_ROOT = package_data('root.cert')


class APIError(Exception):
    pass


class MissingResourceError(APIError):
    pass


class AuthorizationError(APIError):
    pass


def get_admins(certfile):
    """Returns [dns_user, uwnetid_user] given data in cert

    """

    output = subprocess.check_output(
        ['openssl', 'x509', '-in', certfile, '-noout', '-subject'])
    log.debug(output)
    data = {k: v.strip() or None for k, v in [e.split('=') for e in output.split('/')]}

    dns_user = User(uwnetid=data['CN'], type='dns')
    uwnetid_user = User(uwnetid=data['emailAddress'].split('@')[0], type='uwnetid')

    return [dns_user, uwnetid_user]


def check_types(**kwargs):
    def actual_decorator(func):
        @wraps(func)
        def wrapper(*_args, **_kwargs):
            argdict = dict(zip(func.func_code.co_varnames, _args), **_kwargs)
            for arg, obj in kwargs.items():
                if arg in argdict and not isinstance(argdict[arg], obj):
                    raise TypeError('"{}" must be an instance of {}'.format(arg, obj))

            return func(*_args, **_kwargs)
        return wrapper
    return actual_decorator


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
    def __init__(self, certfile, keyfile=None):
        """Initialize the connection. key and cert are paths to the key and
        certificate files, respectively.

        """

        if not certfile or not path.exists(certfile):
            raise ValueError("'certfile' is required and must specify a readable file")

        if keyfile and not path.exists(keyfile):
            raise ValueError("'keyfile' must specify a readable file")

        self.keyfile = keyfile
        self.certfile = certfile
        self.j2env = Environment(loader=PackageLoader('uwgroups', 'templates'))
        self.admins = get_admins(certfile)
        log.info(self.admins)

    def connect(self):
        self.context = httplib.ssl.create_default_context()
        self.context.load_cert_chain(certfile=self.certfile, keyfile=self.keyfile)
        self.context.load_verify_locations(UWCA_ROOT)
        self.connection = httplib.HTTPSConnection(
            GWS_HOST, GWS_PORT, context=self.context)
        log.info('connected to {}:{}'.format(GWS_HOST, GWS_PORT))

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, type, value, tback):
        self.close()

    def close(self):
        self.connection.close()

    def reset(self):
        self.close()
        self.connect()

    @check_types(method=basestring, endpoint=basestring, headers=dict,
                 body=basestring, expect_status=int, attempts=int)
    def request(self, method, endpoint, headers=None, body=None, expect_status=200,
                attempts=3):
        methods = {'GET', 'PUT', 'DELETE'}
        if method not in methods:
            raise ValueError('method must be one of {}'.format(', '.join(methods)))

        url = path.join(API_PATH, endpoint)

        args = {}
        if headers:
            args['headers'] = headers
        if body:
            args['body'] = body

        for attempt in range(attempts):
            try:
                self.connection.request(method, url, **args)
                response = self.connection.getresponse()
            except httplib.BadStatusLine, err:
                log.warning('failure on attempt {}: {}'.format(attempt, err))
                self.reset()
            else:
                break

        msg = '{} {}: {} {}'.format(method, url, response.status, response.reason)
        log.info(msg)

        if response.status == 404:
            raise MissingResourceError(msg)
        elif response.status == 401:
            raise AuthorizationError(msg)
        elif response.status != expect_status:
            raise APIError(msg)

        body = response.read()
        return body

    @check_types(group_name=basestring)
    def get_group(self, group_name):
        endpoint = path.join('group', group_name)
        response = self.request(
            'GET', endpoint,
            headers={"Accept": "text/xml", "Content-Type": "text/xml"})
        return prettify(response)

    @check_types(group_name=basestring, admins=list)
    def create_group(self, group_name, admins=None):
        endpoint = path.join('group', group_name)
        extra_admins = admins or []
        for admin in extra_admins:
            if not isinstance(admin, User):
                raise TypeError('admins must be User instances')

        template = self.j2env.get_template('create_group.xml')
        body = template.render(
            group_name=group_name,
            admins=self.admins + extra_admins)
        log.debug(prettify(body))

        response = self.request(
            'PUT', endpoint,
            headers={"Accept": "text/xml", "Content-Type": "text/xml"},
            body=body,
            expect_status=201)
        log.debug(prettify(response))
        return response

    @check_types(group_name=basestring)
    def delete_group(self, group_name):
        endpoint = path.join('group', group_name)
        response = self.request('DELETE', endpoint)
        return response

    @check_types(group_name=basestring)
    def get_members(self, group_name):
        endpoint = path.join('group', group_name, 'member')
        response = self.request('GET', endpoint, headers={'accept': 'text/xml'})
        root = ET.fromstring(response)
        members = [member.text for member in root.iter('member')]
        return members

    @check_types(group_name=basestring, members=list, batchsize=int)
    def add_members(self, group_name, members, batchsize=200):
        for chunk in grouper(members, batchsize):
            endpoint = path.join('group', group_name, 'member', ','.join(chunk))
            self.request('PUT', endpoint)

    @check_types(group_name=basestring, members=list, batchsize=int)
    def delete_members(self, group_name, members, batchsize=200):
        for chunk in grouper(members, batchsize):
            endpoint = path.join('group', group_name, 'member', ','.join(chunk))
            self.request('DELETE', endpoint)

    @check_types(group_name=basestring)
    def group_exists(self, group_name):
        try:
            self.get_group(group_name)
        except MissingResourceError:
            # closing and reopening the connection seems to be
            # necessary to prevent an httplib.ResponseNotReady error
            # after an exception caused by a missing group.
            self.reset()
            return False
        else:
            return True

    @check_types(group_name=basestring, members=list)
    def sync_members(self, group_name, members, dry_run=False):
        """Define members for group_name, adding and removing users as
        necessary.

        """

        desired_members = set(members)

        if self.group_exists(group_name):
            current_members = set(self.get_members(group_name))
        else:
            current_members = set()
            log.warning('creating group {}'.format(group_name))
            if not dry_run:
                self.create_group(group_name)

        log.info('current members: {}'.format(current_members))
        to_add, to_delete = reconcile(current_members, desired_members)

        if to_add:
            log.info('[+] {}: {}'.format(group_name, ','.join(to_add)))
            if not dry_run:
                self.add_members(group_name, sorted(to_add))

        if to_delete:
            log.info('[-] {}: {}'.format(group_name, ','.join(to_delete)))
            if not dry_run:
                self.delete_members(group_name, sorted(to_delete))

    def set_affiliate(self, group_name, service, active=True):
        services = {'exchange': 'email', 'google': 'google'}
        if service not in services:
            raise ValueError('service must be one of {}'.format(services.keys()))
        endpoint = path.join('group', group_name, 'affiliate', services[service])
        endpoint += '?status=' + ('active' if active else 'inactive')
        response = self.request('PUT', endpoint)
        return response
