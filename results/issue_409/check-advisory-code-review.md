# Advisory code review — issue 409 (iteration 5)

Scope: correctness bugs this patch introduces, plus reuse / simplification. Gates are green
(C4 red→green, 101 tests failing pre-fix and passing post-fix; T3 suite OK). I found no
blocking correctness defect. The three carry-forward items from iteration 4 are in place:
C6 and the row writer both read the last §6 heading, a fresh row protects nothing, and
no-verdict rows are not deferred. Each item has a test that drives production code. Below
are the smaller things worth knowing; none of them needs to stop an accept.

- template/src/pdca_harness/driver.py:334 — `_retire_cleared_deferrals` rebuilds the "fresh"
  row list by re-running `assemble.collect_needs_human` at the iterate transition, not by
  reading what assembly rendered. Anything that `collect_needs_human` reads and that can
  change between assembly and sign-off will shift that list. The clearest case is the
  unregistered-dependency row: `pdca.toml` is re-read live and can change mid-cycle
  (assemble.py:765-767 says so). If the human fixes `pdca.toml` and ticks that row, the
  tick then matches no rendered row exactly, so `retire_cleared` (autoiterate.py:419-423)
  treats it as an edit and fuzzy-matches it against the ledger. A wrong retirement needs a
  ledger entry that `_same_finding` accepts, so this is unlikely. Still, it fails in the
  open direction. A sturdier fix would record the rendered row list at assembly, for
  example in a sidecar next to the ledger, and read that back at retire time. Low priority.
- template/src/pdca_harness/signoff.py:191-197 — `ensure_needs_human_item`
  hand-copies the checkbox-strip and normalise logic that `autoiterate._row_text` / `_norm`
  (autoiterate.py:120-131) already define. Separately, `assemble._deferred_needs_human`
  (assemble.py:505-508) calls the private `autoiterate._norm` through a local import. Both
  copies must stay identical: the `_deferred_needs_human` docstring says that if the dedup
  and retire normalisation differ, a tick matches two rows and retires nothing. Moving
  `_norm` / `_row_text` into `signoff` would leave one definition and drop the cross-module
  private access. `autoiterate` already imports `signoff`, and `assemble` can import it
  without a cycle. This is a cleanup only; today the behaviour matches.
- template/src/pdca_harness/autoiterate.py:290 — `_write_ledger` leaves a stray
  `.deferred-findings.json.<pid>.tmp` in the bundle when `write_text` fails partway (disk
  full, permissions). The live ledger stays intact, so this is only litter. A
  `try/except: tmp.unlink(missing_ok=True); raise` around the write would tidy it.
- template/src/pdca_harness/flow.py:378 (`_maybe_auto_iterate`) — the
  stderr notice counts `rerun` over the raw `items`, while `held` uses the deduplicated
  `deferrable(items)`. The same no-verdict row raised twice is counted twice. This only
  affects the message.

No NEEDS-HUMAN items from this lens.
