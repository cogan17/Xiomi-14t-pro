#!/usr/bin/env python3
"""Focused boot-stage status composition and bounded source protocols; no build."""
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from pycparser import c_ast

from test_rothko_ksun_adb_startup import NAMES as BASE_NAMES, same
from test_rothko_ksun_g5_composition import PIN, git, require
from rothko_ksun_g2_backup_reader_ast import parse_function, _definitions
from rothko_ksun_g2_type_ast import _shape, _walk, _without_comments
from rothko_ksun_boot_dispatch_ast import configured, validate_dispatch
from rothko_ksun_boot_status_ast import validate_boot_status


NAME = 'boot-stage-status-propagation'
NAMES = BASE_NAMES + (NAME,)
CORE = 'kernel/core/init.c'
SEL = 'kernel/selinux/selinux.c'
SEL_H = 'kernel/selinux/selinux.h'
RUN = 'kernel/runtime/ksud_integration.c'
SU = 'kernel/feature/sucompat.c'
CHANGED = {CORE, SEL, SEL_H, RUN, SU}


def definition(source, name):
    # Find the lexical extent before selecting its internal CONFIG branches.
    # Preserve offsets, then return original directives for configured() to
    # validate. The shared parser deliberately rejects raw directives itself.
    source = _without_comments(source)
    discovery = re.sub(r'(?m)^[ \t]*#[^\n]*', lambda m: ' ' * len(m.group()), source)
    found = _definitions(discovery, name)
    require(len(found) == 1, 'one function expected: ' + name)
    start, end, _ = found[0]
    return source[start:end]


def region(runtime):
    start = runtime.index('static int ksu_run_boot_stage(')
    end = runtime.index('\nstatic ssize_t (*orig_read)', start)
    return start, end, runtime[start:end]


def validate_legacy_bridge(runtime):
    source = configured(definition(runtime, 'ksu_execve_hook_ksud_common'), False, False)
    function = parse_function(source, 'ksu_execve_hook_ksud_common')
    require(function.decl.type.type.type.names == ['void'], 'void adapter ABI changed')
    nodes = function.body.block_items
    call_nodes = [(i, n) for i, n in enumerate(nodes) if isinstance(n, c_ast.Assignment)
                  and same(n, 'ret = ksu_handle_execveat_ksud(path, &argv)')]
    require(len(call_nodes) == 1, 'legacy adapter loses internal status')
    index, _ = call_nodes[0]
    guard = nodes[index + 1]
    require(isinstance(guard, c_ast.If) and same(guard.cond, 'ret') and guard.iffalse is None
            and isinstance(guard.iftrue, c_ast.FuncCall) and guard.iftrue.name.name == 'pr_err'
            and any(isinstance(n, c_ast.ID) and n.name == 'ret' for n in _walk(guard.iftrue.args)),
            'void adapter must report captured startup error')
    bounded = [n for n in nodes if isinstance(n, c_ast.If) and same(n.cond, 'ret <= 0 || ret >= sizeof(path)')]
    require(len(bounded) == 1 and nodes.index(bounded[0]) < index
            and any(isinstance(n, c_ast.Return) for n in _walk(bounded[0].iftrue)),
            'truncated/failed path may reach exact string matching')
    for name in ('ksu_execve_hook_ksud', 'ksu_execveat_hook_ksud'):
        caller = parse_function(re.sub(r'\b__user\b', '', definition(runtime, name)), name)
        require(caller.decl.type.type.type.names == ['void'], 'public void bridge ABI changed')


def validate_guarded_core(core):
    # Late-load remains rejected by the separately validated entry guard. Keep
    # the dormant caller type-correct without enabling it or claiming unwind.
    gate = core[core.index('\tif (ksu_late_loaded) {'):]
    gate = gate[:gate.index('\n\t\tksu_allowlist_init();')]
    function = parse_function('int dormant(void) { int ksu_late_loaded; ' + gate + '\n} return 0; }', 'dormant')
    cache = [n for n in _walk(function) if isinstance(n, c_ast.Assignment) and same(n, 'sid_ret = cache_sid()')]
    require(len(cache) == 1, 'dormant caller ignores checked cache')
    guards = [n for n in _walk(function) if isinstance(n, c_ast.If) and same(n.cond, '!sid_ret')]
    require(len(guards) == 1 and same(guards[0].iftrue, 'cred_ret = setup_ksu_cred()'),
            'dormant caller sets READY after cache failure')
    escape = [n for n in _walk(function) if isinstance(n, c_ast.If)
              and same(n.cond, '!rules_ret && !sid_ret && !cred_ret')]
    require(len(escape) == 1 and any(isinstance(n, c_ast.FuncCall) and n.name.name == 'escape_to_root_for_init'
                                   for n in _walk(escape[0].iftrue)), 'dormant escape gate lost cache status')


