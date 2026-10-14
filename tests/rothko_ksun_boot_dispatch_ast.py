"""Finite execution of the actual startup dispatch and common wrapper AST.

Models only path/argument admission and return/audit forwarding. It does not
model the old sucompat transaction, user access helpers or actual exec.
Unknown operations fail closed instead of silently acting as success.
"""
import re

from pycparser import c_ast

from rothko_ksun_g2_backup_reader_ast import parse_function
from rothko_ksun_g2_type_ast import _without_comments


def need(condition, message):
    if not condition:
        raise RuntimeError('boot dispatch AST: ' + message)


def configured(source, susfs, compat):
    """Select reviewed directives in the small extracted dispatch region."""
    active = True
    stack = []
    output = []
    values = {'CONFIG_KSU_SUSFS': susfs, 'CONFIG_COMPAT': compat}
    for line in _without_comments(source).splitlines(keepends=True):
        if not line.lstrip().startswith('#'):
            output.append(line if active else '\n')
            continue
        match = re.fullmatch(r'\s*#\s*(\w+)\s*(.*?)\s*', line)
        need(match, 'invalid directive')
        kind, arg = match.groups()
        if kind in ('ifdef', 'ifndef'):
            need(arg in values, 'unknown conditional: ' + arg)
            branch = values[arg] if kind == 'ifdef' else not values[arg]
            stack.append([active, branch, False])
            active = active and branch
        elif kind == 'else':
            need(not arg and stack and not stack[-1][2], 'invalid else')
            stack[-1][1] = not stack[-1][1]
            stack[-1][2] = True
            active = stack[-1][0] and stack[-1][1]
        elif kind == 'endif':
            need(not arg and stack, 'invalid endif')
            active = stack.pop()[0]
        else:
            raise RuntimeError('boot dispatch AST: unreviewed directive ' + kind)
        output.append('\n')
    need(not stack, 'unterminated config')
    return re.sub(r'\b__user\b', '', ''.join(output))


