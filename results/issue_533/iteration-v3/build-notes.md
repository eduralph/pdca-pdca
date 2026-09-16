# Build notes — issue #533, iteration 3 (a leaf's own terminal error is kept and read)

Target: `eduralph/pdca-harness` @ `main`, base `acb214a` (worktree
`/home/eddie/pdca/pdca-harness.pdca-wt-l1`, `HEAD == origin/main == acb214a`).
All `path:line` below are **post-patch** lines on that base unless marked "(base)".

The sign-off kept the slice and the design — "Rejected on the implementation, not the
slice or the evidence… Do NOT re-cut this slice" — and named four local defects in the
classifier plus one ownership question it settled itself. This round closes all four,
changes nothing else, and re-derives the vendor grounding from the shipped binary again
rather than trusting the round-2 fixture README.

---

## 1. The four carry-forward items

### 1.1 The classifier no longer reads prose for anything but the vendor's own `unknown`

Two defects, three lines, one rule now: **the vendor's kind answers, and it is the only
thing that answers — except the single kind it uses to say it could not answer.**

* `progress.py:715` — `if kind != _CLAUDE_UNKNOWN_ERROR_KIND: return False`. The loose
  fall-through (`return any(_TRANSIENT_CAUSE_RE.search(t) …)` for every kind outside two
  frozensets) is gone, so a kind the vendor adds after 2.1.233 keeps today's substantive
  verdict instead of being classified by regex. This harness pins no CLI version and the
  CLI auto-updates, so "not a permanent kind I know" was a hole that widens by itself.
* `progress.py:677` — `kind = raw_kind if isinstance(raw_kind, str) and raw_kind.strip()
  else None`. An **absent** `error` is no longer collapsed into the string `"unknown"`.
  `_CLAUDE_PERMANENT_ERROR_KINDS` is **deleted** (it had no behaviour left once the
  fall-through went; its enum is documented in the `_CLAUDE_UNKNOWN_ERROR_KIND` comment,
  `progress.py:556-565`, rather than kept as a frozenset that looks like a rule and is not).

Why "absent ⇒ never classified" and not "absent ⇒ read the text": re-derived from
claude-code 2.1.233 this round, `Yd(…)` stamps `isApiErrorMessage:!0` and passes its
`error` through, so **every** `Yd({content: …})` call without an `error:` key produces a
marked message with no kind. Three such emitters, read out of the binary:

| offset in `~/.local/share/claude/versions/2.1.233` | marked message with no `error` |
|---|---|
| 297713850 | `"CLAUDE_CODE_NO_MODEL_FALLBACK is set: model substitution is disabled · unset it to allow the swap"` |
| 297745679 | `"The model's tool call could not be parsed (retry also failed)."` |
| 314689632 (`XFA`) | `"The session process exited with code N…"` **+ the child's own last 2000 bytes of output** |

The third is decisive. Its text is *arbitrary leaf output*, so a regex over it charges
whatever the leaf happened to print to infrastructure. Every one of the three is a
condition a re-invoke repeats. The tests: `test_terminal_error_classification.py:301`
(two cases — the incident's own sentence *unstamped*, and the runner shape whose tail
quotes `ECONNRESET`/`529`) and `:330` (a kind from a hypothetical later CLI).

### 1.2 Signal deaths are excluded — and the boundary is spelled ONCE, publicly

`progress.is_signal_death(rc)` (`progress.py:43-65`, constants `:36`, `:40`) is a **public**
helper next to `TIMEOUT_RC`, and the classification now reads
`terminal["transient"] and rc not in (0, TIMEOUT_RC) and not is_signal_death(rc)`
(`progress.py:358-359`).

It knows **both** spellings a returncode uses, which is the point the sign-off made:

* `-signum` — `subprocess` reporting a direct child's signal death (the vendor binary
  spawned directly);
* `128 + signum` — a wrapper argv (`sh -c`, `docker run`, the documented `local-build`
  shape) that already exited normally after *its* child was killed. 137 = SIGKILL.

