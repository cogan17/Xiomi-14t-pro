"""Path-sensitive source checks for the private SELinux-hide backup borrow.

This is a deliberately bounded C protocol checker, not a compiler or a proof of
callback/module/status-page teardown. Unknown directives, calls and control-flow
forms are rejected. The runner owns patch composition and negative mutations.
"""

from collections import Counter
from dataclasses import dataclass, field, replace
import re

from pycparser import c_ast, c_parser

from rothko_ksun_g2_type_ast import _TOKEN, _shape, _without_comments


_PREAMBLE = """
typedef unsigned int bool;
typedef unsigned int u32;
typedef unsigned short u16;
typedef unsigned long size_t;
typedef long ssize_t;
typedef unsigned int gfp_t;
typedef ssize_t (*write_op_fn)(struct file *, char *, size_t);
typedef int (*setprocattr_fn)(const char *, void *, size_t);
"""
_INCLUDES = {
    '"selinux_hide.h"', '"infra/symbol_resolver.h"', '"linux/jump_label.h"',
    '"selinux/sepolicy.h"', '<linux/cred.h>', '<linux/cpu.h>',
    '<linux/memory.h>', '<linux/uaccess.h>', '<linux/init.h>',
    '<linux/printk.h>', '<linux/string.h>', '<linux/fs.h>', '<linux/types.h>',
    '<asm-generic/errno-base.h>', '<net/genetlink.h>', '<linux/moduleparam.h>',
    '<linux/mutex.h>', '<linux/version.h>', '<security.h>', '<ss/context.h>',
    '<ss/services.h>', '<ss/mls.h>', '<ss/conditional.h>', '"avc.h"',
    '"klog.h"', '"objsec.h"', '"ksu.h"', '"policy/feature.h"',
    '"hook/patch_memory.h"', '"hook/lsm_hook.h"',
    '"linux/rcupdate.h"', '"security.h"', '<linux/lockdep.h>',
    '<linux/slab.h>', '<linux/errno.h>', '"uapi/selinux.h"', '"selinux.h"',
    '"sepolicy.h"', '"ss/services.h"', '"linux/lsm_audit.h"', '"xfrm.h"',
}
_DEFINES = {
    "SELINUX_POLICY_INSTEAD_SELINUX_SS": "",
    "ALL": "NULL",
    "KSU_SEPOLICY_MAX_BATCH_SIZE": "(8U * 1024U * 1024U)",
    "KSU_SEPOLICY_MAX_ARGS": "5",
    "KSU_BOOT_RULE(rule)": r'''do { if (!(rule)) {
        pr_err("KernelSU initial rule failed: %s\n", #rule);
        return false; } } while (0)''',
}
_ANNOTATIONS = {"__nocfi", "__init", "__exit"}
_READERS = ("my_write_context", "my_write_access", "my_setprocattr")
_GET = "ksu_hide_policy_get"
_PUT = "ksu_hide_policy_put"
_BORROW = "ksu_borrow_selinux_backup"
_RETURN = "ksu_return_selinux_backup"
_POINTER = ("pointer",)
_EAGAIN = ("negative_errno", "EAGAIN")
_VOID = ("void",)
_SCALAR_POLICY_HELPERS = {
    "security_context_to_sid", "security_sid_to_context", "security_context_str_to_sid",
    "security_context_to_sid_with_policy", "security_sid_to_context_with_policy",
}


def _fail(message):
    raise RuntimeError("backup reader AST ownership: " + message)


def _condition_value(expression, version, susfs):
    if expression == "CONFIG_KSU_SUSFS":
        return susfs
    if expression.startswith("(") and expression.endswith(")"):
        expression = expression[1:-1].strip()
    match = re.fullmatch(
        r"LINUX_VERSION_CODE\s*(>=|<)\s*KERNEL_VERSION\(\s*(\d+)\s*,\s*"
        r"(\d+)\s*,\s*(\d+)\s*\)", expression,
    )
    if match is None:
        _fail("unknown configuration condition: " + expression)
    threshold = tuple(int(part) for part in match.groups()[1:])
    if threshold not in {(6, 4, 0), (6, 6, 0), (6, 10, 0)}:
        _fail("unreviewed version threshold: " + repr(threshold))
    return version >= threshold if match.group(1) == ">=" else version < threshold


