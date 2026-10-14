# Usage-limit emergency checkpoint and safe stop (10%)

## Trigger and scope

**Only threshold: remaining ChatGPT/Codex usage <= 10%**, for any applicable quota window, based on an authoritative display or an explicitly supplied reading. No 20% threshold. This file is a **policy/specification**, not a running quota monitor: GitHub Actions cannot independently read the user's private ChatGPT/Work usage meter. Never infer a remaining percentage.

## Required safe-stop sequence

1. **Notify immediately:** `WARNING: Usage remaining <=10%. Emergency checkpoint initiated. New development work is paused.` Include the measured value, its source and time if known.
2. **Close admission:** do not start new development tasks, builds, CI reruns, audits, merges or releases. Keep the existing Rothko BUILD HOLD binding.
3. **Quiesce safely:** allow an in-flight atomic write/commit to complete or use the task's documented cancellation/rollback mechanism. Never abruptly kill Git writes, discard uncommitted changes, force-reset branches or cancel unrelated work. A safe stop may require finishing a small critical operation; zero-loss cannot be guaranteed for arbitrary external processes.
4. **Checkpoint selectively:** if meaningful state changed, update the **existing** `docs/ROTHKO_ACTIVE_CHECKPOINT.md` on the active branch with branch/HEAD, validated progress and evidence, pending/uncommitted changes, blockers, next action for `Lanjutkan`, and the trigger reading/source. Never create parallel checkpoints or commit incomplete/unverified work as if validated. If nothing changed, reuse the existing checkpoint and make no commit.
5. **Verify and notify:** confirm the checkpoint commit/branch is retrievable and report its link; if saving fails, explicitly report that the state is not durably saved and retain working files. Mark the development session PAUSED only after safe quiescence and durable handoff. Do not claim success otherwise.
6. **Resume:** after quota recovery and explicit owner `Lanjutkan`, re-check the branch/head and checkpoint, then resume only the first unresolved task. Do not rerun previously green validations without a relevant change.

## Enforcement requirements for future automation

A future session supervisor must receive an **authorized, reliable usage signal** and control the work admission queue plus checkpoint writer. It should debounce threshold events, use one in-flight checkpoint lock, perform an idempotent save, verify its commit, and refuse new jobs until resume. Without that signal and control plane, the above sequence can be followed when the owner reports <=10%, but **automatic triggering, forced stopping of ChatGPT Work, and automatic commit are NOT active**. A GitHub workflow alone cannot safely terminate ChatGPT sessions or guarantee no data loss.

Keep PR #9 Draft, BUILD HOLD, source-only validation, maximum two attempts per approach, and no unnecessary CI. This policy does not modify Android battery-saver settings.