class Dispatch:
    def __init__(self, functions, stage=0, end=0, first=True, second=True,
                 uid=0, compat=False, argument='second_stage'):
        self.functions = functions
        self.stage = stage
        self.end = end
        self.keys = {'is_first_zygote': first,
                     'is_init_second_stage_not_executed': second}
        self.uid = uid
        self.compat = compat
        self.argument = argument
        self.calls = []
        self.depth = self.steps = 0
        self.forward = None

    def value(self, node, frame):
        if isinstance(node, c_ast.ID):
            if node.name in {'NULL', 'false', 'true', 'GFP_KERNEL'}:
                return {'NULL': 0, 'false': False, 'true': True, 'GFP_KERNEL': 16}[node.name]
            need(node.name in frame, 'uninitialized read: ' + node.name)
            return frame[node.name]
        if isinstance(node, c_ast.Constant):
            if node.type == 'string':
                return node.value[1:-1]
            need(node.type == 'int', 'unknown literal')
            return int(node.value, 0)
        if isinstance(node, c_ast.Cast):
            return self.value(node.expr, frame)
        if isinstance(node, c_ast.UnaryOp):
            if node.op == '&':
                need(isinstance(node.expr, c_ast.ID), 'unexpected address')
                return ('address', node.expr.name)
            if node.op == 'sizeof':
                need(isinstance(node.expr, c_ast.ID) and node.expr.name == 'buf', 'unknown size')
                return 16
            value = self.value(node.expr, frame)
            if node.op == '!':
                return not value
            if node.op == '*':
                if (isinstance(node.expr, c_ast.ID) and node.expr.name == 'argv'
                        and isinstance(value, dict) and set(value) == {'is_compat', 'ptr'}):
                    return value
                need(isinstance(value, tuple) and value[0] == 'filename_ref', 'bad filename dereference')
                return value[1]
            raise RuntimeError('boot dispatch AST: unknown unary op')
        if isinstance(node, c_ast.StructRef):
            value = self.value(node.name, frame)
            need(isinstance(value, dict) and node.field.name in value, 'invalid field')
            return value[node.field.name]
        if isinstance(node, c_ast.BinaryOp):
            left = self.value(node.left, frame)
            if node.op == '&&':
                return bool(left) and bool(self.value(node.right, frame))
            if node.op == '||':
                return bool(left) or bool(self.value(node.right, frame))
            need(node.op == '==', 'unexpected binary op')
            return left == self.value(node.right, frame)
        if isinstance(node, c_ast.FuncCall):
            need(isinstance(node.name, c_ast.ID), 'indirect call')
            name = node.name.name
            args = [self.value(n, frame) for n in (node.args.exprs if node.args else [])]
            if name in self.functions:
                return self.run(name, args)
            if name == 'unlikely':
                need(len(args) == 1, 'unlikely arity')
                return args[0]
            if name == 'IS_ERR_OR_NULL':
                need(len(args) == 1, 'filename guard arity')
                return not args[0] or args[0] == ('error',)
            if name == 'static_branch_unlikely':
                need(len(args) == 1 and args[0][0] == 'address', 'key arity')
                need(args[0][1] in self.keys, 'unknown key')
                return self.keys[args[0][1]]
            if name == 'strcmp':
                need(len(args) == 2, 'path comparison arity')
                return int(args[0] != args[1])
            if name == 'check_argv':
                need(len(args) == 5 and args[0] and args[1] == 1 and args[4] == 16,
                     'argument matching contract')
                return self.argument == args[2]
            if name == 'ksu_run_boot_stage':
                need(len(args) == 1 and type(args[0]) is bool, 'stage selection')
                self.calls.append(('stage', args[0]))
                return self.stage
            if name == 'current_euid':
                need(not args, 'uid arity')
                return {'val': self.uid}
            if name == 'ksu_sulog_capture_root_execve_kernel':
                need(len(args) == 3 and args[0] == self.forward[1][1]['name']
                     and args[1] == ('native_argv',) and args[2] == 16 and not self.compat,
                     'logger used non-native layout')
                self.calls.append(('audit_capture',))
                return ('pending',)
            if name == 'ksu_sulog_emit_pending':
                need(args == [('pending',), 0, 16], 'audit completion changed')
                self.calls.append(('audit_emit',))
                return None
            if name == 'ksu_handle_execveat_sucompat':
                need(args == self.forward, 'sucompat arguments not preserved')
                self.calls.append(('sucompat',))
                return self.end
            raise RuntimeError('boot dispatch AST: unknown call ' + name)
        raise RuntimeError('boot dispatch AST: unknown expression ' + type(node).__name__)

    def execute(self, node, frame):
        self.steps += 1
        need(self.steps < 500, 'step bound')
        if node is None:
            return None
        if isinstance(node, c_ast.Compound):
            for child in node.block_items or []:
                result = self.execute(child, frame)
                if result is not None:
                    return result
        elif isinstance(node, c_ast.Decl):
            if node.init is not None:
                frame[node.name] = self.value(node.init, frame)
            elif isinstance(node.type, c_ast.ArrayDecl):
                frame[node.name] = ('buffer',)
        elif isinstance(node, c_ast.If):
            return self.execute(node.iftrue if self.value(node.cond, frame) else node.iffalse, frame)
        elif isinstance(node, c_ast.Assignment):
            need(node.op == '=' and isinstance(node.lvalue, c_ast.ID), 'unexpected output write')
            frame[node.lvalue.name] = self.value(node.rvalue, frame)
        elif isinstance(node, c_ast.Return):
            return ('return', self.value(node.expr, frame))
        elif isinstance(node, c_ast.FuncCall):
            self.value(node, frame)
        else:
            raise RuntimeError('boot dispatch AST: unknown statement ' + type(node).__name__)
        return None

    def run(self, name, args):
        self.depth += 1
        need(self.depth <= 4, 'call depth bound')
        function = self.functions[name]
        params = function.decl.type.args.params
        need(len(params) == len(args), 'function arity')
        result = self.execute(function.body, dict(zip((p.name for p in params), args)))
        self.depth -= 1
        need(result is not None and result[0] == 'return', 'missing dispatch status')
        return result[1]


