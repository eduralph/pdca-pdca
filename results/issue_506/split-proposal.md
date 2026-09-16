<!-- pdca:split-proposal v1 -->
# Split proposal — issue 506

## Why this slice is oversized

Issue 506 reports one incident (an escalated builder ran ~18 minutes, the API connection
dropped mid-response, the attempt was burned and `build.error.log` read `(no output
captured)`), but it names **three separate weaknesses** and the fix for it has to change
two different layers that meet only at `LeafError`:

1. **The stream reader** (`template/src/pdca_harness/progress.py`) never reads the CLI's own
   terminal error report: it parses stdout for a session flag and a tool label and drops the
   rest (`:147-158`), keeps only a bounded **stderr** tail (`:143`, `:162-171`, `:255`), and
   classifies "transient" by the proxy *did the child produce any substantive event*
   (`:144`, `:154-155`, `:365-377`) — a proxy that is wrong for exactly the long sessions
   where an attempt is most expensive.
2. **The leaf-invocation layer** (`template/src/pdca_harness/leaves.py`) never puts the
   *builder* on the resilient path at all (`do_build` → `_invoke`, `:1824`, while the
   reviewer `:2507`, advisory `:2840` and plan advisory `:3142` all use
   `_invoke_leaf_resilient`, `:673-721`), reports an exhausted death as an argv plus an exit
   status, and — the moment retries reach a leaf that already produced work — has three
   harvest sites that copy an artifact `if produced.exists()` without asking which attempt
   wrote it (`:2519-2523`, `:2851-2854`, `:3152-3155`).

Four build rounds were spent on this as one slice. Every round's mechanism was independently
confirmed (red→green reproduced through the real subprocess path, 1780 template tests green,
16/16 mutations of the load-bearing hunks caught, the vendor contract re-derived from the
shipped binary) and every round's findings were **implementation-shaped** — the signature of
a slice too large to converge. The patch reached 92,086 bytes against an 80 KB backstop
(38 KB of it in one test file). The sign-off at iteration 4 rejected on **slicing, not
mechanism**, and directed the split here (`results/issue_506/iteration-v4/SUMMARY.md` §9;
the archived attempt is in `results/issue_506/iteration-v4/`).

The seam is the one the code already has: **what a death IS** (read and retained from the
stream — `progress.py`) versus **what the harness DOES about it** (who is retried, what a
retry may inherit, what the operator is told — `leaves.py`). Each half is a shippable
outcome with its own red, and each is roughly half the rejected patch.

The third item the sign-off asked to stop deferring — the attempt-blind harvest, measured at
~34 lines across two files and deferred twice — is folded into child-1 rather than filed as
a third issue: it is the *same* invariant as the builder-residue problem child-1 already
owns ("nothing a dead attempt left behind may be reported as a live attempt's work"), it is
in the same file, and a third child would cost a third full cycle for ~34 lines.

## Wave sketch

**Both children are independent — same wave, run in parallel.** Neither needs the other's
code to compile, and each has its own genuine red on today's `origin/main`:

