"""Bounded interpreter for the actual exec boot-stage and SID-cache C bodies.

The runner selects CONFIG branches and checks caller propagation separately.
This checks serialized histories and fault paths, not kernel scheduling, policy
rollback, multi-SID atomic publication, or the separate supercall boot path.
Unknown syntax, operations and calls fail closed.
"""

from itertools import product
import re

from pycparser import c_ast

from rothko_ksun_g2_backup_reader_ast import parse_function
from rothko_ksun_g2_type_ast import _without_comments


_UNSET = ("uninitialized",)
_CONTEXTS = ("KERNEL_SU_CONTEXT", "ZYGOTE_CONTEXT", "INIT_CONTEXT",
             "KSU_FILE_CONTEXT")
_CACHES = ("cached_su_sid", "cached_zygote_sid", "cached_init_sid", "ksu_file_sid")
_SIDS = (101, 202, 303, 404)
_ERRORS = (-5, -12, -13, -108, -123)
_CONSTANTS = {"true": 1, "false": 0, "NULL": 0, "EAGAIN": 11,
              "EINVAL": 22, "EIO": 5, "ENOMEM": 12, "EACCES": 13,
              "ESHUTDOWN": 108}
_CONSTANTS.update({name: name for name in _CONTEXTS})


def _require(condition, message):
    if not condition:
        raise RuntimeError("boot status AST: " + message)


def _function(source, name):
    source = _without_comments(source)
    source = re.sub(r"(?m)^\s*#.*$", "", source)
    return parse_function(source, name)


class _Machine:
    def __init__(self, function, globals_):
        self.function = function
        self.globals = dict(globals_)
        self.locals = {}
        self.steps = 0

    def _readglobal(self, name):
        return self.globals[name]

    def _writeglobal(self, name, value):
        self.globals[name] = value

    def _read(self, name):
        if name in self.locals:
            value = self.locals[name]
        elif name in self.globals:
            value = self._readglobal(name)
        elif name in _CONSTANTS:
            value = _CONSTANTS[name]
        else:
            raise RuntimeError("boot status AST: unknown identifier " + name)
        _require(value != _UNSET, "read before initialization: " + name)
        return value

    def _assign(self, target, value):
        _require(isinstance(target, c_ast.ID), "non-scalar assignment")
        if target.name in self.locals:
            self.locals[target.name] = value
        else:
            _require(target.name in self.globals, "undeclared assignment")
            self._writeglobal(target.name, value)

    def _value(self, node):
        if isinstance(node, c_ast.ID):
            return self._read(node.name)
        if isinstance(node, c_ast.Constant):
            if node.type == "string":
                return ("string", node.value)
            _require(node.type in {"int", "unsigned int", "long int"},
                     "unmodeled literal")
            return int(re.sub(r"[uUlL]+$", "", node.value), 0)
        if isinstance(node, c_ast.Cast):
            return self._value(node.expr)
        if isinstance(node, c_ast.UnaryOp):
            if node.op == "&":
                _require(isinstance(node.expr, c_ast.ID), "nonlocal address")
                return ("ref", node.expr.name)
            value = self._value(node.expr)
            if node.op == "!":
                return int(not value)
            if node.op == "-":
                _require(isinstance(value, int), "negated noninteger")
                return -value
        if isinstance(node, c_ast.BinaryOp):
            left = self._value(node.left)
            if node.op == "&&" and not left:
                return 0
            if node.op == "||" and left:
                return 1
            right = self._value(node.right)
            if node.op == "==":
                return int(left == right)
            if node.op == "!=":
                return int(left != right)
            if node.op in {"&&", "||"}:
                return int(bool(right))
        if isinstance(node, c_ast.FuncCall):
            _require(isinstance(node.name, c_ast.ID), "indirect call")
            args = [self._value(arg) for arg in
                    (node.args.exprs if node.args else [])]
            return self._call(node.name.name, args)
        raise RuntimeError("boot status AST: unsupported expression " +
                           type(node).__name__)

    def _statement(self, node):
        self.steps += 1
        _require(self.steps < 300, "statement bound exceeded")
        if node is None or isinstance(node, c_ast.EmptyStatement):
            return None
        if isinstance(node, c_ast.Compound):
            for child in node.block_items or []:
                signal = self._statement(child)
                if signal:
                    return signal
            return None
        if isinstance(node, c_ast.Decl):
            _require(node.name not in self.locals and node.name not in self.globals,
                     "shadowed local or global")
            self.locals[node.name] = (_UNSET if node.init is None else
                                     self._value(node.init))
            return None
        if isinstance(node, c_ast.Assignment):
            _require(node.op == "=", "compound assignment")
            self._assign(node.lvalue, self._value(node.rvalue))
            return None
        if isinstance(node, c_ast.If):
            return self._statement(node.iftrue if self._value(node.cond)
                                   else node.iffalse)
        if isinstance(node, c_ast.FuncCall):
            self._value(node)
            return None
        if isinstance(node, c_ast.Return):
            _require(node.expr is not None, "status return lacks expression")
            return ("return", self._value(node.expr))
        if isinstance(node, c_ast.Goto):
            return ("goto", node.name)
        if isinstance(node, c_ast.Label):
            return self._statement(node.stmt)
        raise RuntimeError("boot status AST: unsupported statement " +
                           type(node).__name__)

    def _execute(self, arguments):
        params = self.function.decl.type.args.params
        names = [param.name for param in params if isinstance(param, c_ast.Decl)]
        _require(len(names) == len(arguments), "function argument count")
        self.locals = dict(zip(names, arguments))
        self.steps = 0
        statements = self.function.body.block_items or []
        labels = {node.name: index for index, node in enumerate(statements)
                  if isinstance(node, c_ast.Label)}
        index = 0
        while index < len(statements):
            signal = self._statement(statements[index])
            if signal:
                if signal[0] == "return":
                    return signal[1]
                _require(signal[0] == "goto" and signal[1] in labels,
                         "goto must target a function-body label")
                index = labels[signal[1]]
            else:
                index += 1
        raise RuntimeError("boot status AST: status function fell through")


