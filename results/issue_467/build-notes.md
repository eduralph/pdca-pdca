# Build notes — issue 467 / split-children-inherit-release-metadata (iteration 2)

Target: `eduralph/pdca-harness @ main`, base `6ba00ba` (2026-09-14, contains #466's
`9a19cb5`). Line numbers marked *base* are on that commit; *patched* ones are in the
worktree after `patch.diff` is applied.

## What sign-off rejected, and what changed

Iteration 1 passed each parent label to gh as a raw `--label <name>`. gh registers
`--label` as a pflag string slice, and pflag reads **every** occurrence as one CSV record
(Go `encoding/csv`). So repeating the flag does not protect a name: `area,backend` became
two labels, and a name containing `"` was a parse error that failed child 1 and with it
the whole split, where `main` files it fine without labels.

This iteration:

1. **New `_gh_label_value(name)`** (`split.py:986-998` patched). It quotes a name that
   contains a comma, a double quote, `\r` or `\n`, and doubles any quotes inside it.
   Every other name is returned unchanged, so `bug` and `help wanted` go out byte-for-byte
   as the carry-forward asked. It is 3 lines of logic (`:996-998`).
2. **`_create_issue` uses it** for every label: `cmd += ["--label", _gh_label_value(name)]`
   (`split.py:1021-1022` patched). It is still one `--label` per name. `--milestone` is
   left verbatim (`:1019-1020`): it is a plain string flag in gh, and quoting it would put
   the quotes into the milestone name gh looks up. The docstring says so (`:1012-1014`),
   so nobody later "fixes" the milestone the same way.
3. **Kept from iteration 1, unchanged in behaviour** (sign-off: "fine and should be kept"):
   the single best-effort lookup `_parent_metadata` (`split.py:1042-1083` patched),
   called once before the filing loop in `file_children` (`:1113-1124`), the
   keyword-only defaults that keep `triage.py:530-535` working, and the fake updates in
   `test_split.py`. Small edits there, all behaviour-neutral:
   - The label list comprehension was reflowed (`:1079-1082`). Same filter, same result.
   - `# noqa: BLE001` plus a reason on the broad `except Exception` (`:1067`), matching
     `leaves.py:789` / `sources.py:79`. The docstring now says why it is `Exception` and
     not `BaseException` (`:1057-1060`): Ctrl-C during the lookup stops the split before
     anything irreversible is filed.
   - The comment above the lookup no longer says it tolerates a failure "in any way"; it
     names the three failure kinds (`:1113-1118`). Ctrl-C is not one of them.
   - The warning now ends "…filing the children WITHOUT them; set them on the tracker by
     hand" (`:1123-1124`), so the operator knows what to do. It is still one line on
     stderr.
4. **One more fake adapted: `test_ctrl_c_stays_an_interrupt`** (`test_split.py:1763-1777`
   patched; `:1731-1739` base). The brief listed it (`:1734`); iteration 1 left it alone.
   With the lookup in place, its fake raised `KeyboardInterrupt` on the *lookup*. That
   escapes before the filing loop's `except BaseException` handler (`split.py:1053-1092`
   base) ever runs. The test stayed green but stopped testing what its docstring says
   ("Reported, then re-raised unchanged"): the handler could then turn Ctrl-C into a
   `SplitError` and this test would not notice. It now answers the lookup, so the
   interrupt lands on the first `gh issue create` again. No assertion was changed.

`test_split_stub_guard.py`'s `_gh` (`:69-77`) is still untouched, for iteration 1's
reason, which the code-review advisory confirmed. Every test using it either stops at the
stub guard before `can_file` runs (and asserts `self.calls == []`), or takes the `--ids`
path, which never calls `file_children`. If the #466 guard ever regressed, the lookup
call would be recorded too and `self.calls == []` would still fail, as it should.

## Evidence that this is gh's real behaviour (gh 2.100.0, offline, nothing created)

- `gh issue create --label <v> --help` exits 1 on `say "hi"` and `area, "quoted"` with
  `parse error on line 1, column 5: bare " in non-quoted-field`, and on `"a` and `"a"b`
  with `extraneous or missing " in quoted-field`. It exits 0 on the CSV-quoted forms.
- `GH_BROWSER=echo gh issue list -R acme/widgets --label <v> --web` prints the search URL
  with one `label:` term per name gh parsed: raw `area,backend` gives `label:area
  label:backend`; `"area,backend"` gives `label:area,backend`; `"say ""hi"""` gives
  `label:"say \"hi\""`; `""""` gives a single label `"`.
- gh's own help text lists `gh issue create --label "bug,help wanted"` as the way to pass
  two labels, so the CSV splitting is documented behaviour, not an accident.
