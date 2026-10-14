#!/usr/bin/env python3
"""Focused ADB precommit/late-load admission checks; no kernel build."""
from pathlib import Path
from collections import Counter
import re
import subprocess
import sys
import tempfile

from pycparser import c_ast, c_parser

from test_rothko_ksun_g2_backup_owner import NAMES as BASE_NAMES
from test_rothko_ksun_g5_composition import PIN, git, require
from rothko_ksun_g2_backup_reader_ast import parse_function
from rothko_ksun_g2_type_ast import _walk, _shape, _without_comments
from rothko_ksun_adb_transaction_ast import validate_transaction

NAME='adb-precommit-lateload-admission'
NAMES=BASE_NAMES+(NAME,)
ADB='kernel/feature/adb_root.c'
CORE='kernel/core/init.c'
SEL='kernel/selinux/selinux.c'
SEL_H='kernel/selinux/selinux.h'
ADB_H='kernel/feature/adb_root.h'
SU='kernel/feature/sucompat.c'
CHANGED={ADB,CORE,SEL,SEL_H,ADB_H,SU}


def configured(source,susfs,compat):
    """Select only the ADB source's two reviewed configuration symbols."""
    lines=[]; frames=[]; active=True
    values={'CONFIG_KSU_SUSFS':susfs,'CONFIG_COMPAT':compat}
    for line in _without_comments(source).splitlines(keepends=True):
        if not line.lstrip().startswith('#'):
            lines.append(line if active else '\n'); continue
        match=re.fullmatch(r'\s*#\s*(\w+)\s*(.*?)\s*',line)
        require(match,'invalid ADB directive')
        kind,arg=match.groups()
        if kind in ('ifdef','ifndef'):
            require(arg in values,'unknown ADB conditional')
            branch=values[arg] if kind=='ifdef' else not values[arg]
            frames.append([active,branch,False]);active=active and branch
        elif kind=='else':
            require(not arg and frames and not frames[-1][2],'invalid ADB else')
            frames[-1][1]=not frames[-1][1];frames[-1][2]=True
            active=frames[-1][0] and frames[-1][1]
        elif kind=='endif':
            require(not arg and frames,'invalid ADB endif');active=frames.pop()[0]
        elif kind=='include':
            require(re.fullmatch(r'[<"][^\n]+[>"]',arg),'invalid include')
        elif kind=='define':
            require(arg=='KSU_ADB_MAX_ENVS 4096','unreviewed ADB bound/macro')
        else:
            raise RuntimeError('unsupported ADB directive: '+kind)
        lines.append('\n')
    require(not frames,'unterminated ADB config')
    return re.sub(r'\b__user\b','', ''.join(lines))


def call_name(node):
    return node.name.name if isinstance(node,c_ast.FuncCall) and isinstance(node.name,c_ast.ID) else None


def expression(text):
    parser=c_parser.CParser()
    ast=parser.parse('void f(void) {'+text+';}')
    return ast.ext[0].body.block_items[0]


def same(actual,text):
    return _shape(actual)==_shape(expression(text))


def failed_guard(node,condition,errno=None):
    require(isinstance(node,c_ast.If) and same(node.cond,condition) and node.iffalse is None,
            'preload guard changed: '+condition)
    branch=node.iftrue.block_items if isinstance(node.iftrue,c_ast.Compound) else [node.iftrue]
    require(isinstance(branch[-1],c_ast.Goto) and branch[-1].name=='out_free','failure does not exit staging')
    if errno:
        require(len(branch)==2 and same(branch[0],'ret = -'+errno),'staging errno lost')
    else:
        require(len(branch)==1,'bound failure changes ownership/status')


