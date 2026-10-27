# Build notes — issue 395 / same-wave-conflict-refused-at-accept (iteration 7)

Target: `eduralph/pdca-harness @ main`, worktree base `a6af7f3` (the brief's origin/main).
Line numbers are in the patched worktree (`$PDCA_WORKTREE`) unless marked "main", which
means the unpatched base `a6af7f3`.

Inputs read: `brief.md` and its `## Iteration 6 — carry-forward` block. The carry-forward
names `iteration-v6/` as the preserved previous attempt and its bugs by v6 line number, so
I read `iteration-v6/patch.diff` (the base of this attempt), `iteration-v6/build-notes.md`,
and the two advisory reviews the carry-forward summarises
(`check-advisory-adversary.md`, `check-advisory-code-review.md`) for the exact findings.
I did not open `iteration-v5/patch.diff` this time (v6 already reused its mechanics), nor
the stray `test_flow_same_wave_prepublish.py`; it is not in the patch.

## What this iteration changes

The design held at sign-off; the human asked for three implementation fixes. I started
from the v6 patch (applied cleanly on `a6af7f3`) and changed only what the three fixes
need, plus one Ctrl-C hole I found while doing fix 3.

### Fix 1 — a session that raises is not "the one more session"

v6 counted the session before `leaves.run_signoff_batch` ran (v6 flow.py:2733-2734), and
the `except` did not undo it. Now the count is in the `try`'s `else:` (flow.py:2778-2783):
only a session that returned is counted. It still runs before the post-session apply
(flow.py:2784-2786), so a new refusal that apply makes gets its own one more session, as
in v6. A chunk whose session raised counts no bundle of it: we cannot tell which bundles
the leaf reached before it died, and offering another session is the safe side (it is what
a plain C6 refusal gets after a dropped session). `_session_offered` docstring:
flow.py:410-416.

### Fix 2 — a later run parks the bundle after one session, not at the pass budget

v6 deleted `same-wave-refusal.json` at wave start (v6 flow.py:2673-2675). On a re-run the
refused bundle then had no record, so C6 refused it every pass until the budget ran out,
with the "raise [driver].max_passes" hint. Now the wave resets the count to 0 and keeps
the record (`_sessions_reset`, flow.py:419-426, called at flow.py:2714). Each run offers
the bundle one session; if it records nothing new, `_parked` (flow.py:429-445) holds and
the wave-end line names the conflict step. This works with or without `trial`: on the
re-run the bundle is alone in a one-wave run, so `trial` is None, but parking only needs
the record and its row still open in §6.

The record now stores the exact `why` and `step` sentences the refusal printed
(flow.py:339-340), and `_report_parked` prints them (flow.py:448-461), so the wave-end line
of a later run says what the refusal said, for each kind of refusal (including the new
tree kind below). `_refusal` requires `item`/`why`/`step` strings and an int `sessions`
(flow.py:396-407). The wave-end wording changed from "the sign-off session after that" to
"the sign-off session it was offered since", which reads right on a re-run too.

`state.py:62-69` (the record's comment) and the `_drive_wave` docstring
(flow.py:2698-2709) say the count is reset, not dropped.

### Fix 3 — a broken integration tree is refused and named, never a fallback accept

v6 caught every `integrate.IntegrationError` at v6 flow.py:303, so
`IntegrationTreeError` (main integrate.py:101) and `_LineBroken` (main integrate.py:110)
went to the shared-path fallback and could accept. The fold treats both as "the tree is in
an unknown state, stop": it re-raises them even under `skipped` (main integrate.py:671-673),
and the flow stops the run on them (main flow.py:3001-3006 for a base build, main
flow.py:3118-3125 for a fold).

Now `_refused_for_wave` catches those two first (flow.py:306-308) and refuses the bundle
whatever files it shares, with a row of kind `"tree"` (`_refusal_words`,
flow.py:351-384). The row names the accepted same-target siblings it could not be checked
against (`integrate.same_wave_siblings`, integrate.py:848-860), the tree's state in the
error's own words, and the step: check that checkout (or remove it to have it recreated),
then tick the row and accept again. It goes through the same `_refuse` (flow.py:329-343)
as the other kinds, so a ticked row is still an override, and the refusal is recorded and
parked like any other (one more session, then the wave-end line with this step). Every
other `IntegrationError` (a lock, a fetch, a commit that does not build) still falls back
exactly as in v6 (flow.py:309-317), and leg (e) is unchanged.

Chaining (the code review's second point): `_back_on` (integrate.py:953-982) now takes the
step it follows (`after`) and the error already on its way out (`first`). When it cannot
put the tree back, the error it raises is `raise … from first` and its message and `cause`
end with "(after an earlier failure: <first cause>)", so the row still says what failed
first. `_would_be` (integrate.py:909-923) and `same_wave_clash` (integrate.py:827-835) use
`except BaseException as exc: _back_on(..., first=exc); raise` instead of
`try/finally`, which is what gives them `first`. The success path calls `_back_on`
once more, as the `finally` did. `_would_be`'s restore is now `_back_on` too (it adds a
`reset --hard` to the tip the branch already has, a no-op).

Ctrl-C (found while doing the above, not in the carry-forward): with `try/finally`, and
with the new chaining, a restore that fails during a `^C` replaced the
`KeyboardInterrupt` with a `_LineBroken`, which `_isolate` (main flow.py:52) contains, and
which `_refused_for_wave` now refuses on — so the run would carry on after the human
pressed Ctrl-C. `_back_on` never replaces a `first` that is not an `Exception`: it puts
the tree back if it can and returns, and the caller raises the `^C` on
(integrate.py:964-967). No test drives this (it needs a signal mid-trial); it is 4 lines.

One reclassification: in `same_wave_clash`, a failed `checkout -B <line> <start>` was
`IntegrationTreeError` in v6. The fold raises a plain `IntegrationError("could not
start …")` for the same step (main integrate.py:614-615); the tree was reset just before
and the step did not run, so it is a failed git step, not an unknown tree. It is now a
plain `IntegrationError` (integrate.py:816-820), which falls back as a fetch failure does.
Left as v6 had it, fix 3 would have turned that into a fail-closed refusal of every
candidate. An unreadable tip after it stays `IntegrationTreeError`, as in the fold (main
integrate.py:650).

#### Why refuse-and-name, not re-raise

The carry-forward allows either ("Re-raise those two (or name the tree state) instead of
falling back"). I chose to refuse and name the state because of where a re-raise goes:

- `_refused_for_wave` runs inside `_apply_decision`, which `_drive_wave` calls through
  `_isolate` on both accept routes (flow.py:2766-2768 and :2784-2786). `_isolate` contains
  every `Exception` (main flow.py:52-73). A re-raise therefore does not stop anything: the
  bundle is "skipped" for the pass with no session (only `UNDECIDED`/`"blocked"` get one,
  flow.py:2769-2770), and the next pass runs the trial again. A tree that stays broken
  spins the wave to the pass budget and ends with "raise [driver].max_passes" — the exact
  outcome fix 2 removes. Measured below.
- Making the re-raise stop the run instead would mean letting it past `_isolate` and
  catching it around `_drive_wave` in `_drive_and_act`. The bundles of the wave accepted
  before the trial broke are COMPLETE and not yet published at that point, so a stop there
  would leave accepted bundles with no PR, which the human ruled out at this Plan. Doing it
  right means publishing the wave first and stopping before the fold — and the fold already
  stops the run on a tree that is still broken (main flow.py:3118-3125). So the run already
  stops at the right place; the trial's job is only to accept nothing on a broken tree.

Refuse-and-name is bounded by the same parking as any refusal, prints the tree state and
its step, and leaves the run-stop to the fold, which happens after every accepted bundle
has its PR.

Experiment (the cost, measured, not argued). Same scenario both times: wave 0 = 10
(`shared.txt`) and 12 (`twelve.txt`), wave 1 = 20 depending on 10, all with a recorded
`accept`, `max_passes = 20`, and every trial of 12 breaking the tree (its `git apply`
fails, then the restore's `checkout -q <line>` fails once). Run as a subclass of the
shipped test class, from stdin (nothing written to disk); the re-raise variant was a
temporary 3-line edit of flow.py:306-308 to `except (…): raise`, reverted afterwards
(worktree checked byte-identical to `patch.diff`).

| | re-raise | refuse-and-name (this patch) |
|---|---|---|
| trials of issue_12 (each a fetch + builds + merges under the lock) | 20 | 1 |
| "skipping this bundle" lines for issue_12 | 20 | 0 |
| sign-off sessions offered to issue_12 | 0 | 1 |
| "raise [driver].max_passes" on stderr | yes | no |
| wave-end line naming the tree state and step | none | yes |
| issue_12 accepted / published | no / no | no / no |

Both fail closed. Re-raise never shows the human a session or the tree's state in §6,
and ends on the pass-budget hint.

## Carried from v6 unchanged

The accept-time trial and refusal (`_AcceptTrial` flow.py:137; `_apply_decision`'s check
after C6 flow.py:206; the record removed once a decision is recorded flow.py:223; both
accept routes passing `trial`, flow.py:2765-2768 and :2784-2786; the trial condition
flow.py:3289-3292), the fold-rule trial in `integrate.same_wave_clash`
(integrate.py:755-845) with `_wave_holds` (:926-950), the shared-path fallback
`same_wave_overlap` (:863-885, now built on `same_wave_siblings`), `publish._checkout_base`
/ `cut_base` (publish.py:767, :779, publish's own call at :262), `state.SAME_WAVE_REFUSAL`
in `DOWNSTREAM_OF_BRIEF` (state.py:158), and the docs paragraphs. See
`iteration-v6/build-notes.md` for their rationale; nothing there changed. The human kept
the brief's hold-count rule (`len(held) <= len(alone)`, integrate.py:836) and the
override loophole, and moved the split-during-last-wave case to a follow-up.

Docs (`docs/07-crosscutting.md:733-748`): the same-wave paragraph now says a session that
fails is not the one more session, that a later run does the same while the row is open
(one session, then the step, not the pass budget), and that a check that leaves the
integration checkout in a state it cannot put back refuses the bundle whatever it shares,
with a row naming that state and its step.

## Test → success criterion

`template/tests/test_flow_same_wave_accept_trial.py` (copy in the bundle). Same fixture and
stubs as v6: real git (`StackFoldGit`), `gh` stubbed, publisher in `command` mode, every
accept through the real `flow._drive_and_act` → `_drive_wave` → `_apply_decision`; the test
never calls `signoff.record(... "accept")` and does not stub `_drive_wave`. Only modules are
imported. The one new symbol a leg touches (`integrate.same_wave_clash`, wrapped by a
pass-through spy in the tree leg) is read with `getattr` and patched with `create=True`, as
the fixture's own `_merged_heads` does for a symbol absent before a fix
(`test_integrate_stack_bases.py:116`), so the red leg fails on an assertion, not an
`AttributeError` (my first run had the `AttributeError`; fixed).

| Leg | Test (line) |
|---|---|
| (a) | `test_a_conflicting_accept_is_refused_and_its_sibling_published` (233) |
| (b) | `test_a_shared_file_that_merges_cleanly_is_accepted` (255) |
| (c) | `test_the_refusal_does_not_depend_on_which_accept_comes_first` (271) |
| (d) | `test_ticking_the_row_accepts_it_and_the_fold_holds_it` (291) |
| (e) | `test_a_trial_that_cannot_run_refuses_only_a_bundle_sharing_a_file` (306) |
| fix 3 (new) | `test_a_check_that_breaks_the_tree_refuses_and_names_it` (331): 12 shares no file with accepted 10; building 12's would-be commit fails (`git apply`), then the restore's `checkout -q <line>` fails once → `_LineBroken`. 12 is refused (not published, no fallback "shares no file" line); its row names `issue_10`, the tree state ("could not put back"), the first cause ("does not apply") and "check that checkout"; the error `same_wave_clash` raised is a `_LineBroken` whose `__cause__` is the `IntegrationError` from the apply; the tree is clean on the line when 12's session opens; 10 and 20 publish; exit 1 |
| (f) | `test_a_reassembled_summary_drops_the_row_and_the_next_accept_refuses_again` (389) |
| (h) | `test_a_refused_bundle_gets_one_more_session_then_the_wave_ends` (418) |
| fix 1 (new) | `test_a_session_that_fails_is_not_the_one_more_session` (440): 11's first session after the refusal raises; it is offered a second, which runs; then parked. Exactly one "session over ['issue_11'] failed" line, `sessions_had["11"] == 2`, record `sessions == 1`, one wave-end line, no pass-budget line |
| re-run (v6) | `test_a_later_run_offers_the_refused_bundle_a_session_again` (464): the re-run where the human ticks and accepts |
| fix 2 (new) | `test_a_later_run_parks_the_refused_bundle_after_one_session_too` (478): the re-run where the row stays open, `max_passes=20`: exactly one session, the row still open, one wave-end line naming `issue_10`, `` `Conflicts with: 10` `` and `iterate-plan`, no `max_passes` / "pass budget exhausted", exit 1 |
| plain C6 | `test_a_plain_c6_refusal_is_still_offered_a_session_every_pass` (503) |
| (g) | `test_on_the_last_wave_both_are_accepted_and_published` (517) |

## Refuting my own test

- **(a) Genuine red? Yes.**
  - C4 through the project's gate (`engine/scripts/run-verify.sh`, `PDCA_BUNDLE` /
    `PDCA_WORKTREE` set, under `timeout`): green leg 13 tests OK; red leg (production
    hunks reverted, test kept) 13 ran, 10 FAIL, 0 errors, no import failure →
    `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`. The 3 green on main are
    (b), plain C6 and (g), which by design pass on both sides.
  - Against v6's production code (the three bugs in place) with this test file: 13 ran,
    exactly the three new legs FAIL, each for its bug — the tree leg: `'COMPLETE' !=
    'AWAITING_SIGNOFF'` for issue_12, after v6 printed "the same-wave conflict check could
    not run (could not put … back …); accepted, as its change shares no file"; the re-run
    leg: `20 != 1` sessions (the spin to the budget); the dropped-session leg: `1 != 2`
    sessions (the dropped one counted).
  - One fix undone at a time on the final code (each reverted afterwards; the worktree was
    checked byte-identical to `patch.diff` after each): A, count a session even when it
    raised → only the dropped-session leg fails; B, delete the record at wave start → only
    the re-run-parks leg fails; C, let tree errors fall to the fallback → only the tree leg
    fails (`COMPLETE`); D, drop the chaining and the first cause from `_back_on` → only the
    tree leg fails.
- **(b) Production path? Yes.** The real `_drive_and_act` → `_drive_wave` →
  `_apply_recorded_decision` / `_apply_decision` → `_refused_for_wave` →
  `integrate.same_wave_clash` (real git in the real integration worktree under the real
  `integ_lock`, real `_would_be` / `_back_on`) → `_refuse` → `signoff.ensure_needs_human_item`
  / `open_needs_human`; then the real `_parked` / `_report_parked`, the real publish loop,
  the real fold. Stubbed: Do/Check (`_build_all`), the sign-off leaf, publish's mechanics,
  `gh` — none of them code this change touches. The tree leg's fault goes through
  `integrate._git` (the trial's own git call), and its spy on `same_wave_clash` calls the
  real function and only records what it raised.
- **(c) Fixture includes the fault? Yes.** The tree leg really fails the trial's `git
  apply` and the restore's `git checkout` in the real worktree, so the real
  `_LineBroken` is raised and chained by production code; the partner (10) is accepted and
  published in the same wave. The dropped-session leg's leaf really raises inside
  `run_signoff_batch`. The re-run leg is a second real `_drive_and_act` over the same
  bundles, with 11's refused `accept` and its open row still on disk.

## Suites and commit readiness

- T3 (`engine/scripts/run-suite.sh`, both target suites, under `timeout`): root 24 tests
  OK, driver 2643 tests OK (skipped=2) — v6's 2640 plus the 3 new legs —
  `PDCA-EVIDENCE: root suite OK, driver suite OK`, rc=0.
- T2 (`engine/scripts/run-docs-check.sh`): `lint_docs: OK`, `render_site: link audit OK`
  (22 pages), rc=0.
- C4 (`engine/scripts/run-verify.sh`): `PDCA-EVIDENCE: C4 PASS` (see "Refuting" above).
- `git diff --check` clean; no added line over 100 columns (the code's wrap).
- The target configures no formatter, linter or pre-commit hook: no
  `.pre-commit-config.yaml`, no ruff/flake8/black/mypy config, no `core.hooksPath`, only
  sample hooks in `.git/hooks`. Its CI runs the docs check (`docs-check.yml`) and the
  suites (`render-check.yml`), which T2/T3 cover. Publish's own `git commit -s` adds the
  DCO trailer.
- `patch.diff` was checked to apply cleanly to `a6af7f3` (`git apply --cached --check`
  with the index at the base), and the bundle's copy of the test is byte-identical to the
  one in the patch.

## Known limits (unchanged from v6 unless noted)

- The split-during-last-wave case (trial off, fold on after `_adopt_split_children`) is a
  follow-up, per the human's decision.
- The hold-count rule's override loophole is accepted as is, per the human's decision.
- New: a broken tree refuses the bundle until the human ticks the row (or a reassembly
  drops it). If the tree was broken only for a moment, that is one tick more than a
  re-raise would cost; the trade is in "Why refuse-and-name" above.
- `_trial` (main code, used by `_held_by` inside the trial) still raises its own
  `_LineBroken` from a `finally` without chaining (main integrate.py:2132-2136). The
  carry-forward asked for `_would_be` / `_back_on`; `_trial` is the fold's and is unchanged.
  A `_LineBroken` from it during the trial is still caught as a tree error and refused, and
  the trial's own `_back_on` then chains to it.
- The PR should say `refs #395`, not `closes`: this is a partial fix (brief, Goal).