- child-1 goes red with the stub leaf `template/tests/test_leaf_resilience.py:28-31` already
  ships (`_TRANSIENT`: stderr only, no stream event → transient under *today's* rule): drive
  `leaves.do_build` with it and count invocations — 1 today, the attempt budget after the
  fix. No new classification is needed for that red.
- child-2 goes red on `progress.run_with_heartbeat` + the reviewer/advisory path, which is
  resilient on *any* base — it needs nothing from child-1.

So neither `Depends on` nor `Conflicts with` is declared, and they land in one wave on
`origin/main`. This also keeps them off the wave>0 path, which in **this** instance (rendered
0.57.0) still carries issue 474's base-export leak — the reason the human's `plan-0.60-bug-order.md`
runs this milestone one wave per run.

They do share `leaves.py`, so the seam is drawn to make that harmless:

| | child-1 owns | child-2 owns |
|---|---|---|
| `progress.py` | — | all of it |
| `leaves.py` | `_invoke_leaf_resilient` **body** (`:698-721`), `_format_leaf_attempt` + a new residue helper (`:724-730`), `do_build` / `_do_build_command` (`:1741-1831`), the three harvest sites (`:2519-2523`, `:2851-2854`, `:3152-3155`) | **prose only** — the four places that restate the transient definition: `LeafError` (`:90-107`), the `_invoke` comment (`:661-670`), `_failure_class` (`:2534-2549`), `_unavailable_classification` (`:2573-2590`) |
| `assemble.py` | — | one comment (`:80`) |
| tests | `template/tests/test_leaf_resilience.py`, `template/tests/test_build_error_log.py` | `template/tests/test_terminal_error_classification.py` (**new**), `template/tests/fixtures/` |

The one place a same-wave collision was likely — both halves appending to the same test file,
as the rejected single slice did — is removed by construction: the children ship their tests
in different files.

**Recommended MERGE order at publish (a human decision, not a scheduling one): child-1, then
child-2.** child-2 widens *which* failures are retried, which is what first makes a leaf
retryable **after** it has produced work — and that is what makes the residue/harvest holes
reachable. child-1 closes them. Merging child-1 first means the window never opens.

<!-- pdca:child child-1 -->
# driver: Do burns a whole attempt on transient infra, and a retried leaf can inherit a dead attempt's work

- **Slug:** an-attempt-is-the-unit-of-accountability
- **Defect:** The builder is the only leaf the harness never retries, and the retry path it
  is missing has two attempt-ownership holes of its own. All verified on the target base
  (`eduralph/pdca-harness` @ `main`, `acb214a`):
  * **Do is never retried.** `_do_build_command` calls plain `_invoke`
    (`template/src/pdca_harness/leaves.py:1824`), while the reviewer (`:2507`), the advisory
    (`:2840`) and the plan advisory (`:3142`) all run under `_invoke_leaf_resilient`
    (`:673-721` — bounded retry with backoff plus a per-attempt error log, #138). So **no**
    builder failure is ever retried — on the leaf where an attempt is most expensive, and
    where the #135 escalation ladder's deep tiers (opus/`--effort max`) run longest. The
    reported incident burned ~18 minutes and a whole cycle round to a dropped connection.
  * **The exhausted death explains nothing and its "next step" would be false.** `do_build`
    captures one record and re-raises (`:1765-1778`); what the operator reads is
    `build/check failed (LeafError: Command '[…]' returned non-zero exit status 1)` — an
    argv and an exit status. And the honest next action depends on what the dead attempt
    left behind: a bundle holding `patch.diff` reads **BUILT** (`state.py:211`), so
    `driver.advance` (`driver.py:76`) runs **Check** on that partial patch, not Do.
  * **A retry would inherit the dead attempt's work.** Two holes, both live the moment any
    leaf is retried after producing output: `_invoke_leaf_resilient` writes its attempt
    records only *after* the loop (`:720`), so while attempt 2 runs there is nothing on disk
    explaining attempt 1 (and a killed run loses them all); and the three harvest sites
    copy their artifact `if produced.exists()` — `:2519-2523` (`check-review.md`),
    `:2851-2854`, `:3152-3155` — with no notion of *which* attempt wrote it, so a truncated
    verdict from a dead attempt can be adopted as the leaf's own. `worktree.ensure` likewise
    runs once, before the wrapper (`:1791`), so a retried builder opens a worktree still
    carrying the dead attempt's edits and a bundle that may already hold `patch.diff` /
    `build-notes.md`.
- **Success criterion:** With the patch:
  (i) a **transient** builder death is retried, bounded, with backoff, under the same
  `_invoke_leaf_resilient` contract the reviewer/advisory leaves use, while a **substantive**
  builder failure is still not retried; either way the final failure is still captured to
  `build.error.log` and still re-raised, so `flow._isolate` drops just this bundle exactly as
  today;
  (ii) each attempt's error record is on disk **before** the next attempt starts, so a
  retried leaf — and a post-mortem of a run that was killed mid-retry — can read the
  predecessor's account instead of a file that does not exist yet;
  (iii) a retried **builder** is told in its prompt that a previous attempt died mid-flight
  and that any `patch.diff` / `build-notes.md` / test file present is that attempt's
  incomplete residue to verify or replace — never evidence the work is done;
  (iv) when the bounded retries are exhausted, what the operator reads names the transient
  classification, points at the on-disk account, and states a next action that is **true for
  the residue actually present** (naming, when a partial `patch.diff` was left, that the
  bundle now reads BUILT and a plain re-run would run Check on it); nothing deletes the
  builder's artifacts to make that sentence true;
  (v) no artifact written by a **dead** attempt is harvested as a **successful** attempt's
  output at the reviewer / advisory / plan-advisory sites;
  (vi) nothing else changes: the existing resilience contract holds unchanged (attempt count,
  backoff, the staleness clear at `:698-702`, the `_memory_log_for` pairing — derive it, do
  not pass `memory_log=` explicitly where the other three call sites do not), the
  memory-telemetry post-mortem (#420) still rides `output` into the same log, a successful
  build is spawned and reported exactly as today, and both offline suites stay green **and
  fast** (see Falsifiability).
- **Falsifiability:** RED is reachable offline on the base toolchain — pure-stdlib Python
  ≥ 3.11 + git, no vendor CLI, no network, no API key — in the target checkout Do is given.
  * (i)/(iii)/(iv): `template/tests/test_leaf_resilience.py:28-40` already ships the harness
    this needs — `_TRANSIENT` (stderr only, no stream event → transient under *today's* rule),
    a leaf whose argv is `[sys.executable, "-c", script]`, and a `$CNT` file counting
    invocations. Driving `leaves.do_build` with such a builder counts **1** invocation today
    and must count the attempt budget after the fix; the prompt note and the exhausted
    message are assertions over the child's stdin and over captured stderr. That red needs no
    new classification, so this child is falsifiable on today's `origin/main` alone.
  * (ii): instrument from inside the stub leaf — attempt 2 asserts `build.error.log` exists
    and holds attempt 1's text. Today it does not exist until the loop ends.
  * (v): a first stub attempt that writes a truncated `check-review.md` into the sandbox and
    then dies transiently, followed by an attempt that exits 0 without writing → the harvest
    copies the dead attempt's file today. Genuine red on the current base.
  * **Wall-clock trap, read this before you build:** `template/tests/test_build_error_log.py:63-71`
    raises `LeafError(1, ["claude"], output="panic…")`, and `produced` defaults to `False`
    (`leaves.py:99`) so `.transient` is `True`. The moment `do_build` retries, that existing
    test spends the real backoff (4 s + 8 s) and calls its mock three times. Keep the suite
    fast **and** honest: make the attempt budget / backoff reachable from the test (or patch
    the sleep), and do **not** weaken `_invoke_leaf_resilient`'s shipped defaults to do it.
  * C4's red leg reverts the production hunks and keeps every `template/tests/*.py` hunk
    (`engine/scripts/run-verify.sh:214-217`), so appended cases earn a genuine red — provided
    the appended tests import no symbol this patch adds at module level: a red-leg import
    failure is recorded `PDCA-UNVERIFIABLE`, not red (`run-verify.sh:231-233`). Note also
    that the C4 gate runs **every** test file the patch touches, so both test files below
    must be red-worthy and green.
- **Invariant to restore:** **An attempt is the unit of accountability.** Two halves, both
  stated over the category rather than this incident: (1) an infrastructure failure the leaf
  did not cause is the harness's to absorb — bounded — on **every** leaf it spawns, not on
  the three that happened to be given the wrapper; and (2) nothing a **dead** attempt left
  behind may be reported as a **live** attempt's work, and nothing the harness tells the
  operator or the retried leaf about that residue may be false. Self-test: it cannot be
  satisfied by guarding one module — the retry lives at the builder call site, the record
  flush inside the wrapper, the ownership at three harvest sites, the honesty in the
  operator's message. Source: internal project invariant (Tier C), the target's own written
  rules — `leaves.py:641-647` (why a captured tail exists at all: `(no output captured)` is
  "a post-mortem artifact that explains nothing", #286 review), `leaves.py:683-697` (the
  resilience contract #138 states), `engine/README.md:44-68` (no evidence must never be filed
  as a verdict). `docs/principles.md` §5/§6 are unfilled scaffolds in this instance, so no §6
  category gate applies.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Ordering note:** No `Depends on` / `Conflicts with` — the sibling child-2 is independent
  (neither needs the other to compile or to go red→green) and both build on `origin/main` in
  one wave, which is also what this instance's own #474 base-export leak makes preferable
  (`plan-0.60-bug-order.md`). The two children share `leaves.py` but in disjoint regions —
  this one owns the wrapper **body**, `do_build`, and the harvest sites; child-2 owns only
  the four prose sites that restate the transient definition — and they ship tests in
  **different files** by construction. Recommended merge order at publish: **this child
  first**, then child-2, because child-2 is what first makes a leaf retryable *after* it has
  produced work, and this child is what makes that safe.
- **Surfaces:** data
- **Difficulty:** high
- **Scope:** Who gets retried, what a retry may inherit, and what the operator is told when
  the retries run out — the leaf-invocation layer of #506. Put the builder on the existing
  resilient path; flush each attempt's record as it happens; tell a retried builder that a
  predecessor died mid-flight and that any artifacts present are its residue; make the
  exhausted-retry report name the class of failure, where its account is, and a next action
  that matches the residue actually on disk; and give the three artifact harvests a notion of
  which attempt produced what.
  **Out of scope:** the stream-side question of *what counts as* a transient death and the
  retention of the leaf's own error text — that is sibling child-2, and this child must not
  touch `progress.py` or change the transient rule; a lane/worktree reset between attempts,
  and any new `pdca.toml` knob (reuse the shipped attempts/backoff defaults — a prompt-level
  statement of the residue is the bounded fix; if the rebuild concludes that is insufficient,
  say so in `build-notes.md` rather than expanding the slice); the gate-side transient
  (issue #371 — the same argument one layer down, its own slice); a leaf **signal-death**
  under the memory cap (issue #510 states it "is neither #506's transient nor #421's
  preflight" — do not fold it in); `flow._isolate`'s containment contract and the `flow_one`
  library route's propagation (`flow.py:302-306` documents why the single-issue path differs);
  the memory-telemetry post-mortem (#420), which must keep working unchanged.
- **Repro instruction:** On a clean checkout of the target base (`origin/main` of
  eduralph/pdca-harness), offline, from `template/`:
  1. `PYTHONPATH=src python3 -m unittest tests.test_leaf_resilience -v` — green today; read
     `:28-40` for the stub-leaf harness and `$CNT` counter this child reuses.
  2. Read the gap: `leaves.py:1824` (`_invoke`, not `_invoke_leaf_resilient`) against the
     three peer call sites `:2507`, `:2840`, `:3142`; `:720` (records written only after the
     loop); `:2519-2523` / `:2851-2854` / `:3152-3155` (`if produced.exists()`, attempt-blind);
     `:1765-1778` (what a failed Do prints); `state.py:211` + `driver.py:76` (why a bundle
     left holding `patch.diff` goes to Check, not Do).
  3. The live incident is named in the parent issue: getwyrd/wyrd-pdca `results/issue_717/`
     (`build.error.log`, `loop-telemetry.json`), failing tier = the
     `[[leaves.builder_escalation]]` opus/max entry; an identical re-run minutes later
     succeeded.
- **External dependencies:** none — the base toolchain suffices. Every leg is driven by a
  stub "leaf" that is a Python interpreter, so the slice builds and goes red→green with no
  vendor CLI, no API key, no network and no container.
- **Test file:** `template/tests/test_leaf_resilience.py` (append — it owns the
  `_invoke_leaf_resilient` contract, #138) **and** `template/tests/test_build_error_log.py`
  (the sibling that pins `build.error.log`'s shape and archival; update it here — it is this
  child's file, and see the wall-clock trap above). Do **not** create
  `template/tests/fixtures/` and do **not** add `template/tests/test_terminal_error_classification.py`:
  both belong to sibling child-2, which builds on the same base in the same wave.
- **Citations expected:** Do must cite `path:line` on the target branch for every change.
  Composition cues — this slice wires into patterns the codebase already applies:
  * `_invoke_leaf_resilient` (`leaves.py:673-721`) is the wrapper to reuse **as it is**:
    its staleness clear (`:698-702`), its `_memory_log_for` derivation, its `records` list and
    the `_format_leaf_attempt` record format (`:724-730`);
  * the three peer call sites that already compose it — `:2507` (reviewer), `:2840`
    (advisory), `:3142` (plan advisory) — show the shape to mirror (`err = _invoke_leaf_resilient(…)`,
    then act on `err`). `do_build`'s outer contract differs and must survive: its failure is
    captured to `build.error.log` **and re-raised** (`:1765-1778`), and its stale-log clear
    (`:1747-1753`) plus the archive rule pinned by `test_build_error_log.py:91-105` still hold
    — a wrapper that writes per-attempt records must not then be overwritten by the outer
    capture;
  * `_stub_build` (`:1755`) and `select_builder` (`:1746`) bound the change: a stub backend
    must behave exactly as today;
  * honesty inputs for the exhausted-retry message: `state.py:211` (a bundle holding
    `patch.diff` reads BUILT) and `driver.py:76` (BUILT → Check).
  * **Prior art you may read, selectively:** the rejected single-slice attempt is archived at
    `results/issue_506/iteration-v4/patch.diff` (+ `build-notes.md`). Its **leaf-side** hunks
    were independently confirmed four rounds running and were rejected for slice size, not
    mechanism, so you may read them for decisions already settled. Read **only** the hunks for
    the files this child owns — re-applying the `progress.py` / `tests/fixtures/` /
    `test_terminal_error_classification` material would recreate the oversized slice this
    split exists to undo — and re-verify anything you take against the current base rather
    than trusting it.

  **Path convention in this brief:** every `template/…` and `tests/…` path is on the **target
  branch** (eduralph/pdca-harness @ main) — the files Do reads and edits. Every `engine/…`,
  `pdca.toml` and `results/…` path is in **this pdca-pdca instance** (the verification engine
  and the bundles that run the cycle); they are cited to explain how the gates will judge the
  patch, and Do must not edit them.
- **Prior-art check (triage cycles):** By file path on `origin/main`:
  `template/src/pdca_harness/leaves.py` — `_invoke_leaf_resilient` arrived with #138 for the
  reviewer/advisory leaves and was never extended to the builder; `do_build`'s error capture
  is #279/#286; the most recent touch of `_invoke` is `0881af9` (#420 memory sampling). Open
  PRs on the target (`gh pr list -R eduralph/pdca-harness --state open`): #519-#525, of which
  #524 (issue 494) and #520 (issue 466) touch `leaves.py` at distant regions (`:782`,
  `:3261`, `:3400`, `:3465`; `do_split`) — no overlap with this child's regions. Open issues
  searched for `retry` / `transient`: #371 (gate-row transient red) and #510 (signal death)
  are adjacent and deliberately excluded above; #509 (crash-resume) is a different beat. Not
  previously attempted as its own slice, not rejected; the parent 506's four-round attempt was
  rejected on slicing (`results/issue_506/iteration-v4/SUMMARY.md` §9).
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.
<!-- pdca:end child-1 -->

<!-- pdca:child child-2 -->
# driver: a leaf's terminal API error is discarded, and a long session that dies of one is misclassified substantive

- **Slug:** a-leafs-own-terminal-error-is-kept-and-read
- **Defect:** `progress.run_with_heartbeat` already reads every event a leaf's stream emits,
  and throws away the one line that explains a death. Two rules, both verified on the target
  base (`eduralph/pdca-harness` @ `main`, `acb214a`):
  * **The stream's own error text is discarded.** The drain parses stdout for a session flag
    and a tool label and keeps nothing else (`template/src/pdca_harness/progress.py:147-158`);
    what it retains is a bounded **stderr** tail (`:143`, `:162-171`), and with `capture` off
    `output` is that stderr tail alone (`:255`). The CLI's API-error line arrives as a stream
    *text* event on **stdout**, so it is displayed and dropped, and `_format_leaf_attempt`
    (`leaves.py:724-730`) falls back to `(no output captured)` — verbatim what the reported
    incident's `build.error.log` contained. The cause was legible only in the CLI's own
    session transcript under `~/.claude/projects/`.
  * **The transient signal cannot see it.** A failure is classified transient only when the
    child produced **no** substantive stream event (`progress.py:144`, `:154-155`,
    `_is_session_event` at `:365-377`; `LeafError.transient` at `leaves.py:103-107`).
    "Produced anything?" is a *proxy* for "died at invocation", and the proxy fails for
    exactly the long sessions where an attempt is most expensive: the incident's 18-minute
    builder did plenty of work and then died of an API connection drop, so it was classified
    substantive — correctly by that rule, wrongly for that cause. The module's own docstring
    (`:55-64`) already records that the CLI emits `system`/`api_retry` on a **retryable** API
    error; the **terminal** report is the case with no reader.
- **Success criterion:** With the patch:
  (i) a leaf whose stream carries the CLI's **own terminal error report** — the report the
  vendor itself marks as an API error — and then exits non-zero is classified **transient**
  when that report's cause is transient (a lost or interrupted connection, an overload or
  5xx, a mid-session rate-limit rejection), however much work came first;
  (ii) it is **not** classified transient when the vendor marks the cause **permanent** (an
  invalid request, an authentication or billing failure) — no prose inside a marked report
  may promote it — nor when a leaf merely mentions or quotes an error, nor when it fails
  substantively; and a report the CLI then **recovers** from, with real **main-session** work
  following it, is not the leaf's death;
  (iii) the report's text is **retained for every marked terminal report, transient or not**,
  so it reaches the leaf's `*.error.log` by the same route the stderr tail takes, and the
  post-mortem explains the failure without opening `~/.claude/projects/`;
  (iv) nothing else changes: a stream-less family still reports substantive
  (`leaves.py:661-670`), `capture` still returns the child's raw stdout unmodified, the
  codex/gemini stream formats degrade to today's behaviour, a leaf that succeeds is spawned
  and reported exactly as today, and the memory-telemetry post-mortem (#420) still rides
  `output` into the same log.
  Demonstrable by C4-verify offline: a stub "leaf" that is a Python interpreter emitting
  chosen stream events and exiting non-zero, driven both through
  `progress.run_with_heartbeat` directly and through `leaves._invoke_leaf_resilient` (the
  reviewer/advisory path, which is resilient on **any** base), so (i)-(iv) are assertions
  over an invocation counter and the error log's bytes.
- **Falsifiability:** RED is reachable offline on the base toolchain — pure-stdlib Python
  ≥ 3.11 + git, no vendor CLI, no network, no API key — in the target checkout Do is given.
  `template/tests/test_leaf_resilience.py:28-40` shows the harness shape to copy into this
  child's own new test file: `_SUBSTANTIVE` emits one `{"type": "assistant"}` event and then
  fails, and the suite asserts it is **not** retried — that is precisely the rule the incident
  falls foul of. A stub leaf that emits a work event, **then** the CLI's marked terminal
  error report, then exits non-zero is the new posture: today it is retried 0 times and its
  error log reads `(no output captured)`, so both assertions fail pre-fix. That is the red.
  Patch the retry backoff from the test so red→green costs no wall-clock.
  **Two gate-shaped traps, both measured against this instance's C4 gate:**
  * `engine/scripts/run-verify.sh:130-137` classifies a changed path as a *test* only when it
    matches `tests/*.py` / `template/tests/*.py`. A **fixture** (`…/fixtures/*.jsonl`) is
    therefore classified **production** and is **reverted on the red leg**, so a case that
    only replays a fixture goes red because the *file is gone*, not because the classifier is
    missing — a vacuous red. So: at least one case per criterion must construct its events
    **inline in the test module**, and a fixture-replaying case must **skip** (not error) when
    its fixture is absent.
  * C4's red leg keeps every `template/tests/*.py` hunk (`:214-217`), so a new test file earns
    a real red — provided it imports no symbol this patch adds at module level: a red-leg
    import failure is recorded `PDCA-UNVERIFIABLE`, not red (`:231-233`). Exercise everything
    through the pre-existing API (`progress.run_with_heartbeat`, `leaves._invoke_leaf_resilient`).
- **Invariant to restore:** **A failure is classified by what actually happened, and the
  evidence of it is kept.** Two halves, stated over the category rather than one API string:
  the harness must read the leaf's **own account** of its death out of the stream it is
  already parsing — never infer a cause from prose it was not given, and never *promote* a
  cause the vendor marked permanent — and it must **retain** that account in the artifact the
  cycle preserves. "Produced no output" is a proxy for "died at invocation" that fails for
  every long session; and "no evidence" must never be filed as a verdict. Self-test: it
  cannot be satisfied by guarding a single module — the classification lives in the stream
  reader, the retention in what `output` carries, and the definition is restated in four
  places downstream that go stale the moment it widens. Source: internal project invariant
  (Tier C), the target's own written rules — `progress.py:55-64` (what the transient signal
  is for, and that a *retryable* API error is already named there and excluded from
  "produced"), `leaves.py:641-647` (`(no output captured)` is "a post-mortem artifact that
  explains nothing", #286 review), `engine/README.md:44-68`. `docs/principles.md` §5/§6 are
  unfilled scaffolds in this instance, so no §6 category gate applies.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Ordering note:** No `Depends on` / `Conflicts with` — the sibling child-1 is independent
  (neither needs the other to compile or to go red→green) and both build on `origin/main` in
  one wave, which is also what this instance's own #474 base-export leak makes preferable
  (`plan-0.60-bug-order.md`). The two children share `leaves.py` but in disjoint regions:
  this one touches **prose only** (the four sites that restate the transient definition),
  child-1 owns the wrapper body, `do_build` and the harvest sites; and they ship tests in
  **different files** by construction. Recommended merge order at publish: **child-1 first**,
  then this one — widening *which* failures are retried is what first makes a leaf retryable
  after it has produced work, and child-1 is what makes that safe.
- **Surfaces:** data
- **Difficulty:** high
- **Scope:** What a leaf's death *is*, on the spawn path every leaf shares — read the CLI's
  own terminal error report out of the stream the driver already parses, classify transient
  by what the **vendor** marked (not by prose the harness guesses at), and keep that text so
  it reaches the leaf's `*.error.log` by the route the stderr tail already takes. Update the
  four downstream prose sites that restate the old definition so the codebase does not carry
  two contradictory statements of it.
  **Out of scope:** who is retried and what a retry may inherit — the builder is **not** put
  on the resilient path here, `_invoke_leaf_resilient`'s body, `do_build`, and the artifact
  harvests are sibling child-1's (this child changes only `progress.py`, the four prose sites
  in `leaves.py`, one comment in `assemble.py`, and its own tests/fixtures); resuming a long
  session via the CLI's own session-resume (a fresh re-invoke is the accepted first cut — say
  so in `build-notes.md` so the human can weigh it); the gate-side transient (issue #371); a
  leaf **signal-death** under the memory cap (issue #510: "neither #506's transient nor
  #421's preflight"); the memory-telemetry post-mortem (#420), which must keep working
  unchanged; any new `pdca.toml` knob.
- **Repro instruction:** On a clean checkout of the target base (`origin/main` of
  eduralph/pdca-harness), offline, from `template/`:
  1. `PYTHONPATH=src python3 -m unittest tests.test_leaf_resilience -v` — green today. Read
     `:32-35` and `:66-74`: `_SUBSTANTIVE` emits one stream event, then fails, and the suite
     asserts it is **not** retried. That is the rule the incident falls foul of.
  2. Read the drop: `progress.py:147-158` (stdout parsed for a session flag and a tool label,
     then discarded), `:143` + `:162-171` (the bounded **stderr** tail), `:255` (`output` is
     that stderr tail when `capture` is off), `:257` (what the third return value means),
     `leaves.py:103-107` (`transient` is `not produced`), `leaves.py:724-730` (the
     `(no output captured)` fallback the incident's log shows verbatim).
  3. Read what the module already knows and does not use: `progress.py:55-64` (claude emits
     `system`/`api_retry` on a **retryable** API error — deliberately excluded from
     "produced") and `_SESSION_EVENT_TYPES` (`:359`).
  4. The live incident is named in the parent issue: getwyrd/wyrd-pdca `results/issue_717/`
     (`build.error.log`, `loop-telemetry.json`); the identical argv re-run minutes later
     succeeded.
- **External dependencies:** none — the base toolchain suffices. Every leg is driven by a
  stub "leaf" that is a Python interpreter, so the slice builds and goes red→green with no
  vendor CLI, no API key, no network and no container. (Grounding the event shape against the
  vendor is a *reading* step, not a build or verification input — see Citations expected.)
- **Test file:** `template/tests/test_terminal_error_classification.py` (**new**), plus
  `template/tests/fixtures/` for the pinned vendor record and its provenance note. Do **not**
  append to `template/tests/test_leaf_resilience.py` and do **not** edit
  `template/tests/test_build_error_log.py`: sibling child-1 owns both and builds on the same
  base in the same wave — a shared test file is the one place the two patches would collide.
- **Citations expected:** Do must cite `path:line` on the target branch for every change.
  Composition cues — this slice wires into patterns the codebase already applies:
  * `progress._is_session_event` (`:365-377`) is the existing per-family stream classifier:
    it dispatches on `stream_format`, parses JSON best-effort and defaults to `False`. A
    terminal-error reader belongs **beside it, in the same shape**, so the codex/gemini
    formats degrade to today's behaviour instead of guessing;
  * `:143` + `:162-171` show how a bounded tail is kept (`deque(maxlen=…)`) and `:255` how it
    becomes `output` — the retained report should reach `LeafError.output` by that same route,
    so `_format_leaf_attempt` (`leaves.py:724-730`) needs **no** special case and this child
    need not touch it (it is child-1's);
  * `leaves.py:661-670` documents why a stream-less family reports `produced=True`; keep that
    fallback intact;
  * the four sites that restate the definition and go stale when it widens — update the prose,
    touch nothing else in them: `leaves.py:90-107` (`LeafError`), `:661-670` (the `_invoke`
    comment), `:2534-2549` (`_failure_class`), `:2573-2590` (`_unavailable_classification`),
    and `assemble.py:80` (`LEAF_STATUS_INFRA`'s "ran, died with no output" comment);
  * **Vendor grounding is the standard this slice is held to.** Two of the parent's four
    rejected rounds were rejected for asserting an event shape the CLI cannot emit, and the
    round that held re-derived it from the shipped binary. Establish the shape from the
    installed `claude` CLI and/or a real session transcript under `~/.claude/projects/`, and
    record next to the fixture which claims are **observed** and which are **derived**.
  * **Prior art you may read, selectively:** the rejected single-slice attempt is archived at
    `results/issue_506/iteration-v4/patch.diff` (+ `build-notes.md`), including a pinned
    fixture and a provenance README that the adversary independently re-derived from
    claude-code 2.1.233. You may reuse them — re-verifying the load-bearing claims first —
    and read the `progress.py` hunks for decisions already settled (the matcher anchored on
    the vendor's own marker; the "the CLI recovered" clearing rule; stickiness against the
    session wrap-up). Two defects were still open against that attempt and must not be
    rebuilt: the clearing rule was **scope-blind** (one trailing *sub-agent* line restored the
    pre-fix outcome exactly — require the clearing event to be main-session), and stickiness
    was implemented over *any* later report so a **second** marked report (a permanent 400
    following a dropped connection) was swallowed. Read **only** the hunks for the files this
    child owns — re-applying the `leaves.py` body / `do_build` / harvest material would
    recreate the oversized slice this split exists to undo.

  **Path convention in this brief:** every `template/…` and `tests/…` path is on the **target
  branch** (eduralph/pdca-harness @ main) — the files Do reads and edits. Every `engine/…`,
  `pdca.toml` and `results/…` path is in **this pdca-pdca instance** (the verification engine
  and the bundles that run the cycle); they are cited to explain how the gates will judge the
  patch, and Do must not edit them.
- **Prior-art check (triage cycles):** By file path on `origin/main`:
  `template/src/pdca_harness/progress.py` — `0881af9` (#420 memory sampling), `4091b94`
  (straggler sweep), `228e80b` (#368 timeouts), `49f6611` (#286, "capture a stream-less leaf's
  stderr too"): the closest relative, and it extended **stderr** capture — the stream's own
  events were never read. Open PRs on the target (`gh pr list -R eduralph/pdca-harness
  --state open`): #519-#525; none touches `progress.py`, and the two that touch `leaves.py`
  (#524 issue 494, #520 issue 466) are at distant regions. Open issues searched for
  `transient`: #371 (gate-row transient red) and #510 (signal death) are adjacent and
  deliberately excluded above; #509 (crash-resume) is a different beat. Not previously
  attempted as its own slice, not rejected; the parent 506's four-round attempt was rejected
  on slicing (`results/issue_506/iteration-v4/SUMMARY.md` §9).
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.
<!-- pdca:end child-2 -->
