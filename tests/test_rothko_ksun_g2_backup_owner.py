#!/usr/bin/env python3
"""Focused backup lifetime contract; no kernel build or earlier green-suite rerun."""
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from pycparser import c_ast

from test_rothko_ksun_g2_checked_rules import NAMES as BASE_NAMES
from test_rothko_ksun_g5_composition import PIN, git, require
from rothko_ksun_g2_backup_owner_ast import validate_owner
from rothko_ksun_g2_backup_reader_ast import parse_function, select_configuration, validate_readers
from rothko_ksun_g2_type_ast import _shape

NAME = 'g2-backup-owner-borrow'
NAMES = BASE_NAMES + (NAME,)
OWNER = 'kernel/selinux/rules.c'
HIDE = 'kernel/feature/selinux_hide.c'
API = 'kernel/selinux/sepolicy.h'
HIDE_HEADER = 'kernel/feature/selinux_hide.h'
KSU_HEADER = 'kernel/include/ksu.h'
CHANGED = {OWNER, HIDE, API, HIDE_HEADER, KSU_HEADER}


def contract(src):
    scenarios = validate_owner(src[OWNER], src[API])
    validate_readers(src[HIDE], src[HIDE_HEADER], src[KSU_HEADER])
    for version in ((6, 1, 57), (6, 6, 0)):
        for susfs in (False, True):
            text = select_configuration(src[HIDE], version, susfs)
            exit_fn = parse_function(text, 'ksu_selinux_hide_exit')
            items = exit_fn.body.block_items
            positions = {}
            for i,node in enumerate(items):
                if not isinstance(node,c_ast.FuncCall) or not isinstance(node.name,c_ast.ID):
                    continue
                name=node.name.name
                if name=='ksu_drop_selinux_backup':
                    positions[name]=i
                elif name in ('mutex_lock','mutex_unlock'):
                    args=node.args.exprs if node.args else []
                    if (len(args)==1 and isinstance(args[0],c_ast.UnaryOp) and args[0].op=='&'
                            and isinstance(args[0].expr,c_ast.ID) and args[0].expr.name=='selinux_hide_mutex'):
                        positions[name]=i
            require(positions['mutex_lock'] < positions['ksu_drop_selinux_backup'] < positions['mutex_unlock'],
                    'exit must close/drain backup under hide mutex even when not running')
            unused = parse_function(text, 'ksu_selinux_hide_drop_backup_if_unused')
            stmts = unused.body.block_items
            gate = stmts[1]
            require(isinstance(gate,c_ast.If) and isinstance(gate.cond,c_ast.UnaryOp)
                    and gate.cond.op=='!' and isinstance(gate.cond.expr,c_ast.ID)
                    and gate.cond.expr.name=='ksu_selinux_hide_running' and gate.iffalse is None,
                    'active hide owner must not be dropped by unused cleanup')
            require(isinstance(gate.iftrue,c_ast.FuncCall) and isinstance(gate.iftrue.name,c_ast.ID)
                    and gate.iftrue.name.name=='ksu_drop_selinux_backup', 'unused path needs owner drain API')
    return scenarios


def rejected_apply(root, patch):
    result = subprocess.run(['git','apply','--check','--whitespace=error',str(patch)],
                            cwd=root,capture_output=True,timeout=30)
    require(result.returncode != 0, 'duplicate/prerequisite bypass accepted')


