# Build notes — issue_566 (split hint honest about a live run)

## What changed, and why

1. **`drive_claim.py`** (`template/src/pdca_harness/drive_claim.py`):
   - `held(cfg, d)` — a read-only peek: "does some other live run hold `d`'s claim right
     now?" It answers by taking and instantly releasing the very same lock `Run.take`
     uses (there is no peek-without-acquiring primitive under `flock` / `LK_NBLCK`), fails
     closed the *opposite* way from `take` (an unclaimable file reads as *not held*, since
     a peek must never claim a hold nothing really took), and adds no second lock
     mechanism — the brief explicitly forbids that ("reuse it, do not add a second lock").
   - `sweep_marker(cfg)` — a bundle-shaped path claimed by `flow.flow_batch` for the span
     between it starting and it finishing its sweep claims, so `held()` on this path
     answers "has a live CSV batch not yet swept?" A CSV batch sweeps *every* in-flight
     bundle in the instance (`flow.py`'s `flow_batch`, not scoped to the CSV's own rows),
     so any parent split during that batch's own Plan session qualifies — no per-bundle
     bookkeeping needed, one marker suffices.
   - `Run.take` now retries a CONTENDED lock up to `_PEEK_RETRIES` times before reporting
     the bundle held. This is criterion (iv): since `held()` must take the SAME lock
     `take()` takes (if only for an instant), a `take()` landing in that instant would
     otherwise read a peek's microsecond hold as a live run's — a **false refusal** of a
     concurrent `pdca flow` over a bundle nobody actually holds. The retry hook
     (`_retry_wait`) is the deterministic seam the test uses to force this collision on a
     fixed schedule rather than trust wall-clock timing.

2. **`cli.py`** (`_split`, the `--accept` tail): the closing line now branches on
   `drive_claim.held(cfg, d) or drive_claim.held(cfg, drive_claim.sweep_marker(cfg))`. If
   either is true, it prints the brief's suggested conditional wording verbatim (adapted
   to the actual parent/children); otherwise it prints today's line, byte-identical.

3. **`flow.py`**:
   - `flow_batch` claims/releases `drive_claim.sweep_marker(cfg)` for its own span
     (best-effort — a marker that cannot be recorded degrades to "no live CSV batch known",
     never gates the batch itself), wrapped in `try/finally` so every return path (and a
     raise) releases it.
   - New `_warn_stranded_split_children` (called just before `_drive_and_act` returns,
     for both CLI shapes and the CSV batch since they share that one function) walks every
     bundle in the run's final drive set plus its adoption seeds, finds ones carrying the
     `close-disposition = split` marker, and names any lineage child that is **not** in the
     final drive set and not itself split (walking through one that is, exactly as
     `_adopt_split_children`'s own queue does).
   - New `_split_marked(d)` helper: checks the raw `close-disposition` marker content,
     **not** gated on `state.state(d)` being confirmed-terminal the way `_is_split_parent`
     deliberately is. This divergence is the one substantive design decision in this
     patch and is worth spelling out:

     `_is_split_parent` (used by live adoption and by `_terminal_hint`) requires
     confirmed-terminal state on purpose — driving a child before a human confirms the
     decomposition at sign-off would spend cycles on work the next sign-off might reopen.
     But a split accepted "from another shell" on a bundle whose *own* wave has already
     returned (the run walked away from it un-terminal, per `_warn_abandoned`) will
     **never** reach confirmed-terminal this run: nothing will ever call `_build_all` +
     sign-off on it again, because only the run that holds it could, and it has already
     moved on. I verified this empirically (see "Refutation" below): `split.accept` alone
     leaves the parent at state `BUILT`, not terminal, until a further `_build_all` +
     sign-off pass runs — which the ordinary "split happens inside its own wave" case
     always gets (mid-wave), but the "already-abandoned, split-from-outside" case never
     will. Yet the **children are materialized on disk the moment `split.accept`
     returns**, regardless of the parent's confirmation status — so an orphaned, undriven
     bundle exists right now, and the report's job is purely informational (it drives and
     claims nothing), so the "don't spend cycles on an unconfirmed decision" guard that
     justifies `_is_split_parent`'s stricter check does not apply to it.

     I considered leaving this report gated on `_is_split_parent` (a two-line, `git diff`
     of maybe 5 fewer lines) and simply accepting that the brief's own probe would not go
     green. I rejected that: the probe is the RED case named in the brief's Falsifiability
     section, and "green on a narrower proxy" (e.g., only the mid-wave case that
     `_adopt_split_children` already half-covers) is exactly the "green mechanical check
     on something adjacent" the standard here forbids. The looser check is the smallest
     change that actually satisfies the criterion.

