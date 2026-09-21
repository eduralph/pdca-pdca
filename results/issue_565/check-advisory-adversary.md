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
