# Usage-limit checkpoint policy (10%)

This document defines a **manual/externally signaled policy**, not an active quota monitor. ChatGPT/Codex remaining usage percentage is not automatically available to repository workflows.

- **Only trigger:** when an authoritative usage display or user-provided reading indicates **10% or less remaining** in a relevant usage window. No 20% threshold.
- On trigger, stop starting optional tasks and prioritize a concise handoff in the existing `docs/ROTHKO_ACTIVE_CHECKPOINT.md` on the active development branch. Update it **only if** meaningful progress, blocker, commit, or next action has changed; otherwise reuse the existing checkpoint and make no commit.
- Record: timestamp/source of usage reading (if known), branch and commit, completed validated work, evidence scope, unresolved issues/dependencies, and one next actionable step for **"Lanjutkan"**. Never assert that source-only checks prove boot safety.
- Preserve BUILD HOLD and Draft PR #9: no kernel/device build, flash, release, merge, force push, history rewrite or gate weakening without separate authorization.
- Avoid duplicate checkpoints, unnecessary CI, and repetitive audits. A validated result is reused. One attempt if sufficient; at most two attempts on the same approach.
- If no usage reading is available, **do not infer a percentage or claim that the trigger fired**. Owner may request a checkpoint manually at any time.

This policy does not change Android battery saver settings and does not enable background monitoring or automatic commits. A future quota signal integration must be verified before claiming automation.
