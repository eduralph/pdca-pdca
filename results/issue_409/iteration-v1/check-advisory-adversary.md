# Adversarial review — issue 409 / autoiterate-budgets-defer-ledger

The red→green evidence holds. The fix has one real fail-open path in the new retirement code, plus one untested rule. Every case below was run against the production modules at `$PDCA_TARGET` (scratch copies in this sandbox, not the target).

## Refutations

- NEEDS-HUMAN — **A §6 heading quoted in §5 retires a ledger entry the human never ticked.** The brief picked `whole_on_missing=False` for the tick reader so that "a `- [x]` quoted in §5 review text … must never retire a ledger entry". The patch covers only the case where the SUMMARY has no §6 heading at all. `signoff.cleared_needs_human` (template/src/pdca_harness/signoff.py:123-136) and `open_needs_human` both go through `_section`, which takes the FIRST `## 6. NEEDS-HUMAN` heading (signoff.py:310-313). `assemble` pastes review and advisory text verbatim into §5, above the real §6 (template/src/pdca_harness/assemble.py:399-400).
  - **Repro:** the ledger holds `[E]`. An advisory writes a fenced example block containing `## 6. NEEDS-HUMAN — items the human must clear before sign-off` and `- [x] E`. The real §6 renders `- [ ] E`. The human records `iterate-do` with nothing ticked, then `driver.advance` runs.
  - **Result:** the ledger becomes `[]`. `retire_cleared` (template/src/pdca_harness/autoiterate.py:303-316) reads the tick from the fake section and cannot see the real open row that would protect E.
  - **Existing hole, not from this diff:** the same bundle's C6 read (the check that blocks accept while §6 rows are open) returned `[]` open rows even with a red gate. The fix belongs in the shared `_section` reader, for example skipping headings inside code fences, or requiring the §6 heading to come after §5. That is a scope call, because C6 uses the same reader.

- NEEDS-HUMAN — **A fresh near-twin row shields an exactly-ticked ledger entry.** The brief says a verbatim open row protects only its own entry, "a near-twin cannot shield its exactly-ticked neighbour". The code at template/src/pdca_harness/autoiterate.py:306-309 treats ANY open row that matches no ledger entry verbatim as an "edited" row. That includes an unedited finding this Check raised fresh.
  - **Repro:** the ledger holds `[P = "C5 Causal adequacy — guards the symptom in the parser"]`. This round's reviewer raises `R = "…in the renderer"`. §6 shows `- [x] P` and `- [ ] R`. The human records `iterate-do`.
  - **Result:** after `driver.advance` the ledger is still `[P]`, so P comes back unticked next round.
  - **Severity:** this fails closed. Nothing is lost; the human just re-ticks P.
  - **Test gap:** the tests only pair twins that are both in the ledger (template/tests/test_autoiterate.py:956-958, :981-986).
  - **Decision needed:** should a verbatim fresh row count as owning itself (protecting nothing), or stay fail-closed as now?

- NEEDS-HUMAN [impl] — **The "more than one fuzzy hit fails closed" rule is untested.** Changing `len(hits) == 1` to `hits` at template/src/pdca_harness/autoiterate.py:316 (retire the first hit) passes all 141 tests in `test_autoiterate` + `test_size_signal`. The rule does matter:
  - **Case:** the ledger holds `[P, R]` as above. The human deletes P's row and edits R's row to `…in the UI layer`, then ticks it.
  - **Current code:** keeps both, which is correct.
  - **Mutated code:** retires P, the one the human did not tick.
  - **Fix:** add this case to `RetiresOnlyWhatTheHumanTicked`.

- NEEDS-HUMAN — **"Loss-proof" does not hold against a leaf, and the patch now tells the builder the file name.** The builder can write the bundle directory (template/src/pdca_harness/leaves.py:2517 grants `d`). The new carry-forward line in the brief the builder reads says the findings are "held in deferred-findings.json" (template/src/pdca_harness/autoiterate.py:339-342).
  - **Effect:** deleting the file reads as "nothing deferred" (autoiterate.py:204), and so does emptying it to `{"items": []}`. Either way every deferred finding silently drops out of the handover §6, and C6 passes. The only remaining copies are in the archived `iteration-v*/SUMMARY.md` files.
  - `auto-iterate.json` has the same exposure (pre-existing). The ledger differs because it is now the only live copy of those findings.
  - **Options:** a cheap partial fix is to stop naming the file in builder-facing text. The real decision is whether bundle files the driver trusts need protection from leaves.

## Tried to refute, could not

- **C4 red→green.** Re-ran the green leg: 141 tests OK. The frozen red leg (gate-logs/C4-verify.log) fails for the right reasons; for example, `TwoStops` fails with "0 != 3" because today's veto declines the round.
  - Many retirement tests go red only through `AttributeError` on a precondition line, so I mutation-tested the discriminating assertions instead. Each of these variants turns at least one test red:
    - the two wrong protection shapes the brief names (symmetric-fuzzy and exact-only);
    - a lenient tick reader;
    - a naive `any(IMPL)` eligibility check;
    - dropping the retire call in the iterate-plan branch, or moving it after the archive;
    - removing `_hold_unreadable_ledger`;
    - deferring after `bump`;
    - no dedup when rendering;
    - filtering out non-string ledger entries;
    - recording STANDING items in the ledger.
  - So tests (a)–(d) and clause 4 discriminate as the brief requires.
- **The C5 row "pass" is vacuous.** The gate log says "patch adds no new test file — nothing to assert", so it proves nothing on its own. It is not a real problem: the tests drive `flow._maybe_auto_iterate`, `driver.advance` and `assemble.assemble_summary`, and mutating production code turns them red.
- **Also tried, could not break:**
  - the size-by-kind stop;
  - the hard cap with `rounds = 0`;
  - an unreadable ledger at accept on the shared `_apply_decision` path;
  - a ledger write failure (it happens before `bump`, so no round is spent);
  - render dedup between ledger entries and fresh findings.
- **Sandbox note:** `test_the_calibrator_uses_THIS_definition` errors in my copies only because `scripts/size-calibrate` was not copied into the sandbox. It is an environment artifact, not a finding.
