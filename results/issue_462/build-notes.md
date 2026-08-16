# Build notes — issue 462 / merge-wave-waits-for-its-evidence

## What I built

Three surfaces, all in `template/src/pdca_harness/` and `template/pdca.toml.jinja` on
`eduralph/pdca-harness @ main` (worktree HEAD `acb214a`):

1. **The wait** (`merge.py:143-160`, new `_wait_for_green`). `_merge_one`'s rollup read
   (`merge.py:231`, was `merge.py:177` pre-patch) now calls `_wait_for_green(pr_url,
   cfg.merge_wait_secs)` instead of a single `_check_rollup`. It re-reads the rollup
   (`_check_rollup`, unchanged, `merge.py:82-130`) in a loop while the verdict is
   `pending`/`empty` and the configured wall-clock budget hasn't been exhausted, sleeping
   between reads through a module-level `_sleep = time.sleep` (`merge.py:58`) so a test can
   replace it with a no-op and pay zero wall-clock. `wait_secs <= 0` short-circuits to a
   single read — today's original behaviour, preserved byte-for-byte for the (documented)
   opt-out.
2. **The undo** (`merge.py:163-175`, new `_undo_ready`). Every path in `_merge_one` that
   returns 1 *after* the `gh pr ready` call at `merge.py:210` now calls `_undo_ready(pr_url)`
   first: the rollup-refusal path (`merge.py:248`, covers failing/unreadable/timed-out
   pending/timed-out empty — one call site, one undo) and the `gh pr merge` failure path
   (`merge.py:261`). The ready-failure path (`merge.py:211-216`, `ready.returncode != 0`) and
   the pre-ready returns (not-COMPLETE, no-patch, no-PR-URL, dry-run, already-merged) are
   untouched — nothing was readied on those paths, so there is nothing to undo, matching the
   brief's "(iii) …an already-merged or dry-run path readies nothing and undoes nothing."
3. **The config knob** (`config.py:369-376` field, `config.py:713-727` loader,
   `config.py:836` constructor, `pdca.toml.jinja:142-153` docs) — `[driver].merge_wait_secs`,
   plumbed through `Config` exactly the way `merge_requires` already is (brief's cited
   composition cue, `config.py:361-368`/`:703-707`/`:813` pre-patch). Default `300`; `0`
   disables the wait. A bad value (unparseable or negative) fails CLOSED to the *wait*
   default (300s), the same "typo must not silently buy back the old behaviour" reasoning
   `merge_requires`'s own coercion already uses at `config.py:704-707` pre-patch — except
   there the safe fallback is "all" (verify) and here it's "wait, don't rush" (also verify);
   both land on the side that never skips the evidence check.

## Message wording (success criterion ii)

