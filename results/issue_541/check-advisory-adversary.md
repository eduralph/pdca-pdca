# Advisory review — adversary (issue 541, round 6)

Lens: try to refute the red→green proof and the fix. Result: **I could not refute the fix.**
Nothing below needs a human decision, so no bullet here is marked for §6. (I quote the
leaf-status marker only by name, never in its literal comment form, so this file cannot be
misread as a placeholder by the harness that is running it.)

## What I re-ran

- **Red→green reproduced** at `template/tests/test_attempt_harvest.py`. I ran it offline on a
  scratch copy of `$PDCA_TARGET`: patched tree 24/24 OK; with `assemble.py` and `leaves.py`
  restored from the base commit (`git show HEAD:…`), FAILED (failures=13, errors=5). That
  matches `gate-logs/C4-verify.log` exactly. The 5 errors are real failures, not load
  failures. Two are missing new symbols referenced inside test bodies (`_LeafHarvest`,
  `LEAF_COMPLETE_TRAILER`). The other three are the base misbehaving: a PermissionError crash
  in `copy2` on an unreadable residue, and two cases where no error log was preserved. The
  module imports only `assemble, autoiterate, leaves, size_signal, state` at module level, so
  the red leg is not UNVERIFIABLE.
- **Each of the three readers flips independently** (`assemble.py:169-171`). The shipped leg
  `test_attempt_harvest.py:574-604` checks the three readers one after another in a single
  test body, so the gate's red leg only proves the first one (it stops at `:586`). I probed all
  three on their own with the brief's artifact: a fenced quote of the infra-empty marker, with
  the trailer as the last line. Results, base → patched:
  `_items_from_artifact` `['human']` → `['impl']`; `_review_drove_the_iterate` `True` →
  `False`; `_plan_findings` `0` → `1`. That matches the brief's Falsifiability table.
- **4d holds.** `test_leaf_status`, `test_leaf_resilience` and `test_attempt_ownership` are
  unmodified (the patch touches only `assemble.py`, `leaves.py` and the new test file) and
  pass: 31 tests OK.

## Refutation attempts that failed

- **Can a harness placeholder end with the trailer?** That would let a placeholder pass as a
  real review and smuggle in `[impl]`, breaking the #278 contract. No. All three placeholders
  end with a line the harness writes itself: `leaves.py:3240-3241`, `:3587-3588`,
  `:4075-4076`. The leaf-derived `reason` sits in the middle of a line, never at the end of the
  file. So a leaf output that ends with the trailer cannot become a placeholder's last line.
- **Does anything else in the harness write into a leaf's artifact after the leaf finishes?**
  Only `_note_bash_unavailable` (`leaves.py:4032-4052`). When there is no trailer, its output
  is byte-identical to the base: `"\n" + note` gives the same bytes as the old literal, so 4b
  holds. When there is a trailer, the note goes above it and the trailer stays last. The plan
  revision pass writes only `brief.md`, not the plan-advisory file (`_plan_revision_prompt`),
  and I found no other writes to `check-advisory-*` / `plan-advisory-*` in the package.
- **Is the closing instruction really the last thing the leaf reads?** Yes. `_invoke` only
  *prefixes* the prompt (`leaves.py:630`, `prompt_prefix + prompt`). The instruction is added
  after the rubric at the review and advisory sites (`leaves.py:3174-3175`, `:3427-3428`) and
  last at the plan site (`:3645-3646`). Each builder has exactly one caller. The 4e leg checks
  the prompt as actually sent, captured from the stub leaf's stdin, with a non-empty rubric.
- **This round's wording change** (`leaves.py:2522-2545`). The runtime string now claims only
  that the trailer "tells the harness this file is your finished report". That is true: it
  makes `leaf_status` return "" at all three readers. It no longer threatens that a report
  without the trailer is ignored, which would be false under 4b. The block comment now states
  what is true: absence changes nothing, and filing never depends on the trailer, because
  `_LeafHarvest` does not read it. No logic changed. `.format(artifact=…)` is applied only to
  the instruction, so braces in a rubric or `leaf_id` cannot break it.
- **Edge inputs to the guard.** CRLF line endings and a trailer padded with non-breaking
  spaces are both recognised. A zero-width character after the trailer is not, so that file
  falls through to today's behaviour. That is 4b working as designed, not a defect.
- **Un-owned path that could not even be `stat`-ed** (`leaves.py:980`, `_unidentified`). This
  refuses a file the live attempt provably wrote. Example: a dead attempt leaves a symlink loop
  at the artifact path, and the live attempt removes it and writes a real file. The docstring
  documents this as intentionally conservative, the brief puts the harvest structure out of
  scope, and the case is exotic, so I am not filing it.

## Notes (not escalated)

- `assemble.py:132-134` still says a report quoting the trailer inside a fenced block "cannot
  stamp itself complete — the fence's closing line is the last one". That fails when the fence
  is never closed. On the patched tree, a text ending with an open code fence followed by the
  trailer line returns `''` from `leaf_status`. `test_attempt_harvest.py:651` says the same
  thing ("what a quotation cannot forge"). Round 5 softened this same overstatement in
  `leaf_status`'s own docstring (`:162-164`), which sits right below and already names the
  exception. It does no harm: only text a leaf wrote can reach this shape, and that text is a
  real report anyway. It is wording only, and it is the truncation gap the human has already
  accepted, so I am leaving it out of §6. The human ruled this the last round.
- The `test_attempt_harvest.py:718` red is only an AttributeError on the new constant, not
  evidence of the defect. That is fine for a 4e write-site guard, but it should not be counted
  as a red→green. I could not see `build-notes.md`, so I cannot check how it was counted there.

Attempted to refute: the C4 evidence, the reader guard, placeholder spoofing, post-harvest
writes, prompt order, this round's wording, and edge line endings. I could not refute any of
them.
