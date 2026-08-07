# Build notes — issue 434 / red-leg-zero-tests-unverifiable

Target: `eduralph/pdca-harness` @ `main` (worktree `/home/eddie/pdca/pdca-harness.pdca-wt-l1`,
HEAD `9d503d1` == `origin/main`). All `path:line` citations below are against that tree.

## What the change is

Three files, 232 added / 1 removed:

| file | change |
|---|---|
| `template/engine/scripts/run-verify.sh:40-75` | the published C4 instructions now decide a leg from **two** facts and name the "no test ran" outcome |
| `template/engine/README.md.jinja:44-69` | §"The two gate shapes that matter" carries the longer explanation + the four-outcome table |
| `template/tests/test_verify_red_leg.py` (new, 177 lines) | holds that wording in place |

### The `.sh` (the load-bearing part)

- `run-verify.sh:42-43` — pseudocode step 2 no longer says "run the test -> expect FAIL
  (red)". It now says *expect a REAL red: a test that RAN and failed*. The old unqualified
  string is gone, and the test asserts its absence (`test_verify_red_leg.py:98`), which is
  the "assert the old wording is gone" half of the shape the brief pointed at
  (`test_verify_base.py:279`).
- `run-verify.sh:47-56` — the rule: judge every leg by *the runner's exit code AND how many
  tests actually ran*; parse a **count of executed tests** from the runner's own
  machine-readable report; never infer that count from the exit code. It also names *why*
  this is routine rather than a corner: reverting the fix removes any symbol the fix added,
  so a test calling one cannot build on exactly the red leg.
- `run-verify.sh:58-66` — the four-outcome table, so the bad row is stated as data, not as
  a caveat a reader can skim past: `non-zero | 0` → `PDCA-UNVERIFIABLE (77), NEVER PASS`.
- `run-verify.sh:68-71` — the two "nothing ran" cases kept distinguishable, with the two
  reason strings spelled out (`runner exited 0: nothing was selected` vs `runner exited
  <rc>: the test did not build/import`). Brief §Scope bullet 3.
- `run-verify.sh:72-75` — the invariant generalised: *for every leg you add here and for
  every other verification step* … *never a pass and never a fail. A gate never turns "no
  evidence" into a verdict.* That is the brief's `Invariant to restore`, stated for every
  step rather than for one leg of one script.

Vocabulary is the existing one, per the brief's citation of `run-verify.sh:46-52` (now
`:77-83`): `PDCA-UNVERIFIABLE: <reason>` / exit 77 / "→ SUMMARY §6 NEEDS-HUMAN,
non-gating" — the same channel `gates.py:19-38` and `gates.py:761-773` already implement
(`rc == 77` → `unverifiable`, and the marker "declares EVIDENCE, never a verdict", #329).
No second vocabulary invented; `test_the_rule_reuses_the_existing_unverifiable_channel`
pins that.

### The README

Placed where the brief said the longer explanation belongs
(`template/engine/README.md.jinja:44-69`, §"The two gate shapes that matter", directly under
the existing #165 bullet it is a sibling of). It names the wrong verdict in plain terms —
"PASS for a bundle whose test never executed" — and repeats the four outcomes as a Markdown
table so the two documents cannot drift apart silently (the test checks both).

## Why this shape, and what I ruled out

**Wording only, no shipped snippet.** The brief left "wording alone vs wording + a reusable
`engine/scripts/lib/` snippet" to Do. I ruled out the snippet, not on cost but because it
cannot be written correctly *generically*: the whole quantity in question — how many tests
executed — is only obtainable from the project's own runner (`cargo test --format json`,
JUnit XML, TAP, `unittest -v`). A shipped `lib/count_tests.sh` would have to either pick one
runner (wrong for everyone else) or shell out to a project-supplied hook, at which point it
is the wording with extra indirection. This is the same reasoning the human already settled
at Plan for option 2 ("there is nowhere generic to do it") applied one level down. Concretely
the snippet would have been ~40 lines of shell plus a config key plus its own test, and the
project would still have to write the per-runner parser — the part that actually matters.

**No change to `gates.py`.** Out of scope per the brief, and unnecessary: exit 77 already
does the right thing (`gates.py:761-773`). Nothing here needs new machinery — the defect is
that no published instruction ever tells a project to *reach* that channel for this case.

**Not guarding a symptom.** The invariant is restored at the only place it can be: the
harness publishes instructions, it does not run anyone's gate. The removed cause is the
instruction "expect FAIL (red)" that made the exit code the sole input.

**Did not touch this instance's own `engine/scripts/run-verify.sh`.** Explicitly out of
scope (brief §Scope, §Settled at Plan) — different repository, ordinary pdca-pdca PR.

## Test

`template/tests/test_verify_red_leg.py`, standard library only, reads files from the
checkout — no network, no cargo, no Docker, no display. Shape copied from
`test_verify_base.py:271-279` and its locator idiom from `:42`.

Two deliberate details:

- `_prose()` (`:47-52`) strips shell comment markers and collapses whitespace before prose
  assertions, so re-flowing a paragraph does not break the suite while *changing what it
  says* does. Needed because both files hard-wrap.
- `_ENGINE_README` (`:38-39`) resolves `README.md.jinja` *or* `README.md`. The suite ships
  into rendered instances and the root render/update-compat suites run it there, where
  copier has stripped the `.jinja` suffix. First run of the root suite caught this
  (4 errors, `FileNotFoundError: /tmp/.../out/engine/README.md.jinja`); the idiom is the
  repo's own (`test_settings_permissions.py:31-33`, `test_split.py:459-466`,
  `test_handoff.py:47-54`). `run-verify.sh` needs no such handling — no `.jinja` suffix, so
  copier copies it verbatim (`copier.yml:14`).
