#!/usr/bin/env python3
"""Read-only G1-only candidate source checks; does not approve integration.

Run *after* four baseline KSUN patches and the isolated fifth helper patch.
All other KSUN/Rothko release gates remain blocked by construction.
"""
import argparse
from pathlib import Path
import sys


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("kernel_root", type=Path)
    p.add_argument("--require-integrated", action="store_true")
    args = p.parse_args()
    root = args.kernel_root
    paths = {
        "selinux": "selinux/selinux.c",
        "header": "selinux/selinux.h",
        "core": "core/init.c",
        "runtime": "runtime/ksud_integration.c",
    }
    code = {key: (root / path).read_text(encoding="utf-8")
            for key, path in paths.items()}
    selinux = code["selinux"]
    anchor = "int setup_ksu_cred(void)\n{"
    terminator = "\n}\n\nvoid escape_to_root_for_adb_root"
    body = selinux.split(anchor, 1)[1].split(terminator, 1)[0] if selinux.count(anchor) == 1 and terminator in selinux.split(anchor, 1)[1] else ""
    checks = []

    def check(description: str, ok: bool):
        checks.append(ok)
        print(("PASS: " if ok else "REVIEW REQUIRED: ") + description, flush=True)

    check("shared helper signature returns status in header and definition",
          "int setup_ksu_cred(void);" in code["header"] and bool(body))
    check("shared helper explicitly includes kernel errno definitions",
          "#include <linux/errno.h>" in selinux)
    check("no shared credential is accepted on NULL",
          "if (!ksu_cred)\n        return -EINVAL;" in body and
          body.index("return -EINVAL;") < body.find("setup_selinux(") if "return -EINVAL;" in body and "setup_selinux(" in body else False)
    check("SELinux error is returned without success masking",
          "ret = setup_selinux(KERNEL_SU_CONTEXT, ksu_cred);" in body and
          "if (ret) {" in body and "return ret;" in body and
          body.index("ret = setup_selinux(") < body.index("if (ret) {") < body.index("return ret;")
          if all(v in body for v in ("ret = setup_selinux(", "if (ret) {", "return ret;")) else False)
    check("candidate checks exact shared credential KSU domain",
          "if (!is_task_ksu_domain(ksu_cred)) {" in body and
          "return -EACCES;" in body and
          body.index("return -EACCES;") < body.index("return 0;")
          if "return -EACCES;" in body and "return 0;" in body else False)
    check("candidate helper never commits credentials itself",
          "commit_creds(" not in body and "override_creds(" not in body)
    check("late-load + CONFIG callers still have unchecked status (not integrated)",
          "setup_ksu_cred();" in code["core"] and
          code["runtime"].count("setup_ksu_cred();") == 3)
    check("module rc still overrides shared cred without a readiness gate",
          "override_creds(ksu_cred)" in code["runtime"])

    print("BLOCK: G1 helper status candidate only; no checked callers, publication, or rollback.")
    print("BLOCK: G2 late-load cleanup, G3 one-shot hooks, G4 module RC, G5 lifetime, G6 kernel ABI/boot.")
    print("BLOCK: SUSFS post-exec authenticated FD and Rothko BSP patch conflicts remain unresolved.")
    print("RELEASE GATE: BLOCKED — success is limited to isolated source evidence.")
    if not all(checks):
        print("AUDIT: FAILED — candidate source contract drifted.", file=sys.stderr)
        return 1
    if args.require_integrated:
        print("INTEGRATION GATE: DENIED — G2–G6 and FD authorization unverified.", file=sys.stderr)
        return 3
    print("AUDIT: PASS — G1 helper source candidate only; RELEASE BLOCKED.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, UnicodeError, ValueError) as e:
        print("AUDIT: FAILED — " + str(e), file=sys.stderr)
        raise SystemExit(1)