class _Boot(_Machine):
    def __init__(self, function, susfs):
        super().__init__(function, {"ksu_boot_error": 0,
                                   "ksu_second_stage_done": 0,
                                   "ksu_first_zygote_done": 0})
        self.susfs = susfs
        self.locked = False
        self.keys = set()
        self.trace = []
        self.effects = []
        self.failure = 0

    def _readglobal(self, name):
        _require(self.locked, "boot state read outside owner mutex")
        return super()._readglobal(name)

    def _writeglobal(self, name, value):
        _require(self.locked, "boot state write outside owner mutex")
        if name == "ksu_boot_error":
            _require(value == self.failure and value < 0 and
                     self.globals[name] == 0, "invalid or cleared sticky errno")
        else:
            expected = ("ksu_first_zygote_done" if self.first else
                        "ksu_second_stage_done")
            _require(name == expected and value == 1 and
                     self.globals[name] == 0 and not self.failure and
                     self.trace == self.expected, "premature stage completion")
        super()._writeglobal(name, value)

    def _call(self, name, args):
        if name == "mutex_lock":
            _require(args == [("ref", "ksu_boot_stage_lock")] and not self.locked,
                     "wrong or recursive owner lock")
            self.locked = True
            return 0
        _require(self.locked, "call outside boot owner mutex: " + name)
        if name == "mutex_unlock":
            _require(args == [("ref", "ksu_boot_stage_lock")], "wrong owner unlock")
            if self.failure:
                _require(self.globals["ksu_boot_error"] == self.failure,
                         "failure escaped without persistent errno")
            self.locked = False
            return 0
        if name == "pr_err":
            _require(args and isinstance(args[0], tuple) and
                     args[0][0] == "string", "logging format")
            return 0
        if name == "static_branch_disable":
            key = "is_first_zygote" if self.first else "is_init_second_stage_not_executed"
            done = "ksu_first_zygote_done" if self.first else "ksu_second_stage_done"
            _require(args == [("ref", key)] and key not in self.keys and
                     self.globals[done] == 1 and self.trace == self.expected and
                     not self.failure, "key disable before completed stage")
            self.keys.add(key)
            return 0
        if name == "ksu_stop_ksud_execve_hook":
            _require(not args and not self.susfs and self.first and
                     self.globals["ksu_first_zygote_done"] == 1 and
                     "is_first_zygote" in self.keys and not self.stopped,
                     "hook stop before first-stage completion")
            self.stopped = True
            return 0
        calls = {"ksu_selinux_hide_handle_second_stage": "hide",
                 "apply_kernelsu_rules": "rules", "cache_sid": "cache",
                 "setup_ksu_cred": "ready", "on_post_fs_data": "post"}
        _require(name in calls, "unmodeled boot call " + name)
        effect = calls[name]
        _require(not args and not self.globals["ksu_boot_error"] and
                 not self.failure and len(self.trace) < len(self.expected) and
                 self.expected[len(self.trace)] == effect,
                 "effect replay, wrong stage or effect order: " + effect)
        self.trace.append(effect)
        self.effects.append((self.first, effect))
        self.failure = self.faults.get(effect, 0)
        _require(self.failure == 0 or (effect in {"rules", "cache", "ready"}
                                      and self.failure < 0), "invalid fault")
        return self.failure

    def invoke(self, first, faults):
        self.first = first
        self.faults = faults
        self.failure = 0
        self.trace = []
        self.stopped = False
        self.expected = (["cache", "ready", "post"] if first else
                         ["hide", "rules", "cache", "ready"])
        before = dict(self.globals)
        result = self._execute([int(first)])
        _require(not self.locked, "return retained owner lock")
        newly_done = first and not before["ksu_first_zygote_done"] and \
            self.globals["ksu_first_zygote_done"]
        _require(self.stopped == bool(newly_done and not self.susfs),
                 "non-SUSFS hook-stop completion mismatch")
        return result


