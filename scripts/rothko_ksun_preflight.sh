#!/usr/bin/env bash
# Fail-closed preflight for Rothko KSUN/SUSFS. Never compiles or flashes.
set -euo pipefail
fail() { printf 'BLOCKED: %s\n' "$*" >&2; exit 1; }
[[ "${ROTHKO_KSUN_SHA:-}" =~ ^[0-9a-f]{40}$ ]] || fail 'ROTHKO_KSUN_SHA must be a reviewed full 40-character commit SHA'
[[ "${ROTHKO_SUSFS_SHA:-}" =~ ^[0-9a-f]{40}$ ]] || fail 'ROTHKO_SUSFS_SHA must be a reviewed full 40-character commit SHA'
[[ "${ROTHKO_KSUN_SHA}" != "${ROTHKO_SUSFS_SHA}" ]] || fail 'Unexpected identical source hashes'
[[ "${ROTHKO_KERNEL_SERIES:-}" == '6.1' ]] || fail 'Expected Xiaomi BSP kernel series 6.1'
[[ "${ROTHKO_SUSFS_BRANCH:-}" == 'gki-android14-6.1' ]] || fail 'SUSFS patch branch must match android14-6.1'
[[ "${ROTHKO_KSUN_AUDIT_APPROVED:-}" == 'yes' ]] || fail 'KSUN API/hook and version guard audit not approved'
[[ "${ROTHKO_SUSFS_AUDIT_APPROVED:-}" == 'yes' ]] || fail 'SUSFS patch-context audit not approved'
[[ "${ROTHKO_ABI_AUDIT_APPROVED:-}" == 'yes' ]] || fail 'ABI/KMI/vendor module audit not approved'
[[ "${ROTHKO_NOMOUNT:-off}" == 'off' ]] || fail 'NoMount must remain disabled for initial KSUN experiment'
printf 'Preflight inputs accepted; this does NOT establish device compatibility.\n'