`TIMEOUT_RC` (-1001) answers `False` with no special case: it is outside the signal range
by construction, which is exactly why it was chosen (`progress.py:27-32`, base).

**Sibling coordination (issue_532).** The sign-off asked for one spelling in both children.
This child owns `progress.py`, so the predicate lives there where 532's `leaves.py` can
call it: `_builder_retryable` should become `… and not progress.is_signal_death(rc)`,
which fixes 532's *opposite* hole (it excludes `rc < 0` but not a positive 137) without
either child inventing half the boundary. That is a one-line change in 532's own hunk —
this child cannot make it (`_invoke_leaf_resilient`'s body and `do_build` are 532's), and
must not: the two patches already collide on the retry print. **Flagging it for the human
at sign-off**, since 532 is in the same wave.

Tests: `:599` (SIGKILL, `rc == -9`, through `run_with_heartbeat`) and `:612` (the wrapper
spelling, `rc == 137`, through `_invoke_leaf_resilient` — asserts 1 run, not 3, *and* that
the report is still retained: the exclusion is about classification, never retention).

### 1.3 The transcript spelling is now supported on BOTH sides, not half

Resolved by **keeping** the camelCase branch and making the scope rule bilingual —
`progress._is_subagent_event` (`:755-771`), used by `_terminal_error` (`:680`) and by
`_is_main_session_work` (`:837`). One predicate, both sides, so they cannot drift.

The sign-off offered "either the shape can appear (honour `isSidechain`) or it cannot
(delete the branch)". This round established that **it can**: 2.1.233's cloud-session
runner (`XFA`, binary offset 314689632) hand-builds a *stream-shaped* assistant event
spelled `isApiErrorMessage` (camelCase) with `parent_tool_use_id: null` — quoted verbatim
in `template/tests/fixtures/README.md:71-101`. And the persisted transcript spelling
carries `isSidechain` and **no** `parent_tool_use_id` at all, so `.get()` returning `None`
there is not "the main session" — the exact misread the sign-off named. 2.1.233 treats
`isSidechain` as that marker itself (it filters sidechain transcripts out of the
resumable-session list by string-matching the first line; quoted at
`fixtures/README.md:167-176`).

Grounding labels are honest: the camelCase-on-stream emitter is **OBSERVED in the binary**
but reaches the cloud worker feed, not a local `claude -p` stdout; `isSidechain: true` is
**DERIVED** — a full re-scan of every transcript on this machine
(`~/.claude/projects/*/*.jsonl`, 553 files, ~136k records) returns **zero** sidechain
records and exactly **two** `isApiErrorMessage` records, which are the two already pinned.
That scan also re-verified both pinned fixtures byte-for-byte this round.

