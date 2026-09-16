# Adversarial review — refutation pass (#506 / issue_536)

Evidence re-run locally at `$PDCA_TARGET`: green leg `PYTHONPATH=src python3 -m unittest
tests.test_attempt_ownership` → 31 tests OK; red leg (production hunks reverted with
`git checkout -- template/src/pdca_harness/`, the new test file kept) → 23 failures + 4
errors, every one behavioural — no module-level import fault, so the red leg cannot have
been the `PDCA-UNVERIFIABLE` route in disguise. Full `template` suite: 1789 tests OK,
`test_leaf_resilience.py` untouched. The C4 row is sound; the findings below attack the
fix, not the proof.

## Findings

- **NEEDS-HUMAN [impl] — `template/src/pdca_harness/assemble.py:85`, newly reached via
  `leaves.py:2940` (`_empty_run_class`) from `leaves.py:2892-2893`: the §6 line the human
  actually reads now files a false account of the run.** The patch is careful to widen the
  *placeholder* sentence (`leaves.py:2984-2996`: "the retries were spent, or one came back
  alive and yielded nothing") on the express grounds that "a slice whose invariant is that
  the harness never files a false account of a run cannot make an exception for the sentence
  the operator actually reads" — then stops one reader short. `_empty_run_class` newly routes
  `LEAF_STATUS_INFRA` for a run whose **last attempt ran to completion and exited 0**, and
  `assemble._LEAF_STATUS_LABEL[LEAF_STATUS_INFRA]` renders that as **"leaf did not run
  (transient infra — safe to re-run)"**. Reproduced against the patched tree: reviewer
  attempt 1 dies with `overloaded_error 529`, attempt 2 exits 0 writing nothing →
  `check-review.md` carries `<!-- pdca:leaf-status infra-empty -->` and
  `assemble.collect_needs_human` emits
  `leaf did not run (transient infra — safe to re-run) — re-run the Check reviewer…`.
  Before this patch `infra-empty` was reachable only through `_failure_class(err)`, where
  "leaf did not run" was true; the diff created the new reachability and neither the label
  (`assemble.py:85`) nor its comment (`assemble.py:80`, "ran, died with no output") followed
  it. Builder-fixable by iterating — widen the label exactly as the placeholder sentence was
  widened.

- **NEEDS-HUMAN [impl] — `template/src/pdca_harness/leaves.py:1033-1034`: the residue record
  asserts "withdrawn" as fact, and on the fail-closed path this patch itself adds, the
  bundle's only durable copy of that claim is false.** `_residue_record` is composed *before*
  `_withdraw_residue` runs (`leaves.py:762-767` — and that ordering is right), so when the
  unlink is refused the archived `check-review.error.log` reads
  `----- attempt 1 — the check-review.md it left behind (withdrawn: a dead attempt's
  artifact is never harvested) -----` over a file still sitting in the sandbox — the very
  condition that ended the run. Reproduced against the patched tree with `Path.unlink`
  refusing `check-review.md`: the correction ("could not withdraw … stopping the retries")
  exists only on **stderr**, i.e. terminal scrollback, which `leaves.py:647` is on record
  saying the error log exists to replace. The branch already re-flushes the records
  (`leaves.py:768-769`), so the hook to correct the wording is in hand; on the
  `may_retry is False` variant (last attempt, or a non-transient death) there is no re-flush
  at all and the same false line is filed unamended. Same defect class the patch condemns two
  hundred lines away.

- **NEEDS-HUMAN — `template/src/pdca_harness/leaves.py:773` narrows the shipped resilience
  contract, and the comment defending it is worded so as not to say so.**
  `if not (may_retry and recorded and owned): break` adds two stop conditions to
  `_invoke_leaf_resilient`; `leaves.py:770-772` claims "Neither widens the retry set" — true,
  and beside the point: they **narrow** it, while brief criterion (vi) asks that "the shipped
  resilience contract holds unchanged (attempt count, backoff, …)". Measured on both legs:
  with `Path.write_text` refusing the bundle log the base spends its full 3 attempts and the
  patch stops after 1 (`template/tests/test_attempt_ownership.py:264`); with `Path.unlink`
  refusing the sandbox artifact the base runs 2 and the patch runs 1
  (`test_attempt_ownership.py:497`; the red-leg log records `2 != 1`). So a recoverable
  rate-limit blip that coincides with a bundle write/unlink refusal now ends as "reviewer
  leaf failed" with **no review of the diff** — the outcome direction this slice exists to
  prevent. There is a fail-closed design that costs no attempts: carry `owned=False` forward
  and refuse to *harvest* that path on the success branch (the residue is already quoted by
  then) rather than ending the run. Whether to trade retries for ownership is an
  architectural / fitness call, not a builder nit — hence no `[impl]`.

- `template/src/pdca_harness/leaves.py:825-828` — minor, recorded rather than raised: the
  `.tmp.<pid>` sibling a kill can strand is correctly *not* claimed by
  `state.DOWNSTREAM_GLOBS` (`state.py:127`), exactly as the docstring says — but the same
  fact means `driver._archive_iteration` (`driver.py:436`) will never move it either, so a
  stranded temp lingers in the bundle root across every later round. Inert, and only
  reachable after a kill mid-write; noted so a later reader does not mistake it for evidence.

## Attempted and could not refute

- **Forging the in-flight trailer.** Tried both quoted channels (`_format_leaf_attempt`'s
  stderr tail, `_residue_record`'s artifact text) and the classic single-pass-`str.replace`
  re-formation attack (`"<!-- pd" + MARKER + "ca:leaf-attempt …"`, plus the nested variant):
  `_defang_in_flight` (`leaves.py:793-801`) cannot re-create the marker — the quoted
  replacement contains it nowhere and shares no suffix/prefix overlap with it. Combined with
  the whole-line, last-non-blank match at `leaves.py:922-923` (which survives `strip()`-
  equivalent payloads: trailing `\r`, NBSP), I could not make a leaf speak for the harness's
  own run.
- **Weakening the accept guard through the new `infra-empty` route.** `_items_from_artifact`
  forces both `infra-empty` and `human-empty` to `HUMAN` (`assemble.py:168-173`), so the
  reclassification changes §6 *wording* (finding 1) but cannot let a bundle auto-iterate or
  reach accept where it previously could not.
- **A fourth reader of the discriminator.** Grepped the package: the only readers of
  `*.error.log`-as-state are the three the patch updated (`leaves.py:2456`, `leaves.py:3202`,
  `assemble.py:425`). The plan-advisory path has no `only_missing` resume, and `docs/` states
  the discriminator nowhere, so no prose was left stale by the semantic change.
- **Sandbox-input collision for `artifact=`.** All three sites checked: `REVIEWER_INPUTS`
  (`leaves.py:68`) and `PLAN_ADVISORY_INPUTS` (`leaves.py:3293`) never seed a file at the path
  passed as `artifact=`, so `_withdraw_residue` cannot unlink a seeded input a later attempt
  needed, and the withdrawn path is always sandbox-local — never the bundle's shipped
  artifact from a prior round.
- **A raise-after-success in `_invoke`.** `_invoke` (`leaves.py:566-668`) raises only on
  `rc != 0`, so no live attempt's artifact can be reclassified as a dead attempt's residue;
  the interactive and stream-less branches reach the wrapper's success path with `records`
  empty and behave byte-identically to the base.
- **Runaway re-run of a recovered leaf.** An in-flight log makes `review_never_ran` true, but
  the recovered run's entry-time clear (`leaves.py:720`) removes it and every terminating
  branch files a placeholder first, so I could not construct a bundle that re-pays for the
  same leaf on successive `advance`s.