def _history(function, susfs, events):
    machine = _Boot(function, susfs)
    error = 0
    second = first_done = False
    expected_effects = []
    for first, faults in events:
        result = 0
        if error:
            result = error
        elif first and not second:
            result = -11
        elif not (first_done if first else second):
            effects = ["cache", "ready", "post"] if first else \
                ["hide", "rules", "cache", "ready"]
            for effect in effects:
                expected_effects.append((first, effect))
                if faults.get(effect):
                    result = error = faults[effect]
                    break
            if not result:
                if first:
                    first_done = True
                else:
                    second = True
        actual = machine.invoke(first, faults)
        _require(actual == result, "errno lost or successful repeat changed status")
        _require(machine.globals == {"ksu_boot_error": error,
                                    "ksu_second_stage_done": int(second),
                                    "ksu_first_zygote_done": int(first_done)},
                 "persistent boot state differs from stage outcome")
        _require(machine.effects == expected_effects, "boot effects replayed or omitted")
        expected_keys = set()
        if second:
            expected_keys.add("is_init_second_stage_not_executed")
        if first_done:
            expected_keys.add("is_first_zygote")
        _require(machine.keys == expected_keys, "completed stage did not disable its key")


class _Cache(_Machine):
    def __init__(self, function, initial, failure_index=None, error=0, zero=False):
        super().__init__(function, dict(zip(_CACHES, initial)))
        self.failure_index = failure_index
        self.error = error
        self.zero = zero
        self.lookups = 0
        self.resolved = []
        self.writes = []

    def _writeglobal(self, name, value):
        index = len(self.writes)
        _require(self.resolved == list(_CONTEXTS) and index < 4 and
                 name == _CACHES[index] and value == _SIDS[index],
                 "SID cache publication before all successful nonzero lookups")
        self.writes.append(name)
        super()._writeglobal(name, value)

    def _call(self, name, args):
        if name in {"pr_warn", "pr_info"}:
            _require(args and isinstance(args[0], tuple) and
                     args[0][0] == "string", "cache logging format")
            return 0
        if name == "strlen":
            _require(len(args) == 1 and args[0] in _CONTEXTS,
                     "unmodeled context length")
            return ("length", args[0])
        _require(name == "security_secctx_to_secid", "unmodeled SID call " + name)
        index = self.lookups
        _require(index < 4 and len(args) == 3 and args[0] == _CONTEXTS[index] and
                 args[1] == ("length", args[0]) and isinstance(args[2], tuple) and
                 len(args[2]) == 2 and args[2][0] == "ref" and
                 args[2][1] in self.locals, "SID lookup arguments or ordering")
        self.lookups += 1
        failed = index == self.failure_index
        # Even failure may overwrite its private output. It must never reach
        # a published cache; this does not assume an undocumented callee rule.
        value = 0 if failed and self.zero else (9999 if failed else _SIDS[index])
        self.locals[args[2][1]] = value
        if not failed:
            self.resolved.append(args[0])
        return self.error if failed else 0

    def check(self):
        before = dict(self.globals)
        result = self._execute([])
        failed = self.failure_index is not None
        expected = (-22 if self.zero else self.error) if failed else 0
        _require(result == expected, "cache failed to propagate exact errno/zero SID")
        _require(self.lookups == (self.failure_index + 1 if failed else 4),
                 "lookup continued after failure or was omitted")
        _require(self.globals == (before if failed else dict(zip(_CACHES, _SIDS))) and
                 self.writes == ([] if failed else list(_CACHES)),
                 "failed cache changed globals or success omitted publication")


def validate_boot_status(runtime, selinux, susfs):
    """Return bounded history/cache scenario count for CONFIG-selected source."""
    _require(type(susfs) is bool, "SUSFS selector must be bool")
    clean = _without_comments(runtime)
    declarations = (r"static\s+DEFINE_MUTEX\(ksu_boot_stage_lock\)\s*;",
                    r"static\s+int\s+ksu_boot_error\s*;",
                    r"static\s+bool\s+ksu_second_stage_done\s*;",
                    r"static\s+bool\s+ksu_first_zygote_done\s*;")
    for declaration in declarations:
        _require(len(re.findall(declaration, clean)) == 1,
                 "missing or changed zero-initialized boot owner state")
    function = _function(runtime, "ksu_run_boot_stage")
    count = 0
    for length in range(1, 5):
        for sequence in product((False, True), repeat=length):
            _history(function, susfs, [(first, {}) for first in sequence])
            count += 1
    for error in _ERRORS:
        for effect in ("rules", "cache", "ready"):
            _history(function, susfs, [(False, {effect: error}), (False, {}),
                                       (True, {}), (False, {}), (True, {})])
            count += 1
        for effect in ("cache", "ready"):
            _history(function, susfs, [(True, {}), (False, {}),
                                       (True, {effect: error}), (True, {}),
                                       (False, {}), (True, {})])
            count += 1
    cache = _function(selinux, "cache_sid")
    for initial in ((0, 0, 0, 0), (701, 702, 703, 704)):
        _Cache(cache, initial).check()
        count += 1
        for index in range(4):
            for error in _ERRORS:
                _Cache(cache, initial, index, error).check()
                count += 1
            _Cache(cache, initial, index, zero=True).check()
            count += 1
    return count
