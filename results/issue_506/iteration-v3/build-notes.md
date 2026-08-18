# Build notes — issue 506 (iteration 3)

> Builder rationale, withheld from the reviewer. Every `path:line` is on the target
> branch (`eduralph/pdca-harness` @ `main`) **as patched**, in `$PDCA_WORKTREE`
> (`/home/eddie/pdca/pdca-harness.pdca-wt`).

## 0. What this iteration is

Iteration 2's mechanism was accepted as sound and told to stay ("KEEP ALL OF THAT"):
the classifier anchored on the CLI's own `is_api_error_message` mark, the retention
route into `*.error.log`, the builder on `_invoke_leaf_resilient`, the honest
exhausted-retry message, the `_has_content` guard, the `capture`-exclusivity guard,
the derived `memory_log`, and the pinned real vendor transcript. I started from that
patch (`iteration-v2/patch.diff`, applied clean to the base worktree) and changed
**only** what the sign-off named. Five defects, each closed and each pinned by a test
that a mutation of the hunk turns red (§3).

Net delta vs iteration 2 — three production changes in `progress.py` (the sticky helper
`_note_terminal` + its call site; the narrowed `result` classification + its new
`_CLAUDE_INFRA_RESULT_SUBTYPES`; the comments/docstrings that state both rules), two in
`leaves.py` (`_write_attempt_records` + its per-attempt call; the unlink-on-success), and
**+9 test cases** with 5 new stub scripts. Nothing else in the patch moved.

## 1. The five carry-forward defects

### (1) The wrap-up silently overturned the incident's own verdict — `progress.py:187`, `:556-579`

`terminal.update(...)` was last-writer-wins, so the real three-event ending —
`assistant`(work) → `assistant{is_api_error_message, "Connection lost mid-response"}` →
`result{is_error, subtype:"error_during_execution", result:"Execution error"}` — ended
with the generic wrap-up as the recorded verdict: `transient=False`, one invocation, the
fix failing on the exact death it was built for.

Fix: `_note_terminal` (`progress.py:556`), called from the drain at `progress.py:187`.
A **transient report is sticky**: a later *non*-transient report cannot overwrite it;
only real work after it clears it (the pre-existing `_is_work_event` branch,
`progress.py:188-192`). Newest-wins still holds between two transient reports.

Two consequences I took deliberately, both documented in the helper's docstring:

* the sticky report also wins the **retention** line, so the log keeps
  `API Error: Connection lost mid-response.` rather than `Execution error` — the cause,
  not the effect. The wrap-up's prose is dropped in that one case; it is the generic
  string the CLI emits for every `error_during_execution`, so nothing diagnostic is lost.
* stickiness is *literally* "sticky unless real work follows", as instructed — including
  the (unobserved) shape where a permanent API-error report follows a transient one with
  no work between. I considered narrowing it to "the wrap-up specifically cannot
  re-classify" (pass a `wrap_up` flag out of `_terminal_error`, ~6 more lines), and
  rejected it: no evidence for that shape, and the asymmetry of cost favours the sticky
  reading — a wrong retry costs 2 extra bounded attempts, a wrong substantive verdict
  costs a whole cycle round, which is the incident itself.

### (2) The `result` branch was still prose-matching — `progress.py:459`, `:548-552`

Iteration 1's "too broad" arm had relocated here: gated only on
`is_error` + `subtype != "success"`, then `_TRANSIENT_CAUSE_RE` over free prose.

