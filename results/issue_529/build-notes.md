# Build notes — issue 529 / signoff-records-human-text-verbatim

## The change

One site, as the brief scopes it: `signoff.record`'s nested `set_field` helper
(`template/src/pdca_harness/signoff.py:180-185` pre-fix, on `main` at `eae11b4`).

Before:
```python
def set_field(body: str, label: str, value: str) -> tuple[str, int]:
    """``(body, substitutions)`` — the count matters for ``Outcome``, see below."""
    pat = re.compile(rf"^(- {re.escape(label)}:).*?$", re.MULTILINE)
    repl = rf"\g<1> {value}" if value else r"\g<1>"
    new, n = pat.subn(repl, body, count=1)
    return (new, n) if n else (body, 0)
```

After (`signoff.py:180-196` post-fix):
```python
def set_field(body: str, label: str, value: str) -> tuple[str, int]:
    ...
    pat = re.compile(rf"^(- {re.escape(label)}:).*?$", re.MULTILINE)
    def repl(m: re.Match[str]) -> str:
        return f"{m.group(1)} {value}" if value else m.group(1)
    new, n = pat.subn(repl, body, count=1)
    return (new, n) if n else (body, 0)
```

`repl` goes from a **string template** (`re.sub` parses its own backslash-escape
grammar in that case — `\g<1>`, `\1`, `\W` treated as an escape and rejected if
unrecognised) to a **callable**. Per the `re.sub` docs the brief cites, a callable's
return value is used exactly as returned — no escape parsing at all. The callable
closes over `value` and `m.group(1)` (the field label, captured by the pattern) and
concatenates them with an ordinary f-string, so every byte of `value` — the human's
own text — reaches the file unchanged, whatever it contains.

This is the single narrowest fix that removes the cause (regex-template
interpretation of untrusted text) rather than guarding a symptom (e.g. pre-escaping
backslashes in `value` before building the old string template, which is a strictly
larger and more fragile change — it has to track every `re.sub` template escape,
including ones not yet observed to trip it, and still leaves the underlying
category error of "treating data as a template" in place). Diff: 2 lines removed,
14 added (mostly the docstring explaining why `repl` must be callable — the code
change itself is 2 lines swapped for 2).

I did not touch `outcome_token`, `iteration_delta`, `_OUTCOME_RE`, `_DELTA_RE`, or
`unrecordable` — none of them build a `re.sub`/`re.subn` replacement string; they
only `search`/parse existing text, which does not run escape processing.

## Same pattern elsewhere (noted, not fixed — out of scope per the brief)

I grepped the package for other `re.sub`/`re.subn` calls with a non-callable
`repl` built from a variable, to check whether #529's category recurs:

```
grep -rn "re\.sub(subn)?(" template/src/pdca_harness/*.py
```

Found no other call whose `repl` argument is built from untrusted/human-supplied
text — the rest are either literal `repl` strings with no interpolation, or the
`pattern`/`string` arguments involve a variable but `repl` is a constant. So I did
not find another instance of this exact defect to flag. (The brief's "note if Do
sees the same pattern elsewhere" clause is why I looked — recording a clean result,
not silence.)

## Test

New file: `template/tests/test_signoff_verbatim.py`, four `unittest.TestCase`s
mapping 1:1 to the brief's success criteria (a)-(d):

- `RationaleWithARegexEscapeIsRecordedVerbatim` — (a): `^\W*`-style rationale,
  asserts the recorded line ends with the delta byte-for-byte.
- `RationaleWithAValidGroupReferenceIsNotExpanded` — (b): `\g<1>` delta, asserts
  the literal characters appear and the field label is not doubled (the pre-fix
  failure mode was recording the label twice, once for the field and once as the
  "expansion").
- `ByWithABackslashEscapeIsRecordedVerbatim` — (c): `CORP\dev`-style `by`, looped
  over all four actions (`accept`/`iterate-do`/`iterate-plan`/`discontinue`) since
  the brief calls out "for every action, including `accept`" specifically.