def select_configuration(source, version_tuple, susfs):
    """Select only the explicitly supported hide-source directives.

    Comments and line continuations follow the shared C lexical masker. Every
    directive is checked, including directives inside an inactive branch. The
    existing rules-source macros are checked and masked, not expanded: their
    invocations remain ordinary C-call syntax for the separate owner checker.
    """
    version = tuple(version_tuple)
    if len(version) != 3 or any(type(part) is not int for part in version):
        _fail("version must be a three-integer tuple")
    if type(susfs) is not bool:
        _fail("SUSFS selection must be bool")
    selected = []
    # Each frame stores its parent's activity, current branch activity, and
    # whether an else has already been encountered. There is no macro engine.
    stack = []
    active = True
    for line in _without_comments(source).splitlines(keepends=True):
        if not line.lstrip().startswith("#"):
            selected.append(line if active else "\n")
            continue
        directive = re.fullmatch(r"\s*#\s*([A-Za-z_]\w*)\s*(.*?)\s*", line)
        if directive is None:
            _fail("malformed configuration directive")
        kind, argument = directive.groups()
        if kind == "include":
            if argument not in _INCLUDES:
                _fail("unknown include: " + argument)
        elif kind == "define":
            definition = re.fullmatch(r"([A-Za-z_]\w*(?:\([^)]*\))?)\s*(.*)", argument)
            if definition is None or definition.group(1) not in _DEFINES:
                _fail("unknown macro definition: " + argument)
            expected = _DEFINES[definition.group(1)]
            if ([token.group() for token in _TOKEN.finditer(definition.group(2))]
                    != [token.group() for token in _TOKEN.finditer(expected)]):
                _fail("unreviewed macro definition: " + definition.group(1))
        elif kind == "undef":
            if argument != "KSU_BOOT_RULE":
                _fail("unknown macro undefinition: " + argument)
        elif kind in {"if", "ifdef", "ifndef"}:
            if kind == "if":
                result = _condition_value(argument, version, susfs)
            else:
                if argument != "CONFIG_KSU_SUSFS":
                    _fail("unknown configuration symbol: " + argument)
                result = susfs if kind == "ifdef" else not susfs
            stack.append([active, bool(result), False])
            active = active and bool(result)
        elif kind == "else":
            if argument or not stack or stack[-1][2]:
                _fail("unmatched, repeated, or annotated else")
            stack[-1][1] = not stack[-1][1]
            stack[-1][2] = True
            active = stack[-1][0] and stack[-1][1]
        elif kind == "endif":
            if argument or not stack:
                _fail("unmatched or annotated endif")
            active = stack.pop()[0]
        else:
            _fail("unknown directive: " + kind)
        selected.append("\n")
    if stack:
        _fail("unterminated configuration conditional")
    return "".join(selected)


def _definitions(source, name):
    """Find top-level definitions by tokens; a prototype is never a body."""
    masked = _without_comments(source)
    tokens = list(_TOKEN.finditer(masked))
    definitions = []
    depth = 0
    boundary = 0
    i = 0
    while i < len(tokens):
        word = tokens[i].group()
        if not depth and word == name and i + 1 < len(tokens) and tokens[i + 1].group() == "(":
            j, parentheses = i + 1, 0
            while j < len(tokens):
                token = tokens[j].group()
                parentheses += (token == "(") - (token == ")")
                j += 1
                if not parentheses:
                    break
            if parentheses:
                _fail("unterminated parameters for " + name)
            # The only ignored annotations are a fixed kernel spelling set.
            while j < len(tokens) and tokens[j].group() in _ANNOTATIONS:
                j += 1
            if j < len(tokens) and tokens[j].group() == "{":
                opening, braces = j, 0
                while j < len(tokens):
                    token = tokens[j].group()
                    braces += (token == "{") - (token == "}")
                    j += 1
                    if not braces:
                        break
                if braces:
                    _fail("unterminated body for " + name)
                start, end = tokens[boundary].start(), tokens[j - 1].end()
                definition = masked[start:end]
                if "#" in [token.group() for token in _TOKEN.finditer(definition)]:
                    _fail("configure source before parsing " + name)
                definitions.append((start, end, definition))
                i = j
                boundary = j
                continue
        if word == "{":
            depth += 1
        elif word == "}":
            depth -= 1
            if depth < 0:
                _fail("unbalanced top-level braces")
            if not depth:
                boundary = i + 1
        elif word == ";" and not depth:
            boundary = i + 1
        i += 1
    if depth:
        _fail("unbalanced source braces")
    return definitions