- **Production argv fed to real gh.** I captured the argv that patched `_create_issue`
  builds for labels `bug`, `help wanted`, `area,backend`, `say "hi"`, `area, "quoted"`,
  `"` and milestone `Milestone 0.60.0, "beta"`, using a recording stub for
  `split.subprocess` (not a real create). Then I passed its `--label` values to
  `gh issue list --web` and read back
  `['"', 'area, "quoted"', 'help wanted', 'say "hi"', 'area,backend', 'bug']`, the same
  six names (gh sorts the terms). `gh issue create <same flags minus --parent> --web`
  exited 0 and its URL carried `milestone=Milestone 0.60.0, "beta"` unchanged.

## The test — `template/tests/test_split_child_metadata.py` (new, 18 tests)

The fake `gh` there does what real gh does with `--label`. `_gh_label_field` (`:53-97`)
is a small port of Go `encoding/csv` with default options, reading one record, which is
what pflag's `readAsCSV` uses. `_gh_reads_labels` (`:100-113`) walks the argv as
flag/value pairs, so a title or body that happens to say `--label` is never mistaken for
the flag. A create whose labels gh could not parse gets exit 1 and files nothing
(`:205-210`), as with gh.

Why not Python's `csv.reader` as the model: it is too lenient. With `strict=True` it
still reads `say "hi"` as `['say "hi"']` (checked on Python 3.14.4), where gh refuses it.
With that model the quote test would have **passed against iteration 1's raw names**,
which is exactly the defect sign-off rejected.

`TheFakeGhReadsLabelsLikeGh` (`:121-151`) pins the model to the gh outputs listed above
(8 reads, 4 refusals), so a reviewer can check the model against gh with two commands.
The class docstring gives them.

Coverage against the criterion:
- (a)+(b) `test_milestone_and_labels_reach_every_child` (`:234`): the brief's repro
  payload. Milestone title passed; gh reads back exactly `["bug", "help wanted"]`.
- (b), comma and quote, as gh reads them: `test_a_comma_in_a_label_name_stays_one_label`
  (`:267`), `test_a_double_quote_in_a_label_name_stays_one_label` (`:278`; `say "hi"`,
  `area, "quoted"`, `"`), plus `test_a_plain_label_name_goes_out_byte_for_byte` (`:289`).
  Each also asserts the returned ids `["601", "602"]`.
- The milestone title stays verbatim: `test_the_milestone_title_goes_out_verbatim` (`:252`).
- (c) `test_no_milestone_no_labels_matches_todays_argv` (`:301`) and
  `test_a_null_milestone_and_no_labels_invent_no_flag` (`:317`). The second was renamed:
  iteration 1 called it "missing milestone key" but its input had the key set to `null`.
- (d) one lookup, before the loop, repo explicit: `:330`. Non-zero exit, raised error,
  `null` and `[]`, and non-JSON output each still file both children and print exactly
  one warning line: `:344`, `:357`, `:368`, `:386`. Ctrl-C during the lookup stays an
  interrupt and files nothing: `:397`.
- (e) `--ids` path and a non-GitHub tracker call no `gh` at all (the fake raises): `:410`,
  `:417`.
- (f) ids and argv asserted together: `:428`, and in every filing test above.

A note on the Ctrl-C test: criterion (d) says a lookup that "raises" still files every
child. I read that as errors. A Ctrl-C is the operator asking to stop, and this file's
rule is that an interrupt stays an interrupt (the handler at `split.py:1053-1092` base
re-raises non-`Exception`s). Nothing has been filed at that point, so letting it through
loses nothing, while swallowing it would go on to file issues the tracker cannot take
back. If sign-off reads (d) literally, the only change is to catch `BaseException` at
`split.py:1067` and invert that one test. I recommend against it.

## Refutation — the three forced questions

**(a) Genuine red? Yes.** From the instance root, run the project runner
`PDCA_BUNDLE=… PDCA_WORKTREE=… ./engine/scripts/run-verify.sh`. Green leg: `test_split.py`
96 OK, `test_split_child_metadata.py` 18 OK. Red leg (production hunks reverted to
`main`): `Ran 18 tests … FAILED (failures=13)`, with no errors and no import failure. The
13 failures are 12 tests (one has two failing subtests). The 6 that pass on `main` are
the 2 model-calibration tests and the 4 that assert something `main` also never did (no
invented flags, no lookup on `--ids` or a non-GitHub tracker). Verdict line:
`PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`.

