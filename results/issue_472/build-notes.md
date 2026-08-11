# Build notes — #472 (flow-adopt-core), iteration v5

Withheld from the reviewer; written for the human at sign-off.

All `path:line` are on the target worktree `/home/eddie/pdca/pdca-harness.pdca-wt`
(target branch `main` @ `3e3b829`, the merge of PR #470) **with `patch.diff` applied**,
unless the line says "on the base".

## 1. What this iteration is

The round-4 carry-forward (`brief.md:127`) says the core mechanism is converged and must
not be re-derived, and names three narrow implementation fixes. So this is v4's patch
(`iteration-v4/patch.diff`, reconstructed and diffed) **plus exactly those three**:

| carry-forward item | change | delta vs v4 |
|---|---|---|
| 1. `flow.py:914`/`:696` — a non-string `children` entry dropped SILENTLY | `_adoptable` counts and echoes what `_lineage_children` refused (`flow.py:946-954`) | +14 lines |
| 2. `flow.py:775` — `_report_held`'s universal "never counted as work" claim | scoped to the child case, with the named-id exception stated (`flow.py:777-782`) | +6 lines |
| 3. `flow.py:849` — an in-root `issue_<id>` symlink drives one directory as two bundles | resolved-path dedup in `_adoptable` (`flow.py:960-970`, `:993-1009`, `_real` at `:831`), reported through `_report_refused` (`flow.py:1071-1078`) | +47 lines |

Measured delta vs the v4 reference: `flow.py` **+95 / −31**, the test module **+80 / −1**
(2 new tests, 25 → 27), `config.py` and `cli.py` **+2 / −2** each (citation re-resolution
only, §4). Nothing else in the patch moved.

## 2. The three changes, and why each is the shape it is

### (a) Every refused entry is named — `flow.py:946-954`

`_lineage_children` (`flow.py:679`, **base** behaviour from #456/#468) filters
`isinstance(c, str) and c.strip()` *before* `_adoptable`'s loop, so `"children": [601,
"602", "603"]` lost 601 in the one branch that printed nothing — and `ids` was non-empty,
so the "no readable children record" line at `flow.py:957` didn't fire either. Reproduced
at the target before the fix: 601 never adopted, never named, left PLANNED; the operator's
only line was `issue_602 held this run — unresolved dependency (601)`.

The report is derived from `_lineage_children`'s **own answer** — it returns one id per
usable entry, so `len(entries) - len(ids)` *is* what it refused. That was the design
constraint: I did not want a second copy of its predicate in this module.

- **Rejected — change `_lineage_children` to return `(ids, refused)`.** It is shipped base
  behaviour with a second caller (`_terminal_hint`, `flow.py:716`) and an existing pin
  (`test_flow_entrypoint_parity.py:357`, four sub-cases). Cost: 1 signature + 2 call sites
  + its docstring + that test's expectations — ~12 lines, and it makes a shipped helper's
  contract serve one reader. The derived count costs 0 extra coupling.
- **Rejected — restate the predicate in a sibling `_unusable_children()`.** Identical line
  count (~6), but the predicate would then live in two places and drift silently; the
  report would go wrong exactly when the filter changed.
- **Truncation** (`flow.py:949`, `entries[:8]` + "first 8 of N") is 1 line and keeps a
  pathological hand-edited record from printing a 10k-element list into the operator's log;
  `repr` also escapes a newline inside an entry, which is the hazard `_PLAIN_ID` exists for
  one step further down.

### (b) `_report_held`'s docstring — `flow.py:769-782`

Documentation only, and deliberately so: the claim was wrong, not the code. The helper has
three callers with two different consequences — a held ADOPTED child leaves the results map
(`flow.py:1148-1154`), a held id the operator NAMED stays in it and the run fails
(`flow.py:1370-1379`, pinned by `test_a_named_id_in_the_re_scheduled_tail_is_held_not_lost`).
Both are now stated where a reader goes to learn what "held" costs. I made the same one-clause
scoping at the second site that repeated the universal claim (`flow.py:1151-1152`), because
leaving it would re-raise the identical finding next round.

**Not done: making the behaviour uniform.** Excluding a held *named* id from the map would
delete the run's answer for an id it was given, and contradicts `flow.py:1370-1379` plus the
test above (`:595-596` asserts `results["811"] == PLANNED`, `rc == 1`). That is a behaviour
change nobody asked for; the carry-forward asked for the docstring.

### (c) One directory, one adoption — `flow.py:960-970`, `:993-1009`

`_inside_bundle_root` deliberately admits an `issue_<id>` that links to another bundle
**inside** the root (it names a bundle this instance owns). v4's docstring then declined the
in-flight case; the reviewer showed the consequence: with `results/issue_601 →
results/issue_910` and `910` also named and un-driven, wave 1 held **both** names for one
directory — under `lanes > 1`, two lanes building, signing off and publishing one bundle.

The fix is the cheap dedup the carry-forward asks for, in `_adoptable`, where the run's own
drive set is in hand:

- `driven` maps the RESOLVED path of every name in `known` → that name (`flow.py:960-967`, 5 code lines);
- `seen_real` dedupes within one record (`flow.py:970`, `:993-999`) — needed on its own: a record naming both
  `601` and a `610` that links to it puts one directory in a wave twice with no help from
  the drive set;
- `owner` is the name the run holds that directory under, carried in the `refused` tuple so
  `_report_refused` looks up the disposition that exists (`flow.py:1071-1078`). Looking up
  the alias instead prints "…is NOT in this run's drive set or its results" about a bundle
  the run is driving — mutation M4 below reproduces exactly that.

- **Rejected — re-key the run's state by resolved path** (the wider change v4 declined).
  Concretely checkable: run-scoped state is keyed by bundle NAME at **17 code sites** —
  `batch_names` at `flow.py:604, 624, 1047, 1072, 1084, 1163, 1188, 1201, 1206, 1355, 1360,
  1392, 1435`, `published` at `:1361, 1440, 1474`, and the results map itself at `:1522`
  (`{d.name.replace("issue_", ""): state.state(d) …}`) — and that last one is the CLI's
  published contract (`cli.py:609`, `{issue_id: state}`), so re-keying changes what
  `pdca flow` prints and what its exit code is computed over. The dedup is ~30 lines
  (including comments) inside one function and changes no shared key.
- **Rejected — refuse the in-root alias in `_inside_bundle_root`.** 1 line, but wrong:
  containment cannot see the drive set, so it would also refuse a legitimate alias of a
  bundle nobody is driving, and the terminal-alias case that already works correctly
  (`state.state` reads through the link) would start failing loudly for no reason.
- **Rejected — skip the alias silently** (~20 lines cheaper: no `driven` map, no third tuple
  element, no `_report_refused` clause). Same class of defect as (a): the record named a
  child, the run did not adopt it, and the log said nothing. The in-record duplicate stays
  silent because that directory *is* adopted under the first name — nothing to resume; the
  drive-set case is reported because the operator's record and the run's set disagree.

## 3. Forced refutation of my own test (the three questions)

**(a) Genuine red?** Yes, three ways.

1. **Through the project's runner**, on the final patch: `PDCA_BUNDLE=… PDCA_WORKTREE=…
   ./engine/scripts/run-verify.sh` → `C4 PASS: red without the fix, green with it`. Green leg
   **27/27 OK**; red leg (production hunks reverted, tests kept) **26 of 27 FAIL**. The single
   pre-fix pass is `test_a_run_that_adopts_nothing_keeps_a_full_budget_per_wave`, a
   no-regression guard that is *supposed* to be green on both legs. Both new tests are in the
   red-leg failure list by name.
2. **Per-hunk mutation of the shipped code** (whole module re-run per mutant, `python3 -B` so
   no stale bytecode can fake a result):

   | mutation | killed by |
   |---|---|
   | M1 drop the unusable-entries report (`if len(entries) > len(ids)` → `if False`) | `…entry_that_is_not_an_id_is_reported_not_dropped_silently` |
   | M2 drop the drive-set alias lookup (`driven.get(real, "")` → `""`) | `…symlinked_alias_of_a_bundle_this_run_drives_is_driven_once` |
   | M3 drop the in-record alias dedup (`if real in seen_real` → `if False`) | same test (leg 2) |
   | M4 report against the alias, not the owner (`if owner in batch_names` → `child`) | same test (leg 1) |
   | M5 the brief's required mutation, `known=batch_names \| taken` → `batch_names` | `…two_parents_splitting_in_one_wave_adopt_a_shared_child_once` + `…shared_child_the_reschedule_holds…` |
   | M6 v3's lexical containment (`d.parent == cfg.bundle_root`) | `…child_bundle_symlinked_out_of_the_instance_is_skipped` |

   M5/M6 are re-run regressions, not new work: they prove the trimming in §5 did not loosen
   anything the earlier rounds pinned.
3. A no-op control mutant (`def _adoptable(` → itself) leaves all 27 green, so the harness is
   not failing for its own reasons.

**(b) Production path?** Yes. Every test calls `cli._flow(self.cfg, args)` — the function
`pdca flow` dispatches to — which reaches the production `flow.flow_ids` → `_drive_and_act`
→ `_adopt_split_children`. Fixtures are built by the production `split.accept`
(`split.py:525`) via `_split_now` (`test_flow_adopt_split.py:178`), so the close marker,
`split-lineage.json` and the child bundles are byte-for-byte what `pdca split --accept`
leaves. The three spies (`_drive_wave`, `_build_all`, `_point_at_integration`) call the real
function and return its exact value (`:258-273`); `_capture_results` wraps the production
`flow.flow_ids` the same way (`:284`). Nothing under test is a copy.

**(c) Fixture includes the fault?** Yes — in each new test the failing element is present,
not curated out:

- **Non-string entry** (`test_flow_adopt_split.py:785-816`): the record on disk really is `[601,
  "602", "603"]` (an int, written through the same `_record` helper the other guard tests
  use), and 601's bundle really exists, briefed and PLANNED — which is precisely what made
  the silent drop harmful. The assertions include `_state("601") == PLANNED` and the
  misleading `issue_602 held this run — unresolved dependency (601)` line, so a build that
  "fixed" it by hiding the hold would fail. 603 is a live control that must reach COMPLETE.
- **Alias, leg 1** (`:935-973`): `results/issue_601` is really `shutil.rmtree`d and replaced by a
  symlink to `results/issue_910`; 910 is really on the command line and really un-driven when
  500 splits (it declares `Depends on: 500`, so it sits in the un-driven tail). The binding
  assertion is on the WAVE CONTENTS — `[["issue_500"], ["issue_602", "issue_910"]]` — not on
  a log line, so a guard that printed a refusal and drove it anyway fails.
- **Alias, leg 2** (`:975-995`): `issue_610` is a real symlink to `issue_601` and the record
  really names `["601", "610", "602"]`; the control is that 601 and 602 both reach COMPLETE
  and the announcement names exactly those two.

## 4. Citations re-resolved (this is where v1–v4 kept bleeding)

My +95 lines in `flow.py` shifted every `flow.py:NNN` citation below line 776 — including
ones **v4's reviewer had already verified**. I re-extracted every `*.py:NNN` reference in the
touched files by script and re-resolved each against the final tree; seven were stale and are
fixed (old → new, verified by content, not by arithmetic):

`flow.py:1094` `1354→1424` (`_point_at_integration` call) · `flow.py:1115` `1300-1309→1370-1379`
(the named-id re-levelling comment) · `config.py:319` `1359→1429` (`min(allowance, budget -
spent)`) · `config.py:326` `1240→1310` (`_warn_abandoned` on an exhausted allowance) ·
`cli.py:609` `1549-1563→1619-1633` · `cli.py:610` `1584-1590→1654-1660` ·
`test_flow_adopt_split.py:349` `1354→1424`. All 48 citations in the touched files now resolve
to the line they name; every one of the 12 cited test names exists.

The bundle's `commit-msg.txt` / `pr-description.md` were re-audited the same way: 13 stale
`flow.py:NNN` pointers refreshed, test counts corrected (25→27 tests, "24 of 25"→"26 of 27",
suite 1658→1660), and the two new guards described. `./scripts/pdca contribcheck 472` → **rc 0**
against the real files. As in v4: publish only drafts these when they are MISSING
(`publish.py:51-54`, "only-if-missing, so re-runs never clobber an edited text"), so it will keep them — the human should read them as drafts and edit
freely, or delete both to restore drafting from scratch.

## 5. The size backstop, and what I trimmed to stay under it

`[driver.size_signal]` (`pdca.toml:200-203`): `patch_kb = 125`, `patch_files = 25`,
`rounds = 3`; the rule fires at `patch_bytes/1024 >= 125` (`size_signal.py:252`). My first
complete draft measured **129,429 B = 126.4 KiB — over**. The final patch is **127,787 B =
124.79 KiB / 8 files**, under it.

What I cut to get there was **only my own new prose** — ~30 lines of docstring/comment I had
written this round, re-densified. No claim was dropped: the ones that overlapped between
`_inside_bundle_root` and `_adoptable` are now stated once, in `_adoptable`, where the code
lives. No v1–v4 content and no test assertion was removed to make room (the test module gained
80 lines and lost 1 — a docstring rewrap). The **rounds** rule will still fire (this is round
5): worth weighing that rounds 1→2 and 2→3 were spent on the T4 row having no artifacts to lint
(`brief.md:112`, `:117`), which §4 closes, and 3→4 and 4→5 on one implementation finding each.

## 6. Everything else I ran (all through the project's runners, from the instance root)

- `./engine/scripts/run-verify.sh` → `C4 PASS` (§3).
- `./engine/scripts/run-suite.sh` → template-repo suite **7 OK**, offline driver suite
  **1660 OK** (skipped 2, pre-existing).
- `./engine/scripts/run-docs-check.sh` → `lint_docs: OK`, `render_site: link audit OK`.
- `./scripts/pdca contribcheck 472` → rc 0.
- Commit-readiness: `git diff --check` clean; `python3 -m compileall` clean; longest line I
  add is **95** chars (file max 106, all pre-existing in `cli.py`'s help text); the target
  ships no formatter/linter config and `$(git rev-parse --git-common-dir)/hooks` holds only
  `*.sample`, so "commit-ready" here is exactly these checks.
- No external dependency was missing: python3 ≥ 3.11 stdlib + git only, as `brief.md:82`
  declares. Nothing to declare on that axis.

## 7. Considered and deliberately NOT done

- **Terminal-parent recovery**, budget re-sizing on adoption, single-id stdout reporting of
  adopted dispositions — the sibling child's, per `brief.md:72-76`.
- **Re-keying the run's drive set by resolved path** — §2(c), 17 name-keyed sites and the
  CLI's results-map contract.
- **`_terminal_hint`'s raw-id breadcrumb** (`flow.py:718`) — pre-existing base behaviour,
  unchanged by this patch; whoever owns that helper owns the quoting there.
- **Uniform "held" semantics** for named ids vs adopted children — §2(b).

## 8. Files delivered

- `patch.diff` — 8 files, +1860 / −41 (against the merged base).
- `test_flow_adopt_split.py` — bundle copy of `template/tests/test_flow_adopt_split.py`
  (27 tests).
- `commit-msg.txt`, `pr-description.md` — refreshed, §4.
