"""Offline request guards, retry behavior, and identifier encoding."""

import http.client
import json
import socket
import tempfile
import unittest
from unittest.mock import Mock, patch

from uwgroups.api import AuthorizationError, OwnershipError, UWGroups


class APIRequestTests(unittest.TestCase):
    def setUp(self):
        self.cert = tempfile.NamedTemporaryFile()
        self.addCleanup(self.cert.close)
        with patch("uwgroups.api.get_admins", return_value=[]):
            self.groups = UWGroups(self.cert.name)
        self.groups.connection = Mock()
        self.response = Mock(status=200, reason="OK")
        self.response.read.return_value = b"{}"
        self.groups.connection.getresponse.return_value = self.response

    def test_check_runs_before_every_retry_and_can_cancel(self):
        check = Mock(side_effect=[None, RuntimeError("lease lost")])
        self.groups.request_check = check
        self.groups.connection.request.side_effect = http.client.BadStatusLine("broken")
        with (
            patch.object(self.groups, "reset"),
            self.assertRaisesRegex(RuntimeError, "lease lost"),
        ):
            self.groups._request("PUT", "group/u_labmed_staff")
        self.assertEqual(self.groups.connection.request.call_count, 1)
        self.assertEqual(check.call_count, 2)

    def test_one_attempt_does_not_repeat_ambiguous_mutation(self):
        self.groups.request_attempts = 1
        self.groups.connection.request.side_effect = socket.timeout("timeout")
        with patch.object(self.groups, "reset"), self.assertRaises(socket.timeout):
            self.groups._request("PUT", "group/u_labmed_staff")
        self.groups.connection.request.assert_called_once()

    def test_each_member_batch_checks_lease(self):
        self.groups.request_check = Mock(side_effect=[None, RuntimeError("lease lost")])
        with self.assertRaisesRegex(RuntimeError, "lease lost"):
            self.groups.add_members("u_labmed_staff", ["alice", "bob"], batchsize=1)
        self.groups.connection.request.assert_called_once()

    def test_successful_retry_runs_check_again(self):
        self.groups.request_check = Mock()
        self.groups.connection.request.side_effect = [
            http.client.BadStatusLine("broken"),
            None,
        ]
        with patch.object(self.groups, "reset"):
            self.assertEqual(self.groups._request("GET", "group/u_labmed_staff"), b"{}")
        self.assertEqual(self.groups.request_check.call_count, 2)

    def test_constructor_exposes_worker_controls(self):
        check = Mock()
        with patch("uwgroups.api.get_admins", return_value=[]):
            groups = UWGroups(
                self.cert.name,
                request_check=check,
                request_attempts=1,
                write_prefix="u_labmed_",
            )
        self.assertIs(groups.request_check, check)
        self.assertEqual(groups.request_attempts, 1)
        self.assertEqual(groups.write_prefix, "u_labmed_")

    def test_recursive_creation_cannot_create_unowned_parent(self):
        self.groups.restrict_writes("u_labmed_")
        with (
            patch.object(self.groups, "group_exists", return_value=False),
            self.assertRaises(OwnershipError),
        ):
            self.groups.create_group("u_labmed_staff")
        self.groups.connection.request.assert_not_called()

    def test_existing_ancestors_can_be_read(self):
        self.groups.restrict_writes("u_labmed_")
        self.groups.get_group("u_labmed")
        self.groups.connection.request.assert_called_once()
        self.groups.connection.reset_mock()
        with self.assertRaises(OwnershipError):
            self.groups.delete_group("u_labmed")
        self.groups.connection.request.assert_not_called()

    def test_writes_allow_managed_groups_and_deny_other_names(self):
        self.groups.restrict_writes("u_labmed_")
        self.groups.delete_group("u_labmed_staff")
        for name in ("u_other_staff", "u_labmed", "u_labmed_x/../../other"):
            with self.subTest(name=name), self.assertRaises(OwnershipError):
                self.groups.delete_group(name)
        self.assertEqual(self.groups.connection.request.call_count, 1)

    def test_namespace_can_change_between_jobs_and_preview_validates_without_requests(
        self,
    ):
        self.groups.restrict_writes("u_old_")
        self.groups.check_write_group("u_old_staff")
        self.groups.restrict_writes("u_new_")
        self.groups.check_write_group("u_new_staff")
        with self.assertRaises(OwnershipError):
            self.groups.check_write_group("u_old_staff")
        self.groups.connection.request.assert_not_called()

    def test_member_identifiers_and_search_terms_are_encoded(self):
        self.groups.add_members("u_labmed_staff", ["alice,other", "id/with?query"])
        url = self.groups.connection.request.call_args.args[1]
        self.assertEqual(
            url,
            "/group_sws/v3/group/u_labmed_staff/member/alice%2Cother,id%2Fwith%3Fquery",
        )
        self.response.read.return_value = json.dumps({"data": []}).encode()
        self.groups.search_groups("u_labmed_*&member=alice")
        self.assertEqual(
            self.groups.connection.request.call_args.args[1],
            "/group_sws/v3/search?name=u_labmed_%2A%26member%3Dalice",
        )

    def test_error_response_is_consumed_and_forbidden_is_authorization_error(self):
        self.response.status = 403
        with self.assertRaises(AuthorizationError):
            self.groups._request("GET", "group/u_labmed_staff")
        self.response.read.assert_called_once()

    def test_optional_controls_preserve_existing_defaults(self):
        self.assertEqual(self.groups.request_attempts, 5)
        self.assertIsNone(self.groups.request_check)
        self.assertIsNone(self.groups.write_prefix)
        self.groups.delete_group("u_other_staff")
        for value in (0, -1, True, "1"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.groups._validate_attempts(value)
        for value in ("", "u_*", None):
            with self.subTest(value=value), self.assertRaises(OwnershipError):
                self.groups.restrict_writes(value)