def main():
    require(len(sys.argv)==2, 'usage: test_rothko_ksun_g2_backup_owner.py PINNED_KSUN')
    upstream=Path(sys.argv[1]).resolve()
    require(git(upstream,'rev-parse','HEAD').decode().strip()==PIN, 'pin mismatch')
    repo=Path(__file__).resolve().parents[1]
    patches=[(n,(repo/'patches'/('rothko-ksun-'+n+'-candidate.patch')).read_bytes().replace(b'\r\n',b'\n')) for n in NAMES]
    paths=set()
    for _,data in patches:
        paths.update(re.findall(r'^--- a/(.*)$', data.decode(), re.M))
    require(set(re.findall(r'^--- a/(.*)$',patches[-1][1].decode(),re.M))==CHANGED, 'unexpected candidate scope')
    originals={p:git(upstream,'show',PIN+':'+p) for p in paths}
    with tempfile.TemporaryDirectory(prefix='rothko-g2-backup-') as td:
        root=Path(td)
        git(root,'init','-q')
        git(root,'config','core.autocrlf','false')
        for p,data in originals.items():
            dst=root/p
            dst.parent.mkdir(parents=True,exist_ok=True)
            dst.write_bytes(data)
        candidate=root/(NAME+'.patch')
        candidate.write_bytes(patches[-1][1])
        rejected_apply(root,candidate)
        applied=[]
        before=None
        for i,(name,data) in enumerate(patches):
            if i==len(BASE_NAMES)-1:
                rejected_apply(root,candidate)
            if i==len(BASE_NAMES):
                before={p:(root/p).read_bytes() for p in paths}
            patch=root/(name+'.patch')
            patch.write_bytes(data)
            flags=['--unidiff-zero'] if i==0 else []
            git(root,'apply','--check','--whitespace=error',*flags,str(patch))
            git(root,'apply','--whitespace=error',*flags,str(patch))
            applied.append((patch,flags))
        require(all((root/p).read_bytes()==data for p,data in before.items() if p not in CHANGED),
                'files outside owner/reader contract changed')
        src={p:(root/p).read_text(encoding='utf-8') for p in CHANGED}
        old_builder=parse_function(select_configuration(before[OWNER].decode(),(6,1,57),False),'ksu_build_boot_policy')
        new_builder=parse_function(select_configuration(src[OWNER],(6,1,57),False),'ksu_build_boot_policy')
        require(_shape(old_builder)==_shape(new_builder), 'validated 60-rule builder changed')
        scenarios=contract(src)
        print('PASS: strict 23-stage applicability;',len(paths)-len(CHANGED),'non-target files and rule builder preserved')
        print('PASS:',scenarios,'owner resource scenarios; reader CFG across four version/CONFIG combinations')
        mutations=(
            ('raw owner exported', OWNER, 'static struct selinux_policy *backup_sepolicy;', 'struct selinux_policy *backup_sepolicy;'),
            ('owner mutex missing', OWNER, 'static DEFINE_MUTEX(ksu_backup_mutex);', ''),
            ('successful borrow prematurely unlocks', OWNER, '    return backup_sepolicy;', '    mutex_unlock(&ksu_backup_mutex);\n    return backup_sepolicy;'),
            ('NULL borrow retains mutex', OWNER, '        mutex_unlock(&ksu_backup_mutex);\n        return NULL;', '        return NULL;'),
            ('return fails to unlock', OWNER, 'void ksu_return_selinux_backup(void)\n{\n    mutex_unlock(&ksu_backup_mutex);', 'void ksu_return_selinux_backup(void)\n{'),
            ('drop lacks drain', OWNER, '    mutex_lock(&ksu_backup_mutex);\n    /* Wait for borrowers', '    /* Wait for borrowers'),
            ('drop reopens admission', OWNER, '    ksu_backup_closed = true;', '    ksu_backup_closed = false;'),
            ('owner remains visible at free', OWNER, '    backup_sepolicy = NULL;', ''),
            ('SID destroy omitted', OWNER, '    sidtab_destroy(backup->sidtab);', ''),
            ('SID container leaked', OWNER, '    kfree(backup->sidtab);', ''),
            ('policy clone leaked', OWNER, '    ksu_destroy_sepolicy(backup);\n}', '}'),
            ('private table init bypassed', OWNER, '    ret = policydb_load_isids(&backup->policydb, sidtab);', '    ret = 0;'),
            ('SID ownership not transferred', OWNER, '    backup->sidtab = sidtab;', ''),
            ('late publication allowed after close', OWNER, 'if (ksu_backup_closed || backup_sepolicy)', 'if (backup_sepolicy)'),
            ('creation failure ignored by startup', OWNER, 'ret = ksu_create_selinux_backup(old_pol);\n    if (ret)', 'ret = ksu_create_selinux_backup(old_pol);\n    if (false)'),
            ('clone errno lost', OWNER, '        return PTR_ERR(backup);', '        return 0;'),
            ('SID container allocation undersized', OWNER, 'sidtab = kzalloc(sizeof(*sidtab), GFP_KERNEL);', 'sidtab = kzalloc(1, GFP_KERNEL);'),
            ('SID owner points to wrong type', OWNER, '    struct sidtab *sidtab;', '    char *sidtab;'),
            ('caller locks wrong policy mutex', OWNER, 'mutex_lock(&selinux_state.policy_mutex);', 'mutex_lock(&ksu_backup_mutex);'),
            ('caller releases policy mutex before constructor', OWNER, '    ret = ksu_create_selinux_backup(old_pol);', '    mutex_unlock(&selinux_state.policy_mutex);\n    ret = ksu_create_selinux_backup(old_pol);'),
            ('failure goto hidden in unreachable branch', OWNER, 'pr_err("KSUN: refusing policy update without initialized hide backup: %d\\n", ret);\n        goto out_unlock;', 'pr_err("KSUN: refusing policy update without initialized hide backup: %d\\n", ret);\n        if (false) goto out_unlock;'),
            ('startup erases construction errno', OWNER, 'pr_err("KSUN: refusing policy update without initialized hide backup: %d\\n", ret);\n        goto out_unlock;', 'pr_err("KSUN: refusing policy update without initialized hide backup: %d\\n", ret);\n        ret = 0;\n        goto out_unlock;'),
            ('legacy fake state exported', HIDE, 'static struct selinux_state fake_state;', 'struct selinux_state fake_state;'),
            ('legacy alias points elsewhere', HIDE, '    fake_state.policy = policy;', '    fake_state.policy = NULL;'),
            ('legacy alias not cleared', HIDE, '    fake_state.policy = NULL;', ''),
            ('legacy initialized not cleared', HIDE, '    fake_state.initialized = false;', ''),
            ('context borrow leaked', HIDE, '    kfree(canon);\n    ksu_hide_policy_put();', '    kfree(canon);'),
            ('access borrow leaked', HIDE, '    kfree(scon);\n    ksu_hide_policy_put();', '    kfree(scon);'),
            ('context releases before final policy use', HIDE, '    length = security_sid_to_context_with_policy(policy,', '    ksu_hide_policy_put();\n    length = security_sid_to_context_with_policy(policy,'),
            ('setprocattr releases after error return', HIDE, '        ksu_hide_policy_put();\n        if (error) {\n            return error;\n        }', '        if (error) {\n            return error;\n        }\n        ksu_hide_policy_put();'),
            ('reader skips acquire', HIDE, 'struct selinux_policy *policy = ksu_hide_policy_get();\n\n    if (!policy)', 'struct selinux_policy *policy = NULL;\n\n    if (!policy)'),
            ('NULL getter returns a fake pointer', HIDE, '    if (!policy)\n        return NULL;', '    if (!policy)\n        return (struct selinux_policy *)1;'),
            ('enable holds owner while hooking', HIDE, '    ksu_return_selinux_backup();\n\n#if LINUX_VERSION_CODE >=', '\n#if LINUX_VERSION_CODE >='),
            ('unused cleanup drops active owner', HIDE, '    if (!ksu_selinux_hide_running)\n        ksu_drop_selinux_backup();', '    if (ksu_selinux_hide_running)\n        ksu_drop_selinux_backup();'),
            ('exit omits owner drain', HIDE, '    ksu_drop_selinux_backup();\n    mutex_unlock(&selinux_hide_mutex);', '    mutex_unlock(&selinux_hide_mutex);'),
            ('raw backup external API restored', KSU_HEADER, 'extern bool ksu_no_custom_rc;', 'extern struct selinux_policy *backup_sepolicy;\nextern bool ksu_no_custom_rc;'),
            ('legacy alias external API restored', HIDE_HEADER, '#endif', 'extern struct selinux_state fake_state;\n#endif'),
            ('borrow API declaration removed', API, 'struct selinux_policy *ksu_borrow_selinux_backup(void);', ''),
        )
        for label,path,old,new in mutations:
            require(old in src[path], 'missing mutation target: '+label)
            changed=dict(src)
            changed[path]=changed[path].replace(old,new,1)
            try:
                contract(changed)
            except (RuntimeError,ValueError,AssertionError,KeyError):
                pass
            else:
                raise RuntimeError('negative mutation accepted: '+label)
        print('PASS:',len(mutations),'ownership/control-flow negative mutations rejected')
        positive=dict(src)
        positive[OWNER]=positive[OWNER].replace('backup_sepolicy = backup;', 'backup_sepolicy /* publish initialized owner */ = backup;',1)
        contract(positive)
        print('PASS: formatting/comment positive control')
        rejected_apply(root,candidate)
        for patch,flags in reversed(applied):
            git(root,'apply','--reverse','--check','--whitespace=error',*flags,str(patch))
            git(root,'apply','--reverse','--whitespace=error',*flags,str(patch))
        require(all((root/p).read_bytes()==data for p,data in originals.items()), 'reverse byte mismatch')
        print('PASS: prerequisite/duplicate rejection and exact restoration of',len(paths),'pinned files')
    print('SOURCE-ONLY PASS; startup/rollback, callback/original-function, status-page/VMA and module teardown remain HOLD')


if __name__=='__main__':
    main()
