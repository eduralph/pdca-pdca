# Build notes — issue 384 / no-issue-mode-into-the-t4-gate (iteration 2)

Target: eduralph/pdca-harness @ main (worktree base `0fbfa26`, edited in
`$PDCA_WORKTREE=/home/eddie/pdca/pdca-harness.pdca-wt-l0`; all `path:line` below are
against that tree with the patch applied unless marked "base").

## Iteration 1 carry-forward — what it asked, what changed

The v1 sign-off iterated on exactly one gate finding:

> T3 Runtime — Copier must be provided and the 7 root render/update tests rerun — all
> were skipped because Copier is not installed … Failing gate: T3 …
> `== T3: root suite OK, driver suite FAILED (rc 1)`

That is an **environmental** finding, not a design rejection — the same sign-off says
"Check found implementation-level items only, no architectural judgment required", and
the v1 review PASSed every verdict on the change itself (C5, T1, T2, T4, T5;
`iteration-v1/check-review.md:9-15`). Accordingly this iteration does **not** rework the
production change (that would be churn against a review that endorsed it); it addresses
the carry-forward by producing the missing evidence on the environment as now provisioned:

1. **Copier is provided.** `.venv/bin/python3 -c "import copier"` → **9.17.0** in the
   instance venv — the exact external dependency the brief registered
   (`copier importable (.venv)`, brief `External dependencies`). At v1 Check time it was
   absent, which is what skipped the render tests.
2. **The 7 root render/update tests were rerun and all RAN — none skipped:**
   `.venv/bin/python3 -m unittest discover -s tests -v` from the worktree root →
   `Ran 7 tests in 20.732s — OK` (20 s of real copier renders; the verbose log shows all
   seven executing, incl. `test_update_compat.*` — clean `copier update` with instance
   edits surviving — and `test_render_and_run`, which renders an instance and re-runs its
   full driver suite inside it). This is the leg the carry-forward demanded.
3. **The `driver suite FAILED (rc 1)` leg does not reproduce.** With the identical patch
   applied on the current base:
   - project T3 runner (`./engine/scripts/run-suite.sh`, `PDCA_WORKTREE` set):
     `== T3: root suite OK, driver suite OK`;
   - driver suite standalone, instance venv python: **1569 tests, OK (skipped=2**, both
     pre-existing skips unrelated to this change**)**;
   - driver suite standalone, system `/usr/bin/python3` (3.14.4 — the interpreter
     `run-suite.sh:14-15` falls back to when no `.venv` resolves from the gate's cwd,
     i.e. the plausible v1 Check environment, which also explains "copier not
     installed"): **1569 tests, OK (skipped=2)**.
   The v1 record keeps only the suite's last line (`run-suite.sh:22-28`, the #402
   stopgap), so the failing test's name is not recoverable. What is checkable: the base
   blob of every file this patch touches is byte-identical to the v1 patch's pre-images
   (`git ls-tree HEAD` → `publish.py b1534ce`, `cli.py 9d98b52`, `pdca.toml.jinja
   87d68f8`, `test_publish_slice.py 8c45a7c`, `test_t4_publish_gate.py 9d15190` — the
   exact index hashes in `iteration-v1/patch.diff`), while the surrounding tree gained
   merges in *other* files since the brief's `9fb4860` fetch (`git log` on
   `template/`: `e7a88b0` #440, `9c69256`/`3fa7c43` integrations, #431, #401). So the
   rc 1 came from environment or from base code this patch never touched, and is green
   on the base this bundle now targets — under both interpreters.

`patch.diff` is therefore intentionally identical to `iteration-v1/patch.diff`
(verified byte-for-byte). The delta of this iteration is the T3 evidence above.

## What changed and why (the change itself, unchanged from v1)

1. **The blanket relax branch is deleted outright** (base `publish.py:194-208`). A failed
   T4 now returns 1 in both modes; the FLAGGED-and-proceed print is gone
   (`template/src/pdca_harness/publish.py:197-210`). The `id_pending` recording and the
   "add the id and re-gate before ready" discipline are untouched
   (`publish.py:386,405,506,514`), as the brief's scope demands.

