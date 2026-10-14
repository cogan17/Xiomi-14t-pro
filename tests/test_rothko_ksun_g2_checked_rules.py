#!/usr/bin/env python3
"""G2 checked rules with AST ownership gates; isolated source, never runtime.

Requires pycparser. Reuses the validated prerequisite chain without rerunning
its earlier contract suites. The exhausted text ownership checker is replaced,
not retried: add_type is parsed and checked from staging through insert/abort.
"""
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from test_rothko_ksun_g2_snapshot_replay import NAMES as BASE_NAMES
from test_rothko_ksun_g5_composition import PIN, body, git, ordered, require
from rothko_ksun_g2_type_ast import validate_add_type

NAME = "g2-checked-rule-construction"
NAMES = BASE_NAMES + (NAME,)
CHANGED = {"kernel/selinux/rules.c", "kernel/selinux/sepolicy.c"}


def impl(text, signature):
    start = text.rindex(signature)
    opening = text.index("\n{", start)
    return text[start:text.index("\n}", opening) + 2]


def contract(src, expected_calls):
    rules, sepol = src["kernel/selinux/rules.c"], src["kernel/selinux/sepolicy.c"]
    boot = impl(rules, "static bool ksu_build_boot_policy(")
    guarded = re.findall(r"KSU_BOOT_RULE\((ksu_\w+\(db,.*\))\);", boot)
    require(guarded == expected_calls, "every pinned boot rule guarded in the original order")
    require(len(guarded) == 60, "pinned startup inventory changed")
    macro = rules[rules.index("#define KSU_BOOT_RULE(rule)"):rules.index("static bool ksu_build_boot_policy(")]
    ordered(macro, "if (!(rule))", 'pr_err("KernelSU initial rule failed:', "return false;")
    require(macro.count("(rule)") == 2, "rule macro must evaluate argument exactly once")
    require("#undef KSU_BOOT_RULE" in rules, "private boot macro scope")
    require(boot.rstrip().endswith("return true;\n}"), "successful builder return")
    require("if (db->policyvers >= POLICYDB_VERSION_XPERMS_IOCTL) {" in boot,
            "old-policy xperm admission unchanged")
    require(not re.search(r"\b(?:rcu_assign_pointer|ksu_destroy_sepolicy)\s*\(", boot),
            "builder must operate only on unpublished policydb")

    apply = body(rules, "int apply_kernelsu_rules(void)")
    ordered(apply, "pol = ksu_dup_sepolicy(", "if (IS_ERR(pol))", "goto out_unlock;",
            "db = &pol->policydb;", "if (!ksu_build_boot_policy(db)) {", "ret = -EIO;",
            "goto out_drop_new_policy;", "rcu_assign_pointer(selinux_state.policy, pol);",
            "synchronize_rcu();", "ksu_destroy_sepolicy(old_pol);")
    publication = apply[apply.index("rcu_assign_pointer(selinux_state.policy, pol);"):]
    ordered(publication, "susfs_set_batch_sid();", "goto out_unlock;", "out_drop_new_policy:",
            "ksu_destroy_sepolicy(pol);", "out_unlock:", "mutex_unlock(&selinux_state.policy_mutex);",
            "return ret;")
    require(apply.count("ksu_destroy_sepolicy(pol);") == 1, "one unpublished clone disposal")
    drop = apply[apply.index("out_drop_new_policy:"):apply.index("out_unlock:")]
    require("backup_sepolicy" not in drop and "sidtab" not in re.sub(r"/\*.*?\*/", "", drop, flags=re.S),
            "clone disposal must not free hide backup or shared SID table")
    require(apply.count("rcu_assign_pointer(selinux_state.policy, pol);") == 1,
            "one checked startup publication")

    validate_add_type(sepol)

    attr = impl(sepol, "static bool add_typeattribute_raw(")
    ordered(attr, "if (ebitmap_set_bit(sattr, attr->value - 1, 1))", "return false;",
            "if (ebitmap_set_bit(&e->names, type->value - 1, 1))", "return false;", "return true;")
    require("return add_typeattribute_raw(db, type_d, attr_d);" in impl(sepol, "static bool add_typeattribute("),
            "attribute wrapper must propagate status")
    state = impl(sepol, "static bool set_type_state(")
    wildcard = state[state.index("if (type_name == NULL)"):state.index("    } else {")]
    ordered(wildcard, "if (ebitmap_set_bit(&db->permissive_map, type->value, permissive)) {",
            "Could not set bit in permissive map", "return false;")

    raw = impl(sepol, "static bool add_xperm_rule_raw(")
    recursive = re.findall(r"if \(!add_xperm_rule_raw\(.*?\)\)\s*return false;", raw, flags=re.S)
    require(len(recursive) == 3, "all wildcard xperm recursion must propagate failure")
    require(re.search(r"if \(!node\) \{\s*pr_warn\([^\n]+\);\s*return false;", raw),
            "xperm node allocation failure must not report success")
    require(re.search(r"if \(!datum->u\.xperms\) \{\s*pr_err\([^\n]+\);\s*return false;", raw),
            "xperm payload allocation failure must not report success")
    ordered(raw, "get_avtab_node(db, &key, &xperms)",
            "datum->u.xperms->perms.p[i] &= ~xperms.perms.p[i];",
            "datum->u.xperms->perms.p[i] |= xperms.perms.p[i];", "return true;")
    require(raw.count("xperm_set(i, xperms.perms.p);") == 2
            and "xperm_clear(i, xperms.perms.p);" not in raw,
            "requested mask must be constructed before union/removal")
    require("#define xperm_set(x, p) (p[x >> 5] |= (1U << (x & 0x1f)))" in sepol,
            "bit 31 shift must be unsigned")
    wrapper = impl(sepol, "static bool add_xperm_rule(")
    require('if (sscanf(range, "%hx-%hx", &low, &high) != 2)' in wrapper,
            "range parse failure must propagate")
    require('if (sscanf(range, "%hx", &low) != 1)' in wrapper,
            "single-value parse failure must propagate")
    ordered(wrapper, "if (low > high)", "return false;",
            "return add_xperm_rule_raw(db, src, tgt, cls, low, high, effect, invert);")


