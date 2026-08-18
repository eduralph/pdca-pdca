# Brief (pointer) — issue 506 / decomposed-into-two-shippable-outcomes

> The Plan artifact for a bundle that is **decomposed, not built**. The plan lives in this
> bundle's own host artifact — `split-proposal.md`, the two child briefs it carries — and
> this file points at it and holds the fields the driver parses. There is no patch to build
> here: the work ships as the children.

- **Slug:** decomposed-into-two-shippable-outcomes
- **Planning artifact:** `results/issue_506/split-proposal.md` — the accepted split proposal.
  It carries the full brief for each child verbatim (they are materialised from it), the
  seam analysis, and the wave/merge reasoning. Authoritative; this file does not restate it.
- **Defect:** Issue 506 reports one incident — an escalated builder ran ~18 minutes, the API
  connection dropped mid-response, the attempt was burned and `build.error.log` recorded only
  `(no output captured)` — but names **three** weaknesses that live in two layers meeting
  only at `LeafError`: the stream reader never reads or retains the CLI's own terminal error
  report and classifies "transient" by the proxy *did the child produce any event*
  (`template/src/pdca_harness/progress.py:147-158`, `:255`, `:365-377`); and the
  leaf-invocation layer never puts the builder on the resilient path at all
  (`leaves.py:1824` vs `:2507` / `:2840` / `:3142`), reports an exhausted death as an argv
  plus an exit status, and harvests artifacts without asking which attempt wrote them
  (`:2519-2523`, `:2851-2854`, `:3152-3155`). Built as ONE slice it reached 92,086 bytes
  against an 80 KB backstop over four rounds, each round's mechanism independently confirmed
  and each round's findings implementation-shaped — the signature of a slice too large to
  converge. The iteration-4 sign-off rejected it on **slicing, not mechanism**
  (`iteration-v4/SUMMARY.md` §9) and directed the split into this beat.
- **Success criterion:** This bundle ships **no patch**. It is discharged when issue 506 is
  decomposed into children that are each one shippable outcome with its own red, filed as
  tracker sub-issues of 506 with a materialised bundle each, and the parent is marked
  `close-disposition = split` so the run drives the children instead of rebuilding the
  rejected slice. Observable: `results/issue_506/split-lineage.json` names both children;
  each child bundle holds an authored `brief.md`; both tracker issues exist as sub-issues of
  #506. The substantive criteria of #506 now live in the children — child-1 (i)-(vi),
  child-2 (i)-(iv) — and Check judges them there, one bundle at a time.
- **Falsifiability:** Not applicable in the red→green sense: there is no production change to
  revert, so C4 is `PDCA-UNVERIFIABLE` by construction (`engine/scripts/run-verify.sh:123`
  — no patch.diff) and the bundle takes the close fast path to sign-off, where the human
  confirms or overrides the decomposition. The decomposition itself is falsifiable by
  inspection: if either child cannot be made red on its own base, the seam is wrong and the
  proposal is what must change. Both were checked and can — child-1 through the stub leaf
  `template/tests/test_leaf_resilience.py:28-31` driving `leaves.do_build` (1 invocation
  today), child-2 through a stub emitting a work event then the CLI's marked terminal error
  (retried 0 times today, error log `(no output captured)`).
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Ordering note:** The two children are independent — neither needs the other to compile or
  to go red→green — so neither declares `Depends on` / `Conflicts with`: they land in one
  wave on `origin/main`, which is also what this instance's own issue-474 base-export leak
  makes preferable (`plan-0.60-bug-order.md`). They share `leaves.py` in disjoint regions and
  ship their tests in **different files** by construction, which is the one collision a same-
  wave pair would otherwise have had. Recommended **merge** order at publish (a human call,
  not a scheduling one): child-1 first, then child-2 — child-2 is what first makes a leaf
  retryable *after* it has produced work, and child-1 is what makes that safe.
- **Surfaces:** data
- **Difficulty:** low
- **Scope:** Decompose issue 506 into its two shippable outcomes and hand them to the run:
  author a complete brief per child, file each as a tracker sub-issue, materialise a bundle
  each, and mark this parent split. **Out of scope:** building any part of the fix here (the
  children own it); re-litigating the mechanism the four archived rounds established (it was
  endorsed — `iteration-v4/SUMMARY.md` §9 says KEEP ALL OF IT — and both child briefs carry
  it forward as requirements); a third child for the attempt-blind harvest (folded into
  child-1: same invariant, same file, and a third child costs a third full cycle).
- **Repro instruction:** `python3 -c` over this bundle: `iteration-v4/patch.diff` is 92,086
  bytes across 8 files against `pdca.toml`'s 80 KB backstop; `loop-telemetry.json` records 4
  attempts against a 3-round threshold; `iteration-v4/SUMMARY.md` §9 records the rejection
  and its reason. `results/issue_506/split-proposal.md` is the decomposition those artifacts
  ask for.
- **External dependencies:** none — decomposition is an authoring act; no build tool, service
  or topology is involved. The children each declare `none` too: every leg of both is driven
  by a stub "leaf" that is a Python interpreter, so both build and go red→green on the base
  toolchain with no vendor CLI, no API key and no network.
- **Test file:** none — a decomposed parent ships no patch and no test. The regressions ship
  in the children: `template/tests/test_leaf_resilience.py` + `template/tests/test_build_error_log.py`
  (child-1) and `template/tests/test_terminal_error_classification.py` + `template/tests/fixtures/`
  (child-2).
- **Citations expected:** none from Do — there is no Do here. The children require
  `path:line` on the target branch for every change, and both carry the archived attempt
  (`results/issue_506/iteration-v4/patch.diff`) as prior art they MAY read for decisions
  already settled, restricted to the files each child owns.
- **Prior-art check (triage cycles):** This bundle's own four archived iterations are the
  prior art: `iteration-v1`…`iteration-v4`, rejected on findings (rounds 1-3) and on slicing
  (round 4). No open PR on the target implements any part of it (`gh pr list -R
  eduralph/pdca-harness --state open` → #519-#525, none touching `progress.py`; #524/#520
  touch `leaves.py` at distant regions). Adjacent issues deliberately excluded from both
  children: #371 (gate-row transient), #510 (leaf signal-death), #509 (crash-resume).
- **Disposition hint:** likely-close

## STOP discipline

Draft only until Check sign-off. The human confirms the decomposition at sign-off; the
children are driven as their own cycles, each with its own Do, Check and PR.