def contract(src):
    require(re.search(r'\bint\s+cache_sid\s*\(\s*void\s*\)\s*;', src[SEL_H]), 'checked cache declaration missing')
    require('ksu_second_stage_attempted' not in _without_comments(src[RUN]), 'superseded atomic latch retained')
    for path, name in ((SEL, 'cache_sid'), (RUN, 'ksu_run_boot_stage')):
        function = parse_function(configured(definition(src[path], name), False, False), name)
        require(function.decl.type.type.type.names == ['int'], 'checked status has wrong return type')
    start, end, runtime_region = region(src[RUN])
    wrapper = definition(src[SU], 'ksu_handle_execveat')
    histories = dispatches = 0
    for susfs in (False, True):
        selected = src[RUN][:start] + configured(runtime_region, susfs, False) + src[RUN][end:]
        histories += validate_boot_status(selected, src[SEL], susfs)
        for compat in (False, True):
            dispatches += validate_dispatch(runtime_region, wrapper, susfs, compat)
    validate_legacy_bridge(src[RUN])
    validate_guarded_core(src[CORE])
    return histories, dispatches


def rejected_apply(root, patch):
    result = subprocess.run(['git', 'apply', '--check', '--whitespace=error', str(patch)],
                            cwd=root, capture_output=True, timeout=30)
    require(result.returncode != 0, 'missing dependency/duplicate accepted')


