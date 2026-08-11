# Build notes — issue_472 (flow-adopt-core), iteration 3

Target: `eduralph/pdca-harness` @ `main` (worktree `/home/eddie/pdca/pdca-harness.pdca-wt`,
HEAD `3e3b829` — the merge of PR #470/#468, so the brief's `Depends on (merged): 468` is
satisfied). Every `path:line` below is against that base **plus this patch**. Verified:
`git apply` of `patch.diff` onto a pristine `git archive 3e3b829` extract reproduces this
worktree **byte-for-byte** (`diff -r` clean apart from the untracked `.cache/`).

## What changed since iteration 2

Iteration 2 converged on every gate (C4 PASS, T2/T3/T4 pass) and the reviewer's 5/5/1 was
all-PASS except the two permanently-human rows. The driver auto-iterated on the adversary's
**two implementation-level findings**. This iteration is v2 **plus** the answers to those
two — one of them a real behaviour fix, not a comment — and the citation upkeep that fix
forces. The adoption core itself (`_report_held`, `SPLIT_DISPOSITION`, `_is_split_parent`,
`_adoptable`, `_reschedule`, `_adopt_split_children`, `_drive_wave` returning its pass
count, the run-wide pool, the splice) is unchanged from the converged carve.

| finding (v2 adversary) | answer | size |
|---|---|---|
| `flow.py:975` / `:948-950` state an invariant the run does not keep: a child adopted by an EARLIER call and held by a LATER one stays in `bundles`/`batch_names`, so it IS in the results map | **fixed the behaviour**, not the sentence: `_adopt_split_children` now drops such a child back out of the drive set and retracts its announcement (`flow.py:1022-1037`) | +16 lines in `_adopt_split_children` (10 code, 6 comment), +1 `named` param, +6 at the caller; +61/−4 test lines (1 new test) |
| `config.py:312` cites `config.py:671` (the *read*) for the clamp, which is at `685` | citation corrected, and it now quotes the clamp expression so a future line-shift is self-evident (`config.py:312-315`) | +4 / −3 comment lines (a 3-line sentence becomes 4); the other +2 / −2 in this file are the two `flow.py` citations the insert shifted |
| (forced by the above: 392 lines of insert shifts every downstream line) | refreshed **every** `path:line` the patch adds or invalidates, incl. two pre-existing ones in `cli.py:609-610` that this patch's insert moves | 2 lines in an 8th file |

Measured delta v2 → v3 (`diff -u` of the v2 tree against this one, per file): `flow.py`
**+52 / −14** — of which **11 are executable** (the 10-line retraction block and the
`frozenset`), the rest docstrings and refreshed citations; `config.py` +6 / −5 (comments
only); `cli.py` +2 / −2 (citations only); `test_flow_adopt_split.py` +61 / −4;
`docs/07-crosscutting.md` +4 / −1. Patch 93 215 → 102 119 bytes (99.7 KB), 7 → 8 files — both under the
`[driver.size_signal]` thresholds of 125 KB / 25 files.

### 1. `flow.py` — "held ⇒ out of the results map" made unconditional

The finding, reproduced by the adversary and re-reproduced here as a test: the promise the
brief's Success criterion states ("a child with an unresolvable dependency is held loudly …
**excluded from the results map** … and the run continues") only held for a child held by
the reschedule that FIRST saw it. Each splice re-levels the whole un-driven tail, so a child
adopted into wave 2 can be held by the wave-1 splice — and v2 left it in `bundles` /
`batch_names`, i.e. in the map, as PLANNED, with a stale `adopted … into wave 2` line still
standing and the run exiting 1.

The adversary offered two exits — "either drop a late-held child from `bundles`/`batch_names`
(and retract the announcement), or narrow the two docstring claims". **I took the behaviour**,
and the reason is not cost, it is the brief: the criterion is unconditional, and the
docstring-only exit leaves the SAME situation reporting two ways (out of the map + rc 0 vs.
in the map + rc 1) decided purely by which reschedule happened to hold the child — the
"invariant to restore" reading of `docs/principles.md` §1.2, not the smallest-diff one. Both
options are small; the sizes are not what separates them:

* narrow the docstrings: −2 / +2 comment lines, 0 behaviour — and the defect the issue exists
  to fix (a split's child stranded, only visible on stderr) keeps a second, quieter form;
* drop it back out: the 16 lines at `flow.py:1022-1037` plus one `frozenset` at
  `flow.py:1191` and one keyword at the call site — and the shape is then identical whenever
  the hold happens.

The fix:

```python
    retracted = sorted(d.name for d in remaining
                       if d.name not in named and d.name not in wave_of)
    if retracted:
        gone = set(retracted)
        bundles[:] = [d for d in bundles if d.name not in gone]
        batch_names -= gone
        for name in retracted:
            print(f"flow: {name} — adopted earlier this run, now held: it is NOT scheduled "
                  f"and NOT in this run's results (the earlier adoption line no longer "
                  f"stands)", file=sys.stderr)
```

`named` (`flow.py:1187-1191`) is the frozen set of ids the run SET OUT to drive. It is
load-bearing in the other direction: an id the OPERATOR named that the re-levelling holds
must stay in the map — the run owes an answer for every id it was given, documented at
`flow.py:1201-1210` and pinned by the pre-existing
`test_a_named_id_in_the_re_scheduled_tail_is_held_not_lost`. Frozen rather than aliased to
`batch_names` for the same reason (an alias would grow with adoption and quietly make every
adopted child "named"); the alias mutation is in the battery below.

`batch_names -= gone` is deliberate, not incidental: `batch_names` and `bundles` are two
representations of one drive set, and leaving the name behind would make `_adoptable` tell a
later parent that a bundle this run is NOT driving is "already in this run's drive set" — a
false line in the log the operator reads. It is pinned by the same test's third parent leg
(801's record also names 602), so the pair cannot drift.

Docstrings re-stated to match, rather than left as the aspiration the code missed:
`flow.py:952-963` (the `named` contract + the retraction), `flow.py:990-995` (the
"exits 0" bullet), `flow.py:795-797` and `flow.py:965-970` (the boundedness claim: "a bundle
already in the drive set is never adopted again" — v2's "adopted at most once" is no longer
true once a retracted child can be taken up again, and saying so is the point of this whole
finding), `flow.py:1208-1210` (the named-id counterpart), and `docs/07-crosscutting.md:264-267`
for the operator-facing statement.

### 2. `config.py:312` — the clamp citation

`config.py:671` is `max_passes = int(driver_cfg.get("max_passes", 20))`, the *read*; the
clamp is `max_auto_iters = min(max_auto_iters, max(1, max_passes - 1))`. The comment now
**quotes the expression** as well as naming the line (`config.py:686`), so the next time an
insert shifts it the sentence still identifies its own referent. This is the site iteration
1's carry-forward flagged and iteration 2 half-fixed (the invariant text was rewritten, the
citation was not).

### 3. Citation upkeep the fix forces (why an 8th file)

392 inserted lines move everything below them in `flow.py`. I re-resolved **every** `*.py:N`
citation the patch adds — script in the transcript, output pasted below — and two
pre-existing ones in `cli.py:609-610` that this patch invalidates (`flow.py:1086-1100` →
`1450-1464`, `flow.py:1121-1127` → `1485-1491`; both point at real code on the base, so the
patch would have broken correct citations). That is the whole `cli.py` change: 2 comment
lines, no behaviour, no test surface. Also tightened two loose anchors the audit caught in
the test module's own prose (`test_flow_slice.py:31-56` → `:32-55`, the actual `_stub_config`
body; `flow.py:387-394` → `:380-394`, the paragraph that actually says it).

Final audit output (all 27 distinct citations added by the patch, each resolved against the
patched tree): every one lands on the statement it names — `flow.py:758` `_warn_abandoned`'s
predicate, `flow.py:678` `_lineage_children`, `flow.py:675` `_TERMINAL`, `flow.py:1141` the
exhaustion report, `flow.py:1255` the `_point_at_integration` call, `flow.py:1260` the
`min(allowance, budget - spent)` hand-down, `split.py:373/382-390/525/627-634/296-311/635`,
`waves.py:243-246`, `cli.py:604-622`, `test_flow_slice.py:32-55` / `:1122-1128` / `:1137`.

## Carried over from iteration 2 (unchanged, and why)

* Adoption lives **once** on `_drive_and_act` (splice call at `flow.py:1265-1266`), the shared
  path both CLI shapes and `flow_batch` reach since #468 — never in `flow_ids`/`flow()`. A
  second site is the divergence #449 spent five iterations chasing.