Fix, keyed on fields the CLI itself sets (the sign-off's own suggestion):

```python
transient = (_transient_status(ev.get("api_error_status"))          # progress.py:550
             and ev.get("subtype") in _CLAUDE_INFRA_RESULT_SUBTYPES)  # {"error_during_execution"}
```

`_TRANSIENT_CAUSE_RE` is now applied **only** to text the CLI marked as its own
API-error message (`progress.py:530-537`); the comment at `progress.py:460-467` says so
and says why. Retention is untouched — a substantive `result` ending still explains
itself in the bundle; only the classification narrowed.

Measured through the production path with the sign-off's own strings (mutating the two
lines back to iteration 2's rule and re-running the new test):

```
AssertionError: True is not false : 'Build failed: the integration test timed out
    waiting for the fixture server' was read as infrastructure
AssertionError: True is not false : '2 tests failed: expected 500, got 404 in
    test_api.py' was read as infrastructure
```

Both are 1 invocation now, 3 under the old rule.

### (3) The branch was entirely unpinned — 4 new cases

`is_error` appeared nowhere under `template/tests/`. The stub leaf now emits `result`
events (`result()` in the prelude, `test_leaf_resilience.py:126-129`) and four cases pin
the branch in both directions:

| case | line | pins |
|---|---|---|
| `test_the_wrap_up_result_does_not_overturn_the_report_that_named_the_cause` | `:430` | the sticky rule (defect 1) |
| `test_a_result_ending_the_cli_did_not_mark_is_explained_but_not_retried` | `:445` | 2 substantive endings — not retried, still explained |
| `test_a_result_the_cli_stamped_with_an_api_status_is_retried` | `:461` | the machine-keyed transient arm |
| `test_a_status_on_an_ending_the_session_owns_does_not_make_it_infra` | `:473` | the subtype guard (`error_max_turns` + 503 ⇒ substantive) |

Disabling the branch outright (`if False:`) now fails 2 of them; it left 63 tests green
before.

### (4) The retry prompt pointed at a file that did not exist — `leaves.py:741`, `:757-765`

`_BUILD_RETRY_NOTE` told the retried builder its predecessor's account "is in
build.error.log in the bundle directory", while the wrapper unlinked that file at the
top and wrote the records only after the loop — so attempts 1/2/3 all saw nothing. Took
the sign-off's first option (it also survives a SIGKILLed run): `_write_attempt_records`
(`leaves.py:757`) is called after **every** failure (`leaves.py:741`), so the log exists
while the next attempt runs.

End state had to stay identical, so a retry that ultimately **succeeds** clears it again
(`leaves.py:732-737`, `contextlib.suppress(OSError)` — the success path did no I/O
before, and an unremovable log must not turn a successful leaf into a failure). Pinned
both ways: `test_a_retried_builder_can_actually_read_that_account` (`:663`) probes the
file **from inside the child** on every attempt — the only vantage point from which the
promise is testable — and `test_a_retry_that_succeeds_leaves_no_error_log` (`:545`) pins
the unchanged end state.

### (5) "The vendor's verdict, not the prose" was not what the tests pinned — 3 new cases

Both `_CLAUDE_TRANSIENT_ERROR_KINDS → frozenset()` and `_transient_status → return False`
survived, because the prose regex rescued every transient case; criterion (i)'s
mid-session rate-limit had no test at all. The new legs use text with **nothing** in it
for a matcher — `_OPAQUE_API_TEXT` / `_OPAQUE_RATE_LIMIT_TEXT`
(`test_leaf_resilience.py:95-102`) — and each pairs the transient leg with an identical
leg under the CLI's fallback kind / no status, so the field is provably what decided:

* `test_the_cli_error_kind_classifies_a_report_whose_text_says_nothing` (`:481`) —
  `overloaded`/`server_error` ⇒ retried; `unknown`/`invalid_request` ⇒ not;
* `test_a_mid_session_rate_limit_rejection_is_retried` (`:495`) — criterion (i)'s third
  category, carried by `rate_limit` alone;
* `test_the_attached_http_status_classifies_a_report_of_no_named_kind` (`:509`) —
  503/429 ⇒ retried, 400 ⇒ not, everything else held equal.

## 2. What I did NOT change, and why

* **`flow_one` / `_isolate`** — out of scope per the brief; untouched.
* **Session-resume** (brief asks Do to say so): the retry is a **fresh re-invoke**, not
  the CLI's `--resume`. For this incident nothing would have been saved either way — the
  identical argv re-run minutes later succeeded — and resume would need a session id the
  harness never captures today (it is in the stream's `session_id`, which nothing
  persists) plus a per-family resume flag. That is a design slice of its own; the retry
  note (`leaves.py:1885`) is what makes a fresh attempt safe over the residue.
* **The reviewer/advisory harvest is attempt-blind — FLAGGED, not fixed.** Widening the
  classification makes those leaves retryable *after* they have produced work, and their
  harvest (`leaves.py:2653-2657`, `:2986-2990`, `:3287-3291`) is `if <artifact>.exists()`,
  unconditional on which attempt wrote it: a truncated `check-review.md` from a dead
  attempt 1 can be copied in if attempt 2 exits 0 having written nothing. The sign-off
  said explicitly "do NOT expand the slice to it", so I did not. The cost of closing it,
  measured, is **≈28 lines in 2 files**:

  ```python
  # leaves.py, _invoke_leaf_resilient — 1 kwarg + 4 docstring lines + 2 in the retry branch
  clear_on_retry: Iterable[Path] = (),
  ...
              for stale in clear_on_retry:      # a dead attempt's partial artifact is not
                  stale.unlink(missing_ok=True)  # evidence the next attempt produced it
  # + 1 line at each of the 3 call sites (:2641 `(sandbox / "check-review.md",)`,
  #   :2975 `(out,)`, :3277 `(out,)`) + ~18 lines of test
  ```

  It is self-contained and I would take it in a follow-up issue; it is not in this patch.
* **`retry_note` at the three sibling call sites** — deliberately not passed (the
  sign-off notes it is "necessary but not sufficient"): it would change three more leaf
  prompts for a hole it does not close. Their attempt-1 prompts stay byte-identical.
* **No new `pdca.toml` knob** — the existing `attempts=3` / `backoff=4.0` defaults are
  reused, per the brief's out-of-scope list.

## 3. Evidence

Run through the project's own runners, from the pdca-pdca instance root:

* **C4 red→green** — `./engine/scripts/run-verify.sh` (`PDCA_BUNDLE`, `PDCA_WORKTREE`):
  green leg `Ran 29` + `Ran 12` OK; red leg (production hunks reverted, all
  `template/tests/*` hunks kept) `Ran 29 ... FAILED (failures=26)`, module imported
  fine (no `_FailedTest`) → `PDCA-EVIDENCE: C4 PASS`.
* **T3 full suite** — `./engine/scripts/run-suite.sh`: root suite `Ran 7 ... OK`,
  driver suite `Ran 1782 tests ... OK (skipped=2)`.
* **T2 docs** — `./engine/scripts/run-docs-check.sh`: lint clean, render + link audit clean.
* **Commit-readiness**: the target configures no formatter/linter (no
  `.pre-commit-config.yaml`, no ruff/black config in `pyproject.toml.jinja`);
  CONTRIBUTING.md's engineering discipline is DCO sign-off + "keep the offline suite
  green", both satisfied. New lines stay within the file's existing width (my longest
  new line is 95; base `progress.py`/`leaves.py` already carry 97/110).

