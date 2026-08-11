# Build notes — #472 (flow-adopt-core), iteration v4

Withheld from the reviewer; written for the human at sign-off.

All `path:line` are on the target worktree `/home/eddie/pdca/pdca-harness.pdca-wt`
(target branch `main` @ `3e3b829`, the merge of PR #470) with `patch.diff` applied,
unless the line says "on the base".

## 1. What this iteration is

v3 converged on everything the brief asks for except two rows, and the carry-forward
(`brief.md:121-124`) names exactly those:

1. **C5 NEEDS-HUMAN [impl] — "make lineage containment resolution-aware"**: the reviewer
   probed an `issue_<id>` **symlink** pointing outside the bundle root and found it
   *adoptable*, because v3's guard compared the LEXICAL parent (`d.parent !=
   cfg.bundle_root`), which `cfg.bundle` makes true by construction.
2. **T4 NEEDS-HUMAN — release text owed**: `commit-msg.txt` / `pr-description.md` were
   absent for three consecutive rounds, so the gating T4 row attested nothing.

I also took the two **builder-fixable** implementation findings the v3 adversary filed
(`iteration-v3/check-advisory-adversary.md:69` and `:87`), since both are cheap, both
are in the code this brief owns, and leaving them would have cost a fifth round.

So this is v3's converged patch **plus four changes**, not a re-derivation. Measured
delta from the v3 reference (`iteration-v3/patch.diff`, reconstructed and diffed):
`flow.py` **+141 / −54** lines (of which ~90 added lines are docstring), the test module
**+120 / −6** lines (3 new tests, 1 assertion updated).

## 2. The four changes, and why each is the shape it is

### (a) Resolution-aware containment — `flow.py:824` `_inside_bundle_root`

`d.resolve().parent == cfg.bundle_root.resolve()`. Both sides resolved so an instance
reached through a symlinked checkout still compares equal; total `except` so an
unresolvable path (symlink loop, permission wall) refuses rather than raises — the same
rule the two readers above it already follow (`split.read_lineage`, `split.py:382-390`).

**The trap I hit and had to design around:** resolution-aware containment *alone* is
strictly WEAKER than the lexical check for the traversal case the brief names.
`realpath` normalises `results/issue_../../etc` → `results/etc`, which is *inside* the
root, so replacing the lexical test with a resolved one would have silently **opened**
the `"../../etc"` hole while closing the symlink one. That is why (b) exists and why
both guards ship; the docstring says so at `flow.py:836-839` so nobody "simplifies" one
away later.

### (b) Id-shape guard — `flow.py:821` `_PLAIN_ID`, applied at `flow.py:932`

Mirrors the rule the WRITER already enforces (`split.validate`, `split.py:297`: "ids may
hold letters, digits, dot, underscore and hyphen only"). It is what makes the traversal
case above impossible before a path is built, and it also closes the adversary's second
[impl] finding in one place instead of three: with the id shape enforced, every branch
below can keep interpolating `{d.name}` / `{cid}` unquoted, so the common-path report
stays quote-free.

Rejected alternative (the adversary's suggested "one-token fix"): `{cid!r}` / `{d.name!r}`
in the three remaining branches. Cost is not the issue — it is 3 lines either way — but
it leaves `results/issue_6\n01` a *drivable* bundle and makes normal output read
`flow: 'issue_601' — child of issue_500 NOT adopted: …` on every ordinary skip. The
guard refuses the id once, quoted, and leaves the ordinary lines alone.

Rejected alternative: filter inside `_lineage_children` (`flow.py:679`), which would also
protect `_terminal_hint`'s `pdca flow <ids>` breadcrumb. Same 1 line, wider blast radius:
that helper is shipped base behaviour (#456/#468) and adoption would then have **no id to
report** ("every skip is reported" is the docstring's promise, and the guard tests assert
the reported id). The breadcrumb hazard is pre-existing and unchanged by this patch; I
left it to whoever owns `_terminal_hint`.

Mirrored rather than imported from `split`: the brief puts "the split command,
`split.accept`, or the lineage schema" out of scope, and exporting a constant from
`split.py` would edit that module to serve a reader. The mirroring is cited both ways
(`flow.py:810-820`).

### (c) Refusal reported AFTER the splice — `flow.py:987` `_report_refused`

The v3 adversary's reproduced case: `pdca flow 500 700`, both split in wave 0, 700's
record also naming 500's child 602, and 602 held by the reschedule. v3 printed
"already in this run's drive set" (from `known = batch_names | taken`, where `taken` is
a *claim*, not a schedule) next to "held this run … left in-flight", with 602 in neither
the drive set nor the results map.

`_adoptable` now appends `(parent, child)` to a `refused` list instead of printing;
`_adopt_split_children` reports it once the splice has settled, testing membership of the
FINAL `batch_names`. That single test covers all four outcomes (named id still in the set;
child claimed and scheduled; child claimed and held; child adopted earlier and retracted
by this splice), which is why I preferred it to "re-report the held child" — one predicate,
no second code path, and the two early exits (nothing adoptable / reschedule failed) fall
into it correctly because `batch_names` is unchanged there.

The call site keeps the literal `known=batch_names | taken` shape the brief's
falsifiability clause names (`brief.md:87`), so the required mutation is still directly
applicable — verified in §4.

To get one exit I hoisted the splice into `if adopted:` and moved the announcement below
it. Against the BASE that is not churn: the whole function is new in this patch.

### (d) `commit-msg.txt` + `pr-description.md` (bundle artifacts, not the diff)

Publish normally drafts these; three rounds of carry-forward show the T4 row cannot be
audited without them, so I supplied them. `./scripts/pdca contribcheck 472` → **rc 0**
against the real artifacts (not the absent-file default-open at `src/pdca_harness/cli.py:1035`).
Every `path:line` in the PR body was re-resolved against the final tree after the last
docstring edit shifted `flow.py` by +7 lines. `publish.py:48` only drafts when the two
files are MISSING, so publish will keep these; the human should read them as drafts and
edit freely — that is the one thing here that is properly theirs, and I am aware I am
pre-empting it. If they would rather the publisher drafted from scratch, deleting the two
files restores exactly the previous behaviour.

## 3. Citations re-resolved (this is where v1–v3 kept bleeding)

Every `path:line` the patch adds was re-extracted from the diff and checked against the
final files by script, twice (my own edits shifted `flow.py` by +1, then by +7). Corrected
this round: `flow.py:758→759`, `:678→679`, `:675→676`, `:458→459`, `:1141→1240`,
`:1255→1354`, `:1260→1359`, `:1201-1210→1300-1309`, `:1450-1464→1549-1563`,
`:1485-1491→1584-1590`, `split.py:296→297`. All 31 citations added by the patch now
resolve to the line they name.

## 4. Forced refutation of my own test (the three questions)

**(a) Genuine red?** Yes — and twice over.

- Whole-fix revert, through the project's runner: `PDCA_BUNDLE=… PDCA_WORKTREE=…
  ./engine/scripts/run-verify.sh` → green leg **25/25 OK**, red leg (production hunks
  reverted, tests kept) **24 of 25 FAIL**, verdict `C4 PASS: red without the fix, green
  with it`. The single test green on both legs is
  `test_a_run_that_adopts_nothing_keeps_a_full_budget_per_wave` — by construction a
  no-regression guard.
- Per-change mutation, on the shipped code (`cd template && PYTHONPATH=src python3 -m
  unittest tests.test_flow_adopt_split`, the invocation run-verify uses):

  | mutation | tests killed |
  |---|---|
  | `_inside_bundle_root(cfg, d)` → v3's `d.parent != cfg.bundle_root` | `test_a_child_bundle_symlinked_out_of_the_instance_is_skipped` |
  | drop the `_PLAIN_ID` guard | `…escapes_the_bundle_root_is_skipped`, `…with_a_newline_cannot_break_the_report` |
  | `refused.append(...)` → v3's eager print | `test_a_shared_child_the_reschedule_holds_is_not_reported_as_driven` |
  | brief-required: `known=batch_names \| taken` → `known=batch_names` | `test_two_parents_splitting_in_one_wave_adopt_a_shared_child_once` (+ the new shared-child test) |

  The symlink mutation's failure output is the reviewer's probe reproduced verbatim:
  with the lexical guard the run prints `flow: issue_500 split → adopted children
  issue_601, issue_602 into wave 1` and drives the bundle that lives outside the instance.

**(b) Production path?** Yes. Every test calls `cli._flow(self.cfg, args)` — the CLI
function `pdca flow` dispatches to (`test_flow_adopt_split.py:158`) — and the fixtures are
built by the production `split.accept` (`split.py:525`; `_split_now`,
`test_flow_adopt_split.py:178`), so the close marker, `split-lineage.json` and the child
bundles are byte-for-byte what `pdca split --accept` leaves. Nothing under test is
re-implemented: the leaves run in the shipped `mode="stub"` configuration, and the three
spies (`_drive_wave`, `_build_all`, `_point_at_integration`) call the real function and
hand its exact return value back (`test_flow_adopt_split.py:258-273`). `_capture_results`
wraps the production `flow.flow_ids` the same way (`:284`).

**(c) Fixture includes the fault?** Yes, in each new test the failing element is present,
not curated out:

- symlink test — `results/issue_601` really is removed and replaced with a symlink to a
  bundle in a second tmp root, and the assertions include the *outside* bundle being
  untouched (`state.state(elsewhere) == PLANNED`, no `patch.diff`), so a guard that
  announced a skip and drove it anyway would fail;
- newline test — the record really carries `"6\n01"` (hand-edited through the same
  `_record` helper the other guard tests use), and the assertion is on the absence of the
  broken second line, not merely on the presence of a report;
- shared-child test — both parents really split in one wave, 700's record really names
  500's child, and 602 really carries the unresolvable `Depends on: GHOST`; the control is
  that 601 and 801 still complete and appear in the results map.

Each new test also carries a **positive control** that fails on the base (an adopted
sibling reaching COMPLETE / a real adoption announcement), so none of them can pass
vacuously on the red leg by asserting only "nothing was adopted".

## 5. Everything else I ran (all through the project's runners, from the instance root)

- `./engine/scripts/run-verify.sh` → `C4 PASS` (above).
- `./engine/scripts/run-suite.sh` → template-repo suite **7 tests OK** (copier render +
  update-compat), offline driver suite **1658 tests OK** (skipped 2, pre-existing).
- `./engine/scripts/run-docs-check.sh` → `lint_docs: OK`, `render_site: link audit OK`.
- `./scripts/pdca contribcheck 472` → rc 0.
- `git diff --check` clean; `python3 -m compileall` clean; no line I added exceeds 97
  chars (the file's existing maximum is 106). The target ships **no** formatter/linter
  config and no git hooks beyond samples (`.git/hooks` has only `*.sample`;
  `CONTRIBUTING.md:22-27` states the discipline as "keep the offline suite green"), so
  "commit-ready" here means exactly those checks.

## 5b. The size backstop, for the human's eyes at sign-off

`[driver.size_signal]` (`pdca.toml:200-203`): `patch_kb = 125`, `patch_files = 25`,
`rounds = 3`. This patch is **114.7 KB / 8 files** — both under. The **rounds** rule will
fire (this is round 4). Worth weighing before it is read as "this slice is too big": the
rounds were not spent on the implementation. Round 1→2 and 2→3 were auto-iterates whose
carry-forward reason was, in both cases, the T4 contribution row having no artifacts to
lint (`brief.md:112`, `:117`) — the exact gap §2(d) closes — and round 3→4 is one real
implementation finding (the symlink guard) plus that same T4 row a third time. The
2026-08-09 Act review already recorded this pattern as noise for this instance
(`pdca.toml:187-191`).

## 6. Considered and deliberately NOT done

- **A symlink alias INSIDE the bundle root** (`issue_601` → `issue_700`). Still adoptable
  by design, stated at `flow.py:841-846`. Refusing it means re-keying the run's drive set
  by resolved path instead of name — `batch_names`, `published`, the results map and
  `_runnable`'s in-batch prereq test all key on `d.name` (7 sites), so it is a
  ~30-line change to shared state, outside this brief, for a hazard that needs a
  hand-made symlink between two bundles and is already caught by the terminal filter in
  the common case (`state.state` reads through the link).
- **Terminal-parent recovery**, budget re-sizing on adoption, single-id stdout reporting
  of adopted dispositions — the sibling child's, per `brief.md:72-76`.
- **`_terminal_hint`'s raw-id breadcrumb** (`flow.py:718`) — pre-existing base behaviour,
  see §2(b).
- No external dependency was missing: python3 3.11+ stdlib and git only, exactly as
  `brief.md:82` declares. Nothing to declare as NEEDS-HUMAN on that axis.

## 7. Files delivered

- `patch.diff` — 8 files, +1695 / −41 (`flow.py` +491 net, the new 1104-line test module,
  the ancillary `test_verify_base.py` env cleanup v3's review accepted).
- `test_flow_adopt_split.py` — bundle copy of `template/tests/test_flow_adopt_split.py`
  (25 tests).
- `commit-msg.txt`, `pr-description.md` — see §2(d).
