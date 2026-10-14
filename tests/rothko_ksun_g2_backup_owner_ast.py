"""Execute the small backup-owner C AST against a finite resource model.

Models allocation failures, publication, borrow exclusion, close and cleanup.
This is source protocol evidence, not a kernel scheduler or helper/runtime test.
"""
import copy
import re

from pycparser import c_ast, c_generator

from rothko_ksun_g2_backup_reader_ast import parse_function, select_configuration
from rothko_ksun_g2_type_ast import _without_comments, _walk


def need(value, message):
    if not value:
        raise RuntimeError('backup owner AST: ' + message)


class Returned(Exception):
    def __init__(self, value):
        self.value = value


class Jump(Exception):
    def __init__(self, label):
        self.label = label


class WouldBlock(RuntimeError):
    pass


class Owner:
    def __init__(self, functions, fault=None, closed=False):
        self.functions = functions
        self.fault = fault
        self.globals = {'backup_sepolicy': None, 'ksu_backup_closed': closed}
        self.locked = False
        self.heap = {}
        self.serial = 0
        self.lockdep = False

    def name(self, expression):
        return c_generator.CGenerator().visit(expression)

    def lookup(self, name, env):
        constants = {'NULL': None, 'true': True, 'false': False,
                     'ENOMEM': 12, 'ESHUTDOWN': 108, 'EALREADY': 114,
                     'GFP_KERNEL': 0}
        if name in env:
            need(env[name] != ('unset',), 'uninitialized owner read: ' + name)
            return env[name]
        if name in self.globals:
            return self.globals[name]
        if name in constants:
            return constants[name]
        raise RuntimeError('backup owner AST: unknown expression identifier ' + name)

    def allocated(self, kind, **fields):
        self.serial += 1
        key = kind + str(self.serial)
        self.heap[key] = dict(kind=kind, alive=True, published=False, **fields)
        return key

    def object(self, key, kind):
        need(key in self.heap and self.heap[key]['alive'], 'invalid or freed ' + kind)
        need(self.heap[key]['kind'] == kind, 'unexpected resource kind')
        return self.heap[key]

    def assign(self, target, value, env):
        if isinstance(target, c_ast.ID):
            key = target.name
            if key in self.globals:
                need(self.locked, 'owner publication/close without its mutex')
                if key == 'ksu_backup_closed':
                    need(value is True, 'closed admission must never reopen')
                elif value is not None:
                    need(not self.globals['ksu_backup_closed'], 'publication after close')
                    need(self.globals[key] is None, 'published owner overwritten')
                    obj = self.object(value, 'policy')
                    table = self.object(obj['sidtab'], 'sidtab')
                    need(table['initialized'] and not table['destroyed'],
                         'partially initialized/borrowed SID table published')
                    obj['published'] = True
                self.globals[key] = value
            else:
                env[key] = value
            return value
        if isinstance(target, c_ast.StructRef) and target.field.name == 'sidtab':
            obj = self.object(self.expr(target.name, env), 'policy')
            need(not obj['published'], 'SID owner changed after publication')
            obj['sidtab'] = value
            return value
        raise RuntimeError('backup owner AST: unsupported owner assignment')

    def expr(self, node, env):
        if node is None:
            return None
        if isinstance(node, c_ast.ID):
            return self.lookup(node.name, env)
        if isinstance(node, c_ast.Constant):
            need(node.type == 'int', 'unexpected constant')
            return int(node.value, 0)
        if isinstance(node, c_ast.UnaryOp):
            if node.op == '&':
                return 'address:' + self.name(node.expr)
            if node.op == 'sizeof':
                return 1
            value = self.expr(node.expr, env)
            if node.op == '!':
                return not value
            if node.op == '-':
                return -value
            raise RuntimeError('backup owner AST: unsupported unary operation')
        if isinstance(node, c_ast.BinaryOp):
            if node.op == '||':
                return bool(self.expr(node.left, env) or self.expr(node.right, env))
            if node.op == '&&':
                return bool(self.expr(node.left, env) and self.expr(node.right, env))
            raise RuntimeError('backup owner AST: unsupported binary operation')
        if isinstance(node, c_ast.TernaryOp):
            return self.expr(node.iftrue if self.expr(node.cond, env) else node.iffalse, env)
        if isinstance(node, c_ast.StructRef):
            need(node.field.name == 'sidtab', 'unexpected policy field read')
            return self.object(self.expr(node.name, env), 'policy')['sidtab']
        if isinstance(node, c_ast.Assignment):
            need(node.op == '=', 'compound owner assignment')
            return self.assign(node.lvalue, self.expr(node.rvalue, env), env)
        if isinstance(node, c_ast.FuncCall):
            need(isinstance(node.name, c_ast.ID), 'indirect owner call')
            name = node.name.name
            args = node.args.exprs if node.args else []
            if name == 'lockdep_assert_held':
                need(len(args) == 1 and self.name(args[0]) == '&selinux_state.policy_mutex',
                     'creation needs the live policy mutex')
                self.lockdep = True
                return 0
            values = [self.expr(arg, env) for arg in args]
            if name in self.functions:
                return self.run(name, values)
            if name == 'mutex_lock':
                need(values == ['address:ksu_backup_mutex'], 'unexpected mutex')
                if self.locked:
                    raise WouldBlock()
                self.locked = True
                return 0
            if name == 'mutex_unlock':
                need(values == ['address:ksu_backup_mutex'] and self.locked, 'unbalanced owner unlock')
                self.locked = False
                return 0
            if name == 'IS_ERR':
                return isinstance(values[0], tuple) and values[0][0] == 'error'
            if name == 'PTR_ERR':
                need(isinstance(values[0], tuple) and values[0][0] == 'error', 'lost clone errno')
                return values[0][1]
            if name == 'ksu_dup_sepolicy':
                need(values == ['live_policy'] and self.lockdep, 'unlocked or wrong policy snapshot')
                if self.fault == 'clone':
                    return ('error', -12)
                return self.allocated('policy', sidtab='live_sidtab')
            if name == 'kzalloc':
                need(len(args) == 2 and isinstance(args[0],c_ast.UnaryOp) and args[0].op=='sizeof'
                     and isinstance(args[0].expr,c_ast.UnaryOp) and args[0].expr.op=='*'
                     and isinstance(args[0].expr.expr,c_ast.ID) and args[0].expr.expr.name=='sidtab'
                     and isinstance(args[1],c_ast.ID) and args[1].name=='GFP_KERNEL',
                     'SID allocation must use the full pointed-to type and sleeping allocation flags')
                if self.fault == 'table':
                    return None
                return self.allocated('sidtab', initialized=False, destroyed=False)
            if name == 'policydb_load_isids':
                need(len(values) == 2 and values[0].startswith('address:backup->policydb'),
                     'initial SID load targets the wrong policy')
                table = self.object(values[1], 'sidtab')
                # On failure the kernel helper destroys its partial contents;
                # the caller still owns and must free the outer SID container.
                table['initialized'] = self.fault != 'isids'
                return -12 if self.fault == 'isids' else 0
            if name == 'sidtab_destroy':
                table = self.object(values[0], 'sidtab')
                need(table['initialized'] and not table['destroyed'], 'SID destruction before init or twice')
                parents = [obj for obj in self.heap.values() if obj['kind'] == 'policy'
                           and obj['alive'] and obj['sidtab'] == values[0]]
                for parent in parents:
                    if parent['published']:
                        need(self.locked and self.globals['ksu_backup_closed']
                             and self.globals['backup_sepolicy'] is None,
                             'published SID table freed before admission close/detach/drain')
                table['destroyed'] = True
                return 0
            if name == 'kfree':
                table = self.object(values[0], 'sidtab')
                need(not table['initialized'] or table['destroyed'], 'SID container freed before content destroy')
                table['alive'] = False
                return 0
            if name == 'ksu_destroy_sepolicy':
                policy = self.object(values[0], 'policy')
                if policy['published']:
                    need(self.locked and self.globals['ksu_backup_closed']
                         and self.globals['backup_sepolicy'] is None,
                         'published policy freed while visible or not drained')
                table = policy['sidtab']
                if table in self.heap:
                    need(not self.heap[table]['alive'], 'owned table leaked on clone destruction')
                else:
                    need(table == 'live_sidtab', 'unexpected borrowed table')
                policy['alive'] = False
                return 0
            raise RuntimeError('backup owner AST: unknown helper ' + name)
        raise RuntimeError('backup owner AST: unsupported expression ' + type(node).__name__)

    def stmt(self, node, env):
        if isinstance(node, c_ast.Decl):
            env[node.name] = self.expr(node.init, env) if node.init else ('unset',)
        elif isinstance(node, c_ast.Compound):
            for statement in node.block_items or []:
                self.stmt(statement, env)
        elif isinstance(node, c_ast.If):
            branch = node.iftrue if self.expr(node.cond, env) else node.iffalse
            if branch is not None:
                self.stmt(branch, env)
        elif isinstance(node, c_ast.Return):
            raise Returned(self.expr(node.expr, env))
        elif isinstance(node, c_ast.Goto):
            raise Jump(node.name)
        elif isinstance(node, c_ast.Label):
            self.stmt(node.stmt, env)
        elif isinstance(node, (c_ast.FuncCall, c_ast.Assignment)):
            self.expr(node, env)
        else:
            raise RuntimeError('backup owner AST: unsupported statement ' + type(node).__name__)

    def run(self, name, values=()):
        function = self.functions[name]
        params = function.decl.type.args.params
        names = [p.name for p in params if isinstance(p, c_ast.Decl)]
        need(len(names) == len(values), 'owner function argument mismatch')
        env = dict(zip(names, values))
        items = function.body.block_items or []
        labels = {node.name: i for i, node in enumerate(items) if isinstance(node, c_ast.Label)}
        pc = 0
        while pc < len(items):
            try:
                self.stmt(items[pc], env)
            except Returned as result:
                return result.value
            except Jump as jump:
                need(jump.label in labels, 'unresolved owner cleanup label')
                pc = labels[jump.label]
                continue
            pc += 1
        return None

    def clean(self):
        need(not self.locked, 'owner mutex retained at scenario exit')
        need(all(not obj['alive'] for obj in self.heap.values()), 'owned allocation leaked')


