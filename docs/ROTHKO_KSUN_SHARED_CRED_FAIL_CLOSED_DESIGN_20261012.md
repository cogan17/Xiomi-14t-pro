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


## G3 partial startup caller candidate — status checks, unsafe retry still blocked

**A separate, non-deployable C patch exists:** `patches/rothko-ksun-shared-cred-stage-guard-candidate.patch`. The audit workflow applies it only **after** the four original patches and the G1 status-returning helper patch to the temporary pinned KSUN source. It changes `kernel/runtime/ksud_integration.c`, not Rothko's actual BSP.

- `CONFIG_KSU_SUSFS`: second-stage `init` and first zygote now each inspect `setup_ksu_cred()`; on nonzero return the pre-exec hook returns 0 **without clearing** its one-shot key.
- `!CONFIG_KSU_SUSFS`: second-stage `init` checks the same status and returns from its `void` callback on failure before clearing its key.
- The non-SUSFS zygote's stop-hook behavior remains unchanged. There is no late-load G2 change and no shared-cred consumer G4 change.
- `scripts/rothko_ksun_stage_guard_candidate_audit.py` checks these source-level relationships and explicitly prints **RELEASE BLOCKED**.
- `tests/test_rothko_ksun_stage_guard_candidate.py` injects **eight targeted negative mutations** into temporary copies to confirm the validator notices bypassed conditions and incorrect stage-key transitions. `--require-safe-retry` must fail with **RETRY GATE: DENIED**.

**This is not a safe implementation of G3.** Under SUSFS, `ksu_selinux_hide_handle_second_stage()`, `apply_kernelsu_rules()` and `cache_sid()` run **before** the second-stage status check; the zygote path runs `on_post_fs_data()` **before** its status check. On failure the static keys remain enabled, so later matching exec events might rerun those operations. Their idempotence, locking, retry frequency, cancellation and failure behavior are unproven. In addition, successful helper return on one mutable shared cred object does not establish a synchronized readiness guarantee for `override_creds`. The callback returns deliberately permit normal exec to continue, but **there is no proof that startup remains functionally sound or safe**.

Before any integratable G3 implementation, choose and validate an explicit bounded retry or permanent fail-closed policy (including impact on init.rc and modules), ensure no irreversible setup side effects repeat, and prove CONFIG-specific control flow against the Rothko 6.1.57 BSP. G2 late-load cleanup, G4/G5 shared-credential publication/lifetime, G6 device integration, and authenticated post-`execve` FD remain **BLOCKED**. No compile/merge/release/flash is authorized by a green source-only audit.


## G2/G4 source inventory and cleanup prerequisites

**New bounded, source-only audit:** `scripts/rothko_ksun_g2_g4_risk_audit.py` and `tests/test_rothko_ksun_g2_g4_risk_audit.py` verify **15 observed relationships and 21 negative mutations** on a pinned checkout with the six previous candidate patches. They deliberately treat today's unsafe ordering as source **evidence** and deny `--require-remediation`. No build artifacts, kernel C integration or automatic release gates are added.

### G2 — registration before late-load credentials

Confirmed in `core/init.c:kernelsu_init`:

| Stage | Operations in pinned upstream |
|---|---|
| Shared object | `prepare_creds` for `ksu_cred` |
| Early setup before late-load branch | symbol resolver, `ksu_feature_init`, `ksu_sulog_init`, `ksu_adb_root_init` |
| Conditional hooks and infrastructure | `ksu_syscall_hook_init` / `ksu_lsm_hook_init` in applicable configs, `ksu_selinux_hide_init`, `ksu_supercalls_init`, `ksu_app_profile_init` |
| SUSFS hooks in applicable configs | `ksu_sucompat_init`, `ksu_setuid_hook_init`, `ksu_avc_spoof_init` |
| Late-load credential attempt | `apply_kernelsu_rules`, `cache_sid`, `setup_ksu_cred`, then `escape_to_root_for_init` |
| Later late-load state | allowlist, manager/observer/file-wrapper, `ksu_boot_completed = true`, enforcing SELinux |

`kernelsu_exit` does not provide a verified **failure unwind** for an arbitrary partially initialized state: the observed exit path stops supercalls, uses `synchronize_rcu`, tears down observers, allowlist, conditional SUSFS/LSM hooks, features and finally calls `put_cred(ksu_cred)`. Calling that complete shutdown path after a failed partially initialized setup could run cleanup on structures that were never initialized; early registration is also conditional on configuration. **Do not insert a lone `return -E...` after late-load SELinux failure.**

Required before G2 can be converted to patch C: inventory each init call's actual return type and side effects, establish successfully initialized component flags or rearrange setup **before registration without breaking policy availability**, and define reverse-order cleanup with quiescence/RCU behavior for all relevant CONFIG paths. Prove `escape_to_root_for_init` result and post-credential state; no blind `commit_creds` retry.

### G4 — credential readiness versus one-shot init.rc consumption

Confirmed in `runtime/ksud_integration.c`:

- `load_module_rc_once` sets `loaded = true` **before** testing credential readiness and calling `override_creds(ksu_cred)`. `revert_creds(old_cred)` is present on the observed success/error cleanup paths; readiness, ownership and reference safety are not established.
- `ksu_install_rc_hook` sets `rc_hooked = true`, and under the non-SUSFS path calls `stop_init_rc_hook()` (or under SUSFS disables `ksu_is_init_rc_hook_enabled`) **before** `load_module_rc_once()`. A failed loader cannot assume a second chance.
- Non-SUSFS `ksu_sys_fstat` can invoke the same loader, so there is an additional entry point to the one-shot state.
- `module_rc_len` is set only after successful `kernel_read`, but the proxy/size adjustment may still proceed with the static `KERNEL_SU_RC` content when module RC is unavailable. An absent module payload and a completed hook are not equivalent to successful module initialization.

**G4 ownership decision remains OPEN:** a correct fix must validate a cred that is already SELinux-domain-ready, has a safe reference lifetime, and will not be modified concurrently. It must decide the observable failure state **before** setting `loaded` or `rc_hooked`, including whether module support becomes disabled with an explicit error or may be retried via a proven safe, bounded path. It must also address the `init.rc` read interception timing and non-SUSFS `fstat`. Simply adding `if (!is_task_ksu_domain(ksu_cred)) return;` after the one-shot flags is **not** sufficient.

Audit pass means all **currently observed** source relationships are unchanged, **not that any G2/G4 prerequisite is satisfied**. A code change that alters these relationships must force reviewer reevaluation rather than silently relabel a changed risk as safe.

**Gate: G2 BLOCKED · G4 BLOCKED · G5 BLOCKED · G6 BLOCKED**. G1/G3 source checks and the unresolved authenticated post-`execve` FD flow remain separate; no merge, build, release or flashing.