def validate_builder(source):
    text=configured(source,True,True)
    function=parse_function(text,'prepare_ld_preload')
    items=function.body.block_items
    calls=[n for n in _walk(function.body) if isinstance(n,c_ast.FuncCall)]
    alloc=[n for n in calls if call_name(n)=='kcalloc']
    require(len(alloc)==1 and same(alloc[0],'kcalloc(KSU_ADB_MAX_ENVS + 3, sizeof(unsigned long), GFP_KERNEL)'),
            'bounded native env allocation changed')
    allocation_positions=[i for i,n in enumerate(items) if isinstance(n,c_ast.Assignment)
                          and n.rvalue is alloc[0]]
    require(len(allocation_positions)==1,'one local staged allocation')
    allocation_guard=items[allocation_positions[0]+1]
    require(isinstance(allocation_guard,c_ast.If) and same(allocation_guard.cond,'!tmp_env_p')
            and same(allocation_guard.iftrue,'return -ENOMEM') and allocation_guard.iffalse is None,
            'allocation failure must return before frame use')
    statuses=[n for n in _walk(function.body) if isinstance(n,c_ast.Decl) and n.name=='ret']
    require(len(statuses)==1 and same(statuses[0].init,'-E2BIG'),'bound failures must default to E2BIG')
    status_writes=[n for n in _walk(function.body) if isinstance(n,c_ast.Assignment)
                   and isinstance(n.lvalue,c_ast.ID) and n.lvalue.name=='ret']
    require(len(status_writes)==3 and sum(same(n.rvalue,'0') for n in status_writes)==1
            and sum(same(n.rvalue,'-EFAULT') for n in status_writes)==2,'staging status can be overwritten outside checked exits')
    loops=[n for n in _walk(function.body) if isinstance(n,c_ast.For)]
    require(len(loops)==1,'one bounded env scan')
    scan=loops[0]
    require(same(scan.init,'env_count = 0') and same(scan.cond,'envp && env_count <= KSU_ADB_MAX_ENVS')
            and same(scan.next,'env_count++'),'NULL/env-count scan bound changed')
    body=scan.stmt.block_items
    failed_guard(body[0],'check_add_overflow(envp, env_count * sizeof(unsigned long), &entry_addr)')
    # Parser needs __user stripped but retains the pointed-to native integer type.
    failed_guard(body[1],'get_user(tmp_env_p[env_count], (unsigned long *)entry_addr)','EFAULT')
    terminator=body[2]
    require(isinstance(terminator,c_ast.If) and same(terminator.cond,'!tmp_env_p[env_count]')
            and isinstance(terminator.iftrue,c_ast.Break) and terminator.iffalse is None,'NULL terminator not honored')
    scan_index=items.index(scan)
    failed_guard(items[scan_index+1],'env_count > KSU_ADB_MAX_ENVS')
    guards=('stackp < sizeof(kLdPreload)','stackp < sizeof(kLdLibraryPath)','stackp < total_size')
    aligns=('ld_preload_p = stackp = ALIGN_DOWN(stackp - sizeof(kLdPreload), 16)',
            'ld_library_path_p = stackp = ALIGN_DOWN(stackp - sizeof(kLdLibraryPath), 16)',
            'stackp = ALIGN_DOWN(stackp - total_size, 16)')
    indices=[]
    for guard,align in zip(guards,aligns):
        found=[i for i,n in enumerate(items) if isinstance(n,c_ast.If) and same(n.cond,guard)]
        require(len(found)==1,'missing subtraction guard: '+guard)
        index=found[0];failed_guard(items[index],guard)
        require(same(items[index+1],align),'subtraction/alignment is not guarded')
        indices.append(index)
    require(indices==sorted(indices) and scan_index<indices[0],'frame is staged before the bounded scan')
    require(any(same(n,'total_size = env_count * sizeof(unsigned long)') for n in items), 'native vector size changed')
    for fragment in ('tmp_env_p[env_count++] = ld_preload_p',
                     'tmp_env_p[env_count++] = ld_library_path_p','tmp_env_p[env_count++] = 0'):
        require(sum(same(n,fragment) for n in items)==1,'appended environment entries changed')
    copies=[n for n in calls if call_name(n)=='copy_to_user']
    require(len(copies)==3,'every staged user copy must be checked')
    copy_gates=[(i,n) for i,n in enumerate(items) if isinstance(n,c_ast.If)
                and any(call_name(x)=='copy_to_user' for x in _walk(n.cond))]
    require(len(copy_gates)==1,'one complete checked staging gate')
    copy_index,copy_gate=copy_gates[0]
    condition=('copy_to_user((void *)ld_preload_p, kLdPreload, sizeof(kLdPreload)) || '
               'copy_to_user((void *)ld_library_path_p, kLdLibraryPath, sizeof(kLdLibraryPath)) || '
               'copy_to_user((void *)stackp, tmp_env_p, total_size)')
    failed_guard(copy_gate,condition,'EFAULT')
    outputs=[i for i,n in enumerate(items) if same(n,'*new_envp = stackp')]
    require(outputs==[copy_index+1] and same(items[copy_index+2],'ret = 0'), 'preload output exposed before all copies')
    require(indices[-1]<copy_index,'vector subtraction not checked before usercopy')
    tail=items[copy_index+3:]
    require(len(tail)==2 and isinstance(tail[0],c_ast.Label) and tail[0].name=='out_free'
            and same(tail[0].stmt,'kfree(tmp_env_p)') and same(tail[1],'return ret'),'staged heap cleanup/status changed')
    require(Counter(call_name(n) for n in calls)==Counter({'kcalloc':1,'untagged_addr':1,'check_add_overflow':1,
            'get_user':1,'ALIGN_DOWN':3,'copy_to_user':3,'kfree':1}),
            'builder gained a commit/publication/unknown helper')


