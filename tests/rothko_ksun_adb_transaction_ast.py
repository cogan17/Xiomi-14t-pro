"""Bounded interpreter of the actual ADB credential/dispatch C protocol.

The runner selects CONFIG branches and independently validates the native
preload builder. This module models that builder's status/output contract;
it does not prove exec rollback, user-stack restoration or concurrency.
Unknown calls, expressions and control-flow forms fail closed.
"""

import re

from pycparser import c_ast

from rothko_ksun_g2_backup_reader_ast import parse_function
from rothko_ksun_g2_type_ast import _without_comments


_CRED = ("owned_credential",)
_ORIGINAL = ("original_envp",)
_STAGED = ("staged_envp",)
_STACK = ("user_stack",)
_FILENAME = ("filename",)
_UNSET = ("uninitialized",)
_CONSTANTS = {
    "NULL": 0, "true": 1, "false": 0, "GLOBAL_ROOT_UID": 0,
    "KERNEL_SU_CONTEXT": ("ksu_context",),
    "EINVAL": 22, "ENOMEM": 12, "EACCES": 13, "EFAULT": 14,
    "E2BIG": 7, "EOPNOTSUPP": 95, "EPERM": 1, "EIO": 5,
    "EAGAIN": 11, "ESHUTDOWN": 108, "EALREADY": 114,
}


def _fail(message):
    raise RuntimeError("ADB transaction AST: " + message)


def _require(condition, message):
    if not condition:
        _fail(message)


def _clean(source):
    source = _without_comments(source)
    source = re.sub(r"(?m)^\s*#.*$", "", source)
    return re.sub(r"\b(?:__user|__nocfi|__always_inline)\b", "", source)