def validate_owner(rules_source, api_header):
    clean = _without_comments(rules_source)
    need(re.search(r'\bstatic\s+DEFINE_MUTEX\(ksu_backup_mutex\)\s*;', clean), 'private initialized mutex')
    need(re.search(r'\bstatic\s+struct selinux_policy \*backup_sepolicy\s*;', clean), 'raw backup owner must be private')
    need(re.search(r'\bstatic\s+bool ksu_backup_closed\s*;', clean), 'admission starts open once')
    for name in ('ksu_borrow_selinux_backup', 'ksu_return_selinux_backup', 'ksu_drop_selinux_backup'):
        need(api_header.count(name+'(void);') == 1, 'missing/duplicate owner API: ' + name)
    config = select_configuration(rules_source, (6, 1, 57), False)
    names = ('ksu_borrow_selinux_backup', 'ksu_return_selinux_backup',
             'ksu_drop_selinux_backup', 'ksu_create_selinux_backup', 'ksu_destroy_owned_backup')
    functions = {name: parse_function(config, name) for name in names}
    declarations = [n for n in _walk(functions['ksu_create_selinux_backup'].body)
                    if isinstance(n,c_ast.Decl) and n.name=='sidtab']
    need(len(declarations)==1, 'one SID container owner without shadowing')
    decl=declarations[0]
    need(isinstance(decl.type,c_ast.PtrDecl) and isinstance(decl.type.type,c_ast.TypeDecl)
         and isinstance(decl.type.type.type,c_ast.Struct) and decl.type.type.type.name=='sidtab',
         'SID owner must point to the actual SID table type')
    for fault in ('clone', 'table', 'isids'):
        world = Owner(functions, fault=fault)
        need(world.run('ksu_create_selinux_backup', ['live_policy']) == -12, 'failure errno lost: '+fault)
        need(world.globals['backup_sepolicy'] is None, 'failed construction exposed owner')
        world.clean()
    world = Owner(functions, closed=True)
    need(world.run('ksu_create_selinux_backup', ['live_policy']) == -108, 'publication admitted after close')
    world.clean()
    world = Owner(functions)
    need(world.run('ksu_borrow_selinux_backup') is None and not world.locked, 'NULL borrow retains mutex')
    need(world.run('ksu_create_selinux_backup', ['live_policy']) == 0, 'normal creation fails')
    published = world.globals['backup_sepolicy']
    need(published is not None and not world.locked, 'successful construction not published/unlocked')
    need(world.run('ksu_create_selinux_backup', ['live_policy']) == -114, 'duplicate owner admitted')
    need(world.globals['backup_sepolicy'] == published, 'duplicate attempt replaced original')
    need(world.run('ksu_borrow_selinux_backup') == published and world.locked, 'non-NULL borrow unprotected')
    before = copy.deepcopy((world.globals, world.heap))
    try:
        world.run('ksu_drop_selinux_backup')
    except WouldBlock:
        pass
    else:
        raise RuntimeError('backup owner AST: drop did not wait for borrower')
    need((world.globals, world.heap) == before, 'blocked drop mutated owner')
    world.run('ksu_return_selinux_backup')
    world.run('ksu_drop_selinux_backup')
    need(world.globals['backup_sepolicy'] is None and world.globals['ksu_backup_closed'], 'drop did not close/detach')
    need(world.run('ksu_borrow_selinux_backup') is None and not world.locked, 'borrow after drop admitted')
    world.run('ksu_drop_selinux_backup')
    world.clean()
    apply = parse_function(config, 'apply_kernelsu_rules')
    items = apply.body.block_items
    assignments = [(i,n) for i,n in enumerate(items) if isinstance(n,c_ast.Assignment)
                   and isinstance(n.rvalue,c_ast.FuncCall) and isinstance(n.rvalue.name,c_ast.ID)
                   and n.rvalue.name.name=='ksu_create_selinux_backup']
    need(len(assignments)==1, 'one owner creation in the selected startup transaction')
    index, assignment = assignments[0]
    need(isinstance(assignment.lvalue,c_ast.ID) and assignment.lvalue.name=='ret', 'creation status dropped')
    gate = items[index+1]
    need(isinstance(gate,c_ast.If) and isinstance(gate.cond,c_ast.ID) and gate.cond.name=='ret'
         and gate.iffalse is None, 'construction failure guard bypassed')
    need(isinstance(gate.iftrue,c_ast.Compound) and gate.iftrue.block_items,
         'construction failure needs an unconditional cleanup exit')
    final=gate.iftrue.block_items[-1]
    need(isinstance(final,c_ast.Goto) and final.name=='out_unlock',
         'construction failure must unconditionally exit before cloning/publication')
    need(not any(isinstance(n,c_ast.Assignment) for n in _walk(gate.iftrue)),
         'construction errno must be preserved on the failure exit')
    gotos=[n.name for n in _walk(gate.iftrue) if isinstance(n,c_ast.Goto)]
    need(gotos==['out_unlock'], 'creation failure continues to clone/publication')
    def live_mutex_call(node,name):
        if not isinstance(node,c_ast.FuncCall) or not isinstance(node.name,c_ast.ID) or node.name.name!=name:
            return False
        args=node.args.exprs if node.args else []
        return (len(args)==1 and isinstance(args[0],c_ast.UnaryOp) and args[0].op=='&'
                and isinstance(args[0].expr,c_ast.StructRef)
                and isinstance(args[0].expr.name,c_ast.ID) and args[0].expr.name.name=='selinux_state'
                and args[0].expr.field.name=='policy_mutex')
    prefix=c_ast.Compound(items[:index])
    locks=[n for n in _walk(prefix) if isinstance(n,c_ast.FuncCall)
           and isinstance(n.name,c_ast.ID) and n.name.name=='mutex_lock']
    need(len(locks)==1 and locks[0] in items[:index] and live_mutex_call(locks[0],'mutex_lock'),
         'constructor caller must hold the actual live policy mutex')
    need(not any(isinstance(n,c_ast.FuncCall) and isinstance(n.name,c_ast.ID)
                 and n.name.name=='mutex_unlock' for n in _walk(prefix)),
         'live policy mutex released before snapshot construction')
    unlocks=[n for n in _walk(apply.body) if live_mutex_call(n,'mutex_unlock')]
    need(len(unlocks)==1, 'one shared live policy mutex cleanup exit')
    calls=[n.name.name for n in _walk(apply.body) if isinstance(n,c_ast.FuncCall) and isinstance(n.name,c_ast.ID)]
    need(calls.index('mutex_lock') < calls.index('ksu_create_selinux_backup') < calls.index('ksu_dup_sepolicy')
         < calls.index('ksu_build_boot_policy') < calls.index('rcu_assign_pointer'), 'startup owner/gate order')
    return 9  # Three allocation failures plus close, NULL, normal, duplicate, drain and repeated drop.
