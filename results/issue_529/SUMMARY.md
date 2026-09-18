# Result — issue 529 / signoff-records-human-text-verbatim

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: `signoff.record` writes the human's §9 decision with a nested `set_field`
  (`template/src/pdca_harness/signoff.py:180-185`) that passes the value to `re.subn` as a
  **replacement template**: `repl = rf"\g<1> {value}"`. `re.sub` parses backslash escapes in a
  template, and the values are unsanitised human text: the `Iteration delta` is the sign-off
  rationale (`flow.py:182-185`, flattened from `signoff-decision`), and `By / date` is
  `f"{by} / {date}"` (`signoff.py:203`), with `by` from `--by` / `[project].author`. Three
  failures follow:
  1. A rationale containing `\W`, `\d`, `\u` and so on raises `re.error` ("bad escape"; named
     `re.PatternError` from Python 3.13). Quoting the code under review is the normal shape of
     a rejection rationale. Observed on pdca-pdca `results/issue_506`: the rationale quoted
     `^\W*`.
  2. A rationale containing a **valid** reference such as `\g<1>` doesn't fail. It is
     silently expanded, so §9 records the field's own label in place of the human's words, and the
     next Do gets that via the carry-forward.
  3. `re.error` is not a `ValueError`, so it escapes both callers: `cli._signoff`
     (`cli.py:1400-1407`) tracebacks, and `flow._apply_decision` (`flow.py:183-192`) either
     tracebacks the single-issue run (no `_isolate` there) or, in the batch sweep, falls to
     `flow._isolate` (`flow.py:51-70`) as "skipping this bundle". `signoff-decision` is only
     unlinked after a successful `record`, so every later pass re-reads it and fails the same
     way. issue_506 burned all 20 passes stuck at AWAITING_SIGNOFF with §9 blank.