**Also red against the rejected iteration 1.** I put iteration 1's `split.py` in the
worktree (base + the `split.py` hunks of `iteration-v1/patch.diff`) and ran the same
runner. Its green leg failed on exactly the two new tests:
`Lists differ: ['bug', 'area', 'backend'] != ['bug', 'area,backend']`, and
`gh refused a child it should have filed: … parse error: bare " in non-quoted-field`.
Result: `FAILED (failures=2)`, `C4 FAIL`. The tests catch the carry-forward's defect, not
only "no metadata at all". Afterwards I restored this iteration's `split.py`; the `git
diff` of the worktree is byte-identical to `patch.diff` (checked with `cmp`).

**(b) Production path? Yes.** Every filing test calls the real `split.file_children`
(and `split.accept` for `--ids`). The only things replaced are
`pdca_harness.split.subprocess` and `.shutil`, the same seam as
`test_split.py:689-694` (base). The encoding under test is production
`_gh_label_value`, reached through `file_children` → `_create_issue`. The test never
calls the encoder directly; it decodes the argv with an independent model of gh's parser,
so the check is not circular. C5 runner: `1 added driver-suite test(s) import the
production package 'pdca_harness'`.

**(c) Fixture includes the fault? Yes.** The parent's lookup answer carries the exact
names that break gh (`area,backend`, `say "hi"`, `area, "quoted"`, `"`). The fake gh
refuses what real gh refuses and splits what real gh splits; that behaviour is pinned by
`TheFakeGhReadsLabelsLikeGh` to observed gh 2.100.0 output. It does not accept
everything. The lookup-failure tests inject each failure kind named in (d), through the
same fake the create calls go through.

## Suites

`./engine/scripts/run-suite.sh` (T3 runner): root suite `Ran 24 tests … OK`, driver
suite `Ran 1806 tests … OK (skipped=2)`, `PDCA-EVIDENCE: root suite OK, driver suite OK`.
The two skips are the same as before this change. The full log is in this bundle at
`.t3-suite-builder.log`; I wrote it there by mistake, and it is not one of the three
artifacts.

## Formatter / commit hooks

The target has no formatter or linter config (no `pyproject.toml`/`ruff.toml`/
`.pre-commit-config.yaml` at the root) and no installed git hooks (only `*.sample`).
`CONTRIBUTING.md:9-19` requires only a DCO `Signed-off-by:` (`git commit -s`), which is
added at publish. `git diff --check` is clean. Every added line is ≤ 92 characters; the
existing files already run to 96 (`split.py`) and 94 (`test_split.py`).

## Alternatives ruled out

- **Always quote every label** (`'"' + name.replace('"', '""') + '"'`, 1 line instead of
  3). Valid for gh, but plain names would change on the wire (`"bug"`), which the
  carry-forward rules out ("plain names … stay byte-identical").
- **Python's `csv.writer` as the encoder**
  (`buf = io.StringIO(); csv.writer(buf, lineterminator="").writerow([name]); return
  buf.getvalue()`). Same 3 lines plus 2 imports, and on Python 3.14.4 it gives the same
  output for every name here. I rejected it because its quoting rules come from the
  dialect and the Python version, not from the reader that matters (gh's Go reader), and
  it writes an empty name as `""`. The hand-written rule says exactly what gh needs.
- **Bypass the CSV flag: create via `gh api` with a JSON label array.** This removes the
  cause entirely, but it replaces `_create_issue` (about 30 lines), needs a second API
  call to link the sub-issue that `--parent` does today, and adds a failure mode between
  the two calls (issue created but not linked). Far outside "one logical change", for no
  gain over an encoding that real gh reads back exactly.
- **Drop labels gh would misread, with a warning.** Loses the metadata this issue exists
  to keep, when encoding keeps it.

## Scope notes

- **Closed milestone (brief: optional).** Not done: not cheap and not safe. To my
  knowledge gh's `milestone` export carries number/title/description/dueOn and no state,
  so detecting "closed" needs a second API call. Retrying a failed create without
  `--milestone` risks a duplicate issue, because a failed `gh issue create` may still
  have created it (`split.py:1073-1080` base says exactly this). Today such a split fails
  at child 1 with "Filed 0 of N" (nothing filed); the operator can clear the parent's
  milestone and re-run.
- Assignees are not inherited (out of scope by design). No docs change: the three places
  describing `split --accept` (`template/agents/splitter.md.jinja:15-16`,
  `template/agents/planner.md.jinja:153-155`, `docs/07-crosscutting.md:213`) never listed
  which fields a child gets, so none is now wrong.
- Line breaks in a label are quoted, but Go's reader turns `\r\n` inside a quoted field
  into `\n`. GitHub label names are single-line, so this cannot matter in practice.
- One of my shell checks wrote a stray scratch file, `/tmp/gh_err_680419` (gh's stderr
  from the `--help` probe). It is outside the worktree and bundle, and I have no
  permission to remove it.

## For the human at sign-off (fitness-to-purpose)

The offline tests prove the argv and how gh parses it; they cannot prove GitHub's stored
result. To validate end to end, use a **disposable** repository and an instance whose
splitter is in `command` mode (a stub proposal is refused by #466):

1. Create labels `bug`, `help wanted`, `area,backend` and `say "hi"`, and an open
   milestone `Milestone 0.60.0`. Open a parent issue carrying all four labels and the
   milestone.
2. Draft a two-child proposal for it and run `pdca split <parent> --accept`.
3. For each child id it prints, run
   `gh issue view <id> --repo <owner/repo> --json milestone,labels`. Both children should
   show milestone title `Milestone 0.60.0` and exactly those four label names, with
   `area,backend` as one label.