2. **The gate is told which mode it runs in.** `_t4_passes` gains `pending_id`
   (`publish.py:781`) and derives `$PDCA_PENDING_ID` per run: the ambient value is
   popped, then set to `"1"` only when this run's flag says so (`publish.py:799-801`).
   This mirrors the brief's cited peer callsite — `gates._run_one` derives
   `PDCA_BRIEF_BASE`/`PDCA_LANE` from driver state, never inheriting them — which was
   opened per the composition cue. `publish()` passes its own flag through
   (`publish.py:207`); `draft_texts` keeps the default (id-known) mode — the flow never
   publishes pending-id — and the scrub now also protects that pre-pass from a stray
   ambient export.

3. **The checker consumes the mode.** `contribcheck` treats a non-empty
   `$PDCA_PENDING_ID` as `--no-issue` (`cli.py:1096-1102`), i.e. the narrow mode that
   already existed: `contribution_problems(d, no_issue=True)` drops *only* the tracker-id
   requirement (`cli.py:1131`). No lint rule changed (out of scope, and none needed).

4. **Restored pre-run announce, heartbeat label unprefixed** (`publish.py:825-833`):
   `· T4 gate <label> (this can take minutes)…` prints to stderr before
   `run_with_heartbeat`, whose label is now the bare `label or "T4 gate"` — the announce
   already says "T4 gate", per the brief. Same announce-then-heartbeat shape as the peer
   gate runner.

5. Stale prose stating the deleted behaviour updated: `publish()`/`draft_texts`
   docstrings (`publish.py:88-92,134-142`), the `--no-issue` help (`cli.py:388-390`),
   the `[tracker]` and T4-row comments (`pdca.toml.jinja:306-308,959-966`), and
   `agents/publisher.md.jinja:21-25`.

## Deliberate deviation from one clause of the Success criterion — with evidence

The brief says "the shipped gate row consumes it as `contribcheck --no-issue`", and the
literal implementation was tried first:

```toml
cmd = "{{ cli_name }} contribcheck${PDCA_PENDING_ID:+ --no-issue}"
```

