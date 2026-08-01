# build-notes — issue 316 / pdca-triage

Target: eduralph/pdca-harness @ main (worktree `pdca-harness.pdca-wt-l1`, base
dfd0427). All `path:line` cites are against that tree with the patch applied.

## What was built

A new engine module `template/src/pdca_harness/triage.py` (534 lines) + `cli.py`
wiring + one additive parameter on the ledger API + one config key, satisfying the
brief's criterion (a)–(d):

- **(a) pull** — `triage._gh` / `triage._api` (triage.py:118-137) run
  `subprocess.run(["gh", "api", …])`, the exact pattern of `cleanup._gh`
  (cleanup.py:66) and publish's gh machinery (publish.py:460). Three calls:
  `repos/<r>/pulls/<n>` (merged state), `…/reviews`, `…/comments` (per_page=100).
  A failed pull **aborts** (triage.py:415-429): a half-ingested PR silently
  under-registers signals, which is the one direction this command must not degrade
  in — same fail-closed rule as cleanup's repo derivation (#300).
- **(b) classify** — `classify` (triage.py:215) + `class_keywords` (triage.py:194):
  whole-word keyword match, severity-first precedence (`CLASSES`, triage.py:70 —
  BUG > TEST-GAP > CONVENTION > NOISE; "nit: this crashes" is a bug someone
  softened, and mis-filing a real bug as noise buries it while the reverse only
  files a too-serious candidate a human downgrades). The rubric's class list
  (#314), where configured, overrides one class's keywords via a `- BUG: kw, kw`
  line (read through `publish._checkout_path` + `rubric._resolve`/`_section`,
  triage.py:228-246, fail-open like rubric.load); instances without a rubric get
  `DEFAULT_KEYWORDS` (triage.py:76), per the brief's compatibility note.
- **(c) route** — `run` (triage.py:405): BUG on a **merged** PR files one tracker
  issue per finding via `split.can_file` + `split._create_issue`
  (split.py:524/580 — "the existing gh machinery" the brief scopes in), body =
  finding + provenance + a `## Carry-forward` note (`_issue_body`, triage.py:327);
  CONVENTION → "candidate gate row / rubric line" appended to the act log; NOISE →
  "candidate rubric-exclusion entry"; TEST-GAP → candidate test note
  (`_entry_text`, triage.py:352). The act log is the ceiling: nothing edits
  pdca.toml, the rubric, or gate rows.
- **(d) register** — every finding becomes a class-keyed signal registered through
  `act.register_signals` (act.py:479) with `min_count=1` (triage.py:505-508), over
  synthetic `ActEntry` rows rebuilt from the per-PR triage records
  (`_entries`, triage.py:299); `act.recurrences` (act.py:510) is then fed the same
  entries, so a class-keyed signal reappearing after `pdca act resolve` marked its
  delta applied is flagged — in the printed summary AND in the act-log entry.

## The signal-name grammar (the brief's open question — Do proposes)

```
codex-pr:<class-slug>[-<keyword-slug>]      e.g. codex-pr:convention-docstring
```

(triage.py:36-45, 108-114.) Both segments come from the keyword table (built-in or
rubric-supplied), **never from the free comment text** — that is what makes the
name stable across runs, which recurrence matching depends on: `act._norm` of a
single hyphenated token is the token itself, so ledger dedupe and
`recurrences()`'s set-membership both match exactly. Keyword granularity is
deliberately finer than the bare four classes: a delta that fixed docstring
conventions is not refuted by a naming-convention finding. Known limit, accepted:
"crash" vs "crashes" are distinct keywords → distinct signals; the keyword table
carries both spellings where that matters (DEFAULT_KEYWORDS BUG row).

## Design decisions and rejected alternatives (with cost)

1. **`min_count` parameter on `act.register_signals` (act.py:479-491, +4 changed
   lines)** rather than working around its recurring-only threshold.
   `register_signals` only registers signals `_recurring` sees ≥2×, but the brief
   requires "registers **every** finding". Rejected alternatives:
   - *Pass `[entry, entry]`* (0 engine lines): makes a first-sight finding
     "recurring" by feeding the same entry twice — lies to the #149 contract and to
     any future reader of `_recurring`; the ledger would record a fabricated
     multiplicity. Cheaper in lines, dearer in honesty.
   - *Hand-append ledger dicts from triage* (~15 lines duplicating the
     schema/dedupe/save of act.py:479-492): bypasses the API the brief explicitly
     names as the peer to compose with, and drifts the first time the ledger
     schema changes.
   The parameter keeps default behaviour bit-identical for the three existing
   callers (cli.py:1216, leaves.py:2676/2693 — all call without `min_count`,
   default `min_count=2` ⇒ `c >= 2` ≡ old `c > 1`).
2. **Carry-forward note lives in the filed issue's body**, not appended to the
   originating bundle. The tracker thread is the one input the next cycle's Plan
   actually reads (the notes fetch); the originating bundle is COMPLETE/frozen, and
   appending to a frozen bundle mutates a record the Act frontier fingerprints
   (act.py:197-213, #299) — a triage run could silently turn a reviewed bundle
   "unreviewed". Cost of the rejected form: ~6 lines to append a file into the
   bundle + an unquantifiable interaction with `_covered_names`; the issue-body
   form is where Plan reads anyway.
3. **Per-PR JSON record (`process/triage/pr-<repo>-<n>.json`)** as both the re-run
   dedupe and the recurrence history. Re-running the same PR is the *normal* case
   (findings arrive over days — the brief's own argument against doing this in
   publish), and tracker issues cannot be rolled back, so a re-run must never
   re-file (split's rule, split.py:609-620). Rejected: refuse-on-existing-record
   (~4 lines cheaper) — it would make the primary use case (new findings arriving
   later) an error. Order inside `run` mirrors split: file (irreversible) → write
   record (makes filing non-repeatable) → register/log; a crash between record and
   register self-heals because registration always re-derives from the FULL record
   history on the next run (triage.py:482-509).
4. **Recurrence entries are grouped per (PR, ingest date)** (`_entries`,
   triage.py:299-323): recurrence compares `e.date > applied`, so folding an old
   finding into a re-run's entry would advance its date past a delta applied in
   between and fabricate a recurrence.
5. **Model pass is a config-gated hook, off by default** (`[triage].model_cmd` →
   `Config.triage_model_cmd`, config.py:350-356/645; `_model_pass`,
   triage.py:249-273): runs only over the unclassified remainder, subprocess-based
   (stubbable), fail-open — exactly the ceiling the brief's scope sets. An unset
   key means an instance taking `copier update` gains no model call it didn't ask
   for (the #342 property the config comments enforce elsewhere).
6. **Bare PR number without `--repo` is refused** (parse_pr, triage.py:142-160;
   exit 2): gh's checkout-default repository could hold an unrelated same-numbered
   PR — the same fail-closed reasoning as cleanup.py:388-396.
7. **Registration + log append run under the shared Act session lock**
   (triage.py:497-503, `act.act_session`, act.py:118): a triage overlapping a
   flow's auto-Act must not interleave ledger/log writes with a review in
   progress; the loser reports and retries, like `act log --append`
   (cli.py:1200-1204).

## Ordering note (brief: conflicts with 317)

317 adds a subparser in the same cli.py registration block — textual collision
acknowledged; this patch adds its block after the `act` group (cli.py:314-337) and
its dispatch after the `act` dispatch (cli.py:462-464). No dependency.

## Verification — red→green through the project's runner

Green leg + red leg were run through the **configured C4 gate command**
(`pdca.toml [gates.checks] → ./engine/scripts/run-verify.sh`, from the instance
root with `PDCA_BUNDLE`/`PDCA_WORKTREE` set):

```
== C4 green leg: bundle test(s) with the fix applied: template/tests/test_triage.py
Ran 15 tests … OK
== C4 red leg: bundle test(s) with the production change reverted
FAILED (errors=1)   (ImportError: cannot import name 'triage' …)
C4 PASS: red without the fix, green with it
```

Also run: the T3 gate `./engine/scripts/run-suite.sh` — root render/update-compat
suite (7 tests, OK — it copies the working tree, so the patch is exercised in a
rendered instance too) + full offline driver suite (**1328 tests, OK**, 2
pre-existing skips). Worktree verified restored after the red leg; `patch.diff`
byte-identical to `git diff` of the worktree.

## Forced self-refutation (the three questions)

- **(a) Genuine red?** YES — the C4 red leg reverts every production hunk
  (triage.py, act.py, cli.py, config.py; the test stays) and the run FAILS: the
  module doesn't exist on main and the parser rejects the verb, exactly the
  brief's falsifiability claim. Evidence: run-verify.sh transcript above.
- **(b) Production path?** YES — the tests import `pdca_harness.triage`,
  `pdca_harness.cli`, `pdca_harness.act`, `pdca_harness.split` from
  `template/src` (PYTHONPATH=src — the production package), drive `triage.run`
  and `cli.main(["triage", …])` end-to-end
  (test_triage.py:test_cli_drives_the_engine_end_to_end), and assert on the REAL
  artifacts the production code writes (`process/act-ledger.json`,
  `process/act-log.md`, `process/triage/pr-*.json`). The only stub is the `gh`
  subprocess boundary — precisely what the brief prescribes ("tests stub gh
  exactly as template/tests/ stubs publish's subprocesses").
- **(c) Fixture includes the fault?** YES — the canned gh payloads include the
  elements that would falsify each claim rather than curating them out: a
  body-less APPROVED review (must NOT become a finding), an **unmerged** PR with a
  BUG finding (must NOT file), a deleted/404 endpoint (must abort, not
  half-ingest), a re-run with identical findings (must not re-file), and the
  recurrence scenario genuinely re-presents the same class-keyed signal on a
  second PR **after** `act.resolve` marks the delta applied — `recurrences()` is
  asserted to flag `codex-pr:bug-crashes` recurred in `pr_8` with the applied
  date, not merely "some output appeared".

## Commit-readiness

The target repo has no formatter/pre-commit hooks (checked: no .pre-commit-config,
no ruff/flake8 config; CONTRIBUTING.md requires only the DCO `Signed-off-by`
trailer, which the publish machinery adds at commit time). Both target suites pass
on the patched tree; style follows the house pattern (heavily-documented modules,
stdlib-only, ~95-col lines, unittest tests).

## STOP discipline

Nothing pushed, no PR opened. Patch + test + notes live in the bundle only.
