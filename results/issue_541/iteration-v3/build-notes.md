# build-notes — issue #541 (round 3 rebuild)

Target: `eduralph/pdca-harness` @ `main`, stacked on `pdca-integration/main` at `480fa6b`
(#540 integrated). Worktree: `/home/eddie/pdca/pdca-harness.pdca-wt`; every `path:line`
below is against that tree with `patch.diff` applied.

## What this round is

The round-2 carry-forward said: *the slice is right, the core landed, do not re-open the
structure or re-slice — close three findings and keep everything else as built.* I did
exactly that. I started by re-applying `iteration-v2/patch.diff` onto the worktree
(`git apply`, clean) and then changed only what the three items name. The shared owner
(`_LeafHarvest`), the three call sites, the retry contract, the residue quoting, the
`unowned-empty` status and every test leg that was already binding are unchanged from v2.

Net effect of this round on the v2 diff (`git apply --numstat`): `assemble.py` **shrinks**
from +46/-2 to +21/-1 (the header-region heuristic and the unknown-token fallback are gone;
the executable body of `_items_from_artifact` is now byte-identical to base), `leaves.py`
grows from +306/-29 to +395/-29 (the identity machinery), and the test file goes 401 → 498
lines (4 new legs).

## The three carry-forward items

### 1. `assemble.py` — the header-region remedy, defeated by an early fenced quote

**Finding (round 3):** `_LEAF_STATUS_HEADER_LINES = 8` classified a REAL artifact as a
placeholder when it quoted an unknown status token on a standalone line inside a fence that
opens in the first 8 lines. Measured against v2's code with the new leg: two genuine
`NEEDS-HUMAN [impl]` findings came back `'human' != 'impl'` — the #264 routing stripped.

**What I did.** I did not build a second heuristic. `assemble.py:99-108` now states the rule
plainly: *only a status in `_LEAF_STATUS_LABEL` ever relabels an artifact*, and
`_items_from_artifact`'s body (`assemble.py:188`) is restored byte-for-byte to base. The new
`unowned-empty` status and its label (`assemble.py:88`, `:95-97`) — criterion 4 — are all
that is left of the v2 `assemble` change.

**Why not the narrower gate the carry-forward named** ("keep `""` for an artifact that
carries a verdict table / findings"). My change satisfies that instruction *a fortiori* — it
keeps `""` for **every** artifact with an unrecognised token — and it does so because the
narrower version still leaks, measurably. `leaf_status()` matches the marker **anywhere**,
so any gate has to guess "placeholder or quoting one", and I measured what each guess costs
against real artifacts in this instance's own `results/` (reproduce with
`assemble._verdict_table_lines` over `results/issue_*/**/check-advisory-*.md`):

| gate | real advisory artifacts it would still mislabel |
|---|---|
| "carries a 5/5/1 verdict table" | **66 of 66** — advisory artifacts never carry that table |
| "…or an `[impl]`-marked finding" | **21 of 66** — findings that exist, relabelled "no verdict" |
| recognised tokens only (shipped) | **0** |

And the cost of declining is measurably nil: across the same corpus there are 13 placeholders
and every one carries a **recognised** token (`human-empty` ×12, `infra-empty` ×1); zero
non-HUMAN items come from an unrecognised-token artifact. A placeholder's own items are
unmarked prose, so `_classify_finding` already returns HUMAN for them and
`autoiterate.eligible` already refuses — the label was prose, not protection. That is
asserted, not assumed, at `template/tests/test_attempt_harvest.py:480`.

The one thing the fallback was genuinely guarding — a status added in `leaves` with no label
in `assemble`, this brief's own twin-blindness shape one module over — is guarded where it
belongs, in a test: `test_attempt_harvest.py:441`.

### 2. `leaves.py` — ownership settled by identity, not by digest

**Finding (round 3):** `_live_attempt_overwrote_it` was digest-only, and destroyed a LIVE
verdict in two measured shapes — (a) an unreadable residue set `_unreadable` permanently, so
an attempt that wrote its review atomically was refused; (b) content equality cannot
distinguish "nobody rewrote it" from "rewritten byte-identically".

**What I did.** `_residue_identity` (`leaves.py:1058-1075`) returns
`(st_dev, st_ino, st_size, st_mtime_ns, st_ctime_ns)`. `withdraw` records it for every
residue it could not withdraw (`leaves.py:916`, `:925`, via `_disown` `:994-1009`), in a
`dict[identity, _Residue]` (`leaves.py:855`, `_Residue` at `:795-806`).
`_live_attempt_took_the_path` (`leaves.py:933-966`) then refuses only when the file at the
path is *the same file, unchanged*: identity in `_residues` **and** its digest still equal.

- (a) closes because a `stat` succeeds on a file this process cannot `open` — the residue's
  identity is knowable when its bytes are not. `_unreadable` is gone; the only permanently
  un-settleable case left is a residue that could not even be `stat`-ed (`_unidentified`,
  `leaves.py:856`, `:1006-1007`), which is documented at `:952-954`.
- (b) closes because any write moves `st_mtime_ns` and an `os.replace` moves `st_ino`.
- The digest is **kept**, as the second chance in the other direction: same identity carrying
  different bytes (a filesystem whose timestamp granularity did not move — ext3's 1 s, HFS+)
  is still a rewrite (`leaves.py:965-966`). Residual: a rewrite that is byte-identical *and*
  lands in the same `st_mtime_ns` tick is refused — and its content is identical to the
  residue's, so what the operator loses is the placeholder-vs-verdict framing, not text.

Refusal remains the safe direction throughout: `_live_attempt_took_the_path` returns False
whenever it cannot settle, so criterion 1 is never traded away for criterion 3.

### 3. `leaves.py` — a residue is accounted for once, not once per attempt

**Finding (round 3):** with the same un-removable residue on the path, `withdraw()` re-read,
re-digested and re-quoted it for attempts 2 and 3, each time as *that* attempt's work.
Measured against v2's code: `3 != 1` occurrences of the dead attempt's mark.

**What I did.** `withdraw` now `stat`s **before** it reads (`leaves.py:898-907`). A file whose
identity is already in `_residues` returns `_unchanged(...)` (`leaves.py:1015-1020`) — one
line naming the attempt that actually left it — and is neither re-read nor re-digested nor
re-unlinked. So the read+sha256 of a large residue is paid once per *distinct* file, not once
per attempt, and no attempt is credited with a file it never wrote.

## Ruled out

- **A second heuristic for the unknown token** (line position, fence tracking, "does it look
  like a placeholder"): every variant has a false-positive shape, and a false positive here
  is a regression against base that strips `[impl]` routing from real findings. Numbers above.
- **Retrying the failed `unlink` on a repeat residue.** It would occasionally clean the path,
  but the outcome is already correct without it (refuse, or harvest what was written since),
  and it would make `withdraw`'s "already accounted for" branch do I/O again — the exact cost
  item 3 is about. ~4 lines saved, no behaviour change.
- **Unlinking a residue that could not be READ** (`leaves.py:912-917`): that destroys a dead
  attempt's text while producing no account of it — criterion 2 inverted. It is left on the
  path and the path is disowned; `test_attempt_harvest.py:360` pins that.
- **Narrowing the retry contract** on an un-withdrawable residue: explicitly decided in the
  brief (criterion 5) and unchanged from v2 — `withdraw` never raises and never breaks the
  loop; `test_attempt_harvest.py:393` asserts `_runs() == 3`, the mechanical check
  `test_leaf_resilience.py:62` uses.
- **Touching `leaves.py:3422` / `size_signal.py:240`** (the other `leaf_status()` readers):
  both are truthiness tests, so the new `unowned-empty` marker is already read as "a
  placeholder — nothing reviewed the diff", which is correct. Identical before and after this
  diff; the round-3 carry-forward names them as an Act candidate, not this child's.

## Verification — red→green through the project's own runner

`./engine/scripts/run-verify.sh` (the registered C4 gate), `PDCA_BUNDLE` + `PDCA_WORKTREE`
set:

```
== C4 green leg: bundle test(s) with the fix applied: template/tests/test_attempt_harvest.py
Ran 17 tests in 1.313s
OK
== C4 red leg: bundle test(s) with the production change reverted
Ran 17 tests in 1.236s
FAILED (failures=9, errors=4)
PDCA-EVIDENCE: C4 PASS — red without the fix, green with it
```

Also green: `./engine/scripts/run-suite.sh` → `root suite OK, driver suite OK` (1820 tests,
2 skipped); `./engine/scripts/run-docs-check.sh` → docs lint + link audit clean;
`PDCA_PROD_PACKAGE=pdca_harness ./engine/scripts/run-prod-path.py` → *"1 added driver-suite
test(s) import the production package `pdca_harness`"*. `git apply --check` of `patch.diff`
on a clean `480fa6b` tree: applies clean. The target repo configures no Python
formatter/linter (no pre-commit config, no ruff/flake8; CI runs only the docs lint, which is
green); added lines stay within the files' existing width (max 96, files already carry 110).

### The four round-3 guards bind against the code they were written for

The three regression guards for items 1 and 2 **cannot** go red against base — base has no
harvest owner at all, so it files the live artifact and passes them. They bind against
**iteration-v2's production code**, which is what the carry-forward is about. Measured by
swapping v2's production hunks in under this round's test file:

```
FAIL: test_a_live_verdict_identical_to_the_residue_is_still_filed
      AssertionError: "# Advisory review — NOT COMPLETED…" != "| Correctness | PASS | DEAD-…"
FAIL: test_a_live_verdict_replacing_an_unreadable_residue_is_still_filed  (×3 sites)
FAIL: test_an_artifact_that_quotes_an_unknown_status_early_keeps_its_findings
      AssertionError: 'human' != 'impl'
FAIL: test_an_unwithdrawable_residue_is_accounted_for_once_not_once_per_attempt
      AssertionError: 3 != 1
Ran 17 tests — FAILED (failures=6)
```

Item 3's leg is red against **both** v2 (`3 != 1`) and base (`0 != 1`, in the C4 red leg).

## Forced self-refutation

**(a) Genuine red?** Yes — not asserted, executed. `run-verify.sh` reverts the production
hunks (`git apply -R --exclude=tests/*`) and re-runs: 9 failures + 4 errors over 17 tests,
with `LOAD_FAILED=0` (the module imports fine on the red leg — it touches only pre-existing
API at module level, per the brief's C4 import trap). Red legs cover criterion 1 at all three
sites, criterion 2, criterion 4, criterion 5 and criterion 6.

**(b) Production path?** Yes. Every leg calls `leaves._run_review_sandboxed`,
`leaves._run_advisory_sandboxed` or `leaves._run_plan_advisory_sandboxed` — the real site
entry points — so the real `_invoke` spawn, the real retry loop, the real sandbox, the real
`_LeafHarvest` and the real `_review_unavailable` / `_advisory_unavailable` /
`_plan_advisory_unavailable` placeholders all run, and the assertions read files out of a
real bundle dir. Nothing is re-implemented in the test: the only stubs are the *leaf* (a
Python interpreter — the same harness `test_leaf_resilience.py:26-35` uses) and
`leaves.time.sleep` (backoff only; attempt count and the transient rule are the shipped
ones). The registered C5 gate independently confirms the added test imports
`pdca_harness`. `test_all_three_sites_go_through_the_one_owner` (`:407`) proves criterion 6
by *driving* all three sites through a recording subclass of the production class, not by
reading the source.

**(c) Fixture includes the fault?** Yes, and the fault is injected by the stub, not simulated
by the test. The dying attempt really writes a truncated verdict into the sandbox and really
dies (exit 1, stderr only, no stdout → the production transient signal); `PDCA_TEST_LOCK`
really `chmod`s the sandbox to `0o500` so `unlink()` really returns EACCES; `PDCA_TEST_UNREADABLE`
really `chmod`s the artifact to `0o000` so the read really fails. Neither is curated out:
`test_an_unreadable_residue_is_refused_when_nothing_replaced_it` (`:360`) asserts the error
log actually says *"could not be read"*, and
`test_a_residue_that_cannot_be_withdrawn_is_refused_at_every_site` (`:376`) asserts the
refusal that only the failed-unlink branch produces. The strongest evidence is the v2 run
above: those legs come back with a `NOT COMPLETED` placeholder, which is reachable **only**
through the `_unowned` branch — so the unlink and the read genuinely failed in the fixture.

## Known limits (not defects against the brief; flagged for the human, not worked around)

- The refusal is right-but-blunt in two unsettleable cases: a residue that cannot be `stat`-ed
  at all, and a path that cannot be examined at harvest time. Both refuse and file the
  `unowned-empty` placeholder whose §6 row tells the operator to read the error log and re-run.
- A byte-identical rewrite landing inside one `st_mtime_ns` tick on the same inode is refused;
  the text at stake is identical to the residue already quoted in the error log.
- The residue quote is bounded per residue (100 head + 100 tail lines, each read capped at
  1000 B ⇒ ≤ ~200 KB), not per run: three *distinct* un-withdrawable residues can still put
  ~600 KB in one log. The round-3 carry-forward explicitly rules that out of scope, and item
  3 removes the repeat-quoting that made the total grow with attempts rather than with
  distinct files.

No external dependency beyond the base toolchain was needed: every leg is driven by a stub
"leaf" that is `sys.executable`.
