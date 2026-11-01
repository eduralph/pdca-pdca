- **Slug:** wave-mode-unknown-value-note
- **Kind:** bug
- **Tracker:** eduralph/pdca-harness#842 (child of #464, split 2026-10-30; the PR links `Refs #842`)
- **Defect / goal:** `Config.load` keeps any `[driver].wave_mode` value as given (`template/src/pdca_harness/config.py:733`). Every check compares against `"merge"` (`flow.py:2888`, `:2901`, `:3080`; `waves.py:149`, `:379`; `publish.py:251`, `:295`), so a typo behaves as `"stack"` with no message.
- **Success criterion:** `Config.load` with `wave_mode = "bogus"` prints one stderr line naming the bad value and the allowed values, and gives `cfg.wave_mode == "stack"`. `"stack"`, `"merge"` and an absent key print nothing and keep their value. `"Merge"`, `"merge "` (trailing space), `"none"` and a non-string value such as `1` count as unknown: each prints the note, falls back to `"stack"`, and raises nothing. Matching stays exact on purpose — no `.lower()` and no `.strip()`: today neither `"Merge"` nor `"merge "` enables merge mode (the checks compare with `==`), and folding case or whitespace would start merging PRs for that instance. `"none"` is an unknown value in this bundle: it gets the note and the fallback like any other; the sibling 843 then adds it to the allowed set (that is what 843 depends on this bundle for), and `pdca.toml` has no `"none"` today (`config.py:733` documents `stack | merge`).
- **Falsifiability:** RED offline with the plain unittest runner: today `cfg.wave_mode` is `"bogus"` (and `"Merge"`, `"merge "`, `1`, `"none"` are kept as given) and stderr is empty. Through the real loader, as `template/tests/test_merge.py:679-697` loads `merge_requires`.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Reproduction:** Load a `pdca.toml` with `[driver] wave_mode = "bogus"`. Read `cfg.wave_mode` and stderr.
- **Scope (one logical fix) / out of scope:** Validating the value at load, and updating the comment at `config.py:733`. / out of scope: adding `"none"` to the allowed set (843); any change to what `"stack"` or `"merge"` do; validating the neighbouring `merge_method` (`config.py:734`, read unvalidated and passed to `merge.merge_wave` at `flow.py:3081`) — the same flaw, left for a follow-up issue so this slice stays one site; no drive-by.
- **External dependencies:** none
- **Test file:** `template/tests/test_config_wave_mode.py` (new). Import only `from pdca_harness.config import Config`, so the red leg imports and fails on assertions.
- **Citations expected:** path:line on main for every change. Peer callsite: validate as `merge_requires` does, `template/src/pdca_harness/config.py:738-742` (print a note, fall back), without its `.strip().lower()`.
- **Prior-art check (triage cycles):** By path: `git -C ../pdca-harness log --oneline origin/main -- template/src/pdca_harness/config.py` (f40c149, b2740ea, 09632f3, 87c7352, 2261b53, 96c9704, e7a88b0, 9ecbb01 …) — none validates `wave_mode`; `git log -i --grep=wave_mode origin/main` likewise. Open PRs: `gh pr list --state open --search wave_mode` → none. Open issues naming `wave_mode`: #464 (the parent), #806, #512, #778, #547 and this split's siblings — none validates the value. Closed PRs: `gh pr list --state closed --search "wave_mode none"` → #619 (stack-mode PRs against the real base) and #484 (rollup gate), neither touches validation. Result: no prior art, no in-flight duplicate.
- **Surfaces:** data
- **Difficulty:** low
- **Disposition hint:** likely-fix

Plan-review response (round 1): all five findings addressed in place. The tracker id is
named (#842; the bundle directory carries it for the PR trailer). `"none"` is ruled an
ordinary unknown value here, with the 843 hand-off stated. `"merge "` is added as a listed
case, pinning the no-`.strip()` half. The prior-art check was re-run by path, over open PRs
and open issues, and its result rewritten to what the evidence shows. `merge_method` is
named out of scope.

## Iteration 1 — carry-forward (from the previous attempt)
- Sign-off rationale: Rejected at sign-off: note-plus-fallback is the wrong policy. A mis-configured `pdca.toml` must produce a message AND a failure — `Config.load` must not continue with a substituted value. Rewrite the success criterion: unknown `wave_mode` (incl. `"Merge"`, `"merge "`, `"none"`, non-string) → one stderr line naming the bad value and the allowed values, then a raise / non-zero exit; no fallback. Keep exact matching, keep "stack"/"merge"/absent silent. Drop "raises nothing". Decide and state the failure form (which exception, or `sys.exit`) and how the CLI surfaces it. The existing patch and test are a good shape to adapt; only the fallback line and the `cfg.wave_mode == "stack"` assertions change. Prior-art (T5) was re-checked at sign-off against origin/main by path and by open/merged/closed PRs: no duplicate — carry that forward, no need to re-run.
- Sign-off session carry-forward (captured live, before §9 flattened it):
  Rejected at sign-off: note-plus-fallback is the wrong policy. A mis-configured `pdca.toml` must produce a message AND a failure — `Config.load` must not continue with a substituted value. Rewrite the success criterion: unknown `wave_mode` (incl. `"Merge"`, `"merge "`, `"none"`, non-string) → one stderr line naming the bad value and the allowed values, then a raise / non-zero exit; no fallback. Keep exact matching, keep "stack"/"merge"/absent silent. Drop "raises nothing". Decide and state the failure form (which exception, or `sys.exit`) and how the CLI surfaces it. The existing patch and test are a good shape to adapt; only the fallback line and the `cfg.wave_mode == "stack"` assertions change.
  Prior-art (T5) was re-checked at sign-off against origin/main by path and by open/merged/closed PRs: no duplicate — carry that forward, no need to re-run.
- Full previous attempt preserved in `iteration-v1/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).
