#!/usr/bin/env python3
"""Negative cases for a host-only reference contract, NOT kernel validation."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from rothko_ksun_su_exec_intent_model import (  # noqa: E402
    RequestIdentity, SessionIntentModel, TaskIdentity,
)


class SuRequestContractTests(unittest.TestCase):
    def setUp(self):
        self.ledger = SessionIntentModel()
        self.owner = TaskIdentity()
        self.request = RequestIdentity()

    def begin(self, **overrides):
        conditions = dict(su_intent=True, allowlisted=True, chrooted=False,
                          fd_profile_eligible=True, precommit_checks_ok=True)
        conditions.update(overrides)
        return self.ledger.begin(self.owner, self.request, **conditions)

    def finish(self, **overrides):
        conditions = dict(exec_succeeded=True, credential_transition_ok=True,
                          selinux_transition_ok=True,
                          credentials_already_committed=True)
        conditions.update(overrides)
        return self.ledger.exec_result(self.owner, self.request, **conditions)

    def test_successful_authorized_request_can_be_consumed_only_once(self):
        self.assertTrue(self.begin())
        self.assertFalse(self.ledger.authorize_issuer_once(self.owner, self.request))
        self.assertTrue(self.finish())
        self.assertTrue(self.ledger.authorize_issuer_once(self.owner, self.request))
        self.assertFalse(self.ledger.authorize_issuer_once(self.owner, self.request))

    def test_exec_success_without_preexisting_su_intent_cannot_grant(self):
        self.assertFalse(self.finish())
        self.assertFalse(self.ledger.authorize_issuer_once(self.owner, self.request))

    def test_explicit_nonsu_exec_denied(self):
        self.assertFalse(self.begin(su_intent=False))

    def test_uid_not_allowlisted_denied(self):
        self.assertFalse(self.begin(allowlisted=False))

    def test_chrooted_request_denied(self):
        self.assertFalse(self.begin(chrooted=True))

    def test_custom_profile_does_not_imply_fd_eligibility(self):
        self.assertFalse(self.begin(fd_profile_eligible=False))

    def test_precommit_failure_denied(self):
        self.assertFalse(self.begin(precommit_checks_ok=False))

    def test_exec_failure_invalidates_request(self):
        self.assertTrue(self.begin())
        self.assertFalse(self.finish(exec_succeeded=False))
        self.assertFalse(self.ledger.authorize_issuer_once(self.owner, self.request))
        self.assertFalse(self.begin())

    def test_credential_transition_failure_invalidates_request(self):
        self.assertTrue(self.begin())
        self.assertFalse(self.finish(credential_transition_ok=False))
        self.assertFalse(self.ledger.authorize_issuer_once(self.owner, self.request))

    def test_selinux_failure_invalidates_request(self):
        self.assertTrue(self.begin())
        self.assertFalse(self.finish(selinux_transition_ok=False))
        self.assertFalse(self.ledger.authorize_issuer_once(self.owner, self.request))

    def test_another_exec_attempt_by_same_task_invalidates_pending(self):
        self.assertTrue(self.begin())
        self.assertFalse(self.ledger.exec_result(
            self.owner, RequestIdentity(), exec_succeeded=True,
            credential_transition_ok=True, selinux_transition_ok=True,
            credentials_already_committed=True))
        self.assertFalse(self.ledger.authorize_issuer_once(self.owner, self.request))

    def test_duplicate_success_callback_revokes_ready_permission(self):
        self.assertTrue(self.begin())
        self.assertTrue(self.finish())
        self.assertFalse(self.finish())
        self.assertFalse(self.ledger.authorize_issuer_once(self.owner, self.request))

    def test_new_exec_after_success_revokes_ready_permission(self):
        self.assertTrue(self.begin())
        self.assertTrue(self.finish())
        self.assertFalse(self.ledger.exec_result(
            self.owner, RequestIdentity(), exec_succeeded=True,
            credential_transition_ok=True, selinux_transition_ok=True,
            credentials_already_committed=True))
        self.assertFalse(self.ledger.authorize_issuer_once(self.owner, self.request))

    def test_failed_new_exec_after_success_revokes_ready_permission(self):
        self.assertTrue(self.begin())
        self.assertTrue(self.finish())
        self.assertFalse(self.ledger.exec_result(
            self.owner, RequestIdentity(), exec_succeeded=False,
            credential_transition_ok=False, selinux_transition_ok=False,
            credentials_already_committed=True))
        self.assertFalse(self.ledger.authorize_issuer_once(self.owner, self.request))

    def test_duplicate_begin_while_pending_revokes_old_permission(self):
        self.assertTrue(self.begin())
        second = RequestIdentity()
        self.assertFalse(self.ledger.begin(
            self.owner, second, su_intent=True, allowlisted=True,
            chrooted=False, fd_profile_eligible=True, precommit_checks_ok=True))
        self.assertFalse(self.finish())
        self.assertFalse(self.ledger.authorize_issuer_once(self.owner, self.request))

    def test_new_begin_after_success_revokes_old_permission(self):
        self.assertTrue(self.begin())
        self.assertTrue(self.finish())
        self.assertFalse(self.ledger.begin(
            self.owner, RequestIdentity(), su_intent=True, allowlisted=True,
            chrooted=False, fd_profile_eligible=True, precommit_checks_ok=True))
        self.assertFalse(self.ledger.authorize_issuer_once(self.owner, self.request))

    def test_denied_new_begin_after_success_revokes_old_permission(self):
        self.assertTrue(self.begin())
        self.assertTrue(self.finish())
        self.assertFalse(self.ledger.begin(
            self.owner, RequestIdentity(), su_intent=False, allowlisted=True,
            chrooted=False, fd_profile_eligible=True, precommit_checks_ok=True))
        self.assertFalse(self.ledger.authorize_issuer_once(self.owner, self.request))

    def test_exec_failure_after_published_creds_latches_hazard(self):
        self.assertTrue(self.begin())
        self.assertFalse(self.finish(exec_succeeded=False))
        self.assertTrue(self.ledger.has_unresolved_credential_hazard(self.owner))
        self.ledger.cancel(self.owner)
        self.assertTrue(self.ledger.has_unresolved_credential_hazard(self.owner))
        # A FRESH request must be denied by the hazard, not by replay rules.
        self.assertFalse(self.ledger.begin(
            self.owner, RequestIdentity(), su_intent=True, allowlisted=True,
            chrooted=False, fd_profile_eligible=True, precommit_checks_ok=True))

    def test_selinux_failure_after_commit_latches_hazard(self):
        self.assertTrue(self.begin())
        self.assertFalse(self.finish(selinux_transition_ok=False))
        self.assertTrue(self.ledger.has_unresolved_credential_hazard(self.owner))

    def test_credential_failure_after_commit_latches_hazard(self):
        self.assertTrue(self.begin())
        self.assertFalse(self.finish(credential_transition_ok=False))
        self.assertTrue(self.ledger.has_unresolved_credential_hazard(self.owner))

    def test_failed_exec_before_commit_has_no_postcommit_hazard(self):
        self.assertTrue(self.begin())
        self.assertFalse(self.finish(exec_succeeded=False,
                                     credentials_already_committed=False))
        self.assertFalse(self.ledger.has_unresolved_credential_hazard(self.owner))
        self.assertFalse(self.ledger.authorize_issuer_once(self.owner, self.request))
        self.assertTrue(self.ledger.begin(
            self.owner, RequestIdentity(), su_intent=True, allowlisted=True,
            chrooted=False, fd_profile_eligible=True, precommit_checks_ok=True))

    def test_successful_exec_without_commit_does_not_authorize(self):
        self.assertTrue(self.begin())
        self.assertFalse(self.finish(credentials_already_committed=False))
        self.assertFalse(self.ledger.authorize_issuer_once(self.owner, self.request))

    def test_mismatched_exec_after_commit_blocks_until_task_exit(self):
        self.assertTrue(self.begin())
        self.assertFalse(self.ledger.exec_result(
            self.owner, RequestIdentity(), exec_succeeded=True,
            credential_transition_ok=True, selinux_transition_ok=True,
            credentials_already_committed=True))
        self.assertTrue(self.ledger.has_unresolved_credential_hazard(self.owner))
        self.ledger.cancel(self.owner)
        self.assertTrue(self.ledger.has_unresolved_credential_hazard(self.owner))
        self.ledger.task_exit(self.owner)
        self.assertFalse(self.ledger.has_unresolved_credential_hazard(self.owner))
        # Retired owner may not resume, even using a never-before-seen token.
        self.assertFalse(self.ledger.begin(
            self.owner, RequestIdentity(), su_intent=True, allowlisted=True,
            chrooted=False, fd_profile_eligible=True, precommit_checks_ok=True))

    def test_other_task_cannot_complete_or_consume_request(self):
        self.assertTrue(self.begin())
        other = TaskIdentity()
        self.assertFalse(self.ledger.exec_result(
            other, self.request, exec_succeeded=True,
            credential_transition_ok=True, selinux_transition_ok=True,
            credentials_already_committed=True))
        self.assertTrue(self.finish())
        self.assertFalse(self.ledger.authorize_issuer_once(other, self.request))
        self.assertTrue(self.ledger.authorize_issuer_once(self.owner, self.request))

    def test_other_request_cannot_consume_ready_state(self):
        self.assertTrue(self.begin())
        self.assertTrue(self.finish())
        self.assertFalse(self.ledger.authorize_issuer_once(self.owner, RequestIdentity()))
        self.assertTrue(self.ledger.authorize_issuer_once(self.owner, self.request))

    def test_task_exit_invalidates_pending_and_ready(self):
        self.assertTrue(self.begin())
        self.ledger.task_exit(self.owner)
        self.assertFalse(self.finish())
        self.assertFalse(self.ledger.authorize_issuer_once(self.owner, self.request))
        second = RequestIdentity()
        self.assertFalse(self.ledger.begin(self.owner, second, su_intent=True,
                      allowlisted=True, chrooted=False, fd_profile_eligible=True,
                      precommit_checks_ok=True))
        new_task = TaskIdentity()
        self.assertTrue(self.ledger.begin(new_task, second, su_intent=True,
                      allowlisted=True, chrooted=False, fd_profile_eligible=True,
                      precommit_checks_ok=True))
        self.assertTrue(self.ledger.exec_result(new_task, second,
                      exec_succeeded=True, credential_transition_ok=True,
                      selinux_transition_ok=True,
            credentials_already_committed=True))
        self.ledger.task_exit(new_task)
        self.assertFalse(self.ledger.authorize_issuer_once(new_task, second))

    def test_abort_discards_pending(self):
        self.assertTrue(self.begin())
        self.ledger.cancel(self.owner)
        self.assertFalse(self.finish())

    def test_duplicate_active_request_rejected(self):
        self.assertTrue(self.begin())
        self.assertFalse(self.ledger.begin(self.owner, RequestIdentity(),
                      su_intent=True, allowlisted=True, chrooted=False,
                      fd_profile_eligible=True, precommit_checks_ok=True))

    def test_replay_request_with_other_owner_rejected(self):
        self.assertTrue(self.begin())
        self.ledger.cancel(self.owner)
        self.assertFalse(self.ledger.begin(TaskIdentity(), self.request,
                      su_intent=True, allowlisted=True, chrooted=False,
                      fd_profile_eligible=True, precommit_checks_ok=True))

    def test_new_request_after_consumption_needs_fresh_identity(self):
        self.assertTrue(self.begin())
        self.assertTrue(self.finish())
        self.assertTrue(self.ledger.authorize_issuer_once(self.owner, self.request))
        followup = RequestIdentity()
        self.assertTrue(self.ledger.begin(self.owner, followup, su_intent=True,
                      allowlisted=True, chrooted=False, fd_profile_eligible=True,
                      precommit_checks_ok=True))
        self.assertFalse(self.ledger.authorize_issuer_once(self.owner, followup))
        self.assertTrue(self.ledger.exec_result(self.owner, followup,
                      exec_succeeded=True, credential_transition_ok=True,
                      selinux_transition_ok=True,
            credentials_already_committed=True))
        self.assertTrue(self.ledger.authorize_issuer_once(self.owner, followup))

    def test_invalid_identity_type_rejected(self):
        self.assertFalse(self.ledger.begin(123, self.request, su_intent=True,
                         allowlisted=True, chrooted=False, fd_profile_eligible=True,
                         precommit_checks_ok=True))
        self.assertFalse(self.ledger.begin(self.owner, 123, su_intent=True,
                         allowlisted=True, chrooted=False, fd_profile_eligible=True,
                         precommit_checks_ok=True))

    def test_equal_looking_but_distinct_tokens_do_not_alias(self):
        self.assertNotEqual(TaskIdentity(), TaskIdentity())
        self.assertNotEqual(RequestIdentity(), RequestIdentity())
        self.assertTrue(self.begin())
        self.assertFalse(self.ledger.authorize_issuer_once(TaskIdentity(), self.request))
        self.assertFalse(self.ledger.authorize_issuer_once(self.owner, RequestIdentity()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
