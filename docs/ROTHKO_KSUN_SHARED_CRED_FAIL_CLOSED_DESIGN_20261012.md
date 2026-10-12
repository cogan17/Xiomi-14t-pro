# Rothko KSUN shared-credential fail-closed design

**Status: DESIGN ONLY — BLOCKED. No C integration, merge, kernel build, release or flash.**

Scope: pinned source `pershoot/KernelSU-Next@3438d6aa431f96a23f9e625bec3d53ce1fb14161`, with the **four existing candidate patches applied only in a temporary checkout**. Rothko base is Xiaomi BSP Linux **6.1.57**, not an automatically compatible GKI 6.1.177 build. GitLab/SUSFS provenance on hold. PR #9 remains Draft.

## Source-verified current behavior

1. `kernel/core/init.c:kernelsu_init` calls `ksu_cred = prepare_creds()` and checks allocation. It registers several facilities/hooks (including `ksu_supercalls_init`, feature, sucompat and other conditional initialization) **before** entering the late-load branch. The late-load branch calls `apply_kernelsu_rules`, `cache_sid`, `setup_ksu_cred()` and then `escape_to_root_for_init()`; results from the latter two are not checked. Simply inserting `return -E...` after failure would **not** unwind earlier initialization.
2. The original `kernel/selinux/selinux.c:setup_ksu_cred` returns `void`; the existing SELinux fail-closed *candidate* changes `setup_selinux` to return an error, but `setup_ksu_cred` still **only logs the error**. The shared `ksu_cred` may therefore be used with an unverified security domain.
3. Under `CONFIG_KSU_SUSFS`, `kernel/runtime/ksud_integration.c` calls `setup_ksu_cred()` in second-stage `init` and first zygote, then disables their one-shot static-key markers. The non-SUSFS second-stage path also calls the void helper before disabling its marker; non-SUSFS zygote behavior differs. Disabling a marker after an unchecked attempt is not proof of successful credential preparation.
4. `load_module_rc_once` sets `loaded = true` **before** `override_creds(ksu_cred)` and never validates the stored credential's SELinux domain. `ksu_install_rc_hook` sets `rc_hooked = true` and deactivates the init.rc hook **before** invoking `load_module_rc_once`. The non-SUSFS `ksu_sys_fstat` handler may also invoke `load_module_rc_once`. A readiness check inserted *after* these latches may silently suppress module RC handling forever. On the read path, this happens in the context of `init.rc` proxy installation; that ordering is a separate concern from root grant/FD access.
5. `load_module_rc_once` uses `revert_creds(old_cred)` on the observed fallthrough and error labels, and `kernelsu_exit` releases `ksu_cred`. These existing cleanup sites are evidence, not a proof that earlier setup failures are safely handled.

## Proposed security contract — requires owner/developer review

The shared credential should have a defined monotonic lifecycle. Suggested *conceptual* states (not a recommendation to add an unguarded global boolean):

- **UNAVAILABLE**: no usable credential; no `override_creds(ksu_cred)` allowed.
- **PREPARED**: allocated, but not yet proven to have the expected KernelSU SID/domain; **must not** be consumed as a privileged credential.
- **READY**: a successful, checked SELinux transition has been confirmed *on the exact credential object* that the consumer will use, with appropriate lifetime and synchronization.
- **STOPPED**: failure/unload path has prevented new consumers and drained or synchronized existing users before `put_cred`.

The transition into **READY** must originate from a checked helper return and domain verification; **do not** treat a static flag, zero return from unrelated privilege code, or `ksu_get_root_profile` as proof. An immutable published credential (or rigorously locked replacement) is preferable to modifying the same published `struct cred` in place; confirm Linux 6.1.57 SELinux credential ownership, RCU/reference, and synchronization rules **before selecting the concrete design**. If the underlying policy/SID is unavailable, block the consumer; do not install a placeholder permissive context.

### Design gates before any C candidate is considered complete