- Success criterion: offline, on the template driver suite, with the recordable SUMMARY
  shape used in `template/tests/test_handoff.py:72-80`:
  (a) `signoff.record(..., action="iterate-do", delta=<text>)` where the text contains a
      regex escape (e.g. ``_ERROR_LEAD_RE's `^\W*` lead``) succeeds, and the §9
      `- Iteration delta (if iterating):` line then ends with exactly that text,
      byte-for-byte;
  (b) a delta containing `\g<1>` is recorded **literally**: the line contains the characters
      `\g<1>` and does not contain a second copy of the field label;
  (c) a `by` value containing a backslash escape (e.g. `CORP\dev`) is recorded literally in
      `- By / date:` for every action, including `accept`;
  (d) end to end: `flow._apply_decision` over a bundle whose `signoff-decision` is
      `iterate-do` plus a rationale containing `^\W*` records §9, consumes (unlinks)
      `signoff-decision`, and returns `"iterate-do"`, so the bundle leaves AWAITING_SIGNOFF;
  (e) the existing sign-off suites (`test_signoff_authority.py`, `test_signoff_orphan.py`,
      `test_handoff.py`) pass unchanged: the Outcome/By/delta match-count guards
      (`signoff.py:188-215`) still raise `ValueError` on a §9 missing a field.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: `signoff.record` writes each §9 field value verbatim, so no character in human
  text is read as regex template syntax. One site (`set_field`, `signoff.py:180-185`).
  / out of scope: `flow._isolate`'s "skipping this bundle" wording and a quarantine path for
  a decision that can never be recorded (the issue flags these as a separate consideration);
  multi-line values in §9 (flow already flattens the rationale, `flow.py:181-182`); the
  instance-side local patch in pdca-pdca (dropped at the next `copier update`); any other
  `re.sub` call in the package. Note in build-notes if Do sees the same pattern elsewhere,
  but don't fix it here.

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: likely-fix
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — (no gate configured)
- C3 Change: none — patch.diff
- C4 fix verified: bundle test red pre-fix, green post-fix: pass — C4 PASS — red without the fix, green with it
- C5 added test exercises production, not a copy: pass — 1 added driver-suite test(s) import the production package 'pdca_harness'

## 4. Conformance (Check — stack)
- T1 Structure: none — (no gate configured)
- T2 shape: docs lint + site render link audit: pass — docs lint clean, site render + link audit clean
- T2 host CI parity: target docs-check.yml on the pushed tree: pass — host CI parity on the patched tree — docs lint clean, site render + link audit clean
- T3 runtime: render/update-compat + offline driver suites: pass — root suite OK, driver suite OK
- T4 PR body has a user-impact opener + tracker id in both artifacts: deferred — pr-description.md not drafted yet — the substantive T4 audit of the contribution artifacts runs at publish
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Review issue #529: preserve backslashes and group-reference text literally when recording human sign-off attribution and rationale, so decisions can be recorded and consumed.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The bounded single-line data-preservation requirement covers crashes, silent corruption, attribution, and decision consumption; the production contract and caller support those outcomes (`target/template/src/pdca_harness/signoff.py:160`, `target/template/src/pdca_harness/flow.py:179`; `brief.md:23`). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing the production fix reproduced six escape errors and one literal-text assertion failure across four tests, including the actual decision caller (`target/template/tests/test_signoff_verbatim.py:74`, `target/template/tests/test_signoff_verbatim.py:124`; `review-red.log:149`). |
| C3 Change | PASS | Human text no longer enters replacement-template parsing; field matching, substitution counts, and refusal before writing retain their existing behavior (`target/template/src/pdca_harness/signoff.py:193`, `target/template/src/pdca_harness/signoff.py:205`, `target/template/src/pdca_harness/signoff.py:215`). |
| C4 Verification (red→green) | PASS | Restoring the exact fix made all four regression tests and the three unchanged sign-off/handoff suites pass: 88 tests, including missing-field safeguards (`review-green.log:3`; `target/template/tests/test_signoff_authority.py:177`, `target/template/tests/test_signoff_verbatim.py:136`). |
| C5 Causal adequacy | PASS | Removing replacement-template interpretation eliminates both observed failure modes at their common cause; the production caller test verifies consumption, and no capability probe or symptom guard was added (`target/template/src/pdca_harness/signoff.py:194`, `target/template/tests/test_signoff_verbatim.py:134`; `gate-logs/C5-prod-path.log:10`). |
| T1 Structure | PASS | The change stays within the existing field-writing helper and a regression module, with no new dependency, interface, or architectural responsibility (`target/template/src/pdca_harness/signoff.py:180`, `target/template/tests/test_signoff_verbatim.py:33`). |
| T2 Shape | PASS | Independent whitespace checking, docs lint, and rendering of 22 pages with internal-link auditing passed; the frozen shape and host-parity logs agree (`target/docs/publishing/tools/README.md:34`; `gate-logs/T2-docs.log:11`, `gate-logs/host-ci-docs.log:11`). |
| T3 Runtime | PASS | Independent offline driver discovery ran 1,792 tests successfully with two skips; frozen evidence additionally shows 24 passing root render/update tests, which this reviewer cannot reproduce without Copier and release tags (`review-suite.log:1103`; `gate-logs/T3-suite.log:36`, `gate-logs/T3-suite.log:54`). |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; the deferred gate explicitly owes the substantive contribution audit to publish (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Establish that merged and closed/rejected work by both affected file paths does not supersede or contradict this fix — the brief reports path-based history but only issue-number closed-PR searching, and this target has one synthetic commit and no remotes (`brief.md:78`; affected paths: `target/template/src/pdca_harness/signoff.py:180`, `target/template/tests/test_signoff_verbatim.py:1`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether preserving single-line rationale and attribution, with a demonstrated successful decision consumption, satisfies the reported operational need while multiline input and quarantine behavior remain outside scope (`brief.md:58`; `target/template/tests/test_signoff_verbatim.py:124`, `target/template/src/pdca_harness/flow.py:181`). |

## Independent evidence and limits

- Grounded source citations against the supplied disposable `$PDCA_TARGET`; it contains the expected patch and is not stale. Stashed only the tracked production change, retained the new regression module for the red leg, and restored the patch before green verification. The target's final source status matches its initial status.
- Used Python 3.14.4 with scratch files confined to this review directory. Red: `PYTHONPATH=src python3 -m unittest tests.test_signoff_verbatim` from `target/template`, exit 1. Green: the same command plus `tests.test_signoff_authority tests.test_signoff_orphan tests.test_handoff`, exit 0. Captured results are in `review-red.log` and `review-green.log`.
- Full driver rerun: `PYTHONPATH=src python3 -m unittest discover -s tests`, exit 0; output in `review-suite.log`. Also reran `git diff --check`, `lint_docs.py`, `render_site.py --check --out /tmp/pdca-review-32moktfz/review-site`, and the supplied production-import scanner with this bundle and `PDCA_PROD_PACKAGE=pdca_harness`; all passed.
- Instance-scoped wrappers are outside the supplied target. Read all six frozen gate logs. Root render/update evidence explicitly includes successful real Copier render and update cases; missing Copier and release tags in the reviewer sandbox limit independent repetition, not that frozen evidence. The fix's declared external dependency, Python, was exercised directly with inputs that reproduce the forbidden failures.
- Prior-art investigation: `git -C target log --all --oneline -- template/src/pdca_harness/signoff.py template/tests/test_signoff_verbatim.py` returns only `cf02b49 pre-fix base 6ba00bad8e9c7257dacfd4b87c54450ab7259bc9`; `git remote -v` and `git tag --list` are empty. No closed/rejected-by-path evidence is provided. This remains the T5 decision, not a patch defect.
- The supplied integration template enumerates no additional human-only checks: its list is still a placeholder (`target/template/docs/INTEGRATION.md.jinja:80`). No visual/manual outcome or contested symptom guard applies here.

No patch defect found. This review is advisory; fitness-to-purpose and prior-art adjudication remain with the human.

### Advisory — code-review

# Check — advisory code review (issue #529)

Scope: `template/src/pdca_harness/signoff.py:180-197` (the `set_field` fix) and the new
`template/tests/test_signoff_verbatim.py`.

## Correctness

Clean. The fix swaps the `repl` argument of `re.subn` from a string template to a
closure (`signoff.py:194-195`) that returns `value` untouched. This is exactly the
documented way to stop `re.sub`/`re.subn` from re-parsing backslash escapes in
replacement text, and it reproduces the original string template's two branches
(non-empty `value` → `f"{m.group(1)} {value}"`, empty `value` → `m.group(1)` alone)
without behavior drift for the ordinary case. The `C4-verify.log` red leg confirms the
pre-fix crash sites and the double-label bug the brief describes line for line
(`re.error`/`re.PatternError: bad escape \d` and `\W` at `signoff.py:184`, and the
`\g<1>` case producing `"...iterating): - Iteration delta (if iterating): literal"`),
and the green leg passes all four new tests. No resource leaks, no new error paths, no
change to the `ValueError` contract the two callers (`cli._signoff`, `flow._apply_decision`)
rely on.

The end-to-end test (`test_signoff_verbatim.py:133-148`) writes the `signoff-decision`
file in the exact `"<action>\n<rationale>\n"` shape `leaves.signoff_decision` /
`leaves.signoff_rationale` expect (`leaves.py:3498-3518`), and `_apply_decision`'s
signature/behavior (`flow.py:133-135`, `152-185`) matches how the test calls it — this
is a real exercise of the production path, not a stand-in.

## Reuse / simplification / efficiency

Nothing to flag. The fix is the minimal, idiomatic change (string `repl` → callable
`repl`); it doesn't introduce a duplicate helper where one already existed, and the
per-call closure allocation is negligible next to the regex compile already happening
in the same function on every `record()` call.

`publish.py:1064` has an f-string built as a `re.sub` `repl` argument with data that
isn't obviously human-authored-adversarial-text — visibly the same *shape* of API
misuse, but the brief explicitly puts "any other `re.sub` call in the package" out of
scope for this bundle, so it's not a finding against this diff.

## Verdict

No implementation bugs and no reuse/efficiency issues introduced by this patch.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T5 Judgment — Establish that merged and closed/rejected work by both affected file paths does not supersede or contradict this fix — the brief reports path-based history but only issue-number closed-PR searching, and this target has one synthetic commit and no remotes (`brief.md:78`; affected paths: `target/template/src/pdca_harness/signoff.py:180`, `target/template/tests/test_signoff_verbatim.py:1`).
- [x] Validation — fitness-to-purpose — Decide whether preserving single-line rationale and attribution, with a demonstrated successful decision consumption, satisfies the reported operational need while multiline input and quarantine behavior remain outside scope (`brief.md:58`; `target/template/tests/test_signoff_verbatim.py:124`, `target/template/src/pdca_harness/flow.py:181`).

## 7. Proven / not proven
- Proven by which oracle: gates overall = pass (stub oracles).
- Unproven / needs manual run: anything flagged in §6.

## 8. Ready-to-ship attachments
- patch.diff
- tracker-comment.md     (ALWAYS, every tracker item)
- build-notes.md         (builder rationale — for the human, not the reviewer)

## 9. Check sign-off                     ← human completes Check here
- Disposition confirmed / overridden:
- Outcome: merged-wider
- Iteration delta (if iterating):
- By / date: Eduard Ralph / 2026-09-15

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