* The pool is sized off the **pre-adoption** schedule (`flow.py:1216`); live re-sizing is the
  sibling child's, per the brief. The rejected floor (`max(budget - spent,
  cfg.max_auto_iters + 1)`) is re-measured in v2's notes: it makes a `--max-passes 3` run
  spend 4. Not repeated here.
* The announced wave index is read back from the recomputed schedule, never `k + 1`.
* Two boundaries stay documented rather than changed, both **deferred to sign-off** in
  `deferred-findings.json`: a bundle that declared `Depends on <parent>` is levelled by its
  own edges and can share a wave with the children the parent decomposed into
  (`flow.py:985-989`); and `pdca split --accept`'s hint still prints `pdca flow <child-ids>`,
  right outside a running flow and redundant inside one (`cli.py:794`).

### T4 Contribution (`commit-msg.txt` / `pr-description.md`) — still deliberately NOT supplied

Third round in which the auto-iterate quotes the reviewer's T4 row ("the contribution texts
were not supplied, so the asserted checker pass cannot be independently rerun"). The answer
is unchanged and is a **cycle-order fact, not a defect in this patch** — restating it because
build-notes is the file the human reads at sign-off:

* `template/src/pdca_harness/cli.py:1075-1083` (issue #401) documents exactly this condition
  — "at Check time the two artifacts it lints do not exist — publish drafts them later" — and
  `cli.py:1098` prints `gates.DEFERRED_MARKER` so the row records as *deferred with its
  reason*. The target's own designed behaviour, already shipped.
* This **instance's** engine predates that render (`DEFERRED_MARKER` is absent from
  `pdca-pdca/src/pdca_harness/gates.py`), so the row reports a bare `pass` and the reviewer
  must raise it as judgment. A `copier update` of the instance is what removes the noise —
  not a change to `template/`, and not something Do can close.
* `publish._ensure_texts` (`template/src/pdca_harness/publish.py:52-62`) is **only-if-missing**.
  A builder-written `commit-msg.txt` would therefore not be "an extra artifact to lint" — it
  would silently become the SHIPPED text and skip the interactive publish drafting the human
  owns, on a bundle whose §9 is not yet recorded.

So: left open for the human at sign-off (it costs one read) rather than fabricating
release-facing text to turn a row green.

## Verification — through the project's own runners only

| runner | result |
|---|---|
| `./engine/scripts/run-verify.sh` (C4, gating) | **`C4 PASS: red without the fix, green with it`** — green leg 22 + 19 tests OK; red leg **21 of 22 failing** |
| `./engine/scripts/run-suite.sh` (T3) | `== T3: root suite OK, driver suite OK` — root 7 OK, offline driver suite **1655 tests OK (skipped=2)** |
| `./engine/scripts/run-docs-check.sh` (T2) | `lint_docs: OK`, `render_site: link audit OK` (22 pages) |
| `./scripts/pdca contribcheck` (T4) | rc 0 |

No hand-rolled runner was used for the legs: `run-verify.sh` is the gate command `pdca.toml`
registers, and it runs `cd template && PYTHONPATH=src python3 -m unittest tests.<module>`
itself. The mutation probes below ran that same module invocation under an explicit
`timeout 300`, each with `flow.py` restored and re-diffed afterwards.

### Mutation evidence for the NEW lines (each mutation, then the full module; restored after)

| mutation | failures |
|---|---|
| delete `bundles[:] = [d for d in bundles if d.name not in gone]` (`flow.py:1032`) | exactly `test_a_child_held_by_a_later_reschedule_leaves_the_run` (`{… '602': 'PLANNED' …} != {'500': 'COMPLETE', '601': 'COMPLETE', '801': 'COMPLETE', '901': 'COMPLETE'}`) |
| delete `batch_names -= gone` (`flow.py:1033`) | exactly the same test (the false "already in this run's drive set" line reappears) |
| delete the retraction `print` (`flow.py:1035-1037`) | exactly the same test |
| `named` guard dropped (`d.name not in named and …` → `… not in wave_of`) | exactly `test_a_named_id_in_the_re_scheduled_tail_is_held_not_lost` (`None != 'PLANNED'` — a NAMED held id would vanish from the map) |
| `named = frozenset(batch_names)` → `named = batch_names` (alias, so it grows with adoption) | exactly `test_a_child_held_by_a_later_reschedule_leaves_the_run` |
| **the whole v2 baseline** (delete the retraction block entirely) | exactly `test_a_child_held_by_a_later_reschedule_leaves_the_run`, reproducing the adversary's finding verbatim: `{'500': 'COMPLETE', '601': 'COMPLETE', '602': 'PLANNED', '801': 'COMPLETE'}` |

v2's battery (the `taken` dedup, both `_adoptable` guards, the bundle-root escape, the `seen`
dedup, the run-pool break, the pass hand-down, both `return used` exits, the live fold test,
`_is_split_parent`'s terminal half and its total `except`, the real-wave read-back,
`scheduled`-only growth, `partition_schedulable` tolerance) is unchanged and was not
re-derived; the adversary confirmed 18/20 killed there and the one survivor is cosmetic
(`sorted(...)`).

## The three refutation questions

**(a) Genuine red?** Yes — actually reverted and re-run through the gate, twice (once before
the final citation pass, once after). The C4 red leg (`git apply -R --exclude=tests/*
--exclude=template/tests/*`) leaves **21 of 22** tests failing, including the new one. Exactly
one test is green on the red leg, deliberately:
`test_a_run_that_adopts_nothing_keeps_a_full_budget_per_wave` is a NO-REGRESSION control —
green pre-fix is its entire point — and it binds by mutation instead (`budget = allowance *
len(wave_list)` → `budget = allowance` fails it, verified in v1). The new test is red for two
INDEPENDENT reasons, which is what makes it bind the actual gap rather than the feature it
sits on: without adoption at all (the C4 leg) 601/801/901 never run; with v2's adoption but
no retraction, the results map carries `602: PLANNED` and the run exits 1.

**(b) Production path?** Yes. Every test drives `cli._flow` (`cli.py:558`) with a real
`argparse.Namespace`, routing through the production `flow.flow_ids` → `_drive_and_act` — the
function this patch changes. The results map under assertion is the map the CLI derives its
report and exit code from: `_capture_results` (`test_flow_adopt_split.py:284`) is a
pass-through around the **real** `flow.flow_ids` that records and returns its exact value.
The split is built by the production `split.accept` (`split.py:525`), so the close marker,
`split-lineage.json` and the child bundles are byte-for-byte what `pdca split --accept`
writes; the child's `Depends on` edge is rewritten from the proposal label by the production
`split.rewrite_ordering`. The only patched functions are pass-through spies (`_build_all`,
`_drive_wave`, `_point_at_integration`, `flow.flow_ids`) that call the real one and return
its value. Leaves are the repo's own offline stubs (the `test_flow_slice.py:32-55` fixture
shape) — headless: no display, no network, no container.

**(c) Fixture includes the fault?** Yes, and the new test is specifically about a fault v2's
fixtures could not exhibit. The split happens *inside the run being measured* (Entry B:
sign-off records `iterate-plan` → the bundle re-opens → the next pass's Plan splits it), and
the new test then injects the missing element rather than curating it out: 601 splits AGAIN
inside its own wave (so a SECOND reschedule really happens — without it there is only one
splice and the bug is unreachable), and 602's brief is re-planned onto an unresolvable
prerequisite in the one window where it is adopted-but-not-yet-driven (`after_wave`, between
the wave returning and adoption reading it). The failing element is the held child itself: it
is present in the run, announced into wave 2, and the assertion is on the WHOLE results map
(`assertEqual`, not a membership probe), so a fixture that quietly lost 602 would fail too.
801's lineage record then names 602 a third time, so "dropped from the drive set" is asserted
against a consumer of that set rather than only against the map.

## Commit-readiness

The target configures no formatter or linter: no `.pre-commit-config.yaml`, no
`ruff.toml`/`.flake8`/`setup.cfg`/`tox.ini`, no root `pyproject.toml`, no `[tool.*]` lint
config. Its CI is `docs-check.yml`, `docs.yml`, `render-check.yml`, `require-linked-issue.yml`
— the first and third are exactly the T2 and T3 gates run above. CONTRIBUTING.md's only
mechanical requirement is the DCO trailer (`git commit -s`), which the publish step adds.
Checked by hand over the whole patch anyway: **0 added lines wider than 95 characters, 0 with
trailing whitespace** (`python3 -m compileall` clean on the changed modules). No external
dependency beyond python3 ≥ 3.11 stdlib + git was needed — nothing to declare.