4. **Text** (`planner.md.jinja`, `leaves.py`'s Plan seed prompt, `docs/07-crosscutting.md`):
   updated at exactly the citations the brief named, to describe the new conditional line
   and the end-of-run report. No other line in any of the three touched.

## What I ruled out

- **A second lock file per (parent, live-run) pair**, keyed some other way, to avoid the
  `held()`/`take()` collision entirely. Rejected: the brief explicitly says "reuse it, do
  not add a second lock", and a second lock only moves the same collision problem onto a
  new pair of primitives — flock still has no true peek-without-acquire mode, so the same
  retry-vs-false-refusal tension would reappear one level down.
- **Gating the CSV "not yet swept" signal per-bundle** (e.g., recording which specific
  bundles the upcoming sweep will touch) instead of one instance-wide marker. Rejected on
  cost and on correctness: `flow_batch`'s sweep pulls in *every* in-flight bundle in the
  instance (not just the CSV's own rows), so a per-bundle registry would have to
  duplicate that same "every in-flight bundle" computation before the sweep has even run,
  for no behavioral gain over a single marker.
- **Keeping `_warn_stranded_split_children` gated on `_is_split_parent`** (see above) —
  rejected because it fails the brief's own probe.
- **A blocking wait in `take()`** instead of a bounded retry, to sidestep the collision
  more "simply". Rejected: `drive_claim`'s whole design is explicitly non-blocking on
  every attempt (stated in the module's own docstring before this patch); a bundle a
  live run genuinely holds must still refuse *quickly*, and the retry window here is
  bounded and small (a handful of ~1-5ms sleeps) specifically so a genuine hold's refusal
  latency barely changes while a peek's microsecond hold is reliably ridden past.

## The three refutation questions

**(a) Genuine red?** Yes — verified directly, not asserted. I reverted the three
production files (`cli.py`, `drive_claim.py`, `flow.py`) to `fe8208f` (this child's base)
while keeping the new test, and re-ran `python3 -m unittest tests.test_split_hint_live_run`
from `template/`: 5 of 8 tests failed (the ones exercising the new conditional line, the
CSV-batch marker, the end-of-run report, and the retry-vs-false-refusal fix); the 3 tests
pinning *unchanged* behavior ((ii)'s three "byte-identical" sub-cases) correctly stayed
green, since that half of the contract was never broken. I then restored the fix and
re-ran: all 8 green. This is the exact revert/re-apply the C4 gate (`run-verify.sh`)
performs; I did not hand-roll a substitute runner — every red/green check here went
through `python3 -m unittest`, the project's own documented way to run this suite (per
every existing test file's own module docstring, e.g. `test_flow_adopt_split.py:25`).

**(b) Production path?** Yes. Every test drives `cli._flow` / `cli._split` directly — the
real CLI entry points — never a hand-picked `flow.*` call or a re-implementation. The
"another shell" test spawns a genuine second OS process running the real `cli._flow`
against the same on-disk instance, so the cross-process `flock` contention this fix
depends on is exercised for real, not simulated with threads. The (iv) retry test drives
the real `drive_claim.Run.take` and a real `fcntl`/`msvcrt` lock via `act._lock_exclusive`
— the only injected seam is the retry-wait *hook*, which is what makes the collision
deterministic instead of a timing gamble; the lock primitive itself is untouched.

**(c) Fixture includes the fault?** Yes. The "another shell" test genuinely runs a second
process and genuinely contends on the same claim file (not a healthy-fleet-style fixture
that excludes the holder). The end-of-run probe genuinely leaves a parent un-terminal via
a real stubbed-out sign-off (nobody answers it) and genuinely calls the production
`split.accept` on it after its own wave has already returned — the exact "walked away,
then split from outside" fault the brief's Defect section describes, not a fixture that
pre-arranges the parent into some more convenient state.

## External dependencies

None beyond what the brief declares (stdlib Python ≥ 3.11, git). `copier` is not
installed in this sandbox, which skips 3 tests in the target repo's *root* suite
(`tests/`, unrelated to `template/tests/`) — pre-existing and unrelated to this change
(the harness's own `run-suite.sh` documents this: "render skips itself unless copier is
importable"). Not flagging as NEEDS-HUMAN since it does not touch anything this brief's
Success criterion depends on (verified: 1963/1963 `template/tests` pass; 19/19 root
`tests/` pass with 3 pre-existing skips).

## Regression scope

Ran the full offline driver suite (`template/tests`, 1963 tests, includes the 8 new ones)
and the root template-repo suite (`tests`, 19 tests) — both green. Specifically re-ran
every test file that references the touched prompts/docs text
(`test_flow_adopt_split.py`, `test_flow_adopt_recovery.py`, `test_flow_single_driver.py`,
`test_flow_entrypoint_parity.py`, `test_plan_advisory_split_children.py`,
`test_plan_policy_split_child.py`, `test_split_convergence.py`, `test_split_stub_guard.py`,
`test_suite_output_hygiene.py`, `test_split.py`) individually — all green, confirming
(vi) "nothing else changes" holds: every existing adoption report line is untouched.

## Formatter / commit hooks

No formatter or pre-commit config exists in this target repo (no `pyproject.toml`,
`.flake8`, `ruff.toml`, or `.git/hooks/pre-commit`) — checked directly. Nothing to run.
