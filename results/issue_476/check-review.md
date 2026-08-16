Task under review: correct the lineage-reader documentation so its abstention and non-numeric-depth behavior match the existing reader, arithmetic, and merge paths.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The required contract is unambiguous and internally consistent: reader rejection, depth fallback, and verbatim merge behavior are distinct decisions grounded at `template/src/pdca_harness/split.py:606`, `template/src/pdca_harness/split.py:628`, and `template/src/pdca_harness/split.py:652`. |
| C2 Reproduction (red pre-fix) | PASS | With the patch stashed, `docs/07-crosscutting.md:278` falsely included non-numeric `depth` among `None` outcomes, while the unchanged regression at `template/tests/test_split_lineage.py:236` passed and demonstrated record return plus depth-1 fallback. |
| C3 Change | PASS | The corrected paragraph now covers read/parse, object shape, version, arithmetic fallback, and separate merge preservation without changing any other file (`docs/07-crosscutting.md:278`). |
| C4 Verification (red→green) | NEEDS-HUMAN | The human must decide whether the semantic prose red→green accurately states the runtime contract — this docs-only patch has no executable failing leg, and C4 correctly reported `PDCA-UNVERIFIABLE` while the relevant lineage tests passed (`docs/07-crosscutting.md:278`). |
| C5 Causal adequacy | PASS | Correcting the normative statement removes the source of false implementation findings directly; no capability probe or runtime guard masks the cause (`docs/07-crosscutting.md:278`). |
| T1 Structure | PASS | Keeping the correction in the existing lineage paragraph preserves the document hierarchy and the intended separation from production code (`docs/07-crosscutting.md:277`). |
| T2 Shape | PASS | Independent patched-tree reruns of the Obsidian lint and site-render/internal-link audit were clean, so the expanded prose retains publishable document shape (`docs/07-crosscutting.md:278`). |
| T3 Runtime | PASS | The 23-test lineage module passed before and after reapplication, including non-object rejection and non-numeric-depth behavior, and the frozen full-suite log reports both suites clean (`template/tests/test_split_lineage.py:236`). |
| T4 Contribution | N/A | Contribution artifacts are intentionally not drafted during Check; the deferred gate records that their substantive audit is mandatory at publish. |
| T5 Judgment | PASS | Affected-path history and all PR states were queried: prior edits were merged and no open or closed-unmerged attempt touched this file, while the final wording agrees with the implementation (`docs/07-crosscutting.md:278`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | The human must decide whether this normative wording is sufficiently clear to prevent future false review findings — automated checks establish syntax, links, and existing behavior, not reader interpretation (`docs/07-crosscutting.md:278`). |