That variant is **red on the target's own root render suite**: `tests/test_update_compat.py`
(#342) simulates the canonical instance shape — a row appended directly beside the shipped
`T4-contribution` row — and `copier update` from v0.56.0 then three-way-merges the edit of
that registered line against the instance's adjacent insertion, producing conflict markers
inside `pdca.toml`:

```
<<<<<<< before updating
  { id = "T4-contribution", ... cmd = "pdca contribcheck", ... },
  { id = "instance-extra", ... },
=======
  { id = "T4-contribution", ... cmd = "pdca contribcheck${PDCA_PENDING_ID:+ --no-issue}", ... },
>>>>>>> after updating
```

→ unparseable TOML; every `pdca` command in the updated instance dies at config load
(5 of the suite's 7 tests fail — reproduced in v1 with the suite's own fixture helpers).
TOML inline tables are single-line, so no diff shape changes that row's `cmd` without
touching the line an instance appends against: the cost is not a size trade-off but
broken `copier update` for every instance with an adjacent row, plus red target CI
(`render-check.yml` runs this suite). So the mode reaches the shipped checker **through
the registered row's run environment** instead: the row line is byte-identical to base
(`pdca.toml.jinja:979`), and the checker it invokes honours `$PDCA_PENDING_ID`
(`cli.py:1101`). The brief's intent — "a rendered instance gets the behaviour without
editing its own config" — is satisfied strictly more broadly: a fresh render *and* a
`copier update`d instance both get it with zero config edits. Every other clause of the
Success criterion holds as written; this iteration finally proves the update-compat leg
green on the demanded environment (7/7, no skips).

Scope note: this adds a 7-line hunk in `_contribcheck` (`cli.py:1096-1101`), near issue
401's territory (the default-open path at `cli.py:1088-1094` is untouched). The brief's
ordering note has 401 declaring the conflict on its side.

## Verification (project runners only, this iteration's runs)

- **C4 gate** (`engine/scripts/run-verify.sh` with `PDCA_BUNDLE`/`PDCA_WORKTREE` set):
  **`C4 PASS: red without the fix, green with it`** — green leg: both bundle test
  modules OK; red leg (production hunks reverted per `run-verify.sh:70-81`, tests kept):
  `tests.test_publish_slice` and `tests.test_t4_publish_gate` fail, e.g.
  `TypeError: _t4_passes() got an unexpected keyword argument 'pending_id'` and
  `'T4 gate' not found in '' : nothing announced before the run` — each failure is a
  test this patch added/replaced.
- **T3 runner** (`engine/scripts/run-suite.sh`): `== T3: root suite OK, driver suite OK`
  — the previously failing evidence line, now green end-to-end.
- **T2 runner** (`engine/scripts/run-docs-check.sh`): `render_site: link audit OK`
  (covers the `.md.jinja` prose edits).
- Root render/update suite and driver suite details: see the carry-forward section
  (7/7 run with copier 9.17.0; 1569 OK under both venv and system python).

## Forced self-refutation

- **(a) Genuine red?** Yes — the C4 red leg *is* revert-and-rerun, executed this
  iteration on the current base: with only the production hunks reverted, both test
  modules fail, and every failing test is one this patch added/replaced (evidence lines
  above). The replaced `test_no_issue_relaxes_failing_t4_to_a_flag` — which encoded the
  defect — is gone; its successor asserts `rc == 1` and `"FLAGGED" not in stderr`, which
  the base's relax-to-flag branch cannot satisfy.
- **(b) Production path?** Yes — the tests drive `publish.publish` / `publish._t4_passes`
  / `cli.main contribcheck` from the tree under test; the end-to-end test additionally
  spawns the real CLI (`python -m pdca_harness.cli` with `PYTHONPATH` at the tree's
  `src`) and builds its gate cmd from the checker invocation the *shipped config*
  registers (read from `pdca.toml.jinja` / rendered `pdca.toml`,
  `test_publish_slice.py:31-46`), not a re-declared copy. No stand-ins.
- **(c) Fixture includes the fault?** Yes — the end-to-end bundle carries the brief's
  exact repro artifacts: a `pr-description.md` with **no** `**User impact:**` opener and
  a `commit-msg.txt` with no tracker id (`test_publish_slice.py:437-450`); refusal is
  asserted on that malformed body under `pending_id=True`, the only-id-missing case is
  asserted to proceed, and the default mode is asserted to still enforce the id. The
  ambient-scrub test plants a hostile `PDCA_PENDING_ID=1` in the environment and asserts
  it is not honoured. Nothing curated out.

## Ruled out

- **Row-cmd rewrite** (`${PDCA_PENDING_ID:+ --no-issue}`) — see the deviation section:
  reproduced `copier update` conflict, 5/7 update-suite tests red; unbounded downstream
  cost (every instance with an adjacent appended row gets unparseable TOML).
- **A second shipped row / publish rewriting the cmd for contribcheck rows** — either
  duplicates tracker-id enforcement in default mode or couples publish to one project's
  checker, which `_t4_passes`' docstring forbids ("keeps publish decoupled from any one
  project's checker", `publish.py:783`).
- **Reworking the production change in response to the carry-forward** — the failing
  gate was environmental (copier absent; rc 1 unreproducible on the current base under
  either interpreter) and the review endorsed the design; changing endorsed production
  code to answer an environment finding would add risk with zero evidence gain. The
  carry-forward's demanded action — provide copier, rerun the 7 render/update tests —
  is done and green.

## Commit-readiness

The target repo configures no pre-commit hooks or formatter (no
`.pre-commit-config.yaml`, no lint step in `.github/workflows/` — docs-check /
render-check / require-linked-issue only; CONTRIBUTING.md's mechanical requirement is
the suites, which are green). New/edited lines follow surrounding style. CI parity:
root render suite (what `render-check.yml` runs) green locally with copier; docs paths
audited green by the T2 runner.

No NEEDS-HUMAN items: the brief's registered external dependency (`copier importable
(.venv)`) is present (9.17.0) and was exercised.
