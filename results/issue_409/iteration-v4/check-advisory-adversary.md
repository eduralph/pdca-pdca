# Adversarial review — issue 409 (iteration 4)

I re-ran the tests and tried to break this round's three retirement fixes. All three hold. I found two gaps next to them, both of which fail safe. Both need a human decision, not a rebuild.

## Findings

- NEEDS-HUMAN — **The accept guard (C6) still reads the FIRST §6 heading, which the patch itself says can belong to a leaf.** See `template/src/pdca_harness/flow.py:233` (`accept_blockers` → `signoff.open_needs_human` with no `last`) and `template/src/pdca_harness/signoff.py:170` (`ensure_needs_human_item`, first heading). The patch's own docstring at `signoff.py:138-145` says the first `## 6. NEEDS-HUMAN` heading can be a block a leaf quoted into §5. It switched only the two retirement readers to the last heading.
  - Concrete case, run against the patched code: a SUMMARY whose §5 holds a quoted `## 6. NEEDS-HUMAN` block with only `- [x] something old`, and whose real §6 holds `- [ ] <deferred finding>`. `flow.accept_blockers(d)` returns `[]`, so the accept goes through. `open_needs_human(..., last=True)` on the same file correctly returns the open row.
  - Second case: with the ledger unreadable, `ensure_needs_human_item` writes the unreadable-ledger row into the quoted block inside §5, not the real §6. C6 still blocks, because it reads the same wrong block. But the human is refused over a row that isn't in the §6 they are looking at.
  - The first-heading C6 read was already there on `main` (base `_section` breaks on the first match). This diff makes it matter more: the brief's goal is that every deferred finding "still reaches the human under the C6 guard", and deferred findings no longer halt the loop before handover.
  - Both readers have to move together. Moving only `ensure_needs_human_item` to the last heading would make C6 miss the row, so it would fail open.
  - Changing which §6 C6 reads touches every accept, so the human should decide on scope.

- NEEDS-HUMAN — **An open fresh near-twin blocks the retirement of a deferred finding the human ticked exactly, and no test pins this either way.** See `template/src/pdca_harness/autoiterate.py:386-390`. The docstring at `:357-358` treats a fresh row left open as a possible edit, so it protects every ledger entry it fuzzy-matches.
  - Concrete case, run against the patched code: ledger `["the fix does not cover the retry path"]`, §6 `- [x] the fix does not cover the retry path` plus the fresh `- [ ] the fix does not cover the CLI path`, `fresh=[that CLI row]`. `retire_cleared` keeps the entry, so it comes back unticked next round.
  - This is the #335 symptom (an entry the human cleared keeps coming back), now across the ledger/fresh boundary. It contradicts the module's own rule at `autoiterate.py:107-110` ("A row equal to one assembly rendered is that row — never an edit of another"). It also contradicts the brief's clause 3: "a near-twin cannot shield its exactly-ticked neighbour".
  - `docs/07-crosscutting.md:458-465` lists when an entry survives a tick, but not this case.
  - It fails safe: the entry is shown again, never lost. Whether that nuisance is acceptable is a design call.
  - Either way the choice is not pinned. I changed the code so that an open row exactly equal to a fresh rendered row protects nothing in the ledger, and all 152 tests still pass. Whichever direction the human picks needs a test.

## Notes (no action needed)

- `test_a_quoted_tick_retires_nothing_on_an_auto_iterate_round` (`template/tests/test_autoiterate.py:1304`) still passes when the tick reader goes back to the first heading. The open-row protection saves the entry, so the test fails only if both readers go back. The unit test at `:1101` catches each reader going back on its own, so the fix is still covered.
- The C5 gate row in `check-gates.json` says `pass`, but its log says "patch adds no new test file — nothing to assert". The gate checked nothing. I confirmed the substance separately: the tests call `autoiterate.retire_cleared`, `driver.advance`, `flow._maybe_auto_iterate` and `cli`/`flow` accept paths directly, and the mutations below prove they exercise production code.

## Refutation attempts that failed

- **Red→green evidence:**
  - I re-ran `tests.test_autoiterate` and `tests.test_size_signal` on a copy of the patched tree: 152 tests, OK.
  - The C4 red leg (`gate-logs/C4-verify.log`) shows 25 failures and 36 errors. 34 of the errors are `AttributeError` on new symbols, which the brief allows. The assertion failures are on the old veto behaviour (`0 != 3` fired rounds, `False is not true` for defer).
  - `test_size_signal` passes on both legs. As the brief says, those are fixture updates, not a red leg.
- **Tests that would pass for the wrong reason:** I tried 17 separate changes to production code (mutations), and every one broke at least one test:
  - reverting the tick reader or the open-row reader to the first heading;
  - dropping the label-equality check before the length floor;
  - ignoring `fresh`;
  - letting a hit on a fresh row retire an entry;
  - fuzzy-matching only against the ledger;
  - removing the exact-first step;
  - making protection flat;
  - removing the ratio or the floor;
  - removing label stripping;
  - removing retirement from `driver.advance`;
  - putting back the CLI's own C6 check;
  - removing `ensure_needs_human_item` from `accept_blockers`;
  - turning off assembly dedup;
  - deferring STANDING rows.
- **Is the last §6 heading really the assembled one?** Yes:
  - The only thing after §6 is fixed text, the §9 fields, and §10 lines built by the harness (`assemble.py:419-440`).
  - §6 rows are single lines (`assemble.py:730-733`).
  - The flow flattens the §9 delta (`flow.py:181-182`). `pdca signoff --delta` is not flattened (`cli.py:1465`), but that text is the human's own.
- **Can `fresh` drift from what assembly rendered?** Both come from `collect_needs_human`, and nothing it reads changes between assembly and the iterate beat in normal use. Any failure while working out `fresh` is caught at `driver.py:336-340` and leaves the ledger as it was, so it fails closed.
- **Size-by-kind stop, hard cap, both accept paths sharing one guard, the unreadable ledger blocking auto-iterate before any budget is spent:** I could not break any of these.