def parse_function(source, name):
    """Return one pycparser FuncDef, ignoring prototypes and known annotations."""
    definitions = _definitions(source, name)
    if len(definitions) != 1:
        _fail("expected exactly one definition of " + name)
    definition = definitions[0][2]
    tokens = list(_TOKEN.finditer(definition))
    # Replace annotation tokens, never text within a string or a comment.
    characters = list(definition)
    for token in tokens:
        if token.group() in _ANNOTATIONS:
            characters[token.start():token.end()] = " " * (token.end() - token.start())
    try:
        parsed = c_parser.CParser().parse(_PREAMBLE + "".join(characters))
    except Exception as exc:
        _fail(name + " C syntax could not be parsed: " + str(exc))
    functions = [node for node in parsed.ext if isinstance(node, c_ast.FuncDef)]
    if len(functions) != 1 or functions[0].decl.name != name:
        _fail("unexpected parsed definition for " + name)
    return functions[0]


def _walk(node):
    if node is not None:
        yield node
        for _, child in node.children():
            yield from _walk(child)


def _ids(source):
    return [token.group() for token in _TOKEN.finditer(_without_comments(source))
            if re.fullmatch(r"[A-Za-z_]\w*", token.group())]


def _root(node):
    while isinstance(node, (c_ast.StructRef, c_ast.ArrayRef, c_ast.UnaryOp, c_ast.Cast)):
        node = node.expr if isinstance(node, (c_ast.UnaryOp, c_ast.Cast)) else node.name
    return node.name if isinstance(node, c_ast.ID) else None


def _callee(node):
    while isinstance(node, c_ast.Cast):
        node = node.expr
    if isinstance(node, c_ast.UnaryOp) and node.op == "*":
        return _callee(node.expr)
    if isinstance(node, c_ast.ID):
        return node.name
    if (isinstance(node, c_ast.StructRef) and node.type == "."
            and isinstance(node.name, c_ast.ID) and node.name.name == "selinux_setprocattr_hook"
            and isinstance(node.field, c_ast.ID) and node.field.name == "original"):
        return "original_setprocattr"
    _fail("unrecognized indirect function call")


def _args(call):
    return call.args.exprs if call.args is not None else []


def _is_id(node, name):
    return isinstance(node, c_ast.ID) and node.name == name


def _fake_address(node):
    return isinstance(node, c_ast.UnaryOp) and node.op == "&" and _is_id(node.expr, "fake_state")


def _mentions(node, names):
    return any(isinstance(child, c_ast.ID) and child.name in names for child in _walk(node))


@dataclass
class _State:
    env: dict = field(default_factory=dict)
    held: bool = False
    acquired: int = 0
    released: int = 0
    attempted: int = 0
    null_get: bool = False
    fake_bound: bool = False
    fake_initialized: bool = False
    policy_calls: tuple = ()
    hooked: int = 0

    def fork(self, **changes):
        return replace(self, env=dict(self.env), **changes)


def _truth(value):
    if isinstance(value, int):
        return bool(value)
    if value == _POINTER or (isinstance(value, tuple) and value[0] in {"negative_errno", "nonzero"}):
        return True
    return None