- **G1 — Helper contract**: `setup_ksu_cred` must return meaningful status and cannot publish unverified security state. Every caller under `CONFIG_KSU_SUSFS`, `!CONFIG_KSU_SUSFS`, built-in and module/late-load alternatives is accounted for. The existing four-patch source-only candidate does *not* implement G1.
- **G2 — Late-load unwind**: check `setup_ksu_cred` and `escape_to_root_for_init` *before* assuming init success. Because multiple facilities are registered earlier in `kernelsu_init`, prove either a safe preregistration reorder or a complete reverse-order unwind of all initialized facilities, including conditional hooks and `ksu_cred` release. **Never add a bare failing `return` after registration.** Avoid a call into `__exit` routines from a built-in init path without proving section/lifetime semantics.
- **G3 — Startup one-shot semantics**: never clear the `is_init_second_stage_not_executed` or `is_first_zygote` key merely because the void helper was invoked; specify whether each failure retries, fails closed permanently, or stops the feature. If retrying, prove boundedness, no accidental re-entrance, and no repeated policy mutation. The non-SUSFS zygote path must be separately analyzed.
- **G4 — Module RC consumption**: validate a READY credential **before** calling `override_creds`. Decide atomically how `loaded`, `rc_hooked`, hook teardown and `module_rc_len` change on error so they cannot silently advertise successful initialization or cause an unbounded retry. Preserve `revert_creds` on every path following a successful override. Audit `load_module_rc_once` callers from init.rc read and non-SUSFS fstat.
- **G5 — Shared object lifetime**: prove no concurrent reader can observe a partially mutated credential; protect reference ownership through `override_creds` and across unload/cleanup. Audit any additional `ksu_cred` consumer, not just `modules.rc`.
- **G6 — Integration gate**: only after G1–G5 are independently reviewed should a source candidate be submitted to the isolated patch-applicability CI. Subsequent kernel build/link, Android/Rothko ABI/KMI/CRC, boot/restore, successful/failed exec, and root-authorization tests remain separate gates.

**Never promote an evidence/mutation-test PASS to approval for any of G1–G6.**

## Reproducible source evidence

- `scripts/rothko_ksun_shared_cred_audit.py`: four pinned C/header source paths, startup variant boundaries, shared credential use, and one-shot flag ordering.
- `tests/test_rothko_ksun_shared_cred_audit.py`: **16 negative mutations** injected into temporary copies; verifies unexpected source deviations are not silently accepted.
- `--require-reviewed-remediation`: intentionally **DENIED** for the current pinned candidate; success of the source evidence audit must not override this.
- `.github/workflows/rothko-ksun-candidate-audit.yml`: applies the original four KSUN patches to a temporary checkout, runs source checks and negative regressions, then reports **RELEASE BLOCKED**. It does not fetch GitLab, integrate KSUN into Rothko BSP, compile a kernel, or produce flashable artifacts.

### Outstanding independent blockers

The KSUN↔SUSFS post-`execve` authorized FD contract is still missing; no unconditional FD installation or stub is allowed. The five rejected Rothko SUSFS hunks, `TIF_PROC_NO_SU` mapping, SELinux/seccomp interactions, vendor ABI/KMI and device testing are still unresolved. BakaSU integration and GitLab fetch remain on hold by owner decision.


## G1 partial source candidate — status-returning shared credential helper

**A candidate implementation is now staged ONLY as a patch file, not applied to the Rothko BSP.** `patches/rothko-ksun-shared-cred-status-candidate.patch` is intentionally applied **after** the original four KSUN candidate patches to the CI-only pinned KSUN checkout.

Scope (limited to upstream KSUN `kernel/selinux/selinux.c` and `selinux.h`):
- Change `setup_ksu_cred` from `void` to `int` and include explicit errno definitions.
- Return `-EINVAL` for absent `ksu_cred`; propagate failure from the already-patched `setup_selinux` helper.
- Require `is_task_ksu_domain(ksu_cred)` on the exact shared cred object; return `-EACCES` if it does not match. Returning an error does not itself make the published mutable cred safe.
- Return 0 only after observed setup and domain checks; do not create, override, commit or publish a new credential in this helper.

**Important:** this is **G1 helper error-reporting only**, not G1 end-to-end readiness. All callers in `core/init.c` and `runtime/ksud_integration.c` still discard the returned status; no safe late-load unwind or one-shot replay policy was installed. `load_module_rc_once` still uses `override_creds(ksu_cred)` without a verifiable readiness gate. Therefore, **the helper patch alone is not safe to compile for deployment or to merge**.

CI audit contract:
1. First apply four existing candidate patches and run prior tests unchanged (37 negative mutations).
2. Apply the fifth helper patch with `git apply --check`, check reverse applicability and `git diff --check` on the ephemeral KSUN checkout only.
3. Run `scripts/rothko_ksun_shared_cred_candidate_audit.py` for scoped G1 evidence, and `tests/test_rothko_ksun_shared_cred_candidate.py` with seven fail-on-unsafe mutation probes.
4. The explicit `--require-integrated` gate must fail while G2–G6 and authorization/ABI/boot hazards remain unresolved.

**Release decision remains BLOCKED** even if every applicability and mutation test passes. Build and flash steps are not part of the new workflow.
