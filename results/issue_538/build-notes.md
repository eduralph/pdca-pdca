# Build notes — issue #538 (iteration 2)

*A leaf's own account of its death is kept.* Target: `eduralph/pdca-harness @ main`, base
`acb214a`. One production file (`template/src/pdca_harness/progress.py`), one new test module,
one fixtures dir — exactly the scope the brief fixes. `leaves.py` and `assemble.py` are
untouched (verified: the patch's file list is the seven files in `git apply --numstat`).

---

## 1. What iteration 1 was returned for, and what I did about it

The carry-forward is implementation-level only; the mechanism was confirmed by both the
reviewer (C1–T5 all PASS) and the advisory ("Clean on the correctness lens — no bugs found").
So I started from iteration 1's patch verbatim (`git apply iteration-v1/patch.diff` on
`acb214a`, applies clean) and addressed the three open items.

**(1) The blocking item — `NEEDS-HUMAN [impl]`: parse once per line, dispatch the decoded
event.** The drain asked three questions of every stream line and each classifier ran its own
`json.loads` + `isinstance(ev, dict)` on the same bytes — two passes before this change, three
after. Fixed by a shared decode:

- `progress.py:423-446` — new `_stream_event(line: str | dict) -> dict`: decodes once, returns
  the record, or `{}` when the line is no JSON object. It is the only `json.loads` left in the
  module (grep: `json\.` matches exactly two lines now, the docstring at `:430` and the call at
  `:444`).
- `progress.py:197` — the drain calls it once per line and hands the **decoded record** to all
  three classifiers (`:198`, `:200`, `:203`). Everything else in the drain body is unchanged.
- `progress.py:450-456`, `:530-578`, `:663-672` — `_is_session_event`, `_terminal_error` and
  `_stream_tool_label` take `str | dict` and delegate to `_stream_event`; the twelve duplicated
  guard lines are gone from the two pre-existing ones (patch numstat for progress.py went from
  `+246/−1` in iteration 1 to `+295/−17` here — the 16 removed lines are those guards plus the
  signature/docstring lines they lived in).

Two design points worth the reviewer's eye:

- **`{}`, not `None`, for "not a record".** Every classifier reads the record with `.get`, so
  the empty dict answers each exactly as the unparseable line did before — no new
  not-a-record branch in the drain, and no `continue` in the drain loop that a later edit
  could fall behind (`progress.py:191-205`).
- **The classifiers still accept a raw line.** `template/tests/test_progress.py` calls them
  with strings at **18** call sites (`:89-186`), and that file is out of this bundle's scope
  (and is #536/#537-adjacent). Widening to `str | dict` keeps every one of them working —
  confirmed: `tests.test_progress` is green unchanged (31 tests).

**(2) The advisory's untested branch** — `_terminal_error`'s "an error record with nothing to
say is not evidence" early return (`progress.py:573-576`). It now has a binding witness, not
just an assertion of silence:

- `test_an_error_record_with_nothing_to_say_files_no_banner`
  (`test_terminal_error_retention.py:249`) — a `result`/`is_error` with `errors: []` and a
  whitespace-only `result` files no banner. *This one is green on both legs* (silence pre-fix
  too), so on its own it does not bind the branch.
- `test_a_mute_wrapup_cannot_bury_the_evidence_it_has_none_to_add_to` (`:357`) — the case that
  does. A mute wrap-up **outranks a sub-agent report by shape** (`_TERMINAL_PRECEDENCE`,
  `progress.py:510`), so if emptiness were kept as a record it would overwrite the only account
  of the failure the stream ever gave. **Mutation-proved**: with the early return replaced by
  `return text, _WRAPUP`, this case fails — and the log it prints is literally
  `(no output captured) LeafError: …`, the artifact this whole bundle exists to end. Guard
  restored; suite green again.

**(3) The reviewer's fitness-to-purpose `NEEDS-HUMAN`** (a whitespace-flattened, 500-character
line may omit decisive context). I did not change the bound — that is a maintainer's call and
the brief's scope is retention, not formatting policy — but I removed the half of it that is
strictly a defect: a cut report now **says it was cut** (`_TRUNCATED_NOTE`, `progress.py:525-527`;
applied in `_report_line`, `:645-661`). A silently truncated report reads as the leaf's *whole*
account of its death, and a reader would never know to go looking for the rest. Witness:
`test_a_report_past_the_bound_is_kept_and_says_it_was_cut` (`:258`) — head kept, tail absent,
`truncated` present. The observed vendor reports are far shorter than the bound (the incident's
is 78 chars); the bound exists for a `result` wrap-up, which can restate a whole final message
(`progress.py:519-523`). **Still the human's call at sign-off:** whether 500 flattened
characters is the right budget.