class _Protocol:
    def __init__(self, name, legacy, mode, expected_policy_calls=()):
        self.name, self.legacy, self.mode = name, legacy, mode
        self.expected_policy_calls = tuple(expected_policy_calls)
        self.terminals = []

    def fail(self, message):
        _fail(self.name + ": " + message)

    def _check_reference(self, node, state):
        if _root(node) == "fake_state":
            if not (state.held and state.fake_bound and state.fake_initialized):
                self.fail("legacy state used outside its bound borrow")
        if _root(node) == "policy" and state.env.get("policy") == _POINTER and not state.held:
            self.fail("policy reference used after return")

    def evaluate(self, node, state):
        if node is None:
            return [(state, _VOID)]
        if isinstance(node, c_ast.ID):
            self._check_reference(node, state)
            constants = {"NULL": 0, "true": 1, "false": 0}
            return [(state, constants.get(node.name, state.env.get(node.name, ("symbol", node.name))))]
        if isinstance(node, c_ast.Constant):
            if node.type in {"int", "unsigned int", "long int", "unsigned long int"}:
                spelling = re.sub(r"[uUlL]+$", "", node.value)
                try:
                    value = int(spelling, 0) if spelling != "0" else 0
                except ValueError:
                    self.fail("unsupported integer literal")
                return [(state, value)]
            return [(state, ("literal", node.type, node.value))]
        if isinstance(node, c_ast.Cast):
            return self.evaluate(node.expr, state)
        if isinstance(node, c_ast.FuncCall):
            return self.call(node, state)
        if isinstance(node, c_ast.UnaryOp):
            if node.op == "sizeof":
                # sizeof's operand is unevaluated in this non-VLA protocol.
                if any(isinstance(child, c_ast.FuncCall) for child in _walk(node.expr)):
                    self.fail("call hidden inside sizeof")
                return [(state, ("size", _shape(node.expr)))]
            results = []
            for current, value in self.evaluate(node.expr, state):
                if node.op == "!":
                    truth = _truth(value)
                    results.extend([(current, int(not truth))] if truth is not None
                                   else [(current.fork(), 0), (current.fork(), 1)])
                elif node.op == "-":
                    if isinstance(value, int):
                        result = -value
                    elif value == ("symbol", "EAGAIN"):
                        result = _EAGAIN
                    else:
                        result = ("unary", "-", value)
                    results.append((current, result))
                elif node.op in {"&", "*", "+", "~"}:
                    results.append((current, ("unary", node.op, value)))
                elif node.op in {"p--", "--", "p++", "++"}:
                    if _root(node.expr) in {"policy", "fake_state"}:
                        self.fail("mutation of a borrowed alias")
                    results.append((current, ("unknown",)))
                else:
                    self.fail("unsupported unary operator " + node.op)
            return results
        if isinstance(node, (c_ast.StructRef, c_ast.ArrayRef)):
            self._check_reference(node, state)
            parts = [node.name]
            if isinstance(node, c_ast.ArrayRef):
                parts.append(node.subscript)
            states = [(state, ())]
            for part in parts:
                states = [(updated, values + (value,)) for previous, values in states
                          for updated, value in self.evaluate(part, previous)]
            return [(current, ("reference", _shape(node))) for current, _ in states]
        if isinstance(node, c_ast.BinaryOp):
            if node.op in {"&&", "||"}:
                results = []
                for current, condition in self.branches(node.left, state):
                    if (node.op == "&&" and not condition) or (node.op == "||" and condition):
                        results.append((current, int(condition)))
                    else:
                        results.extend((after, int(truth)) for after, truth in self.branches(node.right, current))
                return results
            results = []
            for left_state, left in self.evaluate(node.left, state):
                for right_state, right in self.evaluate(node.right, left_state):
                    value = ("binary", node.op, left, right)
                    if isinstance(left, int) and isinstance(right, int):
                        operators = {"==": lambda: left == right, "!=": lambda: left != right,
                                     "<": lambda: left < right, "<=": lambda: left <= right,
                                     ">": lambda: left > right, ">=": lambda: left >= right,
                                     "+": lambda: left + right, "-": lambda: left - right}
                        if node.op in operators:
                            value = int(operators[node.op]())
                    results.append((right_state, value))
            return results
        if isinstance(node, c_ast.Assignment):
            return self.assign(node.lvalue, node.rvalue, state, node.op)
        if isinstance(node, c_ast.ExprList):
            self.fail("comma expressions are outside the ownership protocol")
        self.fail("unsupported expression " + type(node).__name__)

    def branches(self, expression, state):
        results = []
        for current, value in self.evaluate(expression, state):
            truth = _truth(value)
            choices = (truth,) if truth is not None else (False, True)
            for choice in choices:
                branch = current.fork()
                if isinstance(expression, c_ast.ID) and truth is None:
                    branch.env[expression.name] = ("nonzero", expression.name) if choice else 0
                results.append((branch, choice))
        return results

    def assign(self, target, expression, state, operator="=", declaration=False):
        if operator != "=":
            self.fail("compound assignment is outside the ownership protocol")
        root = _root(target)
        if root == "policy" and not declaration:
            self.fail("borrowed policy alias reassigned")
        if root == "fake_state":
            if (self.mode not in {"get", "put"} or not self.legacy or not state.held
                    or not isinstance(target, c_ast.StructRef) or target.type != "."
                    or not _is_id(target.name, "fake_state")
                    or target.field.name not in {"policy", "initialized"}):
                self.fail("legacy alias written outside its owner helper")
        elif _mentions(expression, {"fake_state", "policy"}):
            # These known int-returning conversions consume a policy argument;
            # their scalar errno result does not alias that policy. call()
            # still verifies the held borrow, exact first argument and order,
            # and evaluates every argument (including nested side effects).
            # Pointer assignments, casts/derived policy references, unknown
            # calls, and void compute helpers retain the fail-closed gate.
            scalar_conversion = (
                isinstance(expression, c_ast.FuncCall)
                and _callee(expression.name) in _SCALAR_POLICY_HELPERS
                and _callee(expression.name) in self.expected_policy_calls
            )
            if not scalar_conversion:
                self.fail("borrowed policy/state escaped through an assignment")
        output = []
        for current, value in self.evaluate(expression, state):
            changed = current.fork()
            if root == "fake_state":
                if target.field.name == "policy":
                    expected = _POINTER if self.mode == "get" else 0
                    if value != expected:
                        self.fail("legacy policy binding/clear value changed")
                    changed.fake_bound = value == _POINTER
                else:
                    expected = 1 if self.mode == "get" else 0
                    if value != expected:
                        self.fail("legacy initialized binding/clear value changed")
                    changed.fake_initialized = bool(value)
            elif isinstance(target, c_ast.ID):
                changed.env[target.name] = value
            else:
                # Preserve side effects in subscript expressions, while
                # treating ordinary writes to buf/avd as ownership-neutral.
                for child in _walk(target):
                    if isinstance(child, c_ast.FuncCall):
                        self.fail("call in an assignment target")
            output.append((changed, value))
        return output

    def call(self, call, state):
        name, arguments = _callee(call.name), _args(call)
        acquisition = _BORROW if self.mode in {"get", "enable"} else _GET
        release = _RETURN if self.mode in {"put", "enable"} else _PUT
        if name in {_GET, _BORROW}:
            if name != acquisition or arguments or state.held or state.attempted:
                self.fail("invalid or repeated backup acquisition")
            if self.mode == "put":
                self.fail("put helper acquired another backup")
            held = state.fork(held=True, acquired=1, attempted=1,
                              fake_bound=self.legacy and self.mode == "reader",
                              fake_initialized=self.legacy and self.mode == "reader")
            missing = state.fork(attempted=1, null_get=True)
            return [(held, _POINTER), (missing, 0)]
        if name in {_PUT, _RETURN}:
            if name != release or arguments or not state.held or state.released:
                self.fail("unmatched or repeated backup return")
            if self.mode == "get":
                self.fail("get helper returned its lock early")
            if self.mode == "put" and (state.fake_bound or state.fake_initialized):
                self.fail("legacy alias not cleared before owner unlock")
            return [(state.fork(held=False, released=1, fake_bound=False,
                                fake_initialized=False), _VOID)]
        originals = {"orig_context_write", "orig_access_write", "original_setprocattr"}
        if name in originals:
            if state.held or state.null_get:
                self.fail("original called with a borrow or after NULL acquisition")
            expected = dict(zip(_READERS, ("orig_context_write", "orig_access_write", "original_setprocattr")))
            if name != expected.get(self.name):
                self.fail("wrong original function")
        elif name in self.expected_policy_calls:
            if not state.held or state.env.get("policy") != _POINTER or not arguments:
                self.fail("policy helper without a non-NULL held borrow")
            if self.legacy:
                if not _fake_address(arguments[0]) or not (state.fake_bound and state.fake_initialized):
                    self.fail("legacy helper bypassed bound fake_state")
            elif not _is_id(arguments[0], "policy"):
                self.fail("policy helper bypassed the borrowed policy")
            state = state.fork(policy_calls=state.policy_calls + (name,))
            if state.policy_calls != self.expected_policy_calls[:len(state.policy_calls)]:
                self.fail("policy helper order or multiplicity changed")
        else:
            known = {
                "likely", "unlikely", "current_uid", "current_sid", "avc_has_perm",
                "kzalloc", "kfree", "sscanf", "strlen", "strcmp", "scnprintf", "memcpy",
                "pr_err", "pr_warn", "pr_info", "find_kernel_symbol_exact", "ksu_patch_text",
                "ksu_lsm_hook", "hook_selinux_status_open", "ksu_selinux_hide_unhook",
            }
            if name not in known:
                self.fail("unknown helper " + name)
            if self.mode in {"get", "put"}:
                self.fail("unexpected helper inside get/put: " + name)
            if state.null_get and name not in {"pr_err", "pr_warn", "pr_info"}:
                self.fail("NULL acquisition continued into another helper")
            if any(_mentions(argument, {"policy", "fake_state"}) for argument in arguments):
                self.fail("borrowed policy/state escaped to " + name)
            hooks = {"ksu_patch_text", "ksu_lsm_hook", "hook_selinux_status_open", "ksu_selinux_hide_unhook"}
            if name in hooks:
                if self.mode != "enable" or state.held or state.acquired != 1 or state.released != 1:
                    self.fail("hooking/unhooking before availability borrow was returned")
                state = state.fork(hooked=state.hooked + 1)
        states = [(state, ())]
        for argument in arguments:
            states = [(after, values + (value,)) for before, values in states
                      for after, value in self.evaluate(argument, before)]
        if name in {"likely", "unlikely"}:
            if len(arguments) != 1:
                self.fail("branch hint arity changed")
            return [(current, values[0]) for current, values in states]
        return [(current, ("call", name)) for current, _ in states]

    def finish(self, state, value, implicit=False):
        if self.mode == "get":
            if not state.attempted:
                self.fail("get returned without consulting owner")
            if state.held:
                if (value != _POINTER or state.acquired != 1 or state.released
                        or state.fake_bound != self.legacy or state.fake_initialized != self.legacy):
                    self.fail("get did not return a held and correctly bound policy")
            elif not state.null_get or value != 0 or state.acquired or state.released:
                self.fail("get NULL path did not return unlocked NULL")
        else:
            if state.held or state.released != state.acquired or state.fake_bound or state.fake_initialized:
                self.fail("return/fallthrough leaked a borrow or legacy alias")
            if state.null_get and value != _EAGAIN:
                self.fail("NULL acquisition must return -EAGAIN")
            if self.mode in {"reader", "enable"} and implicit:
                self.fail("non-void function fell through")
            if self.mode == "put" and (state.acquired != 1 or state.released != 1):
                self.fail("put did not return exactly one existing borrow")
        self.terminals.append((state, value))

    def run(self, function):
        graph, labels, unresolved = {}, {}, []

        def emit(kind, node, successors=()):
            index = len(graph)
            graph[index] = [kind, node, successors]
            return index

        end = emit("end", None)

        def compile_statement(node, following):
            if node is None:
                return following
            if isinstance(node, c_ast.Compound):
                for item in reversed(node.block_items or []):
                    following = compile_statement(item, following)
                return following
            if isinstance(node, c_ast.If):
                yes = compile_statement(node.iftrue, following)
                no = compile_statement(node.iffalse, following)
                return emit("if", node.cond, (yes, no))
            if isinstance(node, c_ast.Label):
                if node.name in labels:
                    self.fail("duplicate label " + node.name)
                target = compile_statement(node.stmt, following)
                labels[node.name] = target
                return target
            if isinstance(node, c_ast.Goto):
                instruction = emit("goto", node)
                unresolved.append((instruction, node.name))
                return instruction
            if isinstance(node, c_ast.Return):
                return emit("return", node.expr)
            if isinstance(node, (c_ast.Decl, c_ast.Assignment, c_ast.FuncCall,
                                 c_ast.UnaryOp, c_ast.EmptyStatement)):
                return emit("statement", node, (following,))
            self.fail("unsupported statement " + type(node).__name__)

        entry = compile_statement(function.body, end)
        for instruction, label in unresolved:
            if label not in labels:
                self.fail("goto has no local label: " + label)
            graph[instruction][2] = (labels[label],)
        initial = _State()
        if self.mode == "put":
            initial = _State(held=True, acquired=1, attempted=1,
                             fake_bound=self.legacy, fake_initialized=self.legacy)
        work = [(entry, initial, frozenset())]
        steps = 0
        while work:
            instruction, state, seen = work.pop()
            steps += 1
            if steps > 4096:
                self.fail("path bound exceeded")
            if instruction in seen:
                self.fail("control-flow cycle is outside the checked protocol")
            seen = seen | {instruction}
            kind, node, successors = graph[instruction]
            if kind == "end":
                self.finish(state, _VOID, implicit=True)
            elif kind == "goto":
                work.append((successors[0], state, seen))
            elif kind == "if":
                work.extend((successors[0 if truth else 1], after, seen)
                            for after, truth in self.branches(node, state))
            elif kind == "return":
                for after, value in self.evaluate(node, state):
                    self.finish(after, value)
            else:
                if isinstance(node, c_ast.Decl):
                    if node.name is None:
                        self.fail("anonymous declaration")
                    if node.init is None:
                        results = [(state, _VOID)]
                    else:
                        results = self.assign(c_ast.ID(node.name), node.init, state, declaration=True)
                elif isinstance(node, c_ast.EmptyStatement):
                    results = [(state, _VOID)]
                else:
                    results = self.evaluate(node, state)
                work.extend((successors[0], after, seen) for after, _ in results)
        if not self.terminals:
            self.fail("no terminal paths")
        if self.expected_policy_calls and not any(
                state.policy_calls == self.expected_policy_calls for state, _ in self.terminals):
            self.fail("no feasible path reaches the complete policy operation")
        if self.mode == "enable" and not any(
                state.acquired == state.released == 1 and state.hooked and value == 0
                for state, value in self.terminals):
            self.fail("no released availability path reaches successful hooking")


