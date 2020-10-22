import os
import errno
import logging
import http.client
from os import path
import socket
import subprocess
import json

from uwgroups import package_data
from uwgroups.utils import reconcile, grouper, check_types

log = logging.getLogger(__name__)

# https://groups.uw.edu/group_sws/v3
GWS_HOSTS = {
    'PROD': 'groups.uw.edu',
    'DEV': 'dev.groups.uw.edu',
    'EVAL': 'eval.groups.uw.edu',
}

GWS_PORT = 443
API_PATH = '/group_sws/v3'

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

    output = subprocess.run(
        ['openssl', 'x509', '-in', certfile, '-noout', '-subject'],
        capture_output=True, text=True)
    log.debug(output)
    data = {k: v.strip() or None
            for k, v in [e.split('=') for e in output.stdout.split('/')]}

    dns_user = User(uwnetid=data['CN'], type='dns')
    uwnetid_user = User(uwnetid=data['emailAddress'].split('@')[0], type='uwnetid')

    return [dns_user, uwnetid_user]


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
    """Class providing a connection to the UW groups REST
    API. ``certfile`` and ``keyfile`` are paths to files containing
    the certificate and private keys, respectively. ``timeout`` is
    passed to ``httplib.HTTPSConnection()``

    Example::

        with UWGroups(certfile='/path/to/cert.pem') as conn:
            conn.get_group('some_group')

    """

    def __init__(self, certfile, keyfile=None, environment='PROD', timeout=30):
        """Initialize the connection.

        """

        self.gws_host = GWS_HOSTS[environment]
        log.info(f'using {self.gws_host}')

        if not certfile or not path.exists(certfile):
            raise ValueError("'certfile' is required and must specify a readable file")

        if keyfile and not path.exists(keyfile):
            raise ValueError("'keyfile' must specify a readable file")

        self.keyfile = keyfile
        self.certfile = certfile
        self.admins = get_admins(certfile)
        log.info(self.admins)
        self.timeout = timeout

    def connect(self, timeout=None):
        """Establish a connection. If the ``UWGroups`` object is instantiated
        without a with block, must be called explicitly. ``timeout``
        overrides the value for ``timeout`` in the class constructor.

        """
        self.context = http.client.ssl.create_default_context()
        self.context.load_cert_chain(certfile=self.certfile, keyfile=self.keyfile)
        self.context.load_verify_locations(UWCA_ROOT)
        self.connection = http.client.HTTPSConnection(
            host=self.gws_host,
            timeout=timeout or self.timeout,
            port=GWS_PORT,
            context=self.context)
        log.info(f'connected to {self.gws_host}:{GWS_PORT}')

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, type, value, tback):
        self.close()

    def close(self):
        """Close the connection"""
        self.connection.close()

    def reset(self):
        """Close and reopen the connection; may be necessary after an exception"""
        self.close()
        self.connect()

    @check_types(method=str, endpoint=str, headers=dict,
                 body=str, expect_status=int, attempts=int)
    def _request(self, method, endpoint, headers=None, body=None, expect_status=200,
                 attempts=5):
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
            except http.client.BadStatusLine as err:
                caught_err = err
                log.warning('failure on attempt {}: {}'.format(attempt, err))
                self.reset()
            except socket.error as err:
                caught_err = err
                if err.errno != errno.ETIMEDOUT:
                    log.warning('failure on attempt {}: {}'.format(attempt, err))
                    # response isn't set at all for this case, reraise the exception.
                    raise
                self.reset()
            else:
                break
        else:
            # Hit the limit of attempts. The response variable never got set.
            msg = '{}: {} {}'.format(caught_err, method, url)
            log.info(msg)
            raise APIError(msg)

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

    @check_types(group_name=str)
    def group_exists(self, group_name):
        """Return True if the group exists"""
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

    @check_types(group_name=str)
    def get_group(self, group_name):
        """Return deserialized json representation of a group"""
        endpoint = path.join('group', group_name)
        response = self._request(
            'GET', endpoint,
            headers={"Accept": "application/json", "Content-Type": "application/json"})
        return json.loads(response)

    @check_types(group_name=str, admin_users=list)
    def create_group(self, group_name, admin_users=None):
        """Create a group with name ``group_name``. By default, the dns user
        associated with the certificate, as well as the user
        identified as the email contact for the cert in field
        ``emailAddress`` are added as admins. A list of additional
        admin users identified by uwnetid can be provided in
        ``admin_users``.

        """
        endpoint = path.join('group', group_name)

        admins = self.admins[:]
        if admin_users:
            for uwnetid in admin_users:
                admins.append(User(uwnetid, type='uwnetid'))

        body = {
            "data": {
                "id": group_name,
                "displayName": group_name,
                "description": group_name,
                "contact": "ngh2",
                "authnfactor": 1,
                "classification": "u",
                "admins": [{'id': u.uwnetid, 'type': u.type} for u in admins],
                "updaters": [],
                "creators": [],
                "readers": [],
                "optins": [],
                "optouts": [],
            }
        }

        response = self._request(
            'PUT', endpoint,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            body=json.dumps(body),
            expect_status=201)
        log.debug(response)
        return response

    @check_types(group_name=str)
    def delete_group(self, group_name):
        endpoint = path.join('group', group_name)
        response = self._request('DELETE', endpoint)
        return response

    @check_types(group_name=str)
    def get_members(self, group_name):
        """Return a list of uwnetids"""
        endpoint = path.join('group', group_name, 'member')
        response = self._request(
            'GET', endpoint, headers={'accept': 'application/json'})
        data = json.loads(response)['data']
        members = [d['id'] for d in data]
        return members

    @check_types(group_name=str, members=list, batchsize=int)
    def add_members(self, group_name, members, batchsize=200):
        """Add uwnetids in list ``members`` to the specified group in batches
        of size ``batchsize``.

        """
        for chunk in grouper(members, batchsize):
            endpoint = path.join('group', group_name, 'member', ','.join(chunk))
            self._request('PUT', endpoint)

    @check_types(group_name=str, members=list, batchsize=int)
    def delete_members(self, group_name, members, batchsize=200):
        """Remove uwnetids in list ``members`` from the specified group in
        batches of size ``batchsize``.

        """
        for chunk in grouper(members, batchsize):
            endpoint = path.join('group', group_name, 'member', ','.join(chunk))
            self._request('DELETE', endpoint)

    @check_types(group_name=str, members=list)
    def sync_members(self, group_name, members, dry_run=False):
        """Add or remove users from the specified group as necessary so that
        the group contains ``members`` (a list or uwnetids). When
        ``dry_run`` is True, log the necessary actions but don't
        modify the group. The group is created if it does not already
        exist.

        """

        desired_members = set(members)

        try:
            current_members = set(self.get_members(group_name))
        except MissingResourceError:
            self.reset()
            current_members = set()
            log.warning('creating group {}'.format(group_name))
            if not dry_run:
                self.create_group(group_name)

        log.info('{} current members'.format(len(current_members)))
        log.debug('current members: {}'.format(current_members))
        to_add, to_delete = reconcile(current_members, desired_members)

        if to_add:
            log.info('[+] {}: {}'.format(group_name, ','.join(to_add)))
            if not dry_run:
                self.add_members(group_name, sorted(to_add))

        if to_delete:
            log.info('[-] {}: {}'.format(group_name, ','.join(to_delete)))
            if not dry_run:
                self.delete_members(group_name, sorted(to_delete))

    @check_types(group_name=str, service=str, active=bool)
    def set_affiliate(self, group_name, service, active=True):
        """Activate (``active=True``) or inactivate (``active=False``)
        Exchange (``service=exchange``) or Google Apps
        (``service=google``) for the specified group.

        """

        services = {'exchange': 'email', 'google': 'google'}
        if service not in services:
            raise ValueError('service must be one of {}'.format(list(services.keys())))
        endpoint = path.join('group', group_name, 'affiliate', services[service])
        endpoint += '?status=' + ('active' if active else 'inactive')
        response = self._request('PUT', endpoint)
        return response