def validate_admission(core):
    masked=_without_comments(core)
    start=masked.index('int __init kernelsu_init(void)')
    opening=masked.index('{',start)
    end=masked.index('#ifdef CONFIG_KSU_SUSFS',opening)
    prefix=masked[opening+1:end].strip()
    require(prefix.startswith('#ifdef MODULE\n') and prefix.endswith('#endif'),'late-load guard must precede every subsystem')
    body=prefix[len('#ifdef MODULE\n'):-len('#endif')].strip()
    function=parse_function('int kernelsu_init(void) {'+body+'}','kernelsu_init')
    nodes=function.body.block_items
    require(len(nodes)==1 and isinstance(nodes[0],c_ast.If) and same(nodes[0].cond,'current->pid != 1')
            and nodes[0].iffalse is None and isinstance(nodes[0].iftrue,c_ast.Return)
            and same(nodes[0].iftrue,'return -EOPNOTSUPP'),'unsupported late-load has side effects or is admitted')


def contract(src):
    require('escape_to_root_for_adb_root' not in src[ADB]+src[SEL]+src[SEL_H],'old committing ADB helper retained')
    require('escape_with_root_profile' not in src[ADB],'second credential transaction retained')
    require('ksu_prepare_adb_root_cred(struct cred **out);' in src[SEL_H],'prepared-credential API declaration missing')
    require('envp_user_ptr, bool is_compat);' in src[ADB_H],'SUSFS prototype loses ABI flag')
    require(src[SU].count('ptr.compat, true);')==1 and src[SU].count('ptr.native, false);')==2,
            'typed COMPAT/native caller routing changed')
    validate_builder(src[ADB]);validate_admission(src[CORE])
    count=0
    for susfs in (False,True):
        for compat in (False,True):
            count+=validate_transaction(src[SEL],configured(src[ADB],susfs,compat),susfs,compat)
    return count


def rejected_apply(root,patch):
    r=subprocess.run(['git','apply','--check','--whitespace=error',str(patch)],cwd=root,capture_output=True,timeout=30)
    require(r.returncode!=0,'missing dependency/duplicate accepted')