def _acquisition_shape(function, acquisition, release):
    """Keep ownership effects out of unspecified C operand evaluation order."""
    parents = {id(child): node for node in _walk(function.body) for _, child in node.children()}
    calls = [node for node in _walk(function.body) if isinstance(node, c_ast.FuncCall)]
    acquisition_calls = [node for node in calls if _callee(node.name) == acquisition]
    release_calls = [node for node in calls if _callee(node.name) == release]
    if len(acquisition_calls) != 1 or len(release_calls) != 1:
        _fail(function.decl.name + ": expected one acquisition and one return site")
    acquire_parent = parents.get(id(acquisition_calls[0]))
    if (not isinstance(acquire_parent, c_ast.Decl) or acquire_parent.name != "policy"
            or acquire_parent.init is not acquisition_calls[0] or acquire_parent.storage):
        _fail(function.decl.name + ": acquisition must initialize its local policy owner")
    policy_declarations = [node for node in _walk(function.body)
                           if isinstance(node, c_ast.Decl) and node.name == "policy"]
    if len(policy_declarations) != 1:
        _fail(function.decl.name + ": policy alias has a shadow or duplicate declaration")
    if not isinstance(parents.get(id(release_calls[0])), (c_ast.Compound, c_ast.If, c_ast.Label)):
        _fail(function.decl.name + ": return must be a standalone statement")


