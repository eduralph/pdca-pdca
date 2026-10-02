# Code review (advisory) — issue 409 / autoiterate-budgets-defer-ledger, round 4

Scope: correctness bugs this patch introduces, plus reuse/simplification. All gates in
check-gates.json pass (C4 is red before the fix and green after, per gate-logs/C4-verify.log;
T4 is deferred to publish). The three iteration-3 carry-forward fixes are in and tested: the
tick reader uses the last §6 heading (`test_a_section6_quoted_by_a_leaf_is_not_the_humans`,
`test_a_quoted_tick_retires_nothing_on_an_auto_iterate_round`); a tick equal to a fresh
rendered row never retires a ledger entry (`test_a_tick_on_a_fresh_finding_never_retires_a_deferred_one`,
three repro pairs plus the driver wiring test); and `_same_finding` checks equality after
stripping shared labels, before the floor (template/src/pdca_harness/autoiterate.py:177-181).
I found no new correctness bug in the retirement logic, the ledger read/write, or the
`eligible()` / `write_decision` ordering.

## Findings

- NEEDS-HUMAN — template/src/pdca_harness/signoff.py:102 (`open_needs_human`, default `last=False`)
  and template/src/pdca_harness/flow.py:262 (`accept_blockers`). The patch finds and
  documents a problem: a leaf can quote a `## 6. NEEDS-HUMAN` heading into §5, above the
  real §6 (signoff.py `cleared_needs_human` docstring, :128). The patch fixes only the
  retirement readers. The C6 accept guard still reads the FIRST §6 heading. So an artifact
  that quotes an empty or all-ticked §6 block makes `accept_blockers` report no open rows,
  while the real §6 below still has open ones. That is fail-open on accept. Your own test
  `test_a_section6_quoted_by_a_leaf_is_not_the_humans` (template/tests/test_autoiterate.py:1116-1118)
  builds exactly this SUMMARY shape. The first-heading read existed before this patch.
  But the patch now routes every accept path through `accept_blockers` (cli.py:1450,
  flow.py:176), and it states in code that the first heading can belong to a leaf. The
  human should decide whether to fix C6 here or in a follow-up issue. The fix is not just
  `last=True` in one place: `ensure_needs_human_item` (next bullet) must read the same
  section as the C6 check, or an added row becomes invisible to it.
- template/src/pdca_harness/signoff.py:170 (`ensure_needs_human_item`) writes the
  unreadable-ledger row into the FIRST §6 heading. When a leaf quoted a §6 block, the row
  lands inside the quoted adversary text in §5, not in the real §6. It still blocks accept,
  because C6 reads the same first block. So this is consistent, but the human will find
  the row in the wrong place. The dedup check at :174-178 also misses the copy assembly
  already put in the real §6 (assemble.py `_deferred_needs_human`), so the row shows up
  twice. This should be fixed together with the item above, not alone.
- template/src/pdca_harness/assemble.py:463,466 (`_deferred_needs_human`) re-implements
  `autoiterate._norm` inline (`" ".join(t.split()).casefold()`), even though it already
  imports `autoiterate` locally two lines earlier. signoff.py:174-178 does the same with
  `autoiterate._row_text` / `_BOXES`. Assembly's dedup and `retire_cleared`'s `rnorm` dedup
  (autoiterate.py:376-381) must agree, or a fresh copy of an entry renders twice and its
  tick becomes a two-hit, fail-closed match. Calling `autoiterate._norm` in assemble keeps
  the two in step. signoff cannot import autoiterate (that would create an import cycle),
  so there the inline copy is acceptable. Low priority; no behaviour change today.
- template/src/pdca_harness/autoiterate.py:291-294 (`_write_ledger`): if `tmp.write_text`
  raises partway through (for example, a full disk), the `.deferred-findings.json.<pid>.tmp`
  file stays in the bundle. It is harmless: nothing globs it, and `DOWNSTREAM_GLOBS` does
  not match it. A `try/finally` that unlinks the temp file on failure would tidy this up.
  Cosmetic.

No other findings. The CLI accept path is safe on a SUMMARY with no §6. `accept_blockers`
cannot add the row there, but `signoff.record` then refuses the SUMMARY (signoff.py:223,
:241-246), so an accept is never recorded.
