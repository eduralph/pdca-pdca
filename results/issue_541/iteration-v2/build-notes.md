# Build notes — #541 v2 (no dead attempt's artifact harvested as a live one's)

Target: `eduralph/pdca-harness` @ `main`, built in `$PDCA_WORKTREE`
(`/home/eddie/pdca/pdca-harness.pdca-wt`) on the wave-folded base
`480fa6b pdca-integrate: issue_540` (`pdca-integration/main`, child-1's accepted result —
`stack-base` confirms it). All `path:line` citations are **post-patch** line numbers in that
worktree unless marked "base" or "v1".

## What this iteration changed relative to iteration-v1

The sign-off said: the slice and the structure are right, keep them, fix the three findings.
That is exactly what this is — the shared owner, the three converted sites, the withdrawal,
the preservation and the un-owned carry-forward are unchanged from v1. Three deltas:

**1 — the un-owned refusal no longer destroys a LIVE verdict** (was v1 `leaves.py:836-841`).
`unlink()` needs write permission on the *directory*; `open(path, "w")` needs it only on the
*file* — so in the very scenario the test builds (the dying attempt does `chmod(".", 0o500)`)
the next attempt can still overwrite the residue with its own complete review, and v1 refused
it. Ownership is now **settled by content**, exactly as the sign-off directed: `withdraw`
already reads the residue, so it now also digests it (`_read_residue`, `leaves.py:951`) and
`_disown` keeps that digest (`leaves.py:934-945`). At the harvest,
`_live_attempt_overwrote_it` (`leaves.py:888-907`) re-digests what is at the path: a file
matching **none** of the residues we failed to remove cannot be any dead attempt's work, so
it is the live attempt's and is filed (`leaves.py:851-856`).

Why a *content* digest and not an inode: `open(path, "w")` truncates **in place**, so the
inode is unchanged in precisely the case that must be detected — an inode test would answer
"still the dead attempt's file" for a full live verdict. Streamed in 64 KiB chunks, so the
comparison costs no memory, and only on the un-owned path (a successful harvest still does
zero extra reads).

Criterion 5 is untouched by this: the refusal still fires whenever what is at the path *is*
a residue we could not withdraw (`test_a_residue_that_cannot_be_withdrawn_is_refused_at_every_site`,
red on base), and no attempt is ever spent on it (`_runs() == 3`, the
`test_leaf_resilience.py:62` analogue). The two criteria stop colliding because the refusal
is now aimed at the file it was always about.

**2 — the withdrawn residue is bounded where it lands in a tracked bundle file** (was v1
`leaves.py:852` + `:905-907`). `_read_residue` (`leaves.py:951-983`) keeps
`_RESIDUE_LINES = 100` reads from each end, each read bounded to `_RESIDUE_READ = 1000`
bytes, with an elision line between them that *declares* what was dropped
(`leaves.py:788-791`). Bounded like the channel it rides beside — `progress.py:176`'s
`err_tail = deque(maxlen=200)`, the same attempt's stderr tail. Measured through the
production function on the adversary's own shape:

| | residue at the path | quoted into `check-review.error.log` |
|---|---|---|
| v1 | 1,160,069 B | **1,160,401 B** (measured by the new test against v1's hunks) |
| this patch | 1,160,043 B | **11,645 B** — head line, `… 19802 line(s) elided …`, tail line |
| this patch, pathological 3 MB artifact with **no newline at all** | 3,000,000 B | **200,317 B** (the hard ceiling: 200 reads × 1000 B) |

The read is bounded too, not just the line count (`fh.readline(_RESIDUE_READ)`), because an
artifact need not contain a newline and plain line iteration would hold one 3 MB "line" in
memory — the other half of the finding ("held in memory first"). The digest still covers
every byte, since consecutive bounded reads cover the whole file.

**3 — the unknown-status fallback no longer demotes real findings** (was v1
`assemble.py:190-191`). The sign-off offered two ways; this takes the first — "require the
marker in the placeholder's own header region" — and tightens it with the doctrine already
written in this repo for the *settlement* marker (`state.py:200-211`: read as a **whole
line**, "deliberately not a substring, because these records embed the leaf's own text").
So `_written_as_a_placeholder` (`assemble.py:122-131`) honours an unknown token only when
the marker **stands alone on its line** *and* sits in the artifact's first
`_LEAF_STATUS_HEADER_LINES = 8` lines — where every `leaves` placeholder writes it (line 3
for the two advisory placeholders, line 5 for the reviewer's). An artifact quoting a marker
inside a finding, or verbatim in a fenced block, is left exactly as base leaves it: no label,
`[impl]` routing intact. A **recognised** token is entirely unaffected — it still reads
wherever it sits (`assemble.py:209-212`), so nothing about #278's shipped behaviour moves.

Note the failure mode of the window is contained by construction: it gates only the fallback
for a status this harness does not know. A known status (including the new one) never
consults it, so an unusual placeholder header cannot cost a real placeholder its label.

Everything else is v1 as accepted-in-substance: `_LeafHarvest` (`leaves.py:794`), the three
sites (`leaves.py:2835`, `:3191`, `:3494`), the two call-outs in the retry loop
(`leaves.py:741` `leaf_succeeded`, `leaves.py:752` `withdraw`, the latter deliberately
**before** the stop rule at `:754-755` so the last attempt's residue is preserved like every
earlier one's), `_preserve` (`leaves.py:913`), `_WITHDRAWN_TRAILER` (`leaves.py:778`),
`_FAIL_UNOWNED` (`leaves.py:2861`) → `assemble.LEAF_STATUS_UNOWNED` (`assemble.py:88`) → its
§6 label (`assemble.py:95`) and its placeholder prose (`leaves.py:2941`, now also stating
that a live overwrite *would* have been filed, so the operator can trust the refusal).

## Why each criterion is met

1. **No dead attempt's artifact filed as a live one's, at all three sites.** The residue
   leaves the path as its author dies, so anything present at the harvest was written by the
   live attempt — or, when it could not be removed, is proven to be or not to be that
   residue. `test_no_site_files_a_dead_attempts_artifact_as_a_live_ones` (subTest per site,
   red at all three on base) and `…_refused_at_every_site`.
2. **The dead attempt's text preserved, not merely deleted.** `_preserve` writes the account
   back into the bundle's `*.error.log` on the degrade path — the exact condition the
   criterion states ("while the operator is told none was produced"). JUDGMENT CALL, carried
   over from v1 and unchanged: when the leaf *does* file its own artifact, #540's accepted
   rule wins (no error log beside a real verdict — `test_attempt_ownership.py:288` calls that
   "a lie"), so the account is dropped. In the new overwrite leg there is nothing left to
   preserve anyway: the *leaf* overwrote its own sandbox file, not the harness.
3. **The live attempt's own artifact is harvested exactly as today.**
   `test_the_live_attempts_own_artifact_is_harvested_at_every_site`,
   `test_a_leaf_that_exits_0_writing_nothing_still_degrades_as_today` (both green on base —
   regression guards for the unchanged path), plus the new
   `test_a_live_verdict_written_over_an_unwithdrawable_residue_is_still_filed`, which is the
   finding-1 leg: green on base, **red against v1**, green here.
4. **The leaf-status label tells the truth.** The refusal is a run whose last attempt exited
   0, so it gets its own status/label rather than "leaf did not run"
   (`test_the_label_never_says_a_run_that_exited_0_did_not_run`), and the label table is
   asserted complete (`test_every_leaf_status_the_harness_can_write_has_a_label`).
5. **The retry contract is NOT narrowed.** No `raise`, no early return anywhere in
   `withdraw` / `_disown`; the un-owned state is carried forward and paid at the harvest.
   `test_an_unwithdrawable_residue_does_not_narrow_the_retry_contract` asserts `_runs() == 3`
   through the real reviewer site.
6. **One implementation, three users.** `test_all_three_sites_go_through_the_one_owner`
   swaps the owner for a recording subclass and drives each site, so a site that re-grows its
   own copy fails mechanically. 25 hand-copied lines are gone from the three sites.

## Ruled out (with the cost, not an adjective)

* **Inode/mtime comparison instead of content** for finding 1. `open(path, "w")` truncates in
  place → same inode, so the test answers wrongly in the one case it exists for. Mtime is a
  heuristic (granularity, a leaf that rewrites within the same tick). Content is 3 lines
  (`_artifact_digest`, `leaves.py:985-998`) and is decidable.
* **Keeping the residue in memory to compare it later** instead of a digest: that is the
  9.6 MB-in-memory half of finding 2 re-introduced. The digest is 32 bytes per residue,
  ≤ 3 residues.
* **A stat-based fallback for a residue that could not be READ** (`_unreadable`,
  `leaves.py:906`). We refuse there, so an exotic write-only-unreadable residue can still cost
  a live verdict. It is unfixable by comparison (no bytes were ever read), the human's
  instruction scopes the settlement to "the bytes already read in `withdraw`", and the
  direction is the safe one: refusing costs a re-run, filing costs a false verdict.
* **Dropping the unknown-status fallback entirely** (−6 lines). It would also close finding 3,
  but the sign-off named two remedies and both KEEP the fallback; and the hole it plugs — a
  status added in `leaves` with no label in `assemble` — is the twin-blindness shape this
  child exists to remove, one module over.
* **Fresh sandbox per attempt** (would fix criterion 1 outright): the brief puts "a
  lane/worktree reset between attempts" out of scope, and it discards the mid-retry
  observability #540 just built.
* **Reusing `_FAIL_SUBSTANTIVE` for the refusal** (0 new lines): its label asserts something
  about the *verdict* when the fact is about *attribution*, and gives the operator no hint
  that the remedy is clearing the residue. 3 lines in `leaves` + 4 in `assemble` buys a true
  label.
* **A source-scanning test for criterion 6** (counting `shutil.copy2`): brittle against
  formatting; the recording-subclass drive is behavioural.

## Refuting my own test (forced check)

* **(a) Genuine red?** YES, twice over, both through the project's own gate/runner:
  * vs. the **base**: `PDCA_BUNDLE=… PDCA_WORKTREE=… ./engine/scripts/run-verify.sh` →
    green leg `Ran 13 tests … OK`; red leg (production hunks reverted)
    `Ran 13 tests … FAILED (failures=9, errors=3)` → `PDCA-EVIDENCE: C4 PASS — red without
    the fix, green with it`. The red leg names all three sites
    (`(site='review')`, `(site='advisory')`, `(site='plan-advisory')`) with
    `AssertionError: 'DEAD-ATTEMPT-VERDICT-b3f1' unexpectedly found in …`. 13 tests ran on
    the red leg (no `unittest.loader._FailedTest`), so this is a red, not a C4
    `PDCA-UNVERIFIABLE`.
  * vs. **iteration-v1** (the rejected approach), to prove the carry-forward is addressed and
    not re-submitted: I swapped v1's production hunks into the worktree
    (`git apply --exclude=template/tests/* iteration-v1/patch.diff`) and ran *this* test file
    against them → `FAILED (failures=5)`: the live-verdict leg fails at all three sites
    ("the LIVE attempt's own verdict was refused and died with the sandbox"), the bound leg
    fails with `1160401 not less than 116006`, and the quoted-marker leg fails with
    `'human' != 'impl'`. The worktree was then restored and byte-compared against
    `patch.diff` (`RESTORED: worktree identical to patch.diff`).
* **(b) Production path?** YES — every leg calls the real site entry points
  (`leaves._run_review_sandboxed`, `leaves._run_advisory_sandboxed`,
  `leaves._run_plan_advisory_sandboxed`) with a real `LeafConfig(mode="command",
  family="claude")` whose argv is a Python interpreter, so the real spawn
  (`progress.run_with_heartbeat`), the real stream/transient classification, the real sandbox
  and the real retry loop all run; the §6 legs go through the real
  `assemble.collect_needs_human`. No `_invoke` substitution, no re-implementation. The only
  patched thing is `leaves.time` — a stand-in that delegates every attribute to the real
  `time` and no-ops `sleep`, so the shipped 3-attempt budget and backoff *schedule* run at
  test speed. C5 gate agrees: `1 added driver-suite test(s) import the production package
  'pdca_harness'`.
* **(c) Fixture includes the fault?** YES — the failing element *is* the fixture: the stub
  leaf writes the truncated verdict into the sandbox and then dies at invocation (stderr, no
  stdout ⇒ the genuine transient signal); the un-withdrawable case is produced by the dying
  leaf doing `os.chmod(".", 0o500)` on its own sandbox — a real EACCES from the real kernel,
  not a mocked `unlink`; the overwrite case is the same locked sandbox with the *next* attempt
  writing through the still-writable file, which is precisely the hole the adversary found;
  the bound case writes a real ~1.16 MB residue. Nothing is curated out.

## Runner / environment notes

* Runners used — all the project's own: `./engine/scripts/run-verify.sh` (C4, above),
  `./engine/scripts/run-suite.sh` (T3): `Ran 1816 tests … OK (skipped=2)` →
  `PDCA-EVIDENCE: root suite OK, driver suite OK`;
  `PDCA_PROD_PACKAGE=pdca_harness ./engine/scripts/run-prod-path.py` (C5) and
  `./engine/scripts/run-docs-check.sh` (T2): `docs lint clean, site render + link audit
  clean`. The one-off v1 comparison above ran under `timeout 300`.
* Headless-safe: stdlib + `pdca_harness` only; the "leaf" is `sys.executable -c`. No display,
  no network, no container.
* Three legs `skipIf(os.geteuid() == 0)`: as root the read-only directory does not refuse the
  unlink, so the refusal cannot be produced. Non-root (local + GH `ubuntu-latest`) runs them;
  the criterion-1/2 legs never skip.
* No external dependency beyond the base toolchain — the brief's `External dependencies:
  none` held; nothing to declare.
* Commit-readiness: the target has **no** formatter/linter config and no repo hooks
  (`.pre-commit-config.yaml`, `pyproject.toml`, `setup.cfg`, `.flake8`, `ruff.toml` all
  absent; `core.hooksPath` unset; CI is render-check / docs-check / require-linked-issue).
  `CONTRIBUTING.md:21-27` states the discipline as "keep the offline suite green" (T3 above)
  + one logical change per PR + DCO. Longest added line is 98 chars, within what the touched
  files already carry (`leaves.py` 110, `assemble.py` 103, `test_attempt_ownership.py` 98).
* `git commit -s` (DCO) is publish's step, not mine. Nothing pushed, no PR opened or marked
  ready.