The three refusal strings in the `why` dict (`merge.py:233-240`) keep the *substrings* the
existing suite already asserted on (`"not finished"` for pending, `"EMPTY"` for empty,
`"FAILING"` for failing) but now append `within {merge_wait_secs}s` on the two
evidence-never-arrived paths (pending, empty) and leave `failing`/`unreadable` unchanged —
that's the brief's "distinguishes 'the checks never reported within Ns' from 'a check is
red'" (success criterion ii), and it costs zero new vocabulary: a message that already said
"a check is FAILING" stays exactly that (a red check is a genuine, immediate stop — the
brief's own out-of-scope line: "retrying a *failing* check").

## What I ruled out

- **A separate `poll_interval` config knob.** The brief only asks for the *bound* to be
  configurable ("The bound is new configuration — plumb it through `Config`..."); a second
  knob for the retry cadence is out of scope and would be one more coercion block, one more
  doc paragraph, and one more test axis for something the brief never asked to be tunable. I
  hardcoded `poll_interval=15` as a `_wait_for_green` default parameter instead — 6 lines,
  not a new `[driver]` key.
- **`gh pr merge --auto`.** Explicitly out of scope in the brief (`brief.md:88-91`) — I did
  not touch it.
- **Reading `time.monotonic()` for the elapsed-time check.** I track `waited` purely as an
  accumulator of the `step` values already fed to `_sleep`, never a wall-clock read. This
  means the loop's notion of "elapsed" is *exactly* what it slept, which is what makes the
  whole thing zero-cost under a test's no-op `_sleep` — a `time.monotonic()`-based version
  would need the *clock* patched too (a second seam), for no behavioural gain in production
  (the two are equivalent there, since `_sleep` really does block for `step` seconds).
- **Renaming `test_pending_check_refuses`.** The brief says "update
  `test_pending_check_refuses`, whose current assertion **is** the defect" — I kept the name
  and inverted the body (asserts the bound is honoured, the wait actually happens > 1 read,
  and the ready-mark is undone) rather than adding a same-behaviour twin under a new name.

## Refutation (forced, before declaring done)

**(a) Genuine red?** Yes. `cd $PDCA_WORKTREE && git stash push -m x --
template/src/pdca_harness/merge.py` (reverts ONLY production, keeps every
`template/tests/*.py` hunk — mirrors C4-verify's red leg per
`engine/scripts/run-verify.sh:214-217`), then
`cd template && PYTHONPATH=src python3 -m unittest tests.test_merge -v`:
**6 failures** (`test_pending_check_refuses`, `test_pending_then_green_merges`,
`test_wait_bound_zero_performs_no_wait`, `test_failing_check_refuses_and_never_merges`,
`test_merge_failure_stops`, `test_check_triggered_by_the_ready_mark_is_caught`), all genuine
`AssertionError`s against the mock's recorded `calls`/`err` (not import errors — see the
`create=True` note below), 0.014s (no real sleep even pre-fix). `git stash pop` restored the
fix; the full suite (`python3 -m unittest tests.test_merge -v`) is green again, still
0.014s, and the whole offline suite (`python3 -m unittest discover -s tests`, 1761 tests) is
`OK (skipped=2)`.

**(b) Production path?** Yes. Every new/updated assertion drives `merge.merge_wave` →
`_merge_one` → the real `_wait_for_green`/`_undo_ready`/`_check_rollup`, through the same
`_gh`/`_rollup` mock harness (`test_merge.py:60-73`) the rest of the suite already uses — no
parallel re-implementation. The one seam is `merge._sleep`, patched via
`mock.patch.object(merge, "_sleep", create=True)` — `create=True` because pre-fix `merge.py`
has no `_sleep` attribute at all; without it, every `_drive`-based test would fail with an
`AttributeError` (a real, but uninformative, kind of red) instead of the content-based
`AssertionError`s above. `_sleep` is a thin, honest indirection over `time.sleep` (never
replaced by a fake clock or a stubbed `_wait_for_green`), so the test still exercises the
genuine wait loop, retry count, and bound arithmetic — it only removes the wall-clock cost
of the `time.sleep` call itself.

**(c) Fixture includes the fault?** Yes. The fixture is `_rollup(("ci", "pending"), code=8)`
— the exact shape `_check_rollup` sees for "checks not registered yet," which is the fault
the brief's incident names (getwyrd/wyrd#703, checks still `pending`/`queued` six seconds
after `ready_for_review`). `test_pending_then_green_merges` additionally injects a rollup
that *changes across reads* (pending twice, then green), which is what actually exercises
the retry loop rather than a fixture that's pending once and stays pending forever by
construction.

## Formatter / commit-readiness

No `.pre-commit-config.yaml`, `pyproject.toml`/`setup.cfg` linter config, or documented
Python formatter exists in the target checkout (checked: `find . -iname
'.pre-commit*'`/`pyproject.toml`/`.flake8` under the worktree root — none). Line lengths in
every touched file stay within the file's own pre-existing max (`merge.py` topped out at 95
chars before this patch, 96 after — `test_merge.py` similar); `python3 -m py_compile` and
`ast.parse` both pass clean on all three touched files.

## External dependencies

None beyond what the brief already declares. No `gh` binary, no network, no merge rights
were used or needed — every `subprocess.run` call in the test suite is mocked.