class _Protocol:
    def __init__(self, functions, **scenario):
        self.functions = functions
        self.case = dict(allocated=True, root=True, init=True, domain=0,
                         valid=True, builder=0, filename=1, library=1,
                         compat=False)
        self.case.update(scenario)
        self.memory = {("result", "out"): _UNSET,
                       ("external", "envp"): _ORIGINAL}
        self.frames = 0
        self.owned = False
        self.verified = False
        self.built = False
        self.commits = self.aborts = self.allocations = 0
        self.transitions = self.publications = 0
        self.filename_seen = False
        self.calls = []
        self.steps = 0

    def _read(self, reference):
        _require(isinstance(reference, tuple) and len(reference) == 3
                 and reference[0] == "ref", "invalid dereference")
        value = self.memory.get(reference[1:], _UNSET)
        _require(value != _UNSET, "read before initialization")
        return value

    def _write(self, reference, value, function):
        _require(isinstance(reference, tuple) and len(reference) == 3
                 and reference[0] == "ref", "invalid assignment target")
        if function == "ksu_prepare_adb_root_cred":
            _require(value == 0 or value == _CRED, "invalid credential output")
            if value == _CRED:
                _require(self.owned and self.verified and not self.commits,
                         "unverified credential publication")
        elif function == "commit_adb_root_exec":
            _require(reference[1] != "external" and value == _STAGED
                     and self.commits == 1 and self.built,
                     "local envp publication before completed commit")
        else:
            _require(reference == ("ref", "external", "envp"),
                     "dispatcher writes outside external envp")
            _require(value == _STAGED and self.commits == 1 and self.built,
                     "external envp publication before successful transaction")
            self.publications += 1
        self.memory[reference[1:]] = value

    def _value(self, node, frame, function):
        if isinstance(node, c_ast.ID):
            if node.name in _CONSTANTS:
                return _CONSTANTS[node.name]
            return self._read(("ref", frame, node.name))
        if isinstance(node, c_ast.Constant):
            _require(node.type in {"int", "unsigned int", "long int"},
                     "unmodeled literal")
            return int(re.sub(r"[uUlL]+$", "", node.value), 0)
        if isinstance(node, c_ast.Cast):
            return self._value(node.expr, frame, function)
        if isinstance(node, c_ast.StructRef):
            _require(node.type == "->" and node.field.name == "euid"
                     and self._value(node.name, frame, function) == _CRED
                     and self.owned, "invalid credential field read")
            return 0 if self.case["root"] else 2000
        if isinstance(node, c_ast.UnaryOp):
            if node.op == "&":
                _require(isinstance(node.expr, c_ast.ID), "nonlocal address escape")
                return ("ref", frame, node.expr.name)
            value = self._value(node.expr, frame, function)
            if node.op == "*":
                return self._read(value)
            if node.op == "!":
                return int(not value)
            if node.op == "-":
                _require(isinstance(value, int), "negated pointer")
                return -value
        if isinstance(node, c_ast.BinaryOp):
            left = self._value(node.left, frame, function)
            if node.op == "&&" and not left:
                return 0
            if node.op == "||" and left:
                return 1
            right = self._value(node.right, frame, function)
            if node.op == "==":
                return int(left == right)
            if node.op == "!=":
                return int(left != right)
            if node.op in {"&&", "||"}:
                return int(bool(right))
        if isinstance(node, c_ast.FuncCall):
            _require(isinstance(node.name, c_ast.ID), "indirect call")
            args = [self._value(arg, frame, function)
                    for arg in (node.args.exprs if node.args else [])]
            return self._call(node.name.name, args)
        _fail("unsupported expression " + type(node).__name__)

    def _call(self, name, args):
        _require(not self.commits, "function call after credential commit: " + name)
        self.calls.append(name)
        if name in self.functions:
            return self.invoke(name, args)
        if name == "prepare_creds":
            _require(not args and not self.owned and not self.allocations,
                     "duplicate or malformed credential allocation")
            self.allocations += 1
            self.owned = self.case["allocated"]
            return _CRED if self.owned else 0
        if name == "uid_eq":
            _require(len(args) == 2 and args[1] == 0, "root UID check arguments")
            return int(args[0] == args[1])
        if name in {"is_init", "is_task_ksu_domain"}:
            _require(args == [_CRED] and self.owned, "domain check lacks ownership")
            if name == "is_init":
                return int(self.case["init"])
            _require(self.transitions == 1 and not self.case["domain"],
                     "domain validation without successful transition")
            self.verified = self.case["valid"]
            return int(self.verified)
        if name == "transive_to_domain":
            _require(args == [_CONSTANTS["KERNEL_SU_CONTEXT"], _CRED, 1]
                     and self.owned and self.case["root"] and self.case["init"]
                     and not self.transitions, "domain transition bypasses admission")
            self.transitions += 1
            return self.case["domain"]
        if name == "abort_creds":
            _require(args == [_CRED] and self.owned, "abort without owned credential")
            self.owned = False
            self.aborts += 1
            return 0
        if name == "prepare_ld_preload":
            _require(len(args) == 3 and args[:2] == [_ORIGINAL, _STACK]
                     and self.owned and self.verified and not self.built,
                     "preload preparation outside prepared credential transaction")
            _require(isinstance(args[2], tuple) and len(args[2]) == 3
                     and args[2][0] == "ref" and args[2][1] != "external",
                     "preload output must be a local pointer")
            if not self.case["builder"]:
                self.memory[args[2][1:]] = _STAGED
                self.built = True
            return self.case["builder"]
        if name == "commit_creds":
            _require(args == [_CRED] and self.owned and self.verified and self.built,
                     "commit before all fallible preparation")
            self.owned = False
            self.commits += 1
            return 0
        if name == "is_exec_adbd":
            _require(args == [_FILENAME] and not self.filename_seen,
                     "malformed or repeated filename check")
            self.filename_seen = True
            return self.case["filename"]
        if name in {"is_libadbroot_ok", "in_compat_syscall",
                    "current_user_stack_pointer", "user_stack_pointer"}:
            _require(self.filename_seen and self.case["filename"] == 1,
                     "effect before matching filename")
            if name == "in_compat_syscall":
                _require(not args, "COMPAT predicate arguments")
                return int(self.case["compat"])
            _require(not self.case["compat"], "native operation before COMPAT rejection")
            if name == "is_libadbroot_ok":
                _require(not args, "library lookup arguments")
                return self.case["library"]
            _require(args == ([] if name.startswith("current_") else [("regs",)]),
                     "user stack getter arguments")
            return _STACK
        _fail("unmodeled call " + name)

    def _statement(self, node, frame, function):
        self.steps += 1
        _require(self.steps < 400, "statement bound exceeded")
        if node is None or isinstance(node, c_ast.EmptyStatement):
            return None
        if isinstance(node, c_ast.Compound):
            for child in node.block_items or []:
                signal = self._statement(child, frame, function)
                if signal:
                    return signal
            return None
        if isinstance(node, c_ast.Decl):
            _require((frame, node.name) not in self.memory, "duplicate local declaration")
            self.memory[(frame, node.name)] = (self._value(node.init, frame, function)
                                               if node.init else _UNSET)
        elif isinstance(node, c_ast.Assignment):
            _require(node.op == "=", "compound assignment")
            value = self._value(node.rvalue, frame, function)
            if isinstance(node.lvalue, c_ast.ID):
                key = (frame, node.lvalue.name)
                _require(key in self.memory, "write to undeclared/global variable")
                self.memory[key] = value
            else:
                _require(isinstance(node.lvalue, c_ast.UnaryOp)
                         and node.lvalue.op == "*", "unsupported assignment")
                reference = self._value(node.lvalue.expr, frame, function)
                self._write(reference, value, function)
        elif isinstance(node, c_ast.If):
            branch = node.iftrue if self._value(node.cond, frame, function) else node.iffalse
            return self._statement(branch, frame, function)
        elif isinstance(node, c_ast.Return):
            return ("return", self._value(node.expr, frame, function))
        elif isinstance(node, c_ast.Goto):
            return ("goto", node.name)
        elif isinstance(node, c_ast.Label):
            return self._statement(node.stmt, frame, function)
        elif isinstance(node, c_ast.FuncCall):
            self._value(node, frame, function)
        else:
            _fail("unsupported statement " + type(node).__name__)
        return None

    def invoke(self, name, args):
        function = self.functions[name]
        parameters = function.decl.type.args.params
        _require(len(args) == len(parameters), "incorrect helper arity")
        self.frames += 1
        frame = self.frames
        for parameter, value in zip(parameters, args):
            self.memory[(frame, parameter.name)] = value
        items = function.body.block_items or []
        labels = {node.name: index for index, node in enumerate(items)
                  if isinstance(node, c_ast.Label)}
        index = 0
        while index < len(items):
            signal = self._statement(items[index], frame, name)
            if signal:
                if signal[0] == "return":
                    return signal[1]
                _require(signal[1] in labels, "unknown/nonlocal goto")
                index = labels[signal[1]]
            else:
                index += 1
        _fail("function falls through without status: " + name)


