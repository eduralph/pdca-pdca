# Advisory code review — issue 653 (carry-holds-when-branch-tip-is-not-the-judged-head)

I found no correctness bug that needs a human. The patch does what the brief asks. The notes below are small cleanups. None is tagged NEEDS-HUMAN.

## Correctness

- `template/src/pdca_harness/flow.py:860-863` — The new check reads the same ref the fold will merge. `ref` comes from `integrate._fold_candidates` → `_published_ref` (`template/src/pdca_harness/integrate.py:139-158`), and the fold resolves that same `ref` (`integrate.py:467-468`). It also runs in the checkout `carry_view` just fetched (`integrate.py:185-193`). Both values are full SHAs (`rev-parse --verify` and `gh`'s `headRefOid`), so `!=` compares like with like. A gone branch (`_rev` → None) skips the check and keeps today's `_gone_branch` path, as the brief says it should. The check comes after the MERGED-head-on-base check, so in test (1) the new branch is what fires, not the older "edge" reason. A held P is left out of `heads`, so `foreign_commit` (`flow.py:933`) never counts its extra commit as accounted for. No problem found.
- `template/src/pdca_harness/flow.py:960` — `hint.partition(":")` is safe for the existing hints (`open`, `edge`, `line` have no colon, so `head` becomes `""` and is unused). Every exception path that builds `why` (`flow.py:928, 931, 935-936, 948, 950`) uses plain hint keys, so nothing hits a `KeyError`.
- Tests (`template/tests/test_flow_resume_stack_prereqs.py:374-404`): both new tests are red without the production hunks and green with them (`gate-logs/C4-verify.log`: before the fix, `issue_D` was built on a line holding the carried P). `_lines_with` checks every non-`fix/*` branch on origin for the extra commit, which covers the "no line holds it" claim directly. `self.heads.get(iid) or …` in `_gh_stub` (`:101-102`) leaves every existing test on the old tip-as-head answer, so criterion (3) holds (T3 suite passes).

## Reuse / simplification

- `template/src/pdca_harness/flow.py:863` and `:960` — The judged head travels to the formatter packed into the hint string (`"tip:<sha>"`) and gets split back out with `partition`. That is a small hidden format inside a dict key. A simpler option: put the short head in the `reason` text, which already holds it (`... ({head[:12]})`), and word the `tip` hint without `{head}`. Or carry a third tuple field. It works as written, so this is optional.
- `template/src/pdca_harness/flow.py:873-874` — The hint reads "reset or delete {name}'s branch to {head}". "Delete … to {head}" does not parse. "reset {name}'s branch to {head} or delete it" says the same thing clearly. The test checks only for `reset`/`delete`/the short SHA, so rewording is safe. `docs/07-crosscutting.md:690` has the same wording.

## Scope

The new code adds one `git rev-parse` per finished prerequisite, which is negligible. It touches nothing outside what the brief scopes. The post-read/pre-fold race is left open, as the brief says it would be.
<!-- pdca:leaf-complete -->