**Mutation probes** (each mutation applied to the patched tree, suite re-run, then
reverted) — the tests are not tautological:

| mutation | caught by |
|---|---|
| `_note_terminal` → plain `terminal.update(...)` | `test_the_wrap_up_result_does_not_overturn_the_report_that_named_the_cause` |
| result branch → iteration 2's prose regex | `..._result_ending_the_cli_did_not_mark...`, `..._status_on_an_ending_the_session_owns...` |
| result branch disabled (`if False:`) | `..._result_ending...`, `..._result_the_cli_stamped_with_an_api_status...` |
| `_CLAUDE_TRANSIENT_ERROR_KINDS → frozenset()` | `..._cli_error_kind_classifies...`, `..._mid_session_rate_limit_rejection...` |
| `_transient_status → return False` | `..._attached_http_status...`, `..._result_the_cli_stamped...` |
| `_CLAUDE_INFRA_RESULT_SUBTYPES` widened to `error_max_turns` | `..._status_on_an_ending_the_session_owns...` |
| flush moved back to after the loop (iteration 2's shape) | `test_a_retried_builder_can_actually_read_that_account` (alone) |
| unlink-on-success removed | `test_a_retry_that_succeeds_leaves_no_error_log` |
| terminal text not appended to `output` | 12 cases |

## 4. Forced refutation of my own test

* **(a) Genuine red?** Yes. C4's red leg reverts `progress.py` / `leaves.py` /
  `assemble.py` and keeps every test hunk: **19 of the 29 cases** in
  `test_leaf_resilience.py` fail (unittest counts **26 failures**, each subTest leg
  separately). Every case added this iteration is in that red set except one — the pure
  guard `test_a_status_on_an_ending_the_session_owns_does_not_make_it_infra`, which
  asserts a *negative* the base already gets right; the other nine survivors are the
  pre-existing #138 cases and the precision guards. The module still **imports** on the
  red leg (the appended tests reference no symbol the patch adds at module level), so
  this is a real red, not a `PDCA-UNVERIFIABLE`. Per-hunk reverts are in the table above.
* **(b) Production path?** Yes. Every case drives real production code:
  `leaves.do_build` → `worktree`/lane-lock → `_invoke_leaf_resilient` → `_invoke` →
  `progress.run_with_heartbeat` → a real `subprocess.Popen`. The only stand-in is the
  **leaf itself** (the vendor CLI), which is an external process by construction — a
  Python interpreter speaking claude's stream contract on real stdout, exactly the stub
  the brief's falsifiability section prescribes. Nothing between the child's bytes and
  the assertion is mocked; the sole `mock` in the file is `time.sleep` (so the backoff
  costs no wall-clock) and `os.environ`.
* **(c) Fixture includes the fault?** Yes, twice over. `tests/fixtures/
  claude_api_error_death.transcript.jsonl` is the incident's own last event copied
  byte-for-byte out of `~/.claude/projects/` (provenance in
  `tests/fixtures/README.md`), and the stream twin is derived from it by the CLI's own
  emitter mapping; both are replayed verbatim on the leaf's stdout. The new wrap-up case
  **adds** the `result` event that previously overturned the verdict rather than curating
  it out, and the precision cases feed in the exact substantive strings that were
  measured as 3 invocations.

## 5. Known limits the human should weigh at sign-off

* The `result`-event *shape* is still derived rather than observed: the pinned bytes cover
  the `assistant` API-error event (the incident's actual death). If the CLI ever reports a
  death **only** in a `result` without `api_error_status`, this classifies substantive —
  by design, since prose is not evidence, but it means that shape is unfixed.
* C5 remains vacuous for this bundle ("patch adds no new test file"), because the brief
  directs the work into the existing `template/tests/test_leaf_resilience.py`. It supports
  no production-path claim; §4(b) above is the claim, and the mutation table is its
  evidence.
* Not re-litigated, still open from the previous sign-off: C4's derived stream fixture,
  the PR #524 rebase ownership, and the dirty-worktree fitness question.