def validate_dispatch(runtime_region, wrapper_region, susfs, compat):
    runtime = configured(runtime_region, susfs, compat)
    names = ['ksu_handle_execveat_ksud_path', 'ksu_handle_execveat_ksud']
    functions = {n: parse_function(runtime, n) for n in names}
    if susfs:
        functions['ksu_handle_execveat'] = parse_function(configured(wrapper_region, True, compat), 'ksu_handle_execveat')
    count = 0
    cases = [('/system/bin/init', 'second_stage', False),
             ('/system/bin/app_process', '-Xzygote', True),
             ('/system/bin/app_process32', '-Xzygote', True),
             ('/system/bin/app_process64', '-Xzygote', True),
             ('/system/bin/initx', 'second_stage', None),
             ('/system/bin/app_process_extra', '-Xzygote', None),
             ('/system/bin/init', 'wrong', None),
             ('/system/bin/sh', 'second_stage', None)]
    for path, argument, stage in cases:
        for first, second in ((True, True), (True, False), (False, False)):
            for result in (0, -5, -11, -108, -257):
                argv = {'is_compat': compat, 'ptr': {'native': ('native_argv',)}}
                args = [1, ('filename_ref', {'name': path}), argv, ('envp',), 7]
                protocol = Dispatch(functions, result, -13, first, second, compat=compat, argument=argument)
                protocol.forward = args
                name = 'ksu_handle_execveat' if susfs else 'ksu_handle_execveat_ksud'
                actual = protocol.run(name, args if susfs else [path, argv])
                admitted = stage is not None and (first if stage else second)
                # Common wrapper stops invoking ksud after first-zygote completion.
                if susfs:
                    admitted = admitted and first
                expected_stage = [('stage', stage)] if admitted else []
                stages = [c for c in protocol.calls if c[0] == 'stage']
                need(stages == expected_stage, 'wrong/duplicate boot stage admission')
                expected_status = result if admitted and result else (-13 if susfs else 0)
                need(actual == expected_status, 'startup/sucompat status was swallowed')
                if admitted and result:
                    need(protocol.calls == expected_stage, 'failure continued to success audit/sucompat')
                elif susfs:
                    expected = expected_stage + ([] if compat else [('audit_capture',), ('audit_emit',)]) + [('sucompat',)]
                    need(protocol.calls == expected, 'unexpected post-startup continuation')
                count += 1
    if susfs:
        for filename in (0, ('filename_ref', 0), ('filename_ref', ('error',))):
            protocol = Dispatch(functions)
            need(protocol.run('ksu_handle_execveat', [1, filename, 0, 0, 0]) == 0
                 and not protocol.calls, 'invalid filename had effects')
            count += 1
        protocol = Dispatch(functions)
        args = [1, ('filename_ref', {'name': '/system/bin/sh'}), 0, 0, 0]
        protocol.forward = args
        need(protocol.run('ksu_handle_execveat', args) == 0 and protocol.calls == [('sucompat',)],
             'NULL argv was audited/dereferenced')
        count += 1
        protocol = Dispatch(functions, uid=2000, compat=compat)
        argv = {'is_compat': compat, 'ptr': {'native': ('native_argv',)}}
        args = [1, ('filename_ref', {'name': '/system/bin/sh'}), argv, 0, 0]
        protocol.forward = args
        need(protocol.run('ksu_handle_execveat', args) == 0 and protocol.calls == [('sucompat',)],
             'non-root exec reached root audit')
        count += 1
    return count
