# Result — issue 565 / one-live-driver-per-bundle

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: 
- Success criterion: Through the CLI entry point `cli._flow`, with the patch:
  (i) **A second driver over a held bundle is refused.** While run A (`pdca flow` naming 7)
  is mid-drive, run B — a `pdca flow` whose named ids include 7 — exits non-zero **before it
  changes any bundle's state** (before `flow_ids`' RESOLVED revalidation, `flow.py:1747-1756`,
  and its Plan pre-pass, `:1760-1766`), printing a line that names `issue_7` as held by
  another run. Nothing under `results/` changes because of B.
  (ii) **Implicit reach is skipped, not refused.** A CSV batch's in-flight sweep
  (`flow.py:1678-1692`) and split adoption (`_adopt_split_children`, `flow.py:1119`) each
  skip a bundle another live run holds, print a line naming it, and the rest of that run
  continues.
  (iii) **The claim ends with the run.** After A returns — normally or by raising — a new
  run over 7 proceeds. A run whose process is killed (SIGKILL) leaves nothing that stops a
  later run.
  (iv) **A run never refuses itself.** A's own in-process steps, and every leaf or command A
  spawns (including `pdca split --accept` run from A's Plan or sign-off session), are not
  refused or blocked by A's claims. A bundle A adopts becomes A's under the same rules.
  (v) **A claim that cannot be recorded fails closed.** If the claim cannot be opened or
  locked for a reason other than another run holding it (an unwritable process dir, a
  filesystem without locks), a named id refuses the run non-zero before any write, and an
  implicitly reached one is skipped with a line saying why — the way `act_session` reports
  and skips when its lock cannot be opened (`act.py:143-151`).
  (vi) **A bundle the run decides not to drive is let go at that decision**, so another run
  can take it while A goes on: a named id `flow_ids` skips (no brief, `flow.py:1774-1777`;
  terminal, `:1778-1798` — a split parent handed on as an adoption seed is let go once its
  adoption pre-pass, `flow.py:1482-1484`, is done), a swept bundle `waves.partition_schedulable` holds
  (`flow.py:1692-1697`, including the "nothing schedulable" return), children whose
  reschedule fails (`flow.py:1242-1247`), and a child a later reschedule retracts
  (`flow.py:1261-1270`). **Every one of these release points has a test that fails if that
  release is deleted** (the v2 adversary deleted five such lines with all 63 tests still
  green).
  (vii) **A resume line agrees with the refusal.** When a run prints `resume with \`pdca
  flow N\`` for a bundle it still holds and then keeps running (`_warn_abandoned`,
  `flow.py:777`, reached mid-run from `_drive_wave` `:1362` / `:1399`), the run keeps the
  claim — it still sweeps that bundle's footprint (`flow.py:1641`) and may run Act — and the
  line says the command applies once this run has ended (today's text stays a prefix, so
  existing assertions hold). A `pdca flow N` from another shell meanwhile is refused per (i).
  (viii) **Nothing else changes.** A single run with no second driver behaves and prints
  exactly as today apart from (vii)'s suffix; `split --accept`'s closing line
  (`cli.py:843-844`) is byte-identical (the sibling child owns it); the whole
  `template/tests` suite stays green.
  Shown by the named test going red on the base (B proceeds and drives 7) and green with
  the fix.
- Repo + branch target: eduralph/pdca-harness @ main (base `70ea12b`; every `path:line`
  here verified against it on 2026-09-19)
- Scope (one logical fix) / out of scope: 

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: likely-fix
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — (no gate configured)
- C3 Change: none — patch.diff
- C4 fix verified: bundle test red pre-fix, green post-fix: pass — C4 PASS — red without the fix, green with it
- C5 added test exercises production, not a copy: pass — 1 added driver-suite test(s) import the production package 'pdca_harness'

## 4. Conformance (Check — stack)
- T1 Structure: none — (no gate configured)
- T2 shape: docs lint + site render link audit: pass — docs lint clean, site render + link audit clean
- T2 host CI parity: target docs-check.yml on the pushed tree: pass — host CI parity on the patched tree — docs lint clean, site render + link audit clean
- T3 runtime: render/update-compat + offline driver suites: pass — root suite OK, driver suite OK
- T4 PR body has a user-impact opener + tracker id in both artifacts: deferred — pr-description.md not drafted yet — the substantive T4 audit of the contribution artifacts runs at publish
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Review exclusive ownership of each bundle by one live `pdca flow` run, including contention, claim lifetime, implicit adoption, and release when work is skipped.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The brief defines observable refusal, skip, lifetime, and release outcomes, with explicit exclusions; operator-facing scope agrees at `target/docs/07-crosscutting.md:464` and `target/docs/07-crosscutting.md:482` (criteria: `brief.md:16`). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing production changes lets a real competing subprocess drive the held bundle and return zero; this reproduces the data race rather than an import failure (`target/template/tests/test_flow_single_driver.py:421`; `reviewer-evidence/red.log:73`). |
| C3 Change | PASS | Named contention is refused before bundle writes, implicit contention skips only the affected work, and discarded work releases its claim; the change matches the stated CLI scope (`target/template/src/pdca_harness/cli.py:598`; `target/template/src/pdca_harness/flow.py:1267`, `:1324`, `:1768`, `:1895`). |
| C4 Verification (red→green) | PASS | Independent production-only stash/pop produced 15 assertion failures across 37 tests, then all 37 passed; real subprocess contention, SIGKILL recovery, and early release are exercised (`reviewer-evidence/red.log:261`; `reviewer-evidence/green.log:3`; `target/template/tests/test_flow_single_driver.py:544`, `:714`). |
| C5 Causal adequacy | PASS | The missing serialization is directly supplied by a real exclusive OS lock held through the run; tests exercise production and exhibit the forbidden race without it, with no capability probe masking a load-time cause (`target/template/src/pdca_harness/drive_claim.py:145`, `:195`; `target/template/tests/test_flow_single_driver.py:356`). |
| T1 Structure | PASS | One explicit run-owned claim scope crosses the CLI drive paths and reuses the existing lock primitive; ownership records stay outside bundle state and results commits (`target/template/src/pdca_harness/cli.py:573`; `target/template/src/pdca_harness/drive_claim.py:159`; `target/template/.gitignore.jinja:40`). |
| T2 Shape | PASS | Independent docs lint, 22-page site render/link audit, production-import scanner, and whitespace check passed; host-parity evidence matches the checked workflow (`target/.github/workflows/docs-check.yml:33`; `gate-logs/host-ci-docs.log:10`; `gate-logs/C5-prod-path.log:10`). |
| T3 Runtime | PASS | Independent driver suite passed 1,955 tests with two skips; frozen evidence shows all 24 root render/update tests passed, while the local repeat correctly reports missing importable Copier (`reviewer-evidence/suite.log:1656`; `gate-logs/T3-suite.log:54`; `reviewer-evidence/root-suite.log:6`). |
| T4 Contribution | N/A | Contribution artifacts are deliberately absent at Check; their substantive audit is deferred to the mandatory publish-time gate, not waived (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Confirm the affected-path merged and closed/rejected-work searches cover the current base and all affected paths — the brief records a narrower earlier search, but the supplied target has only one synthetic base commit and no remote, so absence of superseding work cannot be independently established (`brief.md:129`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether exclusive CLI driving is sufficient for intended concurrent use — CSV Plan sessions and single-step verbs can still write held bundles, an explicitly excluded gap whose operational acceptability remains human judgment (`target/docs/07-crosscutting.md:482`; `brief.md:85`). |

No confirmed patch defect found. These verdicts are advisory; they do not authorize acceptance.

Source citations above use the supplied `target/` only. Its synthetic base identifies upstream `b191da4477c4d49064ca8650c280b62e2b08061d`, newer than the brief's cited `70ea12b`; the patch was already applied, and reverse-application checking succeeded after the re-run. The production stash was restored. No stale-target failure was inferred.

Independent reproduction retained both test files while stashing the production and documentation paths, including the new claim module. From `target/template`, both legs ran `PYTHONPATH=src python3 -m unittest tests.test_flow_single_driver tests.test_flow_adopt_recovery`. Red returned 1 with 15 assertion failures and no import errors; green returned 0. The new suite specifically exercises normal return, exceptions, SIGKILL, an unopenable claim directory, unsupported locking, subprocess split acceptance, aliases, and the release decisions for named skips, split seeds, swept holds, failed rescheduling, newly held children, and later retraction. I inspected these release assertions; I did not independently mutation-test each release statement.

The independent full-suite command was `PYTHONPATH=src python3 -m unittest discover -s tests` in `target/template`. Temporary test files were confined below `reviewer-evidence/tmp`. Docs validation ran the commands in the supplied host workflow, with site output below `reviewer-evidence/site`; the production scanner consumed this bundle's `patch.diff`. The instance-root gate wrappers were not assumed to exist in this template checkout.

The local root-suite command `python3 -m tests.run_root_suite` returned 77 because `/usr/bin/python3` cannot import Copier. This is a local host limitation, not a patch failure or a claimed local verification: `gate-logs/T3-suite.log:36` explicitly records the render and update cases executing, followed by 24 passing tests at line 54. The concurrency reproduction itself used real Python processes, git, and filesystem locks; stubbed leaves did not prevent the original race from occurring. The brief's required external dependencies therefore remain discharged by the demonstrated tests.

For prior art, `git log --all --oneline -- template/src/pdca_harness/cli.py template/src/pdca_harness/flow.py template/src/pdca_harness/drive_claim.py` returned only the synthetic base, and `git remote -v` returned nothing. `brief.md:129` records path-based merged history and closed-unmerged searches, but supplies no independently inspectable closed/rejected-work evidence and does not document equivalent history searches for every affected path. T5 carries that decision. The available integration document is the template: its project-specific human-only list remains a placeholder (`target/template/docs/INTEGRATION.md.jinja:80`), so no additional enumerated project items were available.

### Advisory — adversary

# Adversarial review — issue #565 (one-live-driver-per-bundle)

Advisory only; nothing here gates. Everything below was re-run against
`$PDCA_TARGET` (Python 3.14.4, full offline suite 1955 tests green, 2 pre-existing
skips unrelated to this patch).

## Findings

- **NEEDS-HUMAN [impl] — `template/src/pdca_harness/flow.py:641-643`: a wave bundle
  `_runnable` skips for an unmet prerequisite is never let go, so the run the code
  itself tells you to start is refused.** `_runnable` drops a bundle whose
  prerequisite is not ready, prints `flow: issue_8 skipped — prerequisite(s) not
  ready (999); not built on a base missing them.`, and the run never revisits it
  (`_runnable` is called once per wave, at `flow.py:1570`; a bundle sits in exactly
  one wave). That is a final decision not to drive — but no `claims.release(d)`
  follows it, so the bundle stays fenced for the rest of run A. Reproduced end to
  end against the target: brief `issue_8` with `- **Depends on (merged):** 999`
  where `issue_999` is COMPLETE on disk but its PR is unmerged, brief `issue_11`
  plainly, run `pdca flow 8 11`, and pause A inside `issue_11`'s build (both are in
  wave 0, and the `_runnable` skip prints before the build). With A paused, a second
  process running `pdca flow 8` gets
  `flow: issue_8 is held by another live 'flow' run (pid …) — refusing to start a
  second driver over it` and exits 1. This contradicts the patch's own two
  statements: `flow.py:626-627` says of exactly this case "a later `pdca flow` run
  then picks it up", and `docs/07-crosscutting.md:468-471` claims the run "lets go at
  once" of every bundle "it then decides not to drive", enumerating only three of the
  seven release points the patch actually implements. It is the operator-visible
  shape the brief's criterion (vi) is about, and it is the *realistic* one — a long
  unattended batch holds the claim for hours while the human merges the blocking PR
  and wants to drive the dependent. Two candidate fixes, and the builder should pick
  deliberately: (a) release at the skip — but note `_sweep_quietly(cfg, bundles)` at
  `flow.py:1713` still sweeps that bundle's footprint at end of run and `results`
  at `:1714` still reports its state, so a plain `claims.release(d)` would leave A
  stomping a bundle B is now driving; it must also leave `bundles`/`batch_names`, the
  way `partition_schedulable`'s held set does; or (b) keep the claim and qualify the
  line at `flow.py:642-643` the way `_warn_abandoned` was qualified at `:777-782`
  ("…a later run picks it up, once this run has ended"), and correct
  `docs/07-crosscutting.md:468-471`, which as written is not true of the shipped code.
  Either way it wants a test in the shape of the seven that already exist.

- **NEEDS-HUMAN — `template/src/pdca_harness/progress.py:178-183`: the SIGKILL
  release (criterion iii) hands a bundle to the next run while the killed run's
  builder is still writing into it.** Non-interactive leaves — the builder at
  `leaves.py:2069` (`stream_json=True`) and the reviewer at `:2771` — are started
  with `start_new_session=True`, so the leaf is the leader of its own process group,
  deliberately shielded from the driver's. The only code that kills it
  (`_terminate_group`, `progress.py:333-343`; `_sweep_stragglers`, `:354`) runs on
  the driver's normal exit path, which a `SIGKILL` skips entirely. The claim, by
  design, dies with the driver's fd at that instant. So `kill -9 $(pgrep -f 'pdca
  flow 7')` mid-Do leaves an orphaned builder writing `results/issue_7/patch.diff`
  and its worktree, with nothing holding the claim — and `pdca flow 7` from the next
  shell claims it and drives it alongside the orphan. That is exactly the two-writer
  race #565 exists to close, re-created at the one moment the design drops the claim
  on purpose. `test_flow_single_driver.py:543-566` cannot see it: its builder is an
  in-process monkeypatch of `leaves.do_build`, which dies with the process, so the
  test proves the *lock* is released, not that the *work* stopped. This is an
  architectural / scope call (is the claim's lifetime the driver process, or the
  drive? does the SIGKILL case want a liveness probe or a leaf-held claim?), not
  something to iterate on blind — but it should be named in §6 rather than left for
  the first operator who `^C`-then-`kill -9`s a stuck run.

- **NEEDS-HUMAN [impl] — `template/src/pdca_harness/drive_claim.py:174-180`: the
  fail-closed remedy line is wrong for every non-lock `OSError`, and a CSV batch now
  holds one open fd per swept bundle for the life of the run.**
  `_claim_swept` (`flow.py:1796-1808`) claims every in-flight bundle up front and
  `Run.close` is the only thing that closes them (`drive_claim.py:189-192`), so the
  run's open-file count now scales with the size of the sweep where it used to be
  O(1) (Act's peer lock holds exactly one). Measured against the target with
  `RLIMIT_NOFILE` soft-limited to 64 and 120 in-flight bundles: 59 bundles were
  skipped with
  `unclaimable — this run could not record its claim on it ([Errno 24] Too many open
  files: …/process/.drive-claims/issue_1061-e6224c8834b1.lock) … To drive it, make
  …/process/.drive-claims a writable directory on a filesystem that supports file
  locks` — a remedy that is simply false for EMFILE and sends the operator to check
  permissions that are fine — and the run then died with an unhandled
  `OSError: [Errno 24] Too many open files` raised out of `cli._flow` as a bare
  traceback (nothing on the `flow` path catches it; `cli.py:436-443` catches only
  `Config.load`'s). Cheap fix: special-case `EMFILE`/`ENFILE` in `_unrecorded`'s
  remedy (raise the open-file limit), and/or keep the "remedy" generic. The default
  `ulimit -n` on this host is 524288, so the *exhaustion* is not a near-term
  operational risk and the fd scaling is arguably fine to accept — the wrong remedy
  text is the part worth fixing.

## Attempted and could not refute

- **The red→green is real, not a tautology.** Re-ran the target suite: the 23 new
  tests pass with the fix; the frozen `gate-logs/C4-verify.log` shows 14 of the 23
  failing on the red leg plus `test_flow_adopt_recovery`'s text assertion, with
  real assertion messages (`"0 != 1 : a second driver ran while another process
  held 7"`), not import errors — the brief's C4 import-trap was respected (the test
  imports only `act, cli, flow, leaves, split, state, waves`, never `drive_claim`).
- **The test exercises production, not a copy.** Every run goes through `cli._flow`
  (`cli.py:573-574`); the contending run is a real `subprocess.Popen` of a fresh
  interpreter with `PYTHONPATH=template/src` and no inherited `PDCA_*`
  (`test_flow_single_driver.py:352-374`), so a per-process claim could not pass for
  the wrong reason.
- **The v2 adversary's attack — delete a release line, watch the suite stay green —
  fails here.** I deleted or neutered each of the seven release points in turn and
  re-ran the whole 1955-test suite. Every one goes red on a *dedicated* test, none
  on collateral: `flow.py:1895-1896` →
  `test_a_named_id_with_no_brief_is_let_go_at_the_skip`; `:1905-1910` →
  `…already_terminal…`; `:1554-1556` → `…split_parent_seed…`; `:1786-1787` → the two
  swept-bundle tests; `:1324-1326` → all three adoption tests; and each half of
  `:1315-1316` independently → `…reschedule_holds…` and `…later_reschedule_retracts…`.
- **No released bundle is left where the run would still write it.** Checked every
  release against `_sweep_quietly(cfg, bundles)` (`flow.py:1713`): held sweep
  bundles are removed before `_drive_and_act`, retracted children are removed from
  `bundles` at `:1318`, unscheduled children are never added at `:1299`, and seeds
  are never in `bundles`. (The `_runnable` case above is the one that would break
  this if "fixed" naively.)
- **The claim is taken in the process that drives.** `main` re-execs under the
  keep-awake inhibitor at `cli.py:433`, before `Config.load()` and long before
  `_flow` opens the scope at `cli.py:573`.
- **A spawned leaf cannot inherit or extend the lock.** No `os.fork`, no
  `pass_fds`, no `close_fds=False` anywhere in `template/src/pdca_harness`; Python's
  `open()` is `O_CLOEXEC` by default (PEP 446), so the claim fd does not survive
  into a leaf, and `pdca split --accept` spawned from A's session is genuinely
  unblocked (confirmed by `test_a_run_drives_the_children_it_adopts…`).
- **`flock` really does refuse a second `Run` in the same process** — it is held on
  the open file description, not the process — so `drive_claim.py:26-34`'s claim is
  correct on Linux; the NFS caveat it names is documented rather than hidden.
- **The release key matches the claim key.** `waves.partition_schedulable` returns
  `held` keyed by bundle *name* (`waves.py:254, :274`), so `cfg.bundle_root / name`
  at `flow.py:1787` resolves to the same digest `_claim_swept` took — verified by
  the R4 mutation going red rather than silently no-op'ing.
- **Two spellings of one bundle do not refuse the run**, and `--rehearse`'s bundle
  root does not collide with the real one: `_digest` keys on the resolved path
  (`drive_claim.py:73-79`), pinned by `…naming_one_bundle_under_two_names…`.
- **Scope kept.** `cli.py:843-844` (`split --accept`'s closing line) is untouched by
  the diff, and the claim record is confined to `process/.drive-claims/` with a
  render-gitignore test that would catch a rename of `CLAIMS_DIR`.

### Advisory — code-review

# Advisory code review — issue #565 (one live driver per bundle)

Traced the claim/release bookkeeping end to end against the target source
(`drive_claim.py`, `cli.py:558-660`, `flow.py`'s claim/release call sites) and
cross-checked every release point the brief calls out. No correctness bug and
no reuse/simplification opportunity found in this diff.

Specific things checked and found sound:

- `drive_claim.Run.take()` / `.release()` key claims by `_claim_file`, which
  hashes the bundle's *resolved* path (`drive_claim.py:218-224`). The named-id
  claim loop (`cli.py:598-611`), `_claim_swept` (`flow.py:1796-1808`), and the
  `held` release loop (`flow.py:1786-1787`) all build their `Path` from the
  same `cfg.bundle_root / name` / `cfg.bundle(iid)` shape, so a claim taken one
  place is found and released at the other — verified `waves.partition_schedulable`
  keys `held` by the same `b.name` bundle-directory string (`waves.py:255-274`),
  matching the `cfg.bundle_root / name` reconstruction at `flow.py:1787`.
- The `dropped` computation in `_adopt_split_children` (`flow.py:1281-1326`)
  covers all three ways a claimed child stops being driven — never spliced at
  all (`dropped = children`), spliced but held by this reschedule, and adopted
  earlier but retracted by a later one — without releasing a claim more than
  once: once a bundle is dropped it's removed from `bundles`/`batch_names`/the
  rescheduled `wave_list`, so it can't reappear in a later call's `remaining`.
- The keep-awake re-exec ordering the brief calls out is real:
  `main()` calls `_inhibit_suspend_and_reexec()` (`cli.py:433`, which
  `os.execvpe`s and never returns on success) *before* dispatching to `_flow`
  (`cli.py:454`), and `drive_claim.run(cfg)` is entered inside `_flow` itself
  (`cli.py:573`) — so a claim is always taken in the process that actually
  drives, never one that's about to be replaced.
- `_contended()`'s `isinstance(exc, BlockingIOError)` check is redundant with
  its own `exc.errno in _CONTENDED` check (CPython maps EAGAIN/EWOULDBLOCK
  OSErrors to `BlockingIOError` automatically), but it's harmless — not
  flagging as a finding, just noting it in case a reviewer wonders why both are
  there.

Gate evidence corroborates the fix: `C4-verify.log` shows 14/23 tests failing
on the reverted (red) leg for real reasons (the sweep and adoption drive
bundles a held claim should have excluded), green after the fix; `T3-suite.log`
shows the full 1955-test suite passing.

No findings requiring a human or a builder iteration.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T5 Judgment — Confirm the affected-path merged and closed/rejected-work searches cover the current base and all affected paths — the brief records a narrower earlier search, but the supplied target has only one synthetic base commit and no remote, so absence of superseding work cannot be independently established (`brief.md:129`).
- [x] Validation — fitness-to-purpose — Decide whether exclusive CLI driving is sufficient for intended concurrent use — CSV Plan sessions and single-step verbs can still write held bundles, an explicitly excluded gap whose operational acceptability remains human judgment (`target/docs/07-crosscutting.md:482`; `brief.md:85`).

## 7. Proven / not proven
- Proven by which oracle: gates overall = pass (stub oracles).
- Unproven / needs manual run: anything flagged in §6.

## 8. Ready-to-ship attachments
- patch.diff
- tracker-comment.md     (ALWAYS, every tracker item)
- build-notes.md         (builder rationale — for the human, not the reviewer)

## 9. Check sign-off                     ← human completes Check here
- Disposition confirmed / overridden:
- Outcome: merged-wider
- Iteration delta (if iterating):
- By / date: Eduard Ralph / 2026-09-19

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
- issue_565: any time the driver starts processing a bundle it must take a claim — the single-step verbs (`pdca run` / `signoff` / `publish`) and the CSV batch's Plan session take none today (documented gaps, `docs/07-crosscutting.md`). Make an issue for 0.61.
- issue_565: same 0.61 item as above — also cover the `_runnable` prerequisite skip (`flow.py:641-643`), which keeps its claim for the whole run while the new `docs/07-crosscutting.md` paragraph and the comment at `flow.py:626-627` say the bundle is let go and a later run picks it up.
