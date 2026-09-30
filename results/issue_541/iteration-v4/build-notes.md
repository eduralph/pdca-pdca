# Build notes — issue 541, round 5 (`no-dead-attempts-artifact-harvested-as-a-live-ones`)

*Withheld from the reviewer. For the human at sign-off.*

Target branch: `eduralph/pdca-harness` @ `pdca-integration/main`, tip `480fa6b`
(`pdca-integrate: issue_540`). `patch.diff` was round-tripped against that pristine tree:
full revert → `git status` clean at `480fa6b` → `git apply --check` → re-apply → byte-identical
diff. So the shipped patch applies cleanly to the base the driver exports as
`$PDCA_VERIFY_BASE`.

---

## 1. What was built, and why this shape

The brief specified the route, not only the destination (a deliberate, human-taken exception to
`docs/principles.md` §3.1 after three rounds each closed one hole in the same mechanism and
opened another). I followed it literally. The single production idea:

> **Who closed the artifact decides whether it is real. What the artifact mentions decides
> nothing.**

Reader side — one anchored guard at the head of the one function all three readers already
share (`template/src/pdca_harness/assemble.py:126-141`):

```python
closing = next((ln for ln in reversed(artifact_text.splitlines()) if ln.strip()), "")
if closing.strip() == LEAF_COMPLETE_TRAILER:
    return ""
m = _LEAF_STATUS_RE.search(artifact_text)      # unchanged fall-through
```

