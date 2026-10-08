Bash was unavailable in this run (sandbox failed to start: `apply-seccomp: … Permission denied`); review done with Read/Grep/Glob only.

# Plan review — stack-holds-dependent-of-out-of-batch-unmerged-prereq

Inputs: there is no `notes.json` and no `sources/` in the bundle, only `brief.md` and `dependency-state.json`. So nothing could be checked against the tracker thread. The brief cites "iteration-v2/v3 sign-offs of #616", but those are not in the inputs either. Every claim below comes from the target source.

- NEEDS-HUMAN — **The brief changes `merged.is_merged` for every caller, but says merge mode stays the same.** Scope says "make `merged.is_merged` count MERGED only for a PR merged into the target base … mode not `"stacked"`". Criterion (6) says merge mode (#531) is "Unchanged". But `is_merged` has two other callers that the brief never names:
  - `merge.py:233`: `if merged.is_merged(cfg, iid): return 0  # already merged (a resumed run) — idempotent`. This is merge mode's own resume check.
  - `cli.py:1084`: `_blocked_by`, used by status/queue display.

  An `Onto branch` bundle publishes through `_publish_stacked` (`publish.py:225-228`). That path returns before the merge-mode base guard at `publish.py:293`, and it records `"mode": "stacked"` (`publish.py:540`). Under the new rule, a resumed merge-mode run would read that already-merged PR as not merged. It would then call `gh pr ready` and `gh pr merge` on a merged PR and STOP (`merge.py:242-249`).

  The planner needs to do one of two things. Either list `merge.py` and `cli.py` as callers whose behaviour changes, with a criterion for each. Or put the base rule behind a new parameter or function that only `_runnable` uses. As written, criterion (6) can't be checked for merge mode, because no test is planned for `merge.py:233`.

- NEEDS-HUMAN — **"Target base resolved for the bundle" is ambiguous, and `is_merged` can't see the dependent.** `is_merged(cfg: Config, dep_id: str)` (`merged.py:32`) only gets the prerequisite's id. The Invariant says "merged into the **dependent's** target base". The Scope says "record `base` equals the target base resolved for the bundle", which reads as the prerequisite's own `_resolve_target`. These two give different answers when P and D target different bases or repos.

  The brief should say which one it means. If it means the dependent's base, the brief should accept the signature change and the caller updates that come with it. Otherwise Do picks one, and the sign-off can't say whether that pick was "correct".

- NEEDS-HUMAN — **The main "merged elsewhere" case in the brief mostly can't happen on the current code.** The Defect says a `"stacked-pr"` record "whose PR targets an integration branch (`publish.py:420-421`, `"base": pr_base`)" can be MERGED without reaching the base. But `publish.py:282` sets `pr_base = stack_branch if (stack_branch and own_repo and not wave_stacked) else base`, and `publish.py:266-268` explains why: a wave stack-base bundle "opens its PR against its REAL target base … (#593)". `cli.py:1065-1067` says the same: "every PR targets the real base (#593), so it reads ↑main".

  The only way a stacked-pr record gets a non-base `base` is a hand-declared legacy `Stacks on` parent on own-repo, and the brief puts `Stacks on` out of scope. The repro step "record's `base` set to `pdca-integration/main-r<key>`" makes a record that current wave code never writes. So criterion (3)'s RED is real only for legacy `Stacks on` and `Onto branch` records.

  The brief should restate this half as a defensive hardening of a rare path, not a live defect. Or, better, split it out, together with the merge-mode risk above. The live defect, criterion (1), doesn't need it.

- NEEDS-HUMAN — **This is two or three fixes, not one.** These are separate changes:
  - (a) a new hold for plain `Depends on` prerequisites outside the batch, in `_runnable`;
  - (b) a new meaning of "merged" in `is_merged`, which also tightens #186 `Depends on (merged)` and touches merge mode and the CLI (see above);
  - (c) an `OSError` guard in `is_merged`, a copy of the one in `merged_head` (`merged.py:75-79`).

  (a) can ship on its own by calling today's `is_merged`. (b) is the change with the hidden effects on other callers. (c) is a small unrelated hardening. The Difficulty line ("one new hold … target-base rule, `OSError` guard, the hold message, docs") lists them as one item. Each part adds review surface, and (b) is the one most likely to cause trouble at sign-off.

- NEEDS-HUMAN — **Dependency 646 is still PLANNED, and the "requested batch" idea doesn't exist yet.** `dependency-state.json` shows `"646": {"declared": "Depends on", "exists": true, "state": "PLANNED"}`. The Ordering note says this child "needs child-1's 'requested batch' notion". The target `flow.py` has no such idea yet: `_runnable(cfg, wave, batch_names, *, held=…)` at `flow.py:681-682` only has `batch_names`. Do can't start until 646 is COMPLETE and folded in.

  Separately, the brief's line references were checked on `origin/pdca-integration/main @ f594d8e`, but the target is `main`. On the target I read, `integrate._gone_branch`'s base test is at `integrate.py:443`, not `:474-482` as cited. The brief already warns that lines may have moved. Even so, the human should confirm that the `main` base will include 646 when Do runs. If it doesn't, criterion (6)'s "child-1's carry" has nothing to protect.

- NEEDS-HUMAN — **Criterion (1)'s message wording isn't specified tightly enough to test.** "one stderr line names `D`, `P` and the reason, with advice (name `P` in the same `pdca flow <ids>` command … or wait until its PR merges)". Today `_runnable` already prints one generic line per skipped bundle (`flow.py:715-716`: "skipped — prerequisite(s) not ready (P)"). So a test that only checks for `D` and `P` passes against the existing message. The brief should name a distinctive substring the test must assert, for example the advice text. Otherwise the "message" part of RED→GREEN is satisfied by code that already exists.

I tried to fault the root cause of the main defect, criterion (1). I could not: `flow.py:710` really does accept an out-of-batch COMPLETE prerequisite, and the docstring at `flow.py:692-698` admits that the base then lacks it.

> **pdca:** Bash was unavailable to this reviewer. The vendor sandbox could not start on this host, so every Bash call it made failed before running (`apply-seccomp: write /proc/self/setgroups (nested userns is capability-restricted; caller must provide CAP_SYS_ADMIN): Permission denied`) and it ran no commands; this review was delivered without Bash.