- `assertSays()` (`:58-62`) fails with the missing sentence instead of `assertIn`'s dump of
  the whole file. Without it the red leg wrote ~4 KB of README into the gate log per failing
  test, eleven times over — unreadable at sign-off, and a needless risk of a relayed
  `PDCA-UNVERIFIABLE:`-looking line in a gate capture.

## Refuting my own test

**(a) Genuine red? Yes.** Via the project's own runner — `./engine/scripts/run-verify.sh`
with `PDCA_BUNDLE`/`PDCA_WORKTREE` set (the `C4-verify` gate cmd from `pdca.toml`, not a
hand-rolled invocation). It reverts the production hunks and keeps the test
(pdca-pdca `engine/scripts/run-verify.sh:72-81`):

```
== C4 green leg: … Ran 11 tests … OK
== C4 red leg:   … Ran 11 tests … FAILED (failures=11)
C4 PASS: red without the fix, green with it
```

`failures=11, errors=0` — every red is an **assertion** failure, not an import/attribute
error. That matters here specifically: the gate judging this bundle has the very defect
being fixed (it cannot tell "ran and failed" from "never ran"), so a red earned by an import
error would prove nothing (brief §Settled at Plan, last paragraph). I also reverted **only**
`template/engine/scripts/run-verify.sh`, leaving the README hunk in place: `FAILED
(failures=7)`. So the `.sh` — not the README — carries the red, which is Falsifiability
requirement 2.

**(b) Production path? Yes.** There is no code path to drive: the artifact this bundle
changes *is* the published wording, and the test reads the two real shipped files from the
checkout (`_SKELETON`, `_ENGINE_README` resolved from `Path(__file__).parents[1]`) — the
same files copier copies into every instance. No fixture copy, no mock, no re-implementation.
The reference C5 heuristic (`scripts/checks/test_exercises_production.py`) looks for an
import of the production package and is not wired in this instance's `pdca.toml`
(`[gates] checks` lists only C4-verify / T2-docs / T3-suite / T4-contribution); were it
wired it would print `PDCA-UNVERIFIABLE` for this bundle, which is the honest answer for a
data/wording change — flagging it here so it is not mistaken for evasion.

**(c) Fixture includes the fault? Yes.** The "fixture" is the repository checkout itself,
and the failing element — the C4 outline whose instructions cause the bad verdict — is read
directly, at its real path, on both legs. Nothing is curated out: the red leg's tree is base
`origin/main` for that file, i.e. exactly the wording the issue reports.

## Gates run locally (target's own runners)

- `C4-verify` (`./engine/scripts/run-verify.sh`) — **PASS**, red→green as above.
- offline driver suite, `cd template && PYTHONPATH=src python3 -m unittest discover -s tests`
  (the command `CONTRIBUTING.md:29` names) — `Ran 1537 tests … OK (skipped=2)`.
- root render/update-compat suite (`.venv/bin/python3 -m unittest discover -s tests`, the way
  `run-suite.sh` invokes it) — `Ran 7 … OK`. This renders the template with copier and runs
  the *rendered* instance's suite, which is what caught the `.md.jinja` locator bug above.
- `T2-docs` (`./engine/scripts/run-docs-check.sh`) — `lint_docs: OK`, `render_site: link
  audit OK`.
- `git apply --check` of `patch.diff` against a pristine export of `origin/main` — applies
  clean (all three files).

## Commit-readiness for the target

The target repo ships **no** formatter or pre-commit hook (`.git/hooks` empty; no
`.pre-commit-config.yaml`; CI = `docs-check`, `docs`, `render-check`, `require-linked-issue`
— none is a Python linter). The applicable written conventions are `AGENTS.md:19-29` /
`CONTRIBUTING.md:23-29`: one logical change, a test, offline suite green, `git commit -s`
with a conventional prefix (`fix:`) and a `Closes #434` reference — all a publish-step
concern, satisfied by this patch's content. I matched the surrounding line-width convention
rather than a tool: max line length is 94 (test), 95 (`.sh`), 93 (README) against base
maxima of 94 / 94 / 88 — the README's table rows are the widest and were reworded down from
112 to fit.

## No NEEDS-HUMAN external dependencies

Everything ran with the base toolchain the brief listed (python3 + git + bash, plus the
instance venv's copier for the root suite, which the project's doctor already requires).
Nothing was substituted, shimmed, or read-instead-of-run.
