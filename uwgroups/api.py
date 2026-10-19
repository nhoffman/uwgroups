import errno
import logging
import http.client
from os import path
import socket
import subprocess
import json
import re
from urllib.parse import quote, unquote, urlencode, urlsplit

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


class OwnershipError(AuthorizationError):
    """A write would exceed the client's configured group namespace."""


def get_admins(certfile):
    """Returns [dns_user, uwnetid_user] given data in cert

    """

    output = subprocess.run(
        ['openssl', 'x509', '-in', certfile, '-noout', '-subject'],
        capture_output=True, text=True)
    log.info(output)

    # openssl and libressl have differently-formatted outputs:
    # LibreSSL 2.8.3
    # subject= /C=US/ST=Washington/L=Seattle/O=University of Washington/OU=Laboratory Medicine/CN=elmira.labmed.uw.edu/emailAddress=ngh2@uw.edu
    # openssl
    # subject=C = US, ST = Washington, L = Seattle, O = University of Washington, OU = Laboratory Medicine, CN = elmira.labmed.uw.edu, emailAddress = ngh2@uw.edu

    text = output.stdout.replace('subject=', '').strip()
    char = '/' if text.startswith('/') else ','
    data = {k.strip(): v.strip()
            for k, v in [e.split('=') for e in text.strip(char).split(char)]}

    dns_user = User(uwnetid=data['CN'], type='dns')
    uwnetid_user = User(
        uwnetid=data['emailAddress'].split('@')[0], type='uwnetid')

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

    As of 2022-06-28, the UWCA root cert is only 1024 bytes, which
    results in the error

    'ssl.SSLError: [SSL: CA_KEY_TOO_SMALL] ca key too small (_ssl.c:2633)'
    on ubuntu and debian. By default, the connection is initialized with
    context.set_ciphers('DEFAULT@SECLEVEL=1') unless use_default_ciphers is True

    Example::

        with UWGroups(certfile='/path/to/cert.pem') as conn:
            conn.get_group('some_group')

    """

    def __init__(self, certfile, keyfile=None, environment='PROD', timeout=30,
                 use_default_ciphers=False, request_check=None,
                 request_attempts=5, write_prefix=None):
        """Initialize the connection.

        ``request_check`` is called before every HTTP attempt and may raise to
        cancel work. ``request_attempts`` controls transport retries (default 5).
        ``write_prefix`` optionally restricts all writes to a group namespace,
        including writes made while recursively creating parents.

        """

        self.gws_host = GWS_HOSTS[environment]
        log.info(f'using {self.gws_host}')

        if not certfile or not path.exists(certfile):
            raise ValueError(
                "'certfile' is required and must specify a readable file")

        if keyfile and not path.exists(keyfile):
            raise ValueError("'keyfile' must specify a readable file")

        self.keyfile = keyfile
        self.certfile = certfile
        self.admins = get_admins(certfile)
        log.info(self.admins)
        self.timeout = timeout
        self.use_default_ciphers = use_default_ciphers
        self.context = None
        self.connection = None
        if request_check is not None and not callable(request_check):
            raise TypeError('request_check must be callable')
        self.request_check = request_check
        self.request_attempts = self._validate_attempts(request_attempts)
        self.write_prefix = None
        if write_prefix is not None:
            self.restrict_writes(write_prefix)

    @staticmethod
    def _validate_attempts(attempts):
        if type(attempts) is not int or attempts < 1:
            raise ValueError('Request attempts must be a positive integer')
        return attempts

    def restrict_writes(self, prefix):
        """Restrict every mutation, including parent creation, to ``prefix``.

        The prefix root (with trailing underscores removed) is protected.
        Reads remain unrestricted so existing ancestors can be inspected.
        Call again between operations to select another managed namespace.
        """
        if not isinstance(prefix, str) or not re.fullmatch(r'[a-z0-9][a-z0-9_-]*', prefix):
            raise OwnershipError('A valid nonempty group prefix is required')
        self.write_prefix = prefix

    def _check_request(self, method, endpoint):
        if self.request_check is not None:
            self.request_check()
        if method == 'GET' or self.write_prefix is None:
            return
        parts = urlsplit(endpoint).path.split('/')
        name = unquote(parts[1]) if len(parts) > 1 else ''
        if (not parts or parts[0] != 'group'
                or any(unquote(part) in ('.', '..') for part in parts)):
            raise OwnershipError('Mutation outside configured group namespace')
        self.check_write_group(name)

    def check_write_group(self, group_name):
        """Validate a proposed write, also usable before a dry-run preview."""
        if self.write_prefix is not None and (
                not isinstance(group_name, str)
                or not re.fullmatch(r'[a-z0-9][a-z0-9_-]*', group_name)
                or not group_name.startswith(self.write_prefix)
                or group_name == self.write_prefix.rstrip('_')):
            raise OwnershipError('Mutation outside configured group namespace')

    @staticmethod
    def _encode_identifier(value):
        if not isinstance(value, str) or not value or value in ('.', '..'):
            raise ValueError('A nonempty identifier other than . or .. is required')
        return quote(value, safe='')

    @classmethod
    def _group_endpoint(cls, group_name, *segments):
        # Encode identifiers as path segments, never as URL structure.
        return '/'.join(['group', cls._encode_identifier(group_name)] + list(segments))

    def connect(self, timeout=None):
        """Establish a connection. If the ``UWGroups`` object is instantiated
        without a with block, must be called explicitly. ``timeout``
        overrides the value for ``timeout`` in the class constructor.
        """
        self.context = http.client.ssl.create_default_context()
        self.context.load_cert_chain(certfile=self.certfile, keyfile=self.keyfile)
        self.context.load_verify_locations(UWCA_ROOT)
        if not self.use_default_ciphers:
            self.context.set_ciphers('DEFAULT@SECLEVEL=1')
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
        """Close and reopen the connection; may be necessary after an
        exception"""
        self.close()
        self.connect()

    @check_types(method=str, endpoint=str, headers=dict,
                 body=str, expect_status=int, attempts=int)
    def _request(self, method, endpoint, headers=None, body=None,
                 expect_status=200, attempts=None):
        methods = {'GET', 'PUT', 'DELETE'}
        if method not in methods:
            raise ValueError(
                'method must be one of {}'.format(', '.join(methods)))

        url = path.join(API_PATH, endpoint)

        args = {}
        if headers:
            args['headers'] = headers
        if body:
            args['body'] = body

        attempts = self._validate_attempts(
            self.request_attempts if attempts is None else attempts)
        for attempt in range(attempts):
            # This must run outside the retry handler: cancellation exceptions
            # propagate unchanged, including before every member batch/retry.
            self._check_request(method, endpoint)
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
                    # response isn't set at all for this case, reraise
                    # the exception.
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

        # Consume error bodies too, keeping the HTTP connection usable for the
        # next request after a missing resource or authorization failure.
        body = response.read()
        if response.status == 404:
            raise MissingResourceError(msg)
        elif response.status in (401, 403):
            raise AuthorizationError(msg)
        elif response.status != expect_status:
            raise APIError(msg)

        return body

    @check_types(group_name=str)
    def group_exists(self, group_name):
        """Return True if the group exists"""
        try:
            self.get_group(group_name)
        except MissingResourceError:
            return False
        else:
            return True

    @check_types(group_name=str)
    def get_group(self, group_name):
        """Return deserialized json representation of a group"""
        endpoint = self._group_endpoint(group_name)
        response = self._request(
            'GET', endpoint,
            headers={"Accept": "application/json",
                     "Content-Type": "application/json"})
        return json.loads(response)

    @check_types(group_name=str, admin_users=list)
    def create_group(self, group_name, admin_users=None):
        """Create a group with name ``group_name``. The dns user
        associated with the certificate, as well as the user
        identified as the email contact for the cert in field
        ``emailAddress`` are always added as admins. A list of
        additional admin users identified by uwnetid can be provided
        in ``admin_users``.

        Note that the API requires that a parent group ('root_parent')
        must be created before any of its children
        ('root_parent_child'). This method will recursively create
        parent groups if necessary.

        """

        if self.group_exists(group_name):
            log.info(f'group {group_name} exists, skipping creation')
            return {}

        # create parents as necessary, skipping the first (root) group
        hierarchy = group_name.split('_')
        for i in range(2, len(hierarchy)):
            parent = '_'.join(hierarchy[:i])
            self.create_group(parent, admin_users=admin_users or [])

        endpoint = self._group_endpoint(group_name)

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
            headers={"Accept": "application/json",
                     "Content-Type": "application/json"},
            body=json.dumps(body),
            expect_status=201)
        log.debug(response)
        return response

    @check_types(group_name=str)
    def delete_group(self, group_name):
        endpoint = self._group_endpoint(group_name)
        response = self._request('DELETE', endpoint)
        return response

    @check_types(group_name=str)
    def get_members(self, group_name):
        """Return a list of uwnetids"""
        endpoint = self._group_endpoint(group_name, 'member')
        response = self._request(
            'GET', endpoint, headers={'accept': 'application/json'})
        data = json.loads(response)['data']
        members = [d['id'] for d in data]
        return members

    @check_types(group_name=str)
    def get_member_details(self, group_name):
        """Return details of response describing members of the group"""
        endpoint = self._group_endpoint(group_name, 'member')
        response = self._request(
            'GET', endpoint, headers={'accept': 'application/json'})
        data = json.loads(response)['data']
        return data

    @check_types(group_name=str, member=str)
    def is_member(self, group_name, member):
        """Retutn True if `member` is a member of `group_name`"""
        if not self.group_exists(group_name):
            raise ValueError(f'group {group_name} does not exist')

        endpoint = self._group_endpoint(group_name, 'member', self._encode_identifier(member))
        try:
            self._request(
                'GET', endpoint, headers={'accept': 'application/json'})
        except MissingResourceError:
            return False
        else:
            return True

    @check_types(group_name=str, members=list, batchsize=int)
    def add_members(self, group_name, members, batchsize=50):
        """Add uwnetids in list ``members`` to the specified group in batches
        of size ``batchsize``.

        """
        for chunk in grouper(members, batchsize):
            endpoint = self._group_endpoint(
                group_name, 'member', ','.join(self._encode_identifier(member) for member in chunk))
            self._request('PUT', endpoint)

    @check_types(group_name=str, members=list, batchsize=int)
    def delete_members(self, group_name, members, batchsize=50):
        """Remove uwnetids in list ``members`` from the specified group in
        batches of size ``batchsize``.

        """
        for chunk in grouper(members, batchsize):
            endpoint = self._group_endpoint(
                group_name, 'member', ','.join(self._encode_identifier(member) for member in chunk))
            self._request('DELETE', endpoint)

    @check_types(group_name=str, members=list)
    def sync_members(self, group_name, members, batchsize=50, dry_run=False):
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
                self.add_members(group_name, sorted(to_add), batchsize=batchsize)

        if to_delete:
            log.info('[-] {}: {}'.format(group_name, ','.join(to_delete)))
            if not dry_run:
                self.delete_members(
                    group_name, sorted(to_delete), batchsize=batchsize)

    @check_types(group_name=str, service=str, active=bool)
    def set_affiliate(self, group_name, service, active=True):
        """Activate (``active=True``) or inactivate (``active=False``)
        Exchange (``service=exchange``) or Google Apps
        (``service=google``) for the specified group.

        """

        services = {'exchange': 'email', 'google': 'google'}
        if service not in services:
            raise ValueError('service must be one of {}'.format(
                list(services.keys())))
        endpoint = self._group_endpoint(group_name, 'affiliate', services[service])
        endpoint += '?status=' + ('active' if active else 'inactive')
        response = self._request('PUT', endpoint)
        return response

    @check_types(netid=str)
    def search_user(self, netid):
        """Return groups in which `netid` is a member

        """

        endpoint = 'search?' + urlencode({'member': netid})
        response = self._request('GET', endpoint)
        data = json.loads(response)['data']
        groups = [d['id'] for d in data]
        return groups

    @check_types(name=str)
    def search_groups(self, name):
        """Return a list of group names matching pattern `name` (may
        contain * as a wildcard).

        """

        endpoint = 'search?' + urlencode({'name': name})
        response = self._request('GET', endpoint)
        data = json.loads(response)['data']
        groups = [d['id'] for d in data]
        return groups
