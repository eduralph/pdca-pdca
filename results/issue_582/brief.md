# Brief — issue 582 / merge-wait-confirms-green

> The Plan artifact (docs 02 §PLAN). Do reads ONLY this file.

- **Slug:** merge-wait-confirms-green
- **Defect:** Under `[driver].wave_mode = "merge"`, `merge._wait_for_green`
  (`template/src/pdca_harness/merge.py:143-160`) re-reads a PR's check rollup only while it
  is `pending` or `empty` (`merge.py:155`) and returns the first `green` it sees. In the
  seconds after a PR is opened/readied, the rollup reports only the checks that have
  registered SO FAR: one fast workflow that already passed (a DCO or issue-link check)
  reads as a clean `green` (`_check_rollup`, `merge.py:126-130`) while a slow job has not
  created its check run yet. `_merge_one` then merges on that partial green
  (`merge.py:229-231`). If the slow job is host-required, `gh pr merge` refuses and the wave
  stops; if it is not required — the thin-branch-protection case `merge_requires = "all"`
  exists for — the PR merges and the check fails afterwards on the base. The same applies to
  a green reached through the loop (`empty → green` or `pending → green`): that read can be
  just as partial.
- **Success criterion:** Through `merge.merge_wave` (the public entry `flow` calls,
  `merge.py:70-79`), with `subprocess.run` and `merge._sleep` patched as in
  `tests/test_merge.py:289-314`:
  (i) **A green is believed only once it has held.** When a rollup read says `green`, the
  wait re-reads once more, one poll interval later (charged to the `merge_wait_secs`
  budget), and treats the PR as green only if that second read is also `green`. Probe:
  reads `green(dco)`, then `pending(dco pass, e2e pending)`, then `green(dco, e2e)`,
  `green(dco, e2e)` → **merges, and only after the 4th read**; reads `green(dco)`, then
  `failing(e2e fail)` → **does not merge**, returns non-zero, names the failing check, and
  undoes the ready-mark (`gh pr ready --undo`) exactly as a failing rollup does today
  (`tests/test_merge.py:258-269`).
  (ii) **A confirm that does not hold re-enters the wait** — a `pending`/`empty` second read
  goes back into the bounded loop; `failing`/`unreadable` returns at once (no further reads).
  (iii) **The bound holds.** Total slept time never exceeds `merge_wait_secs` (sum of the
  `_sleep` arguments ≤ the bound). A green that first appears when no budget is left for
  its confirm is **not** believed: it is returned as `pending` (the module's fail-closed
  direction, `merge.py:59-63`), so the existing "not finished within Ns" refusal message
  applies, with a detail that says why: the `detail` returned with that `pending` must name
  the green as unconfirmed (e.g. `green first seen with no wait budget left to confirm it
  (2 checks)`), so the refusal reads "a check has not finished within Ns — green first seen
  with no wait budget left to confirm it (2 checks)" rather than a bare count; a test asserts
  `unconfirmed`/`confirm` appears in stderr. This is an intended behaviour change for small
  budgets: with `merge_wait_secs = 15`, `pending → green` merges today and is refused after
  the fix (no budget left to confirm). Operators with slow checks raise `merge_wait_secs`.
  (iv) **`merge_wait_secs <= 0` is unchanged:** exactly one rollup read, no sleep, its
  verdict returned as-is (`tests/test_merge.py:316-328` keeps passing).
  (v) **Nothing else changes.** `_check_rollup`'s classification, `merge_requires =
  "required"` skipping the gate (`tests/test_merge.py:417-425`), the order ready → rollup
  read(s) → merge, and the ready-undo on every decline stay as they are. Two existing tests
  change on purpose, and only these two: `test_pending_then_green_merges`
  (`tests/test_merge.py:289-314`) expects **4** reads (pending, pending, green, green), and
  `test_all_green_readies_then_checks_then_merges` (`:329-334`) expects the gh sequence
  `[ready, checks, checks, merge]` (the confirm read). The whole `template/tests` suite
  stays green **and does not get slower**: four tests reach a green rollup without patching
  `merge._sleep` (`test_merges_then_fetches_base` `:105-121`, `test_merge_failure_stops`
  `:139-160`, `test_readies_before_merging` `:162-182`, `test_first_failure_stops_the_wave`
  `:218-228`) and would each sleep a real 15 s after the fix — patch `merge._sleep` once in
  `MergeWave.setUp` (`mock.patch.object(merge, "_sleep")` + `addCleanup(...stop)`) so no
  test in the class sleeps for real. Tests that already patch it in their own `with` keep
  working (a nested patch).
  Shown by the named test going red on `main` (it merges on the first green read) and green
  with the fix.
- **Falsifiability:** RED is reachable offline on the base toolchain (stdlib Python ≥ 3.11),
  no network and no real `gh`: the existing merge tests already fake `gh pr checks` per read
  (`tests/test_merge.py:296-302`) and patch `merge._sleep` (`:305`). On `main`, a rollup
  sequence `green(dco)` → `failing(e2e)` merges after one read — the test asserts no
  `gh pr merge` call and fails.
- **Invariant to restore:** Merge mode merges a PR only on a green rollup verdict that has
  held across two reads one poll interval apart — a single green reading is not evidence,
  because it can be a partial rollup that is still changing. **Known residual (not fixed
  here, and Check must not count the issue as fully closed by this):** the confirm compares
  verdicts only, so a slow job that has not registered within one poll interval still gets
  through (`green(dco)` → `green(dco)` merges), and so does a confirm that is green on a
  different check set (`green(dco)` → `green(dco, e2e)`). Closing that needs check-name
  comparison or a configured expected-check list — out of scope below.
  Source: internal project rule (Tier C) — the merge-mode contract in the module docstring
  (`merge.py:19-31`: "refuses on any failing, pending or missing check … absence of evidence
  is not green") and #462's wait (`merge.py:33-42`).
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Ordering note:** No `Depends on` / `Conflicts with`: this batch (582, 589, 593, 597) runs
  as ONE wave (the v0.58.0 instance driver carries #593's multi-wave stacking bug). 582
  touches `merge.py`, `tests/test_merge.py`, the `merge_wait_secs` comment in
  `template/pdca.toml.jinja` (`:144-151`) and the `Config.merge_wait_secs` comment in
  `config.py` (`:375-381`). Checked against the other three briefs' file sets: none touches
  `merge.py`/`test_merge.py`/`config.py`; 593 edits `pdca.toml.jinja:176` (the sweep
  rationale), about 25 lines below 582's hunk — separate hunks, so they fold cleanly.
- **Surfaces:** data
- **Difficulty:** low
- **Scope:** Make `_wait_for_green` confirm a green before returning it, per (i)–(iv) above,
  and update its docstring and the module docstring's description of the wait
  (`merge.py:33-42`) to say a green is confirmed once, and the two operator-facing comments
  that describe the wait rule ("re-reads the rollup until it clears pending/empty"):
  `template/pdca.toml.jinja:144-151` and `template/src/pdca_harness/config.py:375-381`. / out
  of scope: comparing check NAMES
  or counts between reads, or waiting for a configured list of expected checks (a richer
  design — file separately if wanted); changing `poll_interval` (15 s) or the
  `merge_wait_secs` default (300); stack mode (`integrate.fold`), which never merges.
- **Repro instruction:** In `tests/test_merge.py`'s fixture (`_cfg` `:41-48`, `_bundle`
  `:86-94`), patch `pdca_harness.merge.subprocess.run` so `gh pr checks` returns
  `_rollup(("dco", "pass"))` on read 1 and
  `_rollup(("dco", "pass"), ("e2e", "fail"), code=1)` from read 2 on; patch `merge._sleep`,
  `merge.state.state` → COMPLETE, `merge.merged.is_merged` → False; call
  `merge.merge_wave(cfg, [b])`. On `main` it returns 0 and calls `gh pr merge` after a single
  rollup read.
- **External dependencies:** none
- **Test file:** `template/tests/test_merge.py` (append new cases to the `MergeWave` class,
  including the (iii) unconfirmed-green refusal text; update the two tests named in (v);
  patch `merge._sleep` in `setUp`). The C4 gate
  reverts only production hunks and runs every test module the patch touches, so appended
  cases earn their red. Use only existing API (`merge.merge_wave`, `merge._sleep`) — no new
  symbols imported at module level.
- **Citations expected:** Do must cite path:line on the target branch for every change. The
  change sits in `_wait_for_green` (`merge.py:143-160`); its only caller is `_merge_one`
  (`merge.py:229-231`), whose refusal messages (`merge.py:232-249`) must still read right
  for a `pending` returned by (iii) — the detail text for that case is fixed in (iii).
- **Prior-art check (triage cycles):** Merged history by path —
  `git -C ../pdca-harness log --oneline origin/main -n 5 -- template/src/pdca_harness/merge.py`:
  `87c7352` (#462, added the wait — the code this fixes), `2261b53` (#413, the rollup gate),
  `126db1f` (#279), `5c4e332` (merge mode). Closed-unmerged PRs touching `merge.py`: none.
  No open PR. The fix is carried downstream on getwyrd/wyrd-pdca as an instance delta (found
  by review of getwyrd/wyrd-pdca#253). Result: not fixed upstream, not in flight.
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.

Plan-review response: all six findings accepted and folded in — second test update and
the `setUp` sleep patch named in (v); invariant narrowed with the residual stated; (iii)
detail text and the small-budget behaviour change stated; operator comments added to scope;
Ordering note re-checked against the other three briefs' file sets.

## Iteration 1 — carry-forward (from the previous attempt)
- Sign-off rationale: Rejected for the C3 boundary gap found in review: when the remaining merge_wait_secs budget is less than one poll_interval, the confirm sleep is shortened via min(poll_interval, wait_secs - waited) (merge.py:182), so the confirm read lands 1-14 s after the first green (e.g. budget 1: green->green merges after 1 s; budget 20: pending->green->green merges after a 5 s confirm). That breaks the brief's "re-read one poll interval later" promise. Next attempt: only take the confirm read when a FULL poll interval of budget remains; if it does not, return the green as `pending` with the "unconfirmed" detail (same path as the no-budget-left case). Add tests through merge.merge_wave for both boundaries (budget 1 with green,green and budget 20 with pending,green,green -> both refused, no merge, ready undone). Everything else in the patch was accepted as-is; keep it.
- Sign-off session carry-forward (captured live, before §9 flattened it):
  Rejected for the C3 boundary gap found in review: when the remaining merge_wait_secs budget
  is less than one poll_interval, the confirm sleep is shortened via min(poll_interval,
  wait_secs - waited) (merge.py:182), so the confirm read lands 1-14 s after the first green
  (e.g. budget 1: green->green merges after 1 s; budget 20: pending->green->green merges after
  a 5 s confirm). That breaks the brief's "re-read one poll interval later" promise.
  Next attempt: only take the confirm read when a FULL poll interval of budget remains; if it
  does not, return the green as `pending` with the "unconfirmed" detail (same path as the
  no-budget-left case). Add tests through merge.merge_wave for both boundaries (budget 1 with
  green,green and budget 20 with pending,green,green -> both refused, no merge, ready undone).
  Everything else in the patch was accepted as-is; keep it.
- Full previous attempt preserved in `iteration-v1/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).
