# Build notes — issue 532 (iteration 3): an attempt is the unit of accountability

Withheld from the reviewer. Every `path:line` below is the **target branch**
(`eduralph/pdca-harness` @ `main`, base `acb214a`) as edited in `$PDCA_WORKTREE`
(`/home/eddie/pdca/pdca-harness.pdca-wt-l0`); line numbers are post-patch unless the text
says "on the base".

## 0. What this round is

The slice was accepted in shape twice and rejected twice on implementation. Iteration 2's
sign-off says so explicitly: *"the shape is right and all six of the previous round's
carry-forwards are genuinely closed with real red→green tests; what remains are local code
defects"*. So this round **keeps** the v2 mechanism (retry wrapper for the builder,
per-attempt flush, residue-aware prompt, state-derived report, attempt-owned harvests) and
fixes the five named defects plus the two non-blocking notes, under the binding scope
constraint about the prose.

Nothing was re-cut and nothing rejected was re-submitted unchanged: every one of the five
findings is a code change here, and each is bound by a test that **fails when the v2
behaviour is restored** (§3, mutation table).

## 1. The five must-close findings

| # | Finding (iteration 2 sign-off) | Fix | Where |
|---|---|---|---|
| 1 | Retry started even when the attempt record failed to write | `_write_attempt_records` now **returns** whether the write landed; the loop starts attempt N+1 only if `may_retry and recorded` | `leaves.py:790-797`, `:826-850` |
| 2 | Unguarded stderr write could replace the exception criterion (i) pins | both prints are under `contextlib.suppress(OSError)` — the retry notice in the wrapper and `_report_transient_do_death` in `do_build` | `leaves.py:799-805`, `:1993-2000` |
| 3 | The report asserted authorship it cannot know | the residue line names the files and says they **may predate this attempt**; no "the interrupted attempt left …" | `leaves.py:2065-2073` |
| 4 | Signal-death carve-out was one wrapper deep (`rc < 0` only) | `_died_of_a_signal` reads **both** spellings: negative *and* 128+N (137/143 from `sh -c` / `docker run` / `local-build`) | `leaves.py:2020-2033` |
| 5 | A leaf that finished was left flagged "in flight" | the retained-log success path re-flushes with `in_flight=False`; and the predicate is now **anchored on the last non-empty line** instead of a substring sniff, with the quoted marker defanged in embedded artifact text | `leaves.py:775-779`, `:853-867`, `:818-823` |

Details worth the reviewer's (and the human's) attention:

* **(1) is the patch's central invariant.** `recorded` gates the retry the same way `owned`
  already did. When the write fails the loop stops, the leaf's own exception is still
  returned/raised, and the operator is told *why* it stopped ("not starting another attempt
  without its predecessor's account on disk", `leaves.py:843-848`). `do_build`'s
  `if not _has_content(error_log)` guard still captures the final failure when nothing
  landed (`leaves.py:1980-1988`).
* **(2)** `_report_transient_do_death` sits *outside* the existing
  `try: … except OSError: pass` deliberately: putting it inside would mean a failed
  `error_log.write_text` skips the report entirely. It has its own suppressor instead, so
  a bundle whose log cannot be written still gets the operator sentence, and a broken
  stderr still yields the `LeafError` to `flow._isolate`.
* **(3)** Because the message no longer claims authorship, the report needed another way to
  say what it *does* know: how many attempts were actually spent. The wrapper stamps that
  on the exception (`_stamp_attempts` / `_attempts_spent`, `leaves.py:681-700`) and the
  report prints "after N attempt(s)" — true both when the budget was exhausted and when the
  loop stopped early under (1). "the bounded retries are exhausted" (v2's wording) would
  have been false in the (1) case, i.e. the same class of defect as the one being fixed.
* **(4)** I chose to **widen** rather than document the hole. Cost of widening, stated
  concretely: a leaf that *chooses* an exit status in 128..255 is not retried — one spawn,
  re-raised, byte-identical to today's behaviour for it. Cost of not widening: an OOM
  SIGKILL one wrapper deep is retried 3× (repeating whatever exhausted the bound) while
  stderr asserts "infra the harness absorbs". The asymmetry is decisive, and the direction
  of the residual error is fail-safe. #510 is untouched: this **declines** to retry a
  signal death, it does not classify it.
* **(5)** The re-flush is one line. The anchoring is the substantive half: the log embeds up
  to `_RESIDUE_KEEP` (20 000) characters of a leaf's own text, and in *this* repo the leaves
  review this file, so a verdict quoting the marker is an ordinary day. Two layers, each
  closing a hole the other cannot: anchoring covers the marker appearing anywhere in a
  **stderr tail** (`_format_leaf_attempt` writes those verbatim); defanging covers a
  **withdrawn artifact** whose last line *is* the marker, which would otherwise be the log's
  last line. Both are proven necessary by mutation (§3, rows E and F).

## 2. The scope constraint (prose belongs to sibling 533) — how it was honoured

Binding instruction: do **not** touch the `_invoke_leaf_resilient` docstring or the
retry-backoff print line.

* **Docstring: untouched, byte for byte.** `git diff -U2` produces no hunk inside it (the
  hunks are the signature at `-679,4` and the body at `-703,23`). The three new keywords are
  documented in a **comment block above the `def`** instead (`leaves.py:703-721`) — a
  different line range, so 533's docstring rewrite applies over it.
* **Retry-backoff print: prose byte-identical.** The only change is +4 indentation from the
  `with contextlib.suppress(OSError):` that finding (2) requires. I could not find a way to
  guard it without touching those lines (wrapping the whole loop would swallow the
  `FileNotFoundError` startup failure the wrapper must *return*, and extracting a helper
  would delete the lines outright — a bigger collision). Because the message text is
  unchanged, this patch **cannot** regress 533's wording in any merge resolution: there is
  no competing wording to win.
* **The label-prefix improvement (`kw.get('label') or workdir.name`) was dropped**, though
  the sign-off allowed keeping it. Rationale: it is the only part that would have changed
  the message *text*, it needs 533's classification wording to be applied correctly, and it
  is a one-token change 533 can fold in while it is rewriting that line anyway. The v2 test
  assertion on `"Do issue_506"` went with it.

## 3. Refuting my own tests (forced record)

**(a) Genuine red?** Yes — via the project's own C4 gate, which reverts the production hunks
and keeps every test hunk (`engine/scripts/run-verify.sh:214-217`):

```
== C4 green leg: test_build_error_log.py test_leaf_resilience.py → Ran 14 OK / Ran 29 OK
== C4 red leg  (production reverted)                             → FAILED (1F,1E) / FAILED (13F,7E)
PDCA-EVIDENCE: C4 PASS — red without the fix, green with it
```

No `unittest.loader._FailedTest` in either leg, so nothing was recorded `PDCA-UNVERIFIABLE`:
the appended cases import no symbol this patch adds at module level (every new name is
reached as `leaves.<name>` at call time).

Because the red leg only proves the cases fail *without the whole patch*, I additionally
mutated the fix back to each v2 defect and re-ran both files. Every one is caught — the
tests bind on **this round's** changes, not merely on the slice:

| Mutation (restore the v2 behaviour) | Caught by |
|---|---|
| A `_died_of_a_signal` → `rc < 0` only | `test_a_signal_death_reported_one_wrapper_deep_is_not_retried_either` |
| B success path never re-flushes | `test_a_finished_loop_is_never_left_flagged_in_flight`, `test_a_dead_attempts_artifact_ending_in_the_marker_is_not_the_trailer` |
| C retry not contingent on the record landing | `test_a_retry_never_starts_without_its_predecessors_account_on_disk` |
| D exhausted-retry report left unguarded | `test_a_broken_stderr_never_replaces_the_builders_own_failure` |
| E in-flight predicate back to a substring sniff | `test_a_leaf_whose_stderr_quotes_the_marker_is_still_read_as_spent` |
| F residue text no longer defanged | `test_a_dead_attempts_artifact_ending_in_the_marker_is_not_the_trailer` |

(Mutation harness: rewrite one anchor in `leaves.py`, run both test modules, restore. It was
run twice — after the first run E and F were *not* caught, which showed the two fixtures were
too weak: the marker sat mid-line and mid-body, where either layer alone saves it. I
strengthened them — artifact ending **on** the marker line for F, marker inside a **stderr
tail** for E — and both then bound. That failure-then-fix is exactly why this step is worth
doing rather than asserting.)

**(b) Production path?** Yes. `BuilderRetriesLikeEveryOtherLeaf` drives
`leaves.do_build → _do_build_command → _invoke_leaf_resilient → _invoke →
progress.run_with_heartbeat → subprocess` with **nothing in `leaves.py` stubbed**; the
"leaf" is a real `python3 -c` child (the harness `test_leaf_resilience.py:28-40` already
ships, reused). The only stand-ins anywhere are `time.sleep` (the backoff's wall clock) and,
in the harvest/#369 classes, `_invoke` (the vendor spawn — a stub leaf process would add
nothing there). Each class's production chain is written out in the module docstring so a
reviewer can check the claim rather than take it.

**(c) Fixture includes the fault?** Yes, in the sense that matters for each leg:

* the retry legs count **actual spawns** through `$CNT` written by the child itself, so a
  count of 3 is three real processes, not three mock calls;
* the per-attempt-flush leg reads `build.error.log` **from inside the child** during
  attempt 2 (`$PROBE/errlog2`) — the fixture cannot pass by inspecting the file after the
  loop, which is precisely what v0 would have let it do;
* the residue legs have the child **write the half-finished files** (`$RESIDUE`) before it
  dies, so the bundle really is in the BUILT/CHECKED/PLANNED shape the report is judged
  against, and `state.state(d)` is asserted alongside the printed sentence;
* the ownership legs let attempt 1 write a **real truncated verdict** into the sandbox, and
  the fail-closed leg makes the unlink genuinely raise.

## 4. What I did not do, and why

* **No lane/worktree reset between attempts, no new `pdca.toml` knob** — out of scope per
  the brief; the prompt-level statement of the residue is the bounded fix. I did not
  conclude it is insufficient: for the incident this comes from (a dropped connection
  minutes into a build) the retried builder needs to *know* the residue is unfinished, and
  it now does, with the predecessor's account on disk to read.
* **No change to `progress.py` or to the transient rule** — sibling child-2 (issue 533)
  owns that, and this patch would collide with it.
* **`_stub_build` / `select_builder` untouched**; a stub backend behaves exactly as today
  (`test_a_stale_log_is_cleared_on_a_stub_rebuild_too` still passes).
* **`assemble._missing_review_text` (`assemble.py:405-430`) left alone**, deliberately. It
  splits its §6 wording on the bare existence of `check-review.error.log`, so in principle
  an in-flight log would be described as "the reviewer RAN AND FAILED". In practice that
  path is foreclosed: `driver.advance` runs `_resume_interrupted_check` *before*
  `assemble_summary` on the CHECKED branch (`driver.py:130-132`), so by assembly the log is
  either gone (the recovered reviewer succeeded) or complete (it spent its attempts). Adding
  a third wording would widen the slice into `assemble.py` for a state the resume cannot
  leave behind. Flagging it here so the reviewer's eye on that file is not a surprise.
* **`_invoke`'s memory telemetry (#420) untouched.** `memory_log` is now *derived* by the
  wrapper (`_memory_log_for("build.error.log") == "build.memory.jsonl"`), matching the other
  three call sites, and `test_leaf_memory_log.py:258-272` (which asserts the builder's
  `memory_log` kwarg) still passes unchanged.

## 5. Notes the human may want at sign-off

* **C5 is vacuously green for the third round** ("patch adds no new test file"): the gate
  asks its question only of **newly added** test files (`engine/scripts/run-prod-path.py:3-6`),
  and the brief directs appending to two existing files. It carries no weight on this bundle
  — the C4 legs plus the mutation table in §3 are what make the appended cases adjudicable.
  I did not add a third test file to satisfy it, because the brief names exactly which files
  this child may ship and forbids the ones child-2 owns.
* **Section 6 (validation — fitness-to-purpose) is still honestly open.** No real interrupted
  provider session was induced; every leg here is a stub leaf. What a human can do to
  validate by hand, offline, in a scratch instance: point `[leaves.builder]` at
  `argv = ["sh", "-c", "sleep 2; exit 1"]` (a transient shape — no stream event), run
  `pdca run <id>`, and watch three spawns with 4 s/8 s backoff, `build.error.log` growing one
  record per attempt *while* the run is still going, and the closing three-line report; then
  `Ctrl-C` during a backoff and confirm the log is already on disk and `pdca run <id>` still
  re-runs the interrupted leaf.
* **Two non-blocking notes from the last round are closed**: `driver.py:123-129` and
  `driver.py:146-162` no longer state the retired "no artifact, no error log" rule, and
  `_do_residue`'s docstring (`leaves.py:2036-2041`) no longer claims a `_stub_build`
  fallback it does not share.
* **Commit-readiness**: the target repo ships no formatter/linter config and no git hooks
  (checked `.pre-commit-config.yaml`, `pyproject.toml`, `setup.cfg`, `.git/hooks`); its stated
  discipline is the offline suite, which is green (1784 tests, 2 skipped, 29.7 s — against
  1758 tests in 29.1 s on the base, measured by stashing the patch: the criterion-(vi)
  "green **and** fast" bar holds because every retry-driven case patches `time.sleep`
  rather than shortening the shipped 3-attempt / 4 s-backoff defaults), plus the docs
  gate (`lint_docs: OK`, `render_site: link audit OK`) and the root render/update-compat
  suites (`PDCA-EVIDENCE: root suite OK, driver suite OK`). New lines stay within the file's
  existing width band (longest added line 96 chars; the file already carries lines to 110).

## 6. Files

* `template/src/pdca_harness/leaves.py` — the wrapper body, `do_build`/`_do_build_command`,
  the #369 discriminators, the three harvest sites.
* `template/src/pdca_harness/driver.py` — comment/docstring alignment only (no behaviour).
* `template/tests/test_leaf_resilience.py` — appended: 3 classes, 24 cases (29 in the file).
* `template/tests/test_build_error_log.py` — updated: the wall-clock trap (patched sleep,
  not weakened defaults) + 2 cases pinning the log's new shape.