def _validate_transaction(selinux_source, adb_configured_source, susfs, compat_enabled):
    """Execute finite failure/success paths over selected actual C functions."""
    _require(type(susfs) is bool and type(compat_enabled) is bool,
             "configuration selectors must be bool")
    dispatcher = ("do_ksu_adb_root_handle_execveat" if susfs
                  else "do_ksu_adb_root_handle_execve")
    functions = {
        "ksu_prepare_adb_root_cred": parse_function(_clean(selinux_source),
                                                   "ksu_prepare_adb_root_cred"),
        "commit_adb_root_exec": parse_function(_clean(adb_configured_source),
                                               "commit_adb_root_exec"),
        dispatcher: parse_function(_clean(adb_configured_source), dispatcher),
    }
    # Each expected status is independent of the interpreted C control flow.
    preparation = [({}, 0), ({"allocated": False}, -12), ({"root": False}, -13),
                   ({"init": False}, -13), ({"domain": -22}, -22),
                   ({"valid": False}, -13)]
    count = 0
    result_ref = ("ref", "result", "out")
    protocol = _Protocol(functions)
    _require(protocol.invoke("ksu_prepare_adb_root_cred", [0]) == -22
             and protocol.allocations == 0, "NULL out must fail before allocation")
    count += 1
    for case, expected in preparation:
        protocol = _Protocol(functions, **case)
        status = protocol.invoke("ksu_prepare_adb_root_cred", [result_ref])
        output = protocol.memory[("result", "out")]
        _require(status == expected and protocol.commits == 0,
                 "credential preparation status/commit mismatch")
        _require(protocol.owned == (expected == 0)
                 and output == (_CRED if expected == 0 else 0)
                 and protocol.aborts == int(expected != 0 and case.get("allocated", True)),
                 "credential preparation leaks, aborts, or publishes wrong ownership")
        count += 1
    transactions = preparation + [({"builder": errno}, errno)
                                  for errno in (-12, -14, -7)]
    for case, expected in transactions:
        protocol = _Protocol(functions, **case)
        status = protocol.invoke("commit_adb_root_exec", [_ORIGINAL, _STACK, result_ref])
        _require(status == expected and not protocol.owned
                 and protocol.commits == int(expected == 0)
                 and protocol.aborts == int(expected != 0 and case.get("allocated", True))
                 and protocol.memory[("result", "out")] == (_STAGED if expected == 0 else _UNSET),
                 "transaction status, local output, or credential disposition mismatch")
        count += 1
    dispatch_cases = transactions + [({"filename": value}, value) for value in (0, -14)]
    dispatch_cases += [({"library": value}, value) for value in (0, -13)]
    if susfs or compat_enabled:
        dispatch_cases += [({"compat": True}, -95)]
        dispatch_cases += [({"compat": True, "filename": value}, value)
                           for value in (0, -14)]
    for case, expected in dispatch_cases:
        protocol = _Protocol(functions, **case)
        external = ("ref", "external", "envp")
        args = ([_FILENAME, external, int(case.get("compat", False))] if susfs
                else [_FILENAME, ("regs",), external])
        status = protocol.invoke(dispatcher, args)
        success = expected == 0 and case.get("filename", 1) == 1 and case.get("library", 1) == 1
        _require(status == expected and not protocol.owned
                 and protocol.commits == int(success)
                 and protocol.publications == int(success)
                 and protocol.memory[("external", "envp")] == (_STAGED if success else _ORIGINAL),
                 "dispatcher loses errno or publishes external envp on failure/skip")
        if case.get("compat") or case.get("filename", 1) != 1 or case.get("library", 1) != 1:
            _require(protocol.allocations == 0, "skip/COMPAT path acquired credentials")
        count += 1
    return count


def validate_transaction(selinux_source, adb_configured_source, susfs, compat_enabled):
    """Return scenario count; reject invalid or unmodeled C with RuntimeError."""
    try:
        return _validate_transaction(selinux_source, adb_configured_source,
                                     susfs, compat_enabled)
    except RuntimeError:
        raise
    except Exception as exc:
        _fail("unmodeled syntax/value: " + str(exc))