def main():
    require(len(sys.argv)==2,'usage: test_rothko_ksun_adb_startup.py PINNED_KSUN')
    upstream=Path(sys.argv[1]).resolve();require(git(upstream,'rev-parse','HEAD').decode().strip()==PIN,'pin mismatch')
    repo=Path(__file__).resolve().parents[1]
    patches=[(n,(repo/'patches'/('rothko-ksun-'+n+'-candidate.patch')).read_bytes().replace(b'\r\n',b'\n')) for n in NAMES]
    paths=set()
    for _,data in patches:paths.update(re.findall(r'^--- a/(.*)$',data.decode(),re.M))
    require(set(re.findall(r'^--- a/(.*)$',patches[-1][1].decode(),re.M))==CHANGED,'candidate scope changed')
    originals={p:git(upstream,'show',PIN+':'+p) for p in paths}
    with tempfile.TemporaryDirectory(prefix='rothko-adb-startup-') as td:
        root=Path(td);git(root,'init','-q');git(root,'config','core.autocrlf','false')
        for p,data in originals.items():
            out=root/p;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(data)
        candidate=root/(NAME+'.patch');candidate.write_bytes(patches[-1][1]);rejected_apply(root,candidate)
        applied=[];before=None
        for i,(name,data) in enumerate(patches):
            # sucompat ABI edits depend on the caller-status composition. The
            # later backup patch is independent, so do not invent a false dependency.
            if name=='su-escape-caller-status':rejected_apply(root,candidate)
            if i==len(BASE_NAMES):before={p:(root/p).read_bytes() for p in paths}
            p=root/(name+'.patch');p.write_bytes(data);flags=['--unidiff-zero'] if i==0 else []
            git(root,'apply','--check','--whitespace=error',*flags,str(p));git(root,'apply','--whitespace=error',*flags,str(p));applied.append((p,flags))
        require(all((root/p).read_bytes()==data for p,data in before.items() if p not in CHANGED),'unrelated preserved source changed')
        src={p:(root/p).read_text(encoding='utf-8') for p in CHANGED}
        scenarios=contract(src)
        print('PASS: strict 24-stage source composition;',len(paths)-len(CHANGED),'non-target files preserved')
        print('PASS:',scenarios,'credential/dispatcher scenarios; bounded native envp and early MODULE admission')
        mutations=(
            ('late-load admitted',CORE,'if (current->pid != 1)','if (false)'),
            ('side effect before late-load rejection',CORE,'#ifdef MODULE\n    /* No late-load','susfs_init();\n#ifdef MODULE\n    /* No late-load'),
            ('wrong late-load errno',CORE,'return -EOPNOTSUPP;','return 0;'),
            ('prepare commits too early',SEL,'    *out = cred;','    commit_creds(cred);\n    *out = cred;'),
            ('prepared credential leaked on failure',SEL,'    abort_creds(cred);\n    return ret;','    return ret;'),
            ('untrusted caller admitted',SEL,'!uid_eq(cred->euid, GLOBAL_ROOT_UID) || !is_init(cred)','false'),
            ('domain status dropped',SEL,'    if (ret)\n        goto out_abort;','    if (false)\n        goto out_abort;'),
            ('domain result not validated',SEL,'if (!is_task_ksu_domain(cred))','if (false)'),
            ('staging error committed',ADB,'    if (ret) {\n        abort_creds(cred);','    if (false) {\n        abort_creds(cred);'),
            ('staging abort omitted',ADB,'        abort_creds(cred);',''),
            ('commit duplicated',ADB,'    commit_creds(cred);','    commit_creds(cred);\n    commit_creds(cred);'),
            ('commit skipped',ADB,'    commit_creds(cred);',''),
            ('precommit output published',ADB,'    *new_envp = staged_envp;','    *new_envp = staged_envp;\n    prepare_ld_preload(envp, stackp, &staged_envp);'),
            ('env cap weakened',ADB,'#define KSU_ADB_MAX_ENVS 4096','#define KSU_ADB_MAX_ENVS 1048576'),
            ('allocation failure ignored',ADB,'    if (!tmp_env_p)\n        return -ENOMEM;',''),
            ('bound failure reports success',ADB,'    long ret = -E2BIG;','    long ret = 0;'),
            ('env loop unbounded',ADB,'envp && env_count <= KSU_ADB_MAX_ENVS','envp'),
            ('NULL envp dereferenced',ADB,'envp && env_count <= KSU_ADB_MAX_ENVS','env_count <= KSU_ADB_MAX_ENVS'),
            ('address overflow ignored',ADB,'if (check_add_overflow(envp, env_count * sizeof(unsigned long),\n                               &entry_addr))','if (false)'),
            ('get_user fault ignored',ADB,'if (get_user(tmp_env_p[env_count], (unsigned long __user *)entry_addr))','if (false)'),
            ('usercopy fault reported as success',ADB,'        ret = -EFAULT;\n        goto out_free;','        ret = 0;\n        goto out_free;'),
            ('vector terminator omitted',ADB,'    tmp_env_p[env_count++] = 0;',''),
            ('stack subtraction unchecked',ADB,'if (stackp < total_size)','if (false)'),
            ('preload frame leaked',ADB,'    kfree(tmp_env_p);',''),
            ('COMPAT allowed in SUSFS',ADB,'    if (is_compat)\n        return -EOPNOTSUPP;',''),
            ('COMPAT allowed in syscall bridge',ADB,'    if (in_compat_syscall())\n        return -EOPNOTSUPP;',''),
            ('typed COMPAT flag lost',SU,'ptr.compat, true);','ptr.compat, false);'),
        )
        for label,path,old,new in mutations:
            require(old in src[path],'missing mutation target: '+label)
            changed=dict(src);changed[path]=changed[path].replace(old,new,1)
            try:contract(changed)
            except (RuntimeError,AssertionError,ValueError,KeyError):pass
            else:raise RuntimeError('negative mutation accepted: '+label)
        print('PASS:',len(mutations),'transaction/bounds/admission negative mutations rejected')
        positive=dict(src);positive[ADB]=positive[ADB].replace('commit_creds(cred);','commit_creds /* single commit */ (cred);',1);contract(positive)
        rejected_apply(root,candidate)
        for p,flags in reversed(applied):
            git(root,'apply','--reverse','--check','--whitespace=error',*flags,str(p));git(root,'apply','--reverse','--whitespace=error',*flags,str(p))
        require(all((root/p).read_bytes()==data for p,data in originals.items()),'reverse byte mismatch')
        print('PASS: formatting control, dependency/duplicate rejection and exact restoration of',len(paths),'pinned files')
    print('SOURCE-ONLY PASS; COMPAT/late-load support, post-exec rollback and full startup/lifecycle integration remain HOLD')


if __name__=='__main__':main()