That converts all three readers at once because they call this one function —
`assemble.py:216` (`_items_from_artifact` → §6 + auto-iterate),
`size_signal.py:240` (`_review_drove_the_iterate`), `leaves.py:3452` (`_plan_findings`). No
second classifier was added anywhere; that was explicitly ruled out by the brief (two parsers
for one artifact is the bug this repo has already paid for in PR #294 and in rounds 2–4 here).

The trailer constant is `assemble.LEAF_COMPLETE_TRAILER = "<!-- pdca:leaf-complete -->"`
(`assemble.py:112`), pinned by the brief so the prompts, the stubs and the test cannot drift
to three spellings.

Write side — one instruction string, three prompts, three stubs:

| Site | path:line (patched tree) |
|---|---|
| `_COMPLETION_INSTRUCTION` (the one sentence) | `leaves.py:2335-2340` |
| `_REVIEW_PROMPT` | `leaves.py:2400` |
| `_advisory_prompt` | `leaves.py:3181` |
| `_plan_advisory_prompt` | `leaves.py:3389` |
| `_stub_review` | `leaves.py:3109` |
| `_stub_advisory` | `leaves.py:3332` |
| `_stub_plan_advisory` | `leaves.py:3636` |
| the three `_*_unavailable` placeholders | untouched — they must NOT carry it |

One `_COMPLETION_INSTRUCTION.format(artifact=…)` rather than three hand-written sentences: the
"twin blindness" this whole slice exists to remove is a change that lands at two of three
sites. `.format()` is safe here — the string's only brace pair is `{artifact}`, and the
`leaf_id` is interpolated into the *argument*, not re-formatted.

### The fourth-token strip (scope item 3), and the comments that justified it

Against the carried `iteration-v3/patch.diff` the production delta is exactly the three
deletions the brief named, plus the comment corrections it required:

- `LEAF_STATUS_UNOWNED = "unowned-empty"` — gone (nothing named `unowned-empty` survives
  anywhere in the patch: `grep -rn "UNOWNED\|unowned" template/src` returns only
  `_FAIL_UNOWNED`, `_LeafHarvest._unowned` and an unrelated `sweep.py` local).
- its `_LEAF_STATUS_LABEL` entry — gone (`assemble.py:95-100`, three entries).
- `_FAIL_UNOWNED: assemble.LEAF_STATUS_UNOWNED,` in `_unavailable_classification` — gone
  (`leaves.py:3039-3042`); the dict's existing `.get(failure, assemble.LEAF_STATUS_HUMAN)`
  now yields `human-empty` for it, as specified.

**KEPT**, as instructed: `_FAIL_UNOWNED = "unowned"` (`leaves.py:2974`) and its prose branch
(`leaves.py:3056-3063`, "**un-owned artifact — the leaf RAN and exited 0 …**"). That prose is
where the precision 4c gives up in §6 now lives.

Both comments the baseline wrote to argue for the fourth token were replaced with the actual
rule rather than deleted — a stale comment justifying a struck design is how the next person
re-adds it:

- `assemble.py:80-90` (was: "hence its own status and its own row") → the trailer decides
  realness, the table only explains why when it is not, the table is **closed at three**, the
  un-owned case shares `human-empty` and carries its distinction in prose.
- `leaves.py:3031-3038` (`_unavailable_classification` docstring, was: "is its own marker for
  the same reason") → same rule, from the writer's side.
- `leaves.py:2967-2973` (the `_FAIL_UNOWNED` block comment) — the baseline's "Distinct
  because…" now says explicitly *a distinct FAILURE CLASS, not a distinct status token*, so
  the next reader does not "restore" the symmetry.
- `assemble.py:113-123` — the baseline's "unrecognised token" paragraph was left in place but
  corrected on one clause that this patch makes false: the marker is matched anywhere **for an
  artifact with no trailer**.

## 2. What I did NOT do (and the cost of each alternative)

- **No fourth status token, in any disguise.** Rejected by the re-plan, and it is the round-4
  design. Concretely it would have been +1 line at `assemble.py:93`, +3 lines in
  `_LEAF_STATUS_LABEL`, +1 line in the `_unavailable_classification` dict — 5 lines, so *not*
  rejected on cost: rejected because a recognised token self-triggers on the next artifact
  that quotes it, which is the defect. The non-growth guard
  (`test_the_recognised_status_set_is_closed_at_three`) is the mechanical form of that ruling.
- **No `_residue_identity` change**, no removal of `st_ctime_ns`, no digest cross-check on a
  moved identity — the metadata-only-touch hole is accepted and filed (v3 SUMMARY §10).
- **No trailer in `_preserve`.** Tempting (a withdrawn residue that carried the trailer *did*
  close, so it is arguably harvestable) and explicitly forbidden: it is the same
  "one more thing" that grew rounds 2–4, and it would re-couple ownership to text.
- **No docs change.** `grep -rn "leaf-status\|leaf_status" docs/ template/docs/ template/PCDA/`
  → nothing: no shipped document describes the marker mechanism, so none went stale.
- **No edits to any other shipped suite.** The stub trailer (scope item 4) broke **zero**
  existing assertions: the full offline driver suite is 1826 tests green, and the root suite
  green, through `./engine/scripts/run-suite.sh` (`PDCA-EVIDENCE: root suite OK, driver suite
  OK`). The brief asked for every such edit to be listed with the assertion it broke — the
  list is empty.
- **4d — `template/tests/test_leaf_status.py` is untouched** (the patch's numstat is three
  files) and passes: 15 tests OK, including `:194`
  `test_an_impl_tagged_finding_in_a_placeholder_cannot_smuggle_in_impl` and `:204`
  `test_a_real_advisory_finding_is_untouched`. A placeholder carries no trailer, so it is
  still a placeholder and its `[impl]` tag is still refused.

## 3. Which legs are red→green and which are guards — stated honestly

Measured, not asserted: the C4 gate's own red leg (`git apply -R --exclude=tests/*
--exclude=template/tests/*`), then `PYTHONPATH=src python3 -m unittest
tests.test_attempt_harvest -v` from `template/`.

**Genuine red→green (part B — this round's work):**

| Leg (`template/tests/test_attempt_harvest.py`) | red leg |
|---|---|
| `:561 test_a_closed_artifact_is_real_at_every_reader_whatever_it_quotes` | FAIL |
| `:590 test_a_closed_advisory_keeps_its_impl_routing_into_section_6` | FAIL |
| `:610 test_the_trailer_counts_only_as_the_artifacts_last_non_blank_line` | FAIL |

The first is the brief's falsifiability table, driven directly at the three named readers:
`assemble._items_from_artifact` (base `kind=human` + "leaf did not run (transient infra…)"
prefix → `kind=impl`, unprefixed), `size_signal._review_drove_the_iterate` (True → False),
`leaves._plan_findings` (0 → 1). The probe artifact is **the same text in both columns** —
`_probe(...)` at `:155`, a real report with a fenced quote of `<!-- pdca:leaf-status
infra-empty -->` **and** the trailer as its last non-blank line — so only the reader's rule
changed, not the fixture.

**Genuine red→green (part A — carried baseline, red because the `Baseline` production hunks
are in this patch and the C4 red leg reverts them):** `:267`, `:296`, `:318`, `:415`, `:431`,
`:448`, `:462`, `:483`, `:286` — FAIL/ERROR on the red leg, green with the fix.

**Guards, green pre-fix by construction — NOT evidence the defect existed:**

- `:628 test_an_artifact_without_the_trailer_classifies_exactly_as_today` (4b) — passes on the
  red leg. It asserts the *base's* behaviour, including the pre-existing mis-read; it exists so
  a later "improvement" cannot make absence of the trailer mean something.
- `:653 test_the_recognised_status_set_is_closed_at_three` (4c ii) — passes on the red leg
  (the base already has exactly three). Shipped as the guard it is.
- `:504`, `:512`, `:543`, `:337`, `:347`, `:359`, `:379`, `:395` — carried baseline guards,
  green on both legs.

**Red on the red leg, but for a reason that is not evidence of the defect — flagged rather
than counted:** `:669 test_every_instructable_leaf_closes_its_artifact_and_no_placeholder_does`
(4e) ERRORs on the red leg because `assemble.LEAF_COMPLETE_TRAILER` does not exist there. That
is "the patch adds a symbol", not "the defect was real". I am naming it so the adversary does
not have to find it. It is still worth shipping: it is the only leg that pins all six write
sites (three prompts carry the instruction, three stubs close their artifact, three
placeholders do **not**) in one loop, and it pins production's spelling of the token against
the test's literal.

**4c (i) — the amendment the brief identified at Plan.** `:483
test_the_label_never_says_a_run_that_exited_0_did_not_run` no longer asserts `"exited 0"`
against the §6 *item* (under B-simple that row is `human-empty`'s — "leaf produced no usable
verdict (needs a human)" — which does not contain it). The assertion moved to the **artifact
text** (`:500-502`), where the kept `_FAIL_UNOWNED` prose branch writes "the leaf RAN and
exited 0"; it also now asserts `"un-owned artifact"` is there. The two §6 assertions are
unchanged and still hold: the label does not start with "leaf did not run", and still contains
"leaf" so the row is still selected.

### C4 red-leg import trap — handled

Module scope references **no** symbol this patch adds: `_TRAILER` (`:142`) and `_QUOTED`
(`:143`) are literals, `_probe` (`:155`) uses only them, and the imports are
`assemble, autoiterate, leaves, size_signal, state` + `Config, LeafConfig` — all present on the
base. `LEAF_COMPLETE_TRAILER`, `_FAIL_UNOWNED` and `_LeafHarvest` appear only inside test
bodies. Proof it worked: the red leg reported **"Ran 23 tests"** with 12 failures + 5 errors
and no `unittest.loader._FailedTest`, so the gate scored it a genuine red rather than
`PDCA-UNVERIFIABLE` (`engine/scripts/run-verify.sh:231-234`). The part-B legs carry **no**
`skipUnless(_rootless())` guard — they are pure text classification and must run even if the
gate ever runs as root, so the red leg stays red there.

## 4. Before declaring done — the three forced questions

**(a) Genuine red?** Yes, and measured through the project's own gate, not by hand:

```
$ PDCA_BUNDLE=results/issue_541 PDCA_WORKTREE=… ./engine/scripts/run-verify.sh
== C4 green leg: … Ran 23 tests … OK
== C4 red leg: … Ran 23 tests … FAILED (failures=12, errors=5)
PDCA-EVIDENCE: C4 PASS — red without the fix, green with it
```

Per-leg red/green is tabulated in §3 above, including the legs that are honestly green pre-fix.

**(b) Production path?** Yes. Every classification leg calls production directly —
`assemble.leaf_status`, `assemble._items_from_artifact`, `assemble.collect_needs_human`,
`size_signal._review_drove_the_iterate`, `leaves._plan_findings`, `leaves._REVIEW_PROMPT`,
`leaves._advisory_prompt`, `leaves._plan_advisory_prompt`, `leaves._stub_review` /
`_stub_advisory` / `_stub_plan_advisory`, `leaves._review_unavailable` /
`_advisory_unavailable` / `_plan_advisory_unavailable`. The part-A legs spawn the three real
sandboxed entry points (`_run_review_sandboxed`, `_run_advisory_sandboxed`,
`_run_plan_advisory_sandboxed`) with a real subprocess as the "leaf". The only two patches in
the whole file are `leaves.time` (so the shipped backoff does not *sleep* — the stop rule
itself is the real one) and, in `:462`, a **recording subclass of the real `_LeafHarvest`**,
which is how that leg proves all three sites go through the one owner. Nothing under test is
mocked, copied or re-implemented.

**(c) Fixture includes the fault?** Yes, and this is the trap the v3 adversary caught last
round. The probe quotes `infra-empty` — a token the **base already recognises**. Quote a token
the base does not know (`some-future-status`, as `test_attempt_harvest.py:449` did) and
`_LEAF_STATUS_LABEL.get()` returns `""`, nothing is relabelled, and every leg is green pre-fix
while proving nothing. The trailer is present in the **red** column too, so the artifact is
constant across legs and the flip is attributable to the reader alone. The negative half is
included as well, not curated out: a trailer quoted inside a fence, and a trailer embedded in
a line of prose, must both still classify as placeholders — asserted at `:622-626`.

## 5. Commit-readiness

- The target repo configures **no** formatter or linter: no `.pre-commit-config.yaml`, no
  `core.hooksPath`, no hooks in `.git/hooks`, no ruff/flake8 config, and its four CI workflows
  are docs-check / docs / render-check / require-linked-issue. So there is no hook command to
  run; "commit-ready" here means matching the file's own conventions, which I checked
  mechanically: every **added** line is ≤ 99 chars (the longest pre-existing line in these two
  modules is 110), no trailing whitespace, no tabs, all three files `py_compile` clean.
- `./engine/scripts/run-suite.sh` (the T3 gate): root suite OK, driver suite OK, 1826 tests.
- `./engine/scripts/run-verify.sh` (the C4 gate): PASS.
- No push, no branch, no PR — nothing was published.

## 6. Residual risks the human may want to weigh at sign-off

1. **A model leaf that forgets the trailer** keeps today's behaviour exactly (4b), so the only
   cost is that it does not *earn* the new protection. That is the deliberate bargain: absence
   is inert, so a non-cooperating third-party leaf can never be read as permanently failing.
2. **`human-empty` is now shared** by "ran, produced nothing" and "ran, artifact un-ownable".
   The brief names this a known and accepted consequence (4c) — the distinction is in the
   placeholder's prose, and no machine consumer that exists reads the token for anything but
   "is this a placeholder?". If one ever does, that is the evidence for a fourth token and it
   returns as its own issue.
3. **`leaf_status` now calls `splitlines()`** on the artifact before the regex search. For the
   multi-MB artifact the bounded-quote leg simulates that is one extra list allocation on a
   text the base already regex-scanned end-to-end; the suite's timing is unchanged (1.3 s for
   this module, 62 s for the 1826-test suite). Worth naming, not worth optimising blind.