def _helper_shape(function, helper, mode):
    calls = [node for node in _walk(function.body) if isinstance(node, c_ast.FuncCall)]
    if len(calls) != 1 or _callee(calls[0].name) != helper or _args(calls[0]):
        _fail(function.decl.name + ": unexpected owner helper calls")
    if mode == "get":
        declarations = [node for node in _walk(function.body) if isinstance(node, c_ast.Decl)
                        and node.name == "policy"]
        if len(declarations) != 1 or declarations[0].init is not calls[0]:
            _fail("get must initialize its local pointer from owner borrow")


def _signature(function, declaration):
    parsed = c_parser.CParser().parse(_PREAMBLE + declaration + " {}")
    expected = [node for node in parsed.ext if isinstance(node, c_ast.FuncDef)][0]
    if _shape(function.decl) != _shape(expected.decl):
        _fail(function.decl.name + ": ownership boundary signature changed")
    if any(isinstance(node, c_ast.Decl) and node.name == "fake_state"
           for node in _walk(function.body)):
        _fail(function.decl.name + ": local declaration shadows the private legacy state")


def _validate_private_state(source, legacy, susfs):
    identifiers = _ids(source)
    if "backup_sepolicy" in identifiers:
        _fail("hide source can access the raw backup owner")
    if susfs or not legacy:
        if "fake_state" in identifiers:
            _fail("legacy state leaked into an unsupported configuration")
        return
    masked = _without_comments(source)
    declarations = list(re.finditer(r"\bstatic\s+struct\s+selinux_state\s+fake_state\s*;", masked))
    if len(declarations) != 1:
        _fail("legacy fake_state must have one private zero-initialized declaration")
    spans = [(match.start(), match.end()) for match in declarations]
    for name in (_GET, _PUT) + _READERS:
        spans.extend((start, end) for start, end, _ in _definitions(source, name))
    for token in _TOKEN.finditer(masked):
        if token.group() == "fake_state" and not any(start <= token.start() < end for start, end in spans):
            _fail("legacy state has an untracked consumer or declaration")


