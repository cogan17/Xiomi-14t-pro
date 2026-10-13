#!/usr/bin/env python3
"""Host-only reference model for a *future* SU_SESSION request handshake.

NO KERNEL CODE, FD ISSUER, CREDENTIAL CHANGE, or AUTHORIZATION API.
Inputs such as allowlisted/success are ASSERTIONS from an imaginary trusted
caller, NOT facts this model can authenticate. Runtime race/refcount, per-task
storage, SELinux, and failed-exec credential-commit hazards remain UNPROVEN.
"""
from dataclasses import dataclass
from enum import Enum, auto


@dataclass(frozen=True, eq=False)
class TaskIdentity:
    """Opaque lifetime identity, NOT a numeric PID (PID reuse is unsafe)."""


@dataclass(frozen=True, eq=False)
class RequestIdentity:
    """Opaque one-attempt nonce. Not an authentication capability by itself."""


class Phase(Enum):
    PENDING = auto()
    EXEC_SUCCEEDED = auto()


@dataclass(frozen=True)
class Intent:
    task: TaskIdentity
    request: RequestIdentity
    phase: Phase


class SessionIntentModel:
    """Sequential, fail-closed permission *model*; never creates an FD.

    No step may promote arbitrary 'exec success' into SU_SESSION permission.
    An authenticated SU intent must precede a separately verified exec result,
    and the same owner/request pair may pass the hypothetical issuer once.
    """

    def __init__(self):
        self._active: dict[TaskIdentity, Intent] = {}
        # These sets are intentionally unbounded in this tiny HOST model.
        # Kernel implementation would require bounded, lifetime-safe storage.
        self._seen: set[RequestIdentity] = set()
        self._retired: set[TaskIdentity] = set()

    def begin(self, task: TaskIdentity, request: RequestIdentity, *,
              su_intent: bool, allowlisted: bool, chrooted: bool,
              fd_profile_eligible: bool, precommit_checks_ok: bool) -> bool:
        if not isinstance(task, TaskIdentity) or not isinstance(request, RequestIdentity):
            return False
        if task in self._active or task in self._retired or request in self._seen:
            return False
        if not (su_intent and allowlisted and not chrooted and
                fd_profile_eligible and precommit_checks_ok):
            return False
        self._seen.add(request)
        self._active[task] = Intent(task, request, Phase.PENDING)
        return True

    def exec_result(self, task: TaskIdentity, request: RequestIdentity, *,
                    exec_succeeded: bool, credential_transition_ok: bool,
                    selinux_transition_ok: bool) -> bool:
        intent = self._active.get(task)
        if intent is None or intent.phase is not Phase.PENDING:
            return False
        # A different exec attempt by the SAME task invalidates any old intent.
        # A foreign task cannot mutate this task's state.
        if intent.request is not request:
            del self._active[task]
            return False
        if not (exec_succeeded and credential_transition_ok and selinux_transition_ok):
            del self._active[task]
            return False
        self._active[task] = Intent(task, request, Phase.EXEC_SUCCEEDED)
        return True

    def authorize_issuer_once(self, task: TaskIdentity, request: RequestIdentity) -> bool:
        """Abstract one-shot decision only; no file, bit, or syscall is touched."""
        intent = self._active.get(task)
        if intent is None or intent.request is not request:
            return False
        if intent.phase is not Phase.EXEC_SUCCEEDED:
            return False
        del self._active[task]
        return True

    def cancel(self, task: TaskIdentity) -> None:
        self._active.pop(task, None)

    def task_exit(self, task: TaskIdentity) -> None:
        self.cancel(task)
        if isinstance(task, TaskIdentity):
            self._retired.add(task)
