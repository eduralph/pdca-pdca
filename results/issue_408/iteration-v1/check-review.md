Review issue #408: route builder-fixable reviewer findings through bounded `[impl]` tags, recognize the supported Validation-row spellings, and align reviewer/advisory prompts.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The scope defines testable routing boundaries and exact label matching, with the advisory-policy trade explicitly reserved for sign-off; the taxonomy boundary is grounded at `target/template/src/pdca_harness/assemble.py:69`. |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing production/prompt changes while retaining the new tests produced 15 failures and 2 errors across 119 tests; substantive routing and label assertions fail, not merely imports (`review-red.log`; `target/template/tests/test_autoiterate.py:1855`). |
| C3 Change | FAIL | Two reproduced regressions violate the requested safety boundaries: normalized duplicate V rows evade ambiguity handling, and Basis-only tags can promote PASS rows; findings below (`target/template/src/pdca_harness/assemble.py:807`, `target/template/src/pdca_harness/assemble.py:814`). |
| C4 Verification (red→green) | PASS | Restoring the stashed fix made all 119 focused tests pass, independently confirming the frozen C4 result; this verifies the supplied cases, which omit both regressions below (`review-green.log`; `gate-logs/C4-verify.log:119`). |
| C5 Causal adequacy | PASS | The change addresses classification and label interpretation directly, without a capability probe or load-time symptom guard; tests call production classification and iteration paths (`target/template/tests/test_autoiterate.py:1848`, `target/template/tests/test_autoiterate.py:1865`). |
| T1 Structure | PASS | Promotion membership follows the canonical taxonomy, with explicit artifact-specific routing and one shared label normalizer; no unrelated subsystem change is required (`target/template/src/pdca_harness/assemble.py:69`, `target/template/src/pdca_harness/assemble.py:364`). |
| T2 Shape | PASS | Independent docs lint, 22-page rendering/internal-link audit, and `git diff --check` passed, consistent with both frozen docs gates (`gate-logs/T2-docs.log:10`; `gate-logs/host-ci-docs.log:10`). |
| T3 Runtime | PASS | Independent offline suite: 2,194 tests, OK with 2 skips; frozen evidence additionally shows all 24 root render/update tests passing, although local Python lacks Copier (`review-suite.log:1761`; `gate-logs/T3-suite.log:56`). |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; the substantive audit is deferred to the mandatory publish gate (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Accept or reject mandatory advisory routing choices and the role-prompt changes, and confirm affected-path merged/closed-work coverage — unbounded advisory tags can spend rebuild rounds, while this snapshot cannot independently establish prior art (`target/template/agents/adversary.md.jinja:60`; `target/template/agents/reviewer.md.jinja:114`; `brief.md:111`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the routing policy improves real reviewer handoffs without misrouting architectural concerns — deterministic parser/prompt tests do not establish the quality of model tagging (`target/template/agents/adversary.md.jinja:64`; `target/template/src/pdca_harness/assemble.py:337`). |

**Finding 1 — preserve duplicate detection before normalizing/deduplicating V rows (P2).** At `target/template/src/pdca_harness/assemble.py:807`, a bare Validation label and a `V —`-prefixed label become identical. If their Basis cells also match, `add()` drops the second row at line 772 before the ambiguity check at line 821. I appended a prefixed V row with the same Basis to a complete verdict table: the base preserved a HUMAN item alongside STANDING; the patch returns only STANDING. The brief expressly requires ambiguous duplicate V rows to lose their exemption. Count row occurrences before text deduplication and add coverage using identical Basis cells; the added test currently uses different Basis text.

**Finding 2 — read the tag from the actual Verdict column (P2).** At `target/template/src/pdca_harness/assemble.py:814`, `cells[vi]` is assumed to be the Verdict cell, but `vi` is the first cell anywhere containing `needs-human` (line 802). In a complete verdict table, `| C5 Causal adequacy | PASS | Quoted NEEDS-HUMAN [impl] from an old review |` therefore becomes IMPL, despite no routing instruction in its Verdict. The base already misread this as HUMAN; this patch newly promotes it to implementation work, potentially triggering unnecessary rebuilds. Use the Verdict column for both verdict recognition and tag extraction, and test this Basis-only quotation with a PASS verdict.

Both findings were executed against patched production code and the pre-fix source obtained only from this target's `HEAD`. Exact comparison output is in `review-edge-cases.log`. To reproduce the patched cases from this sandbox:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=target/template/src:target/template python3 - <<'PY'
from pdca_harness import assemble
from tests.test_autoiterate import _full_review
reviews = [
    _full_review() + "| V — Validation — fitness-to-purpose | NEEDS-HUMAN | fitness is the human's call |\n",
    _full_review({'C5': ('PASS', 'Quoted NEEDS-HUMAN [impl] from an old review')}),
]
for review in reviews:
    print(assemble._items_from_artifact(review, allow_standing=True))
PY
```

Evidence limits: the C5 scanner's frozen output says only “patch adds no new test file”; rerunning the available reference scanner likewise provides no substantive coverage of edits to existing tests. C5 above instead rests on production calls and the actual red→green run. The instance-scoped gate wrappers were not assumed to exist in the target; their frozen logs were read. Local root-suite execution exited 77 because Copier is not importable, but the frozen root log explicitly records successful render and update cases, so this is a reviewer-host caveat, not an unmet gate dependency or patch defect.

Prior art: the brief records merged-history queries by `assemble.py`/`leaves.py` and a closed-unmerged search covering several engine paths. It does not record equivalent coverage for both changed role bodies and the changed test file. My affected-path `git log --all` query finds only synthetic base commit `c0b3d98`; the disposable target has no remotes or closed-PR data. Consequently full prior-art coverage remains a human decision under T5. The available INTEGRATION file is an unfilled template, so the role-prompt human-only requirement is taken from the brief's explicit project-specific statement.

The target was readable and matched the patch. Production changes were restored after the red leg; no source fixes were made. This review is advisory and does not gate acceptance.