- `EndToEndThroughApplyDecision` — (d): drives `flow._apply_decision` (not
  `signoff.record` directly) with a `signoff-decision` file carrying an
  `^\W*`-quoting rationale, mirroring the peer callsite the brief names
  (`test_flow_captures_the_full_rationale_before_the_unlink`,
  `template/tests/test_handoff.py:411-424`). Asserts the action returned
  (`"iterate-do"`), the decision file is unlinked (consumed), and §9 carries the
  literal text — so the fix is proven through the real caller whose `except
  ValueError` the bug used to escape (item 3 of the brief's defect description),
  not just through `signoff.record` in isolation.

The `_SUMMARY` fixture is copied byte-identical from `test_handoff.py:72-80` (the
peer fixture the brief names), and criterion (e) — the existing sign-off suites
unchanged — I did not re-encode as a new assertion; I ran them (see below).

I deliberately do **not** assert on `re.error` / `re.PatternError` anywhere — the
brief's falsifiability clause forbids naming `re.PatternError` (a 3.13-only alias),
and asserting the exception type would tie the pre-fix "red" to an accident of the
old implementation rather than to the recorded text, which is the actual invariant.
Every assertion in the new test is against the recorded §9 text.

## The three refutation questions

**(a) Genuine red?** Yes. With the fix reverted (I used `git stash push -u -m
"issue529-verify-528491" -- template/src/pdca_harness/signoff.py`, ran the test,
then `git stash apply <sha>` + `git stash drop <sha>` to restore — never a bare
`git stash`/`pop`, per the shared-stash-stack warning), `unittest` reported
`Ran 4 tests ... FAILED (failures=1, errors=6)`: `RationaleWithARegexEscapeIs...`
and `EndToEndThroughApplyDecision` each raised `re.PatternError: bad escape`
straight out of `signoff.py:184`; `ByWithABackslashEscapeIsRecordedVerbatim`'s
`subTest` loop raised the same error on every action (`\d` in `CORP\dev` is also
an invalid escape) — unittest counts each failed `subTest` toward `errors`
separately, which is why the error count exceeds the method count; and
`RationaleWithAValidGroupReferenceIsNotExpanded` failed its assertion outright
(the label recorded twice). I then re-ran with the fix restored: all 4 test
methods (7 sub-cases counting the 4 `subTest`s) pass. I also ran this exact
red/green cycle through the project's own C4 gate,
`engine/scripts/run-verify.sh` (from `pdca-pdca`, pointed at the worktree via
`PDCA_BUNDLE`/`PDCA_WORKTREE`/`PDCA_BRIEF_BASE=origin/main`), which reverts only
the production hunk (test files excluded) and re-applies `patch.diff` — its
verdict: `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`.

**(b) Production path?** Yes. `EndToEndThroughApplyDecision` calls
`flow._apply_decision`, the real driver function `flow.py:133` — not a copy — which
calls `signoff.record`, the real production function this patch changes. The other
three tests call `signoff.record` directly (also production, not a mock). No test
in this file imports or defines any stand-in for `signoff.set_field` or `re.subn`.

**(c) Fixture includes the fault?** Yes. Every test constructs a delta/`by` value
that is exactly the shape the defect mishandles — a value containing a regex
metacharacter escape sequence (`\W`, `\d`) or a valid group reference (`\g<1>`) —
rather than a value that happens to avoid backslashes. The `_SUMMARY` fixture
itself is the ordinary recordable shape (matches `test_handoff.py:72-80`
byte-for-byte), not narrowed to exclude the failing field.

## What I ruled out

- **Pre-escaping `value`'s backslashes before building the string `repl`** (e.g.
  `value.replace("\\", "\\\\")`): would also fix the observed cases, but keeps the
  underlying category error — human text is still handed to `re.sub` as a
  template, just with one more layer of quoting to keep synchronized with
  whatever `re.sub`'s template grammar accepts next (it has grown escapes across
  Python versions — `\N{...}` in `str.replace`-adjacent contexts, etc.). The
  callable fix is not larger (2 lines vs. 1, ignoring the docstring) and removes
  the category rather than patching around it, which is what the brief's
  "Invariant to restore" asks for.
- **Sanitizing/rejecting values containing backslashes in `record`**: would turn a
  normal rejection rationale ("quoting `^\W*`") into a hard error — the opposite
  of the invariant ("whatever characters it contains, §9 carries it verbatim").
  Explicitly not what the brief wants.
- **Fixing `flow._isolate`'s wording or adding a quarantine path** for an
  unrecordable decision: out of scope per the brief ("the issue flags these as a
  separate consideration").
- **Auditing every other `re.sub` call in the package for the same shape**: out of
  scope per the brief ("don't fix it here"); I did the narrow grep noted above and
  found nothing else to flag.

## Formatting / commit-readiness

No formatter or pre-commit config exists in the target repo (`pdca-harness`) — I
checked for `.pre-commit-config.yaml`, `pyproject.toml` tool sections, and
`CONTRIBUTING.md`, which names only the DCO sign-off (`git commit -s`) and the two
test entry points (`cd template && PYTHONPATH=src python3 -m unittest discover -s
tests`; `python3 -m tests.run_root_suite`), neither of which is a linter. I matched
the surrounding file's line-length convention (≤ ~97 cols, checked with `awk
'{print length}' | sort -rn`) and docstring/comment style (`` `` `` for code,
`#NNN` for issue references) rather than running an external formatter that isn't
part of this project's toolchain.

## Full suite

`cd template && PYTHONPATH=src python3 -m unittest discover -s tests` after the
fix: `Ran 1792 tests ... OK (skipped=2)` — the existing sign-off suites
(`test_signoff_authority.py`, `test_signoff_orphan.py`, `test_handoff.py`) pass
unchanged, satisfying criterion (e).