def rejected_apply(root, patch):
    result = subprocess.run(["git", "apply", "--check", "--whitespace=error", str(patch)],
                            cwd=root, capture_output=True, timeout=30)
    require(result.returncode != 0, "duplicate/prerequisite bypass accepted")


def main():
    require(len(sys.argv) == 2, "usage: test_rothko_ksun_g2_checked_rules.py PINNED_KSUN")
    upstream = Path(sys.argv[1]).resolve()
    require(git(upstream, "rev-parse", "HEAD").decode().strip() == PIN, "pin mismatch")
    repo = Path(__file__).resolve().parents[1]
    patches = [(n, (repo / "patches" / ("rothko-ksun-" + n + "-candidate.patch"))
                .read_bytes().replace(b"\r\n", b"\n")) for n in NAMES]
    paths = set()
    for _, data in patches:
        paths.update(re.findall(r"^--- a/(.*)$", data.decode(), re.M))
    require(set(re.findall(r"^--- a/(.*)$", patches[-1][1].decode(), re.M)) == CHANGED,
            "candidate scope must be exactly the two policy construction files")
    originals = {p: git(upstream, "show", PIN + ":" + p) for p in paths}
    original = originals["kernel/selinux/rules.c"].decode()
    original_calls = original[original.index('    ksu_type(db, KERNEL_SU_DOMAIN, "domain");'):
                              original.index("    rcu_assign_pointer(selinux_state.policy, pol);")]
    expected_calls = re.findall(r"^\s+(ksu_\w+\(db,.*\));$", original_calls, re.M)
    with tempfile.TemporaryDirectory(prefix="rothko-g2-rules-") as td:
        root = Path(td)
        git(root, "init", "-q")
        git(root, "config", "core.autocrlf", "false")
        for p, data in originals.items():
            dst = root / p
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(data)
        new_patch = root / (NAME + ".patch")
        new_patch.write_bytes(patches[-1][1])
        rejected_apply(root, new_patch)
        applied = []
        base_bytes = None
        for i, (name, data) in enumerate(patches):
            if i == len(BASE_NAMES) - 1:
                rejected_apply(root, new_patch)
            if i == len(BASE_NAMES):
                base_bytes = {p: (root / p).read_bytes() for p in paths}
            patch = root / (name + ".patch")
            patch.write_bytes(data)
            flags = ["--unidiff-zero"] if i == 0 else []
            git(root, "apply", "--check", "--whitespace=error", *flags, str(patch))
            git(root, "apply", "--whitespace=error", *flags, str(patch))
            applied.append((patch, flags))
        require(all((root / p).read_bytes() == data for p, data in base_bytes.items() if p not in CHANGED),
                "preserved composition changed outside the new candidate")
        src = {p: (root / p).read_text(encoding="utf-8") for p in CHANGED}
        contract(src, expected_calls)
        print("PASS: strict 22-stage applicability; 60 original rule calls guarded; 12 other files preserved")
        rules_path, helper_path = "kernel/selinux/rules.c", "kernel/selinux/sepolicy.c"
        # Formatting/comments must not be the ownership boundary. Check the
        # actual C syntax, including line-splicing before comment recognition.
        formatted = src[helper_path].replace(
            "if (symtab_insert(&db->p_types, key, type))",
            "if ( /* transfer boundary */ symtab_insert ( &db->p_types, key, type ) )", 1)
        validate_add_type(formatted)
        key_stage = ("key = kstrdup(type_name, GFP_KERNEL);\n"
                     "    if (!key)\n        goto abort;")
        key_slot = "new_val_to_name_types[value - 1] = key;"
        mutations = (
            ("startup rule status dropped", rules_path,
             'KSU_BOOT_RULE(ksu_type(db, KERNEL_SU_DOMAIN, "domain"));',
             'ksu_type(db, KERNEL_SU_DOMAIN, "domain");'),
            ("builder failure reported as success", rules_path, "            return false; \\",
             "            return true; \\",),
            ("builder failure gate bypassed", rules_path, "if (!ksu_build_boot_policy(db))", "if (false)"),
            ("startup rule failure returns zero", rules_path, "ret = -EIO;", "ret = 0;"),
            ("unpublished clone leak", rules_path, "    ksu_destroy_sepolicy(pol);", ""),
            ("success falls into clone disposal", rules_path, "#endif\n    goto out_unlock;\n\nout_drop_new_policy:",
             "#endif\n\nout_drop_new_policy:"),
            ("borrowed SID table destroyed", rules_path, "    ksu_destroy_sepolicy(pol);",
             "    sidtab_destroy(pol->sidtab);\n    ksu_destroy_sepolicy(pol);"),
            ("type count published before staging", helper_path, "value = db->p_types.nprim + 1;",
             "value = ++db->p_types.nprim;"),
            ("moving realloc invalidates owned arrays", helper_path,
             "new_type_attr_map_array = kvcalloc(", "new_type_attr_map_array = ksu_kvrealloc("),
            ("new self bitmap failure ignored", helper_path,
             "if (ebitmap_set_bit(&new_type_attr_map_array[value - 1], value - 1, 1))", "if (false)"),
            ("role bitmap copy failure ignored", helper_path,
             "if (ebitmap_cpy(&new_role_types[i], &db->role_val_to_struct[i]->types) ||", "if (false ||"),
            ("fallible allocation after symbol transfer", helper_path,
             "old_type_attr_map_array = db->type_attr_map_array;",
             "key = kstrdup(type_name, GFP_KERNEL);\n    old_type_attr_map_array = db->type_attr_map_array;"),
            ("abort destroys existing bitmap", helper_path, "abort:\n    pr_err(",
             "abort:\n    ebitmap_destroy(&db->type_attr_map_array[0]);\n    pr_err("),
            ("array allocation failure ignored", helper_path, "if (!new_type_val_to_struct)", "if (false)"),
            ("attribute membership failure ignored", helper_path,
             "if (ebitmap_set_bit(sattr, attr->value - 1, 1))", "if (false)"),
            ("attribute constraint failure ignored", helper_path,
             "if (ebitmap_set_bit(&e->names, type->value - 1, 1))", "if (false)"),
            ("attribute wrapper drops status", helper_path, "return add_typeattribute_raw(db, type_d, attr_d);",
             "add_typeattribute_raw(db, type_d, attr_d);\n    return true;"),
            ("xperm source recursion drops error", helper_path,
             "if (!add_xperm_rule_raw(db, type, tgt, cls, low, high, effect,", "if (add_xperm_rule_raw(db, type, tgt, cls, low, high, effect,"),
            ("xperm target recursion drops error", helper_path,
             "if (!add_xperm_rule_raw(db, src, type, cls, low, high, effect,", "if (add_xperm_rule_raw(db, src, type, cls, low, high, effect,"),
            ("xperm class recursion drops error", helper_path,
             "if (!add_xperm_rule_raw(db, src, tgt,", "if (add_xperm_rule_raw(db, src, tgt,"),
            ("xperm allocation failure reports success", helper_path,
             'pr_warn("add_xperm_rule_raw cannot found node!\\n");\n            return false;',
             'pr_warn("add_xperm_rule_raw cannot found node!\\n");\n            return true;'),
            ("xperm payload failure reports success", helper_path,
             'pr_err("alloc xperms failed\\n");\n                return false;',
             'pr_err("alloc xperms failed\\n");\n                return true;'),
            ("xperm wrapper drops status", helper_path,
             "return add_xperm_rule_raw(db, src, tgt, cls, low, high, effect, invert);",
             "add_xperm_rule_raw(db, src, tgt, cls, low, high, effect, invert);\n    return true;"),
            ("range parse failure ignored", helper_path,
             'if (sscanf(range, "%hx-%hx", &low, &high) != 2)', "if (false)"),
            ("reversed range admitted", helper_path, "if (low > high)", "if (false)"),
            ("existing xperm bits overwritten", helper_path,
             "datum->u.xperms->perms.p[i] |= xperms.perms.p[i];",
             "datum->u.xperms->perms.p[i] = xperms.perms.p[i];"),
            ("inverted xperm mask grants bits", helper_path,
             "datum->u.xperms->perms.p[i] &= ~xperms.perms.p[i];",
             "datum->u.xperms->perms.p[i] |= xperms.perms.p[i];"),
            ("signed bit 31 shift", helper_path,
             "#define xperm_set(x, p) (p[x >> 5] |= (1U << (x & 0x1f)))",
             "#define xperm_set(x, p) (p[x >> 5] |= (1 << (x & 0x1f)))"),
            ("wildcard permissive failure reports success", helper_path,
             'pr_info("Could not set bit in permissive map\\n");\n                return false;',
             'pr_info("Could not set bit in permissive map\\n");\n                return true;'),
            ("unreachable key allocation retains NULL owner", helper_path,
             key_stage, "if (0) {\n    " + key_stage + "\n    }"),
            ("key container populated before owner allocation", helper_path,
             key_stage, ""),
            ("insertion failure guard bypassed", helper_path,
             "if (symtab_insert(&db->p_types, key, type))", "if (0)"),
            ("insertion hidden in unreachable branch", helper_path,
             "if (symtab_insert(&db->p_types, key, type))\n        goto abort;",
             "if (0) {\n        if (symtab_insert(&db->p_types, key, type))\n            goto abort;\n    }"),
            ("nested fallible call before first publication", helper_path,
             "old_type_attr_map_array = db->type_attr_map_array;",
             "if (value) { key = kstrdup(type_name, GFP_KERNEL); }\n    old_type_attr_map_array = db->type_attr_map_array;"),
            ("post-insertion abort jump frees transferred owners", helper_path,
             "old_type_attr_map_array = db->type_attr_map_array;",
             "if (value) goto abort;\n    old_type_attr_map_array = db->type_attr_map_array;"),
            ("success destroys staged role map after transfer", helper_path,
             "ebitmap_init(&new_role_types[i]);", "ebitmap_destroy(&new_role_types[i]);"),
            ("abort destroys shallow-copied existing bitmap", helper_path,
             "ebitmap_destroy(&new_type_attr_map_array[value - 1]);",
             "ebitmap_destroy(&new_type_attr_map_array[0]);"),
            ("unknown helper hidden in abort diagnostic", helper_path,
             'pr_err("add_type: staging failed for %s\\n", type_name);',
             'pr_err("add_type: staging failed for %s\\n", kstrdup(type_name, GFP_KERNEL));'),
            ("line-spliced comment hides key failure guard", helper_path,
             "if (!key)\n        goto abort;",
             "// hidden C guard " + "\\" + "\n    if (!key)\n        goto abort;"),
            ("conditional compilation hides allocation", helper_path,
             key_stage, "#if 0\n    " + key_stage + "\n#endif"),
            ("unchecked control flow added before insertion", helper_path,
             "if (symtab_insert(&db->p_types, key, type))",
             "if (attr) goto abort;\n    if (symtab_insert(&db->p_types, key, type))"),
            ("narrow role counter can wrap", helper_path,
             "    u32 i;\n\n    if (type)", "    unsigned char i;\n\n    if (type)"),
        )
        for label, path, old, new in mutations:
            require(old in src[path], "missing negative target: " + label)
            changed = dict(src)
            changed[path] = src[path].replace(old, new, 1)
            if label == "key container populated before owner allocation":
                changed[path] = changed[path].replace(key_slot, key_slot + "\n    " + key_stage, 1)
            try:
                contract(changed, expected_calls)
            except (RuntimeError, AssertionError, ValueError):
                pass
            else:
                raise RuntimeError("negative mutation accepted: " + label)
        print("PASS:", len(mutations), "distinct negative mutations rejected")
        print("PASS: AST syntax/ownership boundary and formatting-positive control")
        rejected_apply(root, new_patch)
        for patch, flags in reversed(applied):
            git(root, "apply", "--reverse", "--check", "--whitespace=error", *flags, str(patch))
            git(root, "apply", "--reverse", "--whitespace=error", *flags, str(patch))
        require(all((root / p).read_bytes() == data for p, data in originals.items()), "reverse byte mismatch")
        print("PASS: prerequisite/duplicate rejection and exact restoration of", len(paths), "pinned files")
    print("SOURCE-ONLY PASS; backup readers, rollback, batch semantics and startup/ADB/lifecycle remain BLOCKED")


if __name__ == "__main__":
    main()