Tests: `:436` (a transcript-shaped sidechain **report** — evidence, labelled, never the
verdict) and `:454` (a transcript-shaped sidechain **work** line must not clear the main
session's report). Helper: `transcript_shaped()` at `:95`.

### 1.4 The `result` exclusion from `_WORK_EVENT_TYPES` is now asserted

One event appended to `test_report_survives_the_wrapups_that_name_no_cause`
(`:245`, case `success-with-no-text` at `:258`):
`{"type":"result","subtype":"success","is_error":true,"result":""}`. A **text-less**
`is_error` result is the only wrap-up that reaches the clearing branch — every wordy one
is a record in its own right and takes `_note_terminal` instead, which is precisely why
the previous suite stayed green under the mutation. Verified: adding `"result"` to
`_WORK_EVENT_TYPES` now fails this case and only this case (M1 below).

### 1.5 Ownership (settled at sign-off, not re-litigated)

`leaves.py:683-706` (the `_invoke_leaf_resilient` docstring) and `:730-732` (the retry
print, now "on transient infra" rather than "with no output (transient)") **stay with this
child**, as instructed. Nothing else in `leaves.py` is touched — no logic, no `do_build`,
no harvest, no `_format_leaf_attempt`.

---

## 2. The change, in full (for a reader who has not seen v1/v2)

| Site | What it does |
|---|---|
| `progress.py:36-65` | `is_signal_death` — one spelling of the signal boundary, both returncode conventions |
| `progress.py:222` | one more piece of drain state: `terminal = {"text","transient","shape"}` |
| `progress.py:231-240` | in the existing drain loop, beside `_is_session_event`: read a marked terminal record; a **main-session** work event after one clears it |
| `progress.py:341-347` | the report rides `output` into the caller's `*.error.log` by the same route the stderr tail takes (skipped under `capture`, where `output` is raw stdout) |
| `progress.py:349-360` | `produced and not died_of_reported_infra` — scoped to a non-zero exit **the child itself made**, and never a timeout or a signal death |
| `progress.py:465-467` | `_WORK_EVENT_TYPES` — the `assistant`/`user` subset (a `result` is the wrap-up, not "it recovered") |
| `progress.py:486-552` | section comment: the incident, why the *mark* and not the prose discriminates, which field lives on which event, whose death a mark denotes |
| `progress.py:553-582` | the constants — three record shapes, their precedence, the sub-agent label, the vendor's transient kinds, its `unknown` kind, the retryable statuses, the category regex, the 500-char bound |
| `progress.py:611-691` | `_terminal_error` — per-family classifier in `_is_session_event`'s shape (dispatch on `stream_format`, best-effort JSON, degrade-to-today default) |
| `progress.py:693-718` | `_kind_is_transient` — the vendor's kind answers; the text is read for exactly one kind |
| `progress.py:720-752` | `_note_terminal` — newest wins *within a shape*, never across a shape nearer the leaf's own death |
| `progress.py:755-771` | `_is_subagent_event` — both spellings of "whose record is this" |
| `progress.py:774-812` | `_claude_message_texts` / `_claude_result_texts` / `_transient_status` / `_report_line` |
| `progress.py:814-838` | `_is_main_session_work` — only the MAIN session carrying on clears a report |
| `progress.py:85-142` | `run_with_heartbeat`'s docstring: both halves of the signal, what `produced` still means, why retention is wider than classification |

**Prose sites that restated the old definition** (prose only): `leaves.py:90-107`
(`LeafError`), `:111-114` (`.transient`), `:674-679` (the `_invoke` comment; the
`produced or not use_stream` fallback at `:680` untouched), `:683-706`
(`_invoke_leaf_resilient`'s docstring), `:730-732` (the retry print), `:2544`
(`_FAIL_TRANSIENT`), `:2549-2562` (`_failure_class`), `:2598` + `:2611-2617`
(`_unavailable_classification`), and `assemble.py:80` (`LEAF_STATUS_INFRA`).

**Tests + fixtures.** `template/tests/test_terminal_error_classification.py` (34 cases)
and `template/tests/fixtures/` (README + two observed vendor records + their derived
stream forms). Both ship **inside `patch.diff`** at the paths the brief names — the C4
gate runs the test out of `$PDCA_WORKTREE`, and a second copy in the bundle dir is not in
`state.DOWNSTREAM_OF_BRIEF`, so it would not be archived on an iterate and would leak into
the next round. `template/tests/test_leaf_resilience.py` and `test_build_error_log.py` are
untouched (child-1 owns both).

---

## 3. Refuting my own test (forced, recorded)

**(a) Genuine red?** Yes, twice over.

* Against the **base** (what C4 measures): `./engine/scripts/run-verify.sh` →
  `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`. Green leg: 34 ran, OK.
  Red leg (production hunks reverted, tests kept): 34 ran, **30 failures**, no
  `unittest.loader._FailedTest` — the module imports nothing this patch adds.
* Against **iteration 2's production code** (the delta this round is judged on): I applied
  v2's patch minus its tests and ran this round's suite — exactly the six new cases fail
  (7 case failures, `test_an_unstamped_report…` failing both subtests):

  ```
  FAIL: test_a_kind_this_harness_does_not_know_is_not_classified_by_its_prose
  FAIL: test_a_sidechain_line_in_the_transcript_spelling_does_not_clear_the_report
  FAIL: test_a_sidechain_report_in_the_transcript_spelling_is_not_the_leafs_death
  FAIL: test_an_unstamped_report_is_retained_but_never_classified_by_its_prose (case='same-text-unstamped')
  FAIL: test_an_unstamped_report_is_retained_but_never_classified_by_its_prose (case='runner-tail')
  FAIL: test_a_signal_death_is_not_reclassified_by_its_stream
  FAIL: test_a_wrapper_reported_signal_death_is_not_reclassified_either
  ```

  So no carry-forward item is closed only in prose.

**(b) Production path?** Yes. Every case spawns a real child through the production
functions — `progress.run_with_heartbeat` and `leaves._invoke_leaf_resilient` — with a
real `LeafConfig`, the real family profile, the real drain thread and the real error-log
write. No stand-in, no monkeypatch, no re-implementation; the module imports only
pre-existing API (`progress`, `leaves`, `config.LeafConfig`). C5 concurs:
`PDCA-EVIDENCE: 1 added driver-suite test(s) import the production package 'pdca_harness'`.

**(c) Fixture includes the fault?** Yes. The stub leaf actually emits the marked report on
stdout and actually dies: `sys.exit(1)`, `sys.exit(137)`, or `os.kill(os.getpid(), 9)`
(`test_…:44-56`) — the SIGKILL case is observed as `rc == -9`, not simulated. The
fixture-replaying cases replay the **pinned vendor bytes** (`fixtures/*.stream.jsonl`) and
`skipTest` when absent, so the C4 red leg cannot manufacture a red by deleting a file. No
case curates the failing element out; the sub-agent and sidechain cases deliberately keep
*both* records in the stream and assert which one wins.

### Mutation battery (13 planted, 0 survivors)

Each mutation re-run through the same suite (`.cache/mutate.py` in the worktree):

| # | Mutation | Result |
|---|---|---|
| M1 | `result` counted as work | CAUGHT (1 case — the new text-less wrap-up) |
| M2 | prose read for any unrecognised kind (v2's rule) | CAUGHT (3) |
| M3 | absent `error` collapsed into `"unknown"` (v2's rule) | CAUGHT (2) |
| M4 | scope forgets `isSidechain` | CAUGHT (2) |
| M5 | scope forgets `parent_tool_use_id` | CAUGHT (3) |
| M6 | signal death: wrapper `128+n` spelling missed (532's hole) | CAUGHT (1) |
| M7 | signal death: `-signum` spelling missed | CAUGHT (1) |
| M8 | signal deaths not excluded at all (v2's rule) | CAUGHT (2) |
| M9 | classification ignores the exit code | CAUGHT (4) |
| M10 | newest marked record always wins (v1's rule) | CAUGHT (4) |
| M11 | the report is never retained | CAUGHT (29) |
| M12 | a sub-agent report classifies too | CAUGHT (2) |
| M13 | main-session work no longer clears a report | CAUGHT (1) |

### Gates run locally

* C4-verify: **PASS** (above).
* T3-suite: root suite OK + driver suite OK — `Ran 1792 tests … OK (skipped=2)`.
* T2-docs: `lint_docs: OK`, `render_site: link audit OK`.
* C5-prod-path: PASS (quoted above).
* Commit-hook readiness: the target has **no** formatter/linter hook (no
  `.pre-commit-config.yaml`, no ruff/black/flake8 config anywhere in the repo; CI is
  docs-check + render-check + the offline suite, all run above). `docs/publishing/tools/
  lint_docs.py` scans `docs/*.md` and `template/PCDA/quality-cycle/*.md` only, so the new
  `fixtures/README.md` is out of its scope — checked, not assumed. Longest line added: 97
  chars, inside a file whose existing maximum is 97 and a package whose maximum is 236.
  DCO sign-off is a publish-step concern (`git commit -s`), not a patch property.

---

## 4. Decisions and rejected alternatives (with their cost)

**Deleting `_CLAUDE_PERMANENT_ERROR_KINDS` rather than keeping it.** Once the fall-through
was closed, the frozenset had zero behavioural effect: `kind != "unknown" → False` already
covers every member. Keeping it would have been 6 lines of constant + 2 lines of branch
that no test can distinguish from their absence — the "branch that looks like coverage and
is not" this slice is held against. Its content survives as documentation at
`progress.py:556-565`.

**Sub-agent reports: retained-and-labelled, not ignored.** Ignoring them is cheaper —
delete `_SUBAGENT_REPORT`, `_SUBAGENT_NOTE` and the rank table, fold the scope test into
the mark test: **5 fewer code lines** (3 constants, 2 branch lines) plus ~14 comment lines.
What those 5 lines buy: when a session's *only* marked record is a sub-agent's, the
`*.error.log` still carries the one account that exists instead of reverting to
`(no output captured)`. The label is what keeps that honest — a log that confidently names
the wrong death is worse than none.

**Keeping the camelCase branch rather than deleting it.** Deleting it saves **1 `or`
clause** in `_terminal_error` (`:665-666`), **1 clause** in `_is_subagent_event` (`:771`)
and **2 test cases** (`:436`, `:454`, ~30 lines). It also removes the only defence against
the vendor normalising spellings — and 2.1.233 *does* build a stream-shaped record with the
camelCase mark (§1.3). With the bilingual scope rule the branch can no longer misattribute,
which was the sign-off's whole objection; without the branch, a spelling change lands as a
silent regression with the suite green. Kept.

**A fresh re-invoke, not the CLI's own session resume** (the brief asks that this be said
so the human can weigh it). A retry here re-runs the leaf's argv from scratch: the
18-minute session's work is *lost*, and the attempt is paid again in full. `claude
--resume <session_id>` could in principle continue the dead session — the stream carries
`session_id` on every event, so the id is already in reach — but resuming changes what a
retry *is* (inherited context, a partially-written artifact, a prompt that no longer
matches the state), which is squarely sibling child-1's territory (what a retry may
inherit) and is out of scope here. This patch's accepted first cut is the cheap, correct
one: classify honestly, keep the evidence, re-invoke.

**Where the error falls, deliberately.** Every judgement call is biased toward *not*
retrying: an unrecognised kind, an unstamped report, a sub-agent's report, a signal death,
a wrap-up without a status. A false "transient" costs three of the most expensive runs in
the cycle and tells the operator "safe to re-run" about a failure that repeats; a false
"substantive" costs one un-retried leaf and an error log that now, at least, explains why.

---

## 5. For the human at sign-off

* **Cross-child, needs a decision this round:** sibling issue_532's `_builder_retryable`
  should call `progress.is_signal_death(rc)` instead of its own `rc < 0` test (§1.2). Both
  children are in the same wave; if 532 lands its half-spelling, the boundary is stated two
  ways in one codebase — the contradiction the invariant exists to prevent. Recommended
  merge order is unchanged (child-1 first, then this one).
* **Not fixed here, by scope:** what a retry may inherit, the builder joining the resilient
  path, `do_build`, the harvests (`_invoke_leaf_resilient`'s *body*) — all child-1's; the
  gate-side transient (#371); what a signal death should *become* (#510 — this patch only
  refuses to answer it by relabelling).
* **Vendor grounding is version-pinned prose, not a runtime dependency.** Everything the
  classifier keys on is re-derived from claude-code 2.1.233 and recorded, claim by claim,
  as OBSERVED or DERIVED in `template/tests/fixtures/README.md`. If the CLI changes an
  event shape, the tests keep passing and the classifier degrades to today's behaviour —
  by construction (unknown kinds and unreadable formats are substantive), never silently
  to "retry everything".
