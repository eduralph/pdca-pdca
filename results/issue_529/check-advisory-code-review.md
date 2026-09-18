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
