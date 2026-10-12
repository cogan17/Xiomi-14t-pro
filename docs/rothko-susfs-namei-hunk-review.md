# SUSFS Rothko: rejected namei hunk

Official SUSFS `gki-android14-6.1` patch failed `git apply --check` at `fs/namei.c:1614` in run 38236950368.

The patch expected a closing block followed by `EXPORT_SYMBOL(lookup_one_qstr_excl);`. In `dev/rothko:fs/namei.c`, `lookup_one_qstr_excl` does not occur at all. The nearby Xiaomi functions are `__lookup_hash` (around 1583), `lookup_fast` (around 1609), and `__lookup_slow` (around 1658). Thus this is an API/function-layout mismatch, not just a hunk offset.

Do not inject a stub, rename another lookup function, or transplant the hunk into `__lookup_hash` without examining the exact SUSFS additions, call sites and locking/error semantics. Keep the patch check failing until the port is reviewed. No kernel source changes or compilation.