## 2. The change itself (unchanged in mechanism from iteration 1)

The stream drain already read every event; the retention half was missing. Now:

- `progress.py:182` — `terminal = {"text": "", "shape": ""}`, the drain's held account.
- `progress.py:200-202` — every **marked** record is noted (`_note_terminal`, `:580-604`), with
  precedence by how near the record is to the leaf's own death, so a `result` wrap-up or a
  sub-agent's report cannot bury the main session's own report **in either arrival order**.
- `progress.py:303-311` — the held text is appended to `output`, the same route the stderr tail
  takes and the same one the #420 memory post-mortem already rides (`leaves.py:663-666`), so
  `_format_leaf_attempt` (`leaves.py:724-730`, #536's file) needs no special case.
- The discriminator is the CLI's **own mark**, never prose: `is_api_error_message` (stream) /
  `isApiErrorMessage` (transcript). Whose death it is comes from one predicate,
  `_is_subagent_event` (`progress.py:606-615`), answering both spellings of the scope
  (`parent_tool_use_id`, `isSidechain`) so they cannot drift apart.
- Nothing is classified: `produced` is returned exactly as before (`progress.py:313-315`), so
  `LeafError.transient` and the retry counts are byte-identical.

**Vendor grounding re-verified this iteration** against the installed binary
(`claude --version` → 2.1.234, `/home/eddie/.local/share/claude/versions/2.1.234`), i.e. the
same build the fixtures README pins:

- the two spellings are one field — `...r.isApiErrorMessage===!0&&{is_api_error_message:!0}`
  (stream emitter) and `...t.is_api_error_message===!0&&{isApiErrorMessage:!0}` (transcript
  writer), plus the schema's own words: *"@internal True when this assistant message wraps an
  API error"*;
- the sub-agent forward: `e.data.type==="agent_progress"…yield{type:"assistant",…,
  parent_tool_use_id:e.parentToolUseID,…,…i.isApiErrorMessage===!0&&{is_api_error_message:!0}…}`
  — a marked report may be a Task's, and only `parent_tool_use_id` says so;
- the wrap-up: `common:{…,is_error:rt,num_turns:ze},variant:{subtype:"success",
  api_error_status:mt,result:rt?Ut:We,…}`.

The three greps that reproduce this are in `template/tests/fixtures/README.md` ("Re-verifying").

**Blast radius on the other callers, re-verified on this base:** `run_with_heartbeat` has four
callers — `gates.py:559`, `publish.py:833`, `leaves.py:752` all pass `capture=True` (the append
is skipped there: `progress.py:303`), and only the leaf spawn `leaves.py:657` does not. So a
gate's evidence line cannot pick up the appended text, and the raw-capture guard is exercised
directly (`test_capture_returns_the_childs_raw_stdout_unmodified`, `:401`).

## 3. Alternatives considered, with their costs

- **Keep three independent `json.loads` (i.e. re-submit iteration 1).** Rejected: it is the
  carry-forward item, and the cost is real — the drain is per-line on a stream that runs for
  minutes: 3 decodes/line × thousands of lines. Cost of *not* fixing it: 12 duplicated guard
  lines kept in the tree, free to drift.
- **Dict-only cores + thin string wrappers** (`_event_is_session(ev)` etc., with
  `_is_session_event(line)` delegating). Rejected on surface: 3 extra functions ≈ +12 lines
  over the chosen shape, and six public-ish names where three plus one shared decode suffice.
  It buys nothing the `str | dict` widening doesn't.
- **Make the classifiers dict-only and update their callers.** Rejected: it edits
  `template/tests/test_progress.py` at **18** call sites (`:89, 97, 100, 101, 103, 105, 108,
  109, 110, 112, 114, 164, 170, 175, 179, 181, 185, 186`) — a file this bundle is not scoped to
  touch and that sits next to #536/#537's live work, exactly the collision the brief's scope
  section forbids.
- **Cache the decode on the line string (an lru_cache keyed by text).** Rejected: unbounded
  growth over a long stream and a cache keyed on megabytes of text to save one parse — strictly
  worse than passing the parsed record 3 statements down.
- **Raise/remove `_TERMINAL_ERROR_MAX`.** Not taken: it is the maintainer's open question, and
  an unbounded append can put a whole final message into every `*.error.log`. The honest half —
  saying that the line was cut — is in (§1.3).
- **Retain the report in a *new* artifact instead of `output`.** Rejected in iteration 1 and
  still: it needs a reader change in `leaves.py` (out of scope, #536's file), where riding
  `output` needs none.

## 4. Refuting my own test (forced check)

**(a) Genuine red?** Yes — measured by the project's own C4 gate
(`engine/scripts/run-verify.sh`, which reverts only the production hunks and re-runs):

```
== C4 green leg: … Ran 34 tests … OK
== C4 red leg:  … Ran 34 tests … FAILED (failures=23)
PDCA-EVIDENCE: C4 PASS — red without the fix, green with it
```

23 of 34 cases fail with the fix reverted, and the module **imported** on the red leg (no
`unittest.loader._FailedTest`, so it is a real red, not a `PDCA-UNVERIFIABLE`). The red set
includes this iteration's new cases:
`OneDecodePerStreamLine.test_a_stream_line_is_decoded_once_not_once_per_classifier`,
`…test_the_decode_count_tracks_the_line_count` (pre-fix the drain decodes 2×/line),
`ReportReachesTheErrorLog.test_a_report_past_the_bound_is_kept_and_says_it_was_cut`, and
`NearestRecordWins.test_a_mute_wrapup_cannot_bury_the_evidence_it_has_none_to_add_to`. The
11 green-on-both cases are the deliberate guards — the brief's criterion (v) ("assert the
invocation counts explicitly so a later change cannot silently move them") plus the
capture/codex/stream-less no-change cases. Additionally, the mute-wrap-up case was
**mutation-tested** against its own branch (§1.2).

**(b) Production path?** Yes. Every case drives production code: `leaves._invoke_leaf_resilient`
→ `_invoke` → `progress.run_with_heartbeat` with a `family="claude"` stub leaf, ending in the
real `*.error.log` that `_invoke_leaf_resilient` writes (`leaves.py:720`), plus direct
`run_with_heartbeat` calls where `output` is assembled. No re-implementation, no stubbed
harness code. The one patch in the module — `_CountingJson` over `progress.json`
(`test_terminal_error_retention.py:130-142`) — **delegates every call to the real
`json.loads`**; it counts, it does not replace behaviour, and it is scoped to
`progress`'s own reference so nothing else in the process sees it.

**(c) Fixture includes the fault?** Yes. The stub leaf really emits the marked API-error record
on **stdout** and really exits non-zero with empty stderr — the incident's exact shape (that is
why the red leg's failure text is `(no output captured) LeafError: …`). The sub-agent cases
include the sub-agent record rather than curating it out, in both spellings; the precedence
cases include the competing record in **both** arrival orders; and `PinnedVendorRecords`
(`:481-500`) replays bytes a real CLI wrote (`template/tests/fixtures/*.jsonl`), skipping
itself rather than erroring if the fixture dir is absent — the brief's C4 red-leg trap, since
`run-verify.sh:131-137` classifies `…/fixtures/*.jsonl` as production and reverts it.

## 5. Gate evidence (run here, before hand-off)

| gate | command | result |
| --- | --- | --- |
| C4 | `engine/scripts/run-verify.sh` | `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it` (green 34/34; red 23 failures) |
| C5 | `PDCA_PROD_PACKAGE=pdca_harness engine/scripts/run-prod-path.py` | `1 added driver-suite test(s) import the production package 'pdca_harness'` |
| T2 | `engine/scripts/run-docs-check.sh` | docs lint clean, site render + link audit clean |
| T3 | `engine/scripts/run-suite.sh` | root suite OK (7), driver suite OK (1792, 2 skipped) |

Commit-readiness: the target configures **no** formatter/linter hook (no `.pre-commit-config.yaml`,
no ruff/black/mypy config; CI is docs/render only) — `git diff --check` is clean, and added lines
stay within the file's existing ~90-char convention (base max is 97, mine is 90).

**No external dependency was missing.** Everything above ran offline on the base toolchain
(python3 + git); the vendor CLI was consulted only as a *reading* step for grounding, exactly as
the brief's `External dependencies: none` says.

## 6. What I deliberately did **not** do

- No classification: `produced`, `LeafError.transient`, retry counts and `_invoke_leaf_resilient`'s
  loop are untouched — no error kinds, no HTTP statuses, no "the CLI recovered" clearing rule, no
  signal-death predicate. That is child-2 (#539).
- No edits to `leaves.py` / `assemble.py` / `test_progress.py` / `test_leaf_resilience.py` /
  `test_build_error_log.py` / `test_attempt_ownership.py` / `test_builder_retry.py` — the sibling
  bundles' files.
- No new `pdca.toml` knob, no session-resume, nothing about #371 / #510.
