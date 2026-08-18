# Build notes — #540 per-attempt record & one meaning for the error log (iteration 2)

Target: `eduralph/pdca-harness` — worktree `$PDCA_WORKTREE` on `pdca-integration/main`
(`d2938ef`, "pdca-integrate: issue_538", stacked on the brief's base `acb214a`). Every
`path:line` below is the patched worktree.

Artifacts: `patch.diff` (4 production files + 1 new test + 3 fixture lines in one shipped
test), `template/tests/test_attempt_ownership.py` (new, 11 cases), these notes.

---

## 1. What iteration 1 got right, and the one thing that blocked it

The sign-off accepted the design ("right-sized, the single-point-of-truth predicate is the
right shape, red→green held under independent reproduction and four mutants") and blocked
on one defect plus one secondary:

1. **BLOCKING** — the record write was `Path.write_text`, i.e. `open(O_TRUNC) → write →
   close`. The marker was the *last* thing written, so every partial state (0-byte, prefix)
   had **no** marker and therefore read as "the leaf ran and FAILED" → a reviewer that still
   had attempts left was **retired** instead of re-run. Measured under `RLIMIT_FSIZE`.
2. **SECONDARY** — "remove the asymmetry **at the source**: an EMPTY or contentless log
   currently reads as settled by default. Consider making the predicate fail towards
   re-running for a log with no recognisable attempt record at all, consistent with the
   stated fail-direction."

Both are addressed, and they are addressed **together**, because they are one fact: under
iteration 1's polarity ("marked ⇒ unfinished, unmarked ⇒ spent"), *silence means retired*.
Every degraded shape — torn, empty, foreign, from an older harness — is silence.

## 2. What this rebuild does differently

### (a) Settlement is asserted POSITIVELY (the root fix for #2, which subsumes #1's danger)

`state.ATTEMPTS_SPENT_MARKER` (`state.py:90`) is written as the **last line of a spent
leaf's record** (`state.settled_record`, `:214`; called at `leaves.py:745`).
`state.leaf_ran_and_failed` (`:182`) is exactly *"the last non-blank line is that marker"*.
Consequences, by construction rather than by guard:

| log on disk | reads as | leaf is |
|---|---|---|
| absent | not settled | re-run |
| unfinished (mid-retry flush) | not settled | re-run |
| **0-byte / blank** | not settled | re-run |
| **torn off part-way by a dead write** | not settled | re-run |
| unreadable (`OSError`) | not settled | re-run |
| written by an older harness (no marker) | not settled | re-run |
| settled by this harness | **ran and FAILED** | retired |

The sign-off asked for a leg pinning *"a torn/0-byte error log must recover its leaf, not
retire it"*. Under iteration 1's polarity that leg is **unsatisfiable for a torn record with
content**: a prefix of a real record carries no marker, and "no marker" meant *spent*. No
content rule fixes that — `"----- attempt 1 — exit 1 -----\nboom\n"` (the shipped fixture at
`test_check_resume.py:111` on the base, `:118` after this patch) is byte-indistinguishable
from a truncated record. So the leg the human asked for **is** the polarity flip; the flip
is not an embellishment I chose over the directive.

### (b) The directed crash-safe write, exactly as specified (BLOCKING #1)

`_replace_record` (`leaves.py:765`) writes a sibling temp (`.<name>.partial`) and
`os.replace()`s it into place — all-or-nothing, and the temp is removed on failure so no
partial sibling is ever left in the bundle. `_flush_attempt_records` (`:749`) keeps it
**best-effort** (`except OSError` → warn, records stay in hand, the loop's stop rule
untouched — criterion 5). The **final** settling write goes through the same helper
(`:745`) and raises exactly as the `write_text` it replaces did: without that, the last
write would reintroduce the very tearing the human blocked on, one line after fixing it.

This is not redundant with (a). (a) stops a torn record from *lying*; (b) stops a failed
write from *destroying the last good record* — the mid-retry post-mortem criterion 1 exists
to guarantee. It is pinned by a test that reproduces the sign-off's own scenario against
production (`test_a_record_a_dying_write_cut_off_leaves_the_last_whole_one`) and measured on
both trees (§4.3): base leaves a 600-byte truncated file that retires the leaf; patched
keeps attempt 1's **complete** record and re-runs it.

### (c) Everything else carried over from iteration 1 (unchanged in substance)

- per-attempt flush inside the loop (`leaves.py:735`) — criterion 1;
- the success path restores "no error log" (`:723`), so a leaf that recovered on retry
  leaves nothing behind;
- the four readers all consult the one predicate: `leaves.review_never_ran` (`:2177`),
  `run_advisory_leaves(only_missing=True)` (`:2876`), `assemble._missing_review_text`
  (`assemble.py:420`, both wordings named at `:429`), `driver._resume_interrupted_check`
  (`driver.py:152`, `:176`);
- a leaf's own text cannot impersonate the distinction: `state.neutralize_leaf_text`
  (`:226`) rewrites (never drops) a line that IS the marker, called from
  `_format_leaf_attempt` (`leaves.py:798`); the marker is read only as a whole final line
  (`state._last_nonblank`, `:199`).

## 3. The one shipped test I touched, and why that is the honest option

`template/tests/test_check_resume.py` — **3 fixture lines** (`:118`, `:130`, `:153`), no
assertion changed, plus 4 doc lines. Those fixtures were hand-written stand-ins
(`"boom\n"`) for "a leaf that ran and failed", from the era when *existence* was the rule.
Under (a) they must be what the writer actually produces, so they now call the production
writer: `state.settled_record("…")`.

Blast radius, measured not asserted: the **entire** offline suite is 1802 tests; before the
fixture update exactly **3** failed, all in this file; after it, `Ran 1802 tests … OK`. The
root suite (render + `copier update` compat, 7 tests) is OK too. `test_leaf_resilience.py`
is **untouched and green** (criterion 4): its content assertions are `assertIn` (`:64`,
`:74`) and its existence assertions read the final state (`:63`, `:83`, `:91`), all
unaffected by a trailing marker line.

Operational cost of (a) for logs written by an **older** harness: such a log reads as
unfinished, so the leaf is re-run once (then it writes a settled log, or succeeds). The
cost is one leaf run, in the window where it can even matter — and that window is tiny,
because a failed leaf normally also leaves a §6 placeholder artifact, which short-circuits
both discriminators before the log is consulted. The opposite error costs the review of the
diff. This is the fail-direction `state.py` already declares and the sign-off asked me to
make true.

## 4. Evidence

### 4.1 Red → green (the project's own gate, not a hand-rolled run)

`PDCA_BUNDLE=… PDCA_WORKTREE=… ./engine/scripts/run-verify.sh` →
`PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`.

- green leg: `test_attempt_ownership` 11/11 OK, `test_check_resume` 10/10 OK;
- red leg (production hunks reverted, tests kept): `test_attempt_ownership`
  **FAILED (failures=15)** — 9 of the 11 cases fail on real assertions, incl. every
  criterion-1/2/3 leg and the torn-write leg; `test_check_resume` errors on the 3 fixtures
  that call API this patch adds. No `unittest.loader._FailedTest`, so no PDCA-UNVERIFIABLE:
  module-level imports are pre-existing API only
  (`from pdca_harness import assemble, leaves, state`).
- The 2 cases that stay green on the base are the deliberate guards for criteria 4 and 5
  (a successful leaf leaves no log; a failed flush costs no attempts) — they pin what must
  **not** change, so "green on base" is their correct behaviour.

Also run: `./engine/scripts/run-suite.sh` → `root suite OK, driver suite OK`;
`PDCA_PROD_PACKAGE=pdca_harness ./engine/scripts/run-prod-path.py` →
`PDCA-EVIDENCE: 1 added driver-suite test(s) import the production package 'pdca_harness'`.

### 4.2 Mutants of *this* patch (each must be caught, all were)

| mutant | caught by |
|---|---|
| M1 drop `neutralize_leaf_text` | `…only_the_harness_can_close_a_record…`, `…torn_record_carrying_that_line…` |
| M2 `write_text` instead of temp+`os.replace` | `…each_record_lands_whole_and_never_truncates…`, `…dying_write_cut_off_leaves_the_last_whole_one` |
| M3 an empty record reads as settled | `…torn_or_empty_record_recovers_its_leaf` |
| M4 marker matched as a substring | `…recognised_only_whole_and_last`, `…torn_record_carrying_that_line…` |
| M5 no per-attempt flush | 4 cases incl. `…attempt_two_finds_attempt_ones_account` |
| M6 a failed flush ends the run | `…unwritable_record_does_not_narrow_the_retry_contract` |
| M7 a recovered leaf keeps its record | `…recovers_on_retry_leaves_no_record_behind` |
| M8 a failed write leaves its partial sibling | `…dying_write_cut_off_leaves_the_last_whole_one` |

(M1 initially escaped the torn-record leg because my slice arithmetic left a stray `-`
line; the cut is now `_before_last_line` (`test_attempt_ownership.py:155`), and M1 is
caught by both legs.)

### 4.3 The sign-off's own scenario, measured on both trees — and shipped as a test

The same scenario is a **shipped leg**, so the reviewer sees the evidence too:
`test_a_record_a_dying_write_cut_off_leaves_the_last_whole_one`
(`test_attempt_ownership.py:255`, driver at `:80`, harness at `:180`) drives the
production wrapper in a child process under
`RLIMIT_FSIZE` (process-wide, so it must not be set inside the runner; `SIGXFSZ` ignored so
the write returns `EFBIG` rather than killing the process, and only the SOFT limit is
lowered since the hard one cannot be raised back). The child reports **facts** — the bytes
on disk — and the parent asks the engine's own pre-existing `leaves.review_never_ran` for
the verdict, so nothing in the leg depends on API this patch adds (red-leg import safe).
It is red on the base (`AssertionError: unexpectedly None : attempt 2 found no record of
attempt 1`) and catches M2 and M8.

Standalone measurement, both trees, same script:

Driving the production wrapper under `RLIMIT_FSIZE = 600` with `SIGXFSZ` ignored (so the
write returns `EFBIG` mid-write), 3 attempts, ~300-byte stderr per attempt:

```
== patched ==                          == base ==
attempts run     : 3                   attempts run     : 3
final write      : OSError             final write      : OSError
error log        : exists, 428 bytes   error log        : exists, 600 bytes
ends with        : …still retrying…    ends with        : xxxxxxxxxxxxxxxxxx  (torn)
reads as RETIRED : False               reads as RETIRED : True
stray partials   : []
```

Base: a torn file that retires an interrupted leaf — the catastrophe the sign-off measured.
Patched: attempt 1's **complete** unfinished record survives the failed flush, the leaf is
re-run, no partial sibling is left, and the attempt budget is untouched. The docstring's
"strictly no worse than before" is now true in the torn case, with numbers.

### 4.4 The three refutation questions (asked and answered before declaring done)

- **(a) Genuine red?** Yes — measured by reverting, not reasoned: `run-verify.sh`'s red leg
  reverts the production hunks and the module goes **FAILED (failures=14)**; with them it is
  **OK**. Seven targeted mutants of the fix itself are each caught (§4.2).
- **(b) Production path?** Yes — the tests call the shipped functions:
  `leaves._invoke_leaf_resilient` (spawning a real subprocess through `progress`, the
  stream path, the real `LeafError`/transient classification), `leaves.review_never_ran`,
  `leaves.run_advisory_leaves(only_missing=True)`, `assemble._missing_review_text`. Nothing
  is mocked, nothing is re-implemented; C5 confirms the module imports `pdca_harness`.
- **(c) Fixture includes the fault?** Yes — the mid-retry fixture is **not hand-built**: the
  stub leaf copies the bundle's error log aside *while the production retry loop is running*
  (`test_attempt_ownership.py:45-56`), so the bytes under test are byte-for-byte what a kill
  inside the loop leaves. The torn/empty shapes are prefixes of the production **settled**
  record; the torn-write leg lets a real write die part-way under a real file-size limit;
  the impersonation text comes out of the leaf's own stderr through the production capture
  path. Nothing curates the failing element out.

## 5. Alternatives weighed (with the cost, not an adjective)

- **Iteration 1's polarity + atomic write + "empty ⇒ unfinished" only.** Diff would be ~6
  lines smaller (one constant, one branch in `_last_nonblank`) and would leave
  `test_check_resume.py` untouched (3 fixture lines + 4 doc lines saved). Rejected: it
  cannot satisfy the sign-off's leg for a **torn record with content** — §2(a) shows why no
  content rule can, since the shipped fixture and a truncated record are the same bytes. It
  guards the symptom (the harness stops *producing* torn files) where the flip removes the
  cause (a torn file can no longer *mean* "spent").
- **Keep polarity, add `fsync` + directory `fsync` to the record write.** +4 lines and a
  per-attempt disk sync. Rejected: the failure model in the brief is a *killed process*
  (Ctrl-C, OOM, a killed session), for which `os.replace` on a fully-written file is
  sufficient — the page cache survives the process. Machine-level power loss is out of scope
  and would also need the bundle's other writers to sync.
- **`tempfile.NamedTemporaryFile` for the temp.** Same line count. Rejected: it creates the
  file `0600`, so every error log would silently change mode from the umask default the
  shipped `write_text` produced; a plain `open` keeps the shipped permissions.
- **Settle at harvest / pass an artifact path into the wrapper / residue quote.** Explicitly
  child-2 (`#541`) in the brief's out-of-scope list. Not touched: `:2519-2523`,
  `:2851-2854`, `:3152-3155` are byte-identical, and the unfinished state never leaves
  `_invoke_leaf_resilient`. No caller changed.
- **Touch `assemble.py:80-89` (leaf-status labels).** Out of scope per brief, and unneeded:
  those labels read the *artifact's* marker comment, not the error log — my change cannot
  make them false.
- **Adopt #539's `"on transient infra"` wording while in the same function.** Refused per
  the brief's ordering note: it is only accurate after #539 redefines transient. The print
  at `leaves.py:737-739` and the whole staleness clear (`:706-710`) are byte-identical; I
  own the loop body, #539 owns the strings.

## 6. Housekeeping for the human

- The measurement in §4.3 was driven by a scratch script left in the worktree at
  `.pdca-measure.py` (untracked, repo root, outside `template/`). It is **not** part of the
  change: `git diff` matches `patch.diff` byte-for-byte after the base/patched legs, both
  suites are green with it present, and publish applies `patch.diff` in the publisher
  checkout, so it cannot be committed. The harness reclaims the worktree.
- A `.<name>.error.log.partial` can only survive a hard kill *during* a record write; the
  next flush truncates it and the next successful replace consumes it. It matches no
  archive glob (`state.DOWNSTREAM_GLOBS` is `*.error.log`, `*.memory.jsonl`,
  `check-advisory-*.md`), so it is never archived as evidence.
- No external dependency beyond the base toolchain: every leg is a Python interpreter as the
  "leaf" — no vendor CLI, no key, no network, no container. Nothing to declare.
- Carried to Act, unchanged from the sign-off's note: the mid-retry post-mortem is unlinked
  by the wrapper's staleness clear (`leaves.py:706`) before `assemble` runs on a *later*
  advance. The brief pre-decided that under criterion 4 and the adversary called it a human
  scope call; criterion 4 is honoured here (that clear is byte-identical).