def main():
    require(len(sys.argv) == 2, 'usage: test_rothko_ksun_boot_status.py PINNED_KSUN')
    upstream = Path(sys.argv[1]).resolve()
    require(git(upstream, 'rev-parse', 'HEAD').decode().strip() == PIN, 'pin mismatch')
    repo = Path(__file__).resolve().parents[1]
    patches = [(name, (repo / 'patches' / ('rothko-ksun-' + name + '-candidate.patch')).read_bytes().replace(b'\r\n', b'\n')) for name in NAMES]
    paths = set()
    for _, data in patches:
        paths.update(re.findall(r'^--- a/(.*)$', data.decode(), re.M))
    require(set(re.findall(r'^--- a/(.*)$', patches[-1][1].decode(), re.M)) == CHANGED, 'candidate scope changed')
    originals = {p: git(upstream, 'show', PIN + ':' + p) for p in paths}
    with tempfile.TemporaryDirectory(prefix='rothko-boot-status-') as temp:
        root = Path(temp)
        git(root, 'init', '-q')
        git(root, 'config', 'core.autocrlf', 'false')
        for path, data in originals.items():
            out = root / path
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(data)
        candidate = root / (NAME + '.patch')
        candidate.write_bytes(patches[-1][1])
        rejected_apply(root, candidate)
        applied = []
        before = None
        for index, (name, data) in enumerate(patches):
            if name == 'g2-snapshot-replay-composable':
                rejected_apply(root, candidate)
            if index == len(BASE_NAMES):
                before = {p: (root / p).read_bytes() for p in paths}
            patch = root / (name + '.patch')
            patch.write_bytes(data)
            flags = ['--unidiff-zero'] if index == 0 else []
            git(root, 'apply', '--check', '--whitespace=error', *flags, str(patch))
            git(root, 'apply', '--whitespace=error', *flags, str(patch))
            applied.append((patch, flags))
        require(all((root / p).read_bytes() == data for p, data in before.items() if p not in CHANGED),
                'unrelated preserved source changed')
        src = {p: (root / p).read_text(encoding='utf-8') for p in CHANGED}
        core_boundary = '\tif (ksu_late_loaded) {'
        require(before[CORE].decode().split(core_boundary)[0] == src[CORE].split(core_boundary)[0],
                'existing init admission/registration changed')
        # Preserve validated routines embedded in changed files; do not rerun
        # their old green validators or claim broader semantics from this suite.
        preserved = 0
        for path, names in ((SEL, ('ksu_prepare_adb_root_cred',)),
                            (CORE, ('setup_ksu_cred', 'ksu_ready_cred_setup_status', 'ksu_borrow_ready_cred')),
                            (SU, ('ksu_handle_execveat_sucompat',))):
            for name in names:
                old = [item[2] for item in _definitions(before[path].decode(), name)]
                new = [item[2] for item in _definitions(src[path], name)]
                require(old and old == new, 'previously validated routine changed: ' + name)
                preserved += len(old)
        histories, dispatches = contract(src)
        print('PASS: strict 25-stage composition;', len(paths) - len(CHANGED), 'non-target files and', preserved, 'validated routine definitions preserved')
        print('PASS:', histories, 'boot/SID histories;', dispatches, 'dispatch cases across SUSFS/native/COMPAT selections')
        mutations = (
            ('owner lock missing', RUN, '    mutex_lock(&ksu_boot_stage_lock);', ''),
            ('owner unlock missing', RUN, '    mutex_unlock(&ksu_boot_stage_lock);', ''),
            ('failure errno cleared', RUN, '    ksu_boot_error = ret;', '    ksu_boot_error = 0;'),
            ('sticky failure bypassed', RUN, '    ret = ksu_boot_error;', '    ret = 0;'),
            ('prerequisite bypassed', RUN, 'if (!ksu_second_stage_done)', 'if (false)'),
            ('premature first-stage says success', RUN, 'ret = -EAGAIN;', 'ret = 0;'),
            ('first-stage replay', RUN, 'if (ksu_first_zygote_done)', 'if (false)'),
            ('second-stage replay', RUN, 'if (ksu_second_stage_done)', 'if (false)'),
            ('policy status swallowed', RUN, 'ret = apply_kernelsu_rules();', 'apply_kernelsu_rules();'),
            ('cache status swallowed', RUN, 'ret = cache_sid();', 'cache_sid();'),
            ('READY status swallowed', RUN, 'ret = setup_ksu_cred();', 'setup_ksu_cred();'),
            ('post-fs effect before readiness', RUN, '        ret = cache_sid();', '        on_post_fs_data();\n        ret = cache_sid();'),
            ('first completion missing', RUN, '        ksu_first_zygote_done = true;', ''),
            ('second key prematurely disabled', RUN, '        ret = apply_kernelsu_rules();', '        static_branch_disable(&is_init_second_stage_not_executed);\n        ret = apply_kernelsu_rules();'),
            ('first key never disabled', RUN, '        static_branch_disable(&is_first_zygote);', ''),
            ('nonSUSFS hook never stopped', RUN, '        ksu_stop_ksud_execve_hook();', ''),
            ('stage result swallowed', RUN, 'return ksu_run_boot_stage(false);', 'return 0;'),
            ('wrong zygote stage', RUN, 'return ksu_run_boot_stage(true);', 'return ksu_run_boot_stage(false);'),
            ('ABI-suffixed zygote lost', RUN, '!strcmp(path, "/system/bin/app_process64")', '!strcmp(path, "/system/bin/other")'),
            ('wrong argv selector', RUN, '"second_stage", buf', '"wrong", buf'),
            ('legacy status ignored', RUN, 'ret = ksu_handle_execveat_ksud(path, &argv);', 'ksu_handle_execveat_ksud(path, &argv);'),
            ('truncated path admitted', RUN, 'ret <= 0 || ret >= sizeof(path)', 'ret < 0'),
            ('common status swallowed', SU, '        if (ret)\n            return ret;', '        if (ret)\n            return 0;'),
            ('common stage result ignored', SU, 'ret = ksu_handle_execveat_ksud(fd, filename_ptr, argv, envp, flags);', 'ksu_handle_execveat_ksud(fd, filename_ptr, argv, envp, flags);\n        ret = 0;'),
            ('NULL argv audited', SU, 'current_euid().val == 0 && argv_ptr', 'current_euid().val == 0'),
            ('non-root exec audited', SU, 'current_euid().val == 0 && argv_ptr', 'true && argv_ptr'),
            ('COMPAT audited as native', SU, '&& !argv_ptr->is_compat', '&& true'),
            ('sucompat result swallowed', SU, 'return ksu_handle_execveat_sucompat(fd, filename_ptr, argv, envp,\n                        flags);', 'ksu_handle_execveat_sucompat(fd, filename_ptr, argv, envp, flags);\n    return 0;'),
            ('cache signature wrong', SEL_H, 'int cache_sid(void);', 'void cache_sid(void);'),
            ('lookup failure swallowed', SEL, 'pr_warn("Failed to cache kernel su domain SID: %d\\n", err);\n        return err;', 'pr_warn("Failed to cache kernel su domain SID: %d\\n", err);\n        return 0;'),
            ('zero SID accepted', SEL, 'if (!su_sid)', 'if (false)'),
            ('cache global used as private output', SEL, '&su_sid);', '&cached_su_sid);'),
            ('partial cache publication', SEL, '    if (!zygote_sid)', '    cached_su_sid = su_sid;\n    if (!zygote_sid)'),
            ('wrong cache publication', SEL, '    cached_init_sid = init_sid;', '    cached_init_sid = su_sid;'),
            ('dormant cache status ignored', CORE, 'sid_ret = cache_sid();', 'cache_sid();'),
            ('dormant READY after cache failure', CORE, 'if (!sid_ret)', 'if (true)'),
        )
        for label, path, old, new in mutations:
            require(old in src[path], 'missing negative target: ' + label)
            changed = dict(src)
            changed[path] = changed[path].replace(old, new, 1)
            try:
                contract(changed)
            except (RuntimeError, AssertionError, ValueError, KeyError):
                pass
            else:
                raise RuntimeError('negative mutation accepted: ' + label)
        print('PASS:', len(mutations), 'negative status/ownership/order mutations rejected')
        positive = dict(src)
        positive[RUN] = positive[RUN].replace('mutex_lock(&ksu_boot_stage_lock);', 'mutex_lock /* owner */ (&ksu_boot_stage_lock);', 1)
        contract(positive)
        rejected_apply(root, candidate)
        for patch, flags in reversed(applied):
            git(root, 'apply', '--reverse', '--check', '--whitespace=error', *flags, str(patch))
            git(root, 'apply', '--reverse', '--whitespace=error', *flags, str(patch))
        require(all((root / p).read_bytes() == data for p, data in originals.items()), 'reverse pinned-byte mismatch')
        print('PASS: formatting control, dependency/duplicate rejection and exact restoration of', len(paths), 'pinned files')
    print('SOURCE-ONLY PASS; no global READY revocation, boot rollback, runtime/compile or lifecycle proof')


if __name__ == '__main__':
    main()