def validate_readers(hide_source, hide_header, ksu_header):
    """Raise RuntimeError unless all four selected reader protocols are safe.

    Success returns None. This checks only private-backup access and the enable
    availability borrow; the caller must keep hook/module/status lifetime HOLD.
    """
    for label, source in (("hide source", hide_source), ("hide header", hide_header),
                          ("ksu header", ksu_header)):
        if "backup_sepolicy" in _ids(source):
            _fail(label + " exposes the raw backup owner")
    if "fake_state" in _ids(hide_header) or "fake_state" in _ids(ksu_header):
        _fail("public header exposes legacy fake_state")
    for version in ((6, 1, 57), (6, 6, 0)):
        for susfs in (False, True):
            selected = select_configuration(hide_source, version, susfs)
            legacy = version < (6, 6, 0)
            _validate_private_state(selected, legacy, susfs)
            enable = parse_function(selected, "ksu_selinux_hide_enable")
            _signature(enable, "static int ksu_selinux_hide_enable()")
            _acquisition_shape(enable, _BORROW, _RETURN)
            _Protocol(enable.decl.name, False, "enable").run(enable)
            if susfs:
                for name in (_GET, _PUT) + _READERS:
                    if _definitions(selected, name):
                        _fail(name + " compiled despite SUSFS reader exclusion")
                continue
            get, put = parse_function(selected, _GET), parse_function(selected, _PUT)
            _signature(get, "static struct selinux_policy *ksu_hide_policy_get(void)")
            _signature(put, "static void ksu_hide_policy_put(void)")
            _helper_shape(get, _BORROW, "get")
            _helper_shape(put, _RETURN, "put")
            _Protocol(_GET, legacy, "get").run(get)
            _Protocol(_PUT, legacy, "put").run(put)
            expected = {
                "my_write_context": ("security_context_to_sid", "security_sid_to_context"),
                "my_write_access": ("security_context_str_to_sid", "security_context_str_to_sid",
                                    "security_compute_av_user"),
                "my_setprocattr": ("security_context_to_sid",),
            }
            if not legacy:
                expected = {
                    "my_write_context": ("security_context_to_sid_with_policy", "security_sid_to_context_with_policy"),
                    "my_write_access": ("security_context_to_sid_with_policy", "security_context_to_sid_with_policy",
                                        "security_compute_av_user_with_policy"),
                    "my_setprocattr": ("security_context_to_sid_with_policy",),
                }
            for name in _READERS:
                function = parse_function(selected, name)
                signatures = {
                    "my_write_context": "static ssize_t my_write_context(struct file *file, char *buf, size_t size)",
                    "my_write_access": "static ssize_t my_write_access(struct file *file, char *buf, size_t size)",
                    "my_setprocattr": "static int my_setprocattr(const char *name, void *value, size_t size)",
                }
                _signature(function, signatures[name])
                _acquisition_shape(function, _GET, _PUT)
                calls = Counter(_callee(node.name) for node in _walk(function.body)
                                if isinstance(node, c_ast.FuncCall))
                for helper, count in Counter(expected[name]).items():
                    if calls[helper] != count:
                        _fail(name + ": policy helper inventory changed")
                _Protocol(name, legacy, "reader", expected[name]).run(function)
