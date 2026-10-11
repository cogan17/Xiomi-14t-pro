# Cogan Rothko — Stage 2: Root Source Audit (Development Only)

Repository: `cogan17/Xiomi-14t-pro`  
Development branch: `dev/rothko`  
Protected-by-process source baseline: `bsp-rothko-u-oss`

> **Status: planning and source inspection only.** No root framework integrated, no
> kernel compiled, and **no flashable artifacts** are authorized by this document.

## Requested root variants

| Selection | Source repository | Branch observed | Example audited tip* |
| --- | --- | --- | --- |
| KernelSU (KSU) | https://github.com/tiann/KernelSU | `main` | `f895b80a3aad79948ba8074f53cf8f65a314d576` |
| KernelSU-Next (KSUN) | https://github.com/KernelSU-Next/KernelSU-Next | `dev` | `02a9e1c5fb2c4fd8117429fe004136332788c1b6` |
| BakaSU | https://github.com/Baka-SU/BakaSU | `main` | `f6cb7e70c10ebde149f3121ae68b945514fd0801` |
| All | Exactly the above three **independent variants** | — | **Never** combine their drivers into a single kernel tree |

*These SHA values document what was observed when auditing on 2026-10-12. They
are **not** approvals to apply code or guarantees of driver/manager compatibility.
Re-audit the exact commit before making real builds.

The upstream integration scripts for these three projects each use the
`drivers/kernelsu` integration path (with different checkout structures). This
makes combined installation into one source tree inappropriate. The All option
means a matrix of **three separate workspaces and builds**, not simultaneous root
engines.

The current workflow is a **selection/matrix preview only**. A future,
separately reviewed CI audit should resolve each selected upstream ref, fetch
its `kernel/setup.sh` from the exact resolved commit, and perform a shell syntax
check. It must **not** execute setup.sh, patch the kernel tree, or build images.

## Kernel baseline observations

- `Makefile` declares Linux `6.1.57`; the existing Cogan GKI project target
  `6.1.177` is not a source-level match.
- `build.config.gki.aarch64.vendor` can select a `VENDOR_DEFCONFIG`, but
  `arch/arm64/configs/` lists only generic configs; no `rothko.config` was
  found in that directory.
- `arch/arm64/boot/dts/mediatek/` contains upstream platform DT sources, but
  no `rothko` or `mt6989` DT file was found in that directory listing.
- `COPYING` and `LICENSES/` must be retained. Linux kernel licensing is not
  replaced by labeling the repository as independent.
- The imported `.github/workflows/Patch Kernel Features.yml` did not provide
  a complete build-and-test pipeline. It has been replaced **on dev/rothko only**
  with a selection/source-validation workflow.
- The default `bsp-rothko-u-oss` baseline is intentionally untouched.

## Explicit exclusions

- No DroidSpaces.
- No NTSync (including the NTSync-enabled performance preset).
- Do not suppress kernel module ABI/version checks or force-load mismatched
  modules.
- Do not silently select an alternative root implementation if the requested
  one fails.

## Mandatory gates before compiling anything for a device

1. Verify exact Xiaomi 14T Pro / Redmi K70 Ultra board and firmware differences,
   required MediaTek vendor files, DT/DLKM modules, and device defconfig.
2. Compare live device `uname -r`, kernel config, ABI/KMI, firmware build and
   partition layout **without making changes to the device**.
3. Integrate **one** root driver variant in an isolated checkout, using a
   reviewed commit and recording its SHA and manager build version.
4. Establish root + SUSFS + NoMount source-version and patch-compatibility
   checks; stop on an unsuccessful patch or mismatched ABI.
5. Perform controlled compilation and static checks; **do not publish flashable
   artifacts** until actual on-device compatibility is demonstrated.

## Important operational note

The workflow currently lives on `dev/rothko`. GitHub workflow dispatch UI can
depend on the workflow file's presence on the repository default branch. If it
does not appear in Actions, **do not merge the source baseline just to expose a
button**; review a separate CI rollout plan first.
