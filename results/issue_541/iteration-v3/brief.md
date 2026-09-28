- **Slug:** no-dead-attempts-artifact-harvested-as-a-live-ones
- **Defect / goal:** The three harvest sites copy their artifact on a bare existence test —
  `leaves.py:2519-2523` (`check-review.md`), `:2851-2854` (advisory), `:3152-3155` (plan
  advisory) — with no notion of *which attempt* wrote it. So a truncated verdict a **dead**
  attempt left in the sandbox is adopted as the leaf's own output, which
  `engine/README.md:44-68` names directly: no evidence must never be filed as a verdict. The
  mechanism is hand-copied at all three sites, which is the "twin blindness" face the v5
  sign-off identified — a fix or a test that lands at two of three leaves the third wrong.
  A second reader carries the same root: the leaf-status label at `assemble.py:84-85` reads
  `"leaf did not run (transient infra — safe to re-run)"`, which becomes **false** once a run
  whose last attempt exited 0 can be routed there (v5's final unconverted reader).
- **Success criterion:** With the patch applied on top of child-1's accepted result:
  1. **No artifact written by a dead attempt is copied out as a successful attempt's
     output**, at **all three** harvest sites — not two of three.
  2. **A dead attempt's text is preserved** in the bundle's `*.error.log` rather than merely
     deleted: a real verdict must not be destroyed while the operator is told none was
     produced.
  3. **The live attempt's own artifact is harvested exactly as today**, and a leaf that exits
     0 having written nothing still degrades to today's placeholder.
  4. **The leaf-status label tells the truth** for every run it can now classify: a run whose
     last attempt exited 0 must not be labelled "leaf did not run".
  5. **DECIDED HERE, not left to Do — the retry contract is NOT narrowed**, the same ruling
     child-1 makes for the record flush. On a residue that cannot be withdrawn, **carry the
     un-owned state forward and refuse to HARVEST on the success branch** (the residue is
     already quoted by then) rather than ending the run. This is the v5 sign-off's own
     no-cost alternative, quoted verbatim as an instruction: v5 measured the fail-closed
     variant at base-3-attempts → patch-1 on a bundle write refusal and 2 → 1 on an unlink
     refusal, while its criterion demanded the contract "hold unchanged" — the builder was
     asked to satisfy both and could not. `test_leaf_resilience.py:62` (`_runs() == 3`) is
     the mechanical check.
  6. **The three harvest sites end up sharing one implementation, not three copies.** This is
     the point of the child: the v5 code-review advisory flagged the de-duplication as a
     legitimate Act candidate and round 3 refused it on the express grounds that "this patch
     is already oversized" — that refusal *is* the loop, and this child exists to break it.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Reproduction:** From `template/` on a clean checkout, offline. Drive
  `leaves._run_review_sandboxed` with a stub reviewer whose **first** attempt writes a
  truncated `check-review.md` into the sandbox then dies transiently, followed by an attempt
  that exits 0 without writing: today the harvest copies the dead attempt's file out as the
  review. Copy the stub-leaf harness from `template/tests/test_leaf_resilience.py:26-35`
  (`_TRANSIENT`, `_SUBSTANTIVE`, the `[sys.executable, "-c", script]` argv, the `$CNT`
  counter) — do not import it across modules. Assert the same shape at **all three** sites,
  not just the reviewer's, or the twin-blindness face survives. **C4 red-leg import trap:**
  import only pre-existing API at module level (`from pdca_harness import leaves`) and drive
  through pre-existing entry points, since a red-leg import failure is recorded
  `PDCA-UNVERIFIABLE`, not red (`run-verify.sh:229-232`).
- **Scope (one logical fix) / out of scope:** Give the three harvest sites one owner, and
  through it make a harvest attempt-aware: what a dead attempt left at the artifact path is
  preserved as that attempt's account and cannot be reported as a later attempt's work, and
  every reader of the resulting classification — including the leaf-status label — is told
  the truth by consulting that one owner rather than restating it. **Out of scope:** the
  record half (child-1's — do not revisit the per-attempt flush, the unsettled marker, or the
  four `*.error.log` readers except where this child's own change makes one false); the
  builder path (`#537` — `_do_build_command` `:1824`, `do_build`'s capture `:1765-1778`,
  `_build_prompt` `:1834`, `_stub_build` `:1889`); what counts *as* a transient death (`#539`
  — `progress.py`, `LeafError.transient` `:103-108`, any signal-death predicate); a
  lane/worktree reset between attempts; any new `pdca.toml` knob; #371; #510's remedy; the
  nine other leaves still on plain `_invoke`. Do **not** create `template/tests/fixtures/`.
- **External dependencies:** none — the base toolchain suffices; every leg is driven by a
  stub "leaf" that is a Python interpreter.
- **Test file:** `template/tests/test_attempt_harvest.py` (**new**, and confirmed at Plan to
  collide with nothing tracked in the target). It must be a **new** file rather than an
  append to child-1's `test_attempt_ownership.py`, and the binding reason is C5: the gate
  keys on *newly added* test files, so an append prints "patch adds no new test file —
  nothing to assert" — the degradation that let two unfaithful-stub findings survive to the
  adversary for three rounds. (A secondary, non-blocking effect: C4 runs every test file the
  patch touches, so an append would also re-run child-1's tests on this bundle's legs. Those
  would pass — child-1's production code is in this bundle's base, not in its patch — so it
  costs noise, not a false verdict.) Do **not** touch `test_leaf_resilience.py` or
  `test_attempt_ownership.py`.
- **Difficulty:** high
- **Depends on:** 540
- **Conflicts with:** 539
- **Ordering note:** Child-2 of the split of #536. `Depends on: 540` for two independent
  reasons, either of which alone forces the order: (a) semantic — this slice must know
  *which attempt is live* to refuse a dead attempt's artifact, and that notion is exactly
  what #540 creates; (b) textual — both edit the body of `_invoke_leaf_resilient`'s
  `for attempt` loop (`leaves.py:705-719`), so they are never co-scheduled. The wave fold
  gives you #540's version of that loop — read it before editing. `Conflicts with: 539`
  because #539 rewrites the strings and comments in that same function; do not adopt its
  `"on transient infra"` wording. `#537` (`Depends on: 540, 541`) stacks after this.

## Iteration 1 — carry-forward (from the previous attempt)
- Sign-off rationale: Rebuild for issue_541. The slice itself is right and the core landed: all three harvest sites genuinely share one owner (criterion 6 — the whole point of this child), and the red→green is honest (independently re-verified through the real entry points). Do NOT re-open the structure or re-slice; fix the three findings the adversary raised and keep everything else as built. 1. The un-owned refusal can destroy a LIVE verdict (leaves.py:836-841). `unlink()` needs write permission on the DIRECTORY; `open(path,"w")` needs it only on the FILE — so in the very scenario the patch's own test builds (dying attempt does `chmod(".", 0o500)`), the next attempt can still overwrite the residue with its complete real review, and the harvest then refuses it. The live verdict dies with the temp dir while the bundle says "NOT COMPLETED". Settle ownership by content/inode comparison against the bytes already read in `withdraw` (leaves.py:851-857): if the file at the path is no longer the dead attempt's, it is the live attempt's work and must be harvested. That satisfies criterion 3 without weakening criterion 5's refusal, so the two stop colliding. Test gap to close with it: every `lock=True` leg passes the default `live=""` (test_attempt_harvest.py:150,236,251,284) — no leg has a live attempt writing under a locked sandbox. Add that leg. 2. The withdrawn residue is quoted with NO bound into a tracked bundle file. leaves.py:852 reads the whole artifact and :905-907 embeds it whole, once per attempt. Measured: a 3.2 MB artifact dying transiently three times yields a 9.6 MB `check-review.error.log`, held in memory first, plus a `.partial` sibling — committed into project history, since `results/` is tracked and only `results/issue_selftest/` is ignored. Cap it head/tail with an elision line, exactly like the channel it mirrors (`progress.py:176`, `deque(maxlen=200)`). 3. The unknown-status fallback demotes REAL findings (assemble.py:191). `leaf_status` matches the marker ANYWHERE in the artifact, so an artifact carrying a full verdict table and real `NEEDS-HUMAN [impl]` items — one merely QUOTING a marker with an unknown token — comes back labelled "leaf produced no verdict" for every item, losing the #264 `[impl]` routing. Pre-fix an unknown token gave "" and left the artifact alone. This is self-triggering in this repo and the brief never asked for it (criterion 4 is about the leaf-status LABEL, not about unrecognised markers). Either require the marker in the placeholder's own header region, or keep "" for an artifact that carries a verdict table — restoring the old behaviour while keeping the #541 label. Not in scope for the rebuild: the T5 dependency-ordering item is a publish-time concern, not a patch defect — the stack base (`pdca-integration/main`, on #540's `480fa6b`) is already correct.
- Sign-off session carry-forward (captured live, before §9 flattened it):
  Rebuild for issue_541. The slice itself is right and the core landed: all three
  harvest sites genuinely share one owner (criterion 6 — the whole point of this
  child), and the red→green is honest (independently re-verified through the real
  entry points). Do NOT re-open the structure or re-slice; fix the three findings
  the adversary raised and keep everything else as built.

  1. The un-owned refusal can destroy a LIVE verdict (leaves.py:836-841).
     `unlink()` needs write permission on the DIRECTORY; `open(path,"w")` needs it
     only on the FILE — so in the very scenario the patch's own test builds
     (dying attempt does `chmod(".", 0o500)`), the next attempt can still overwrite
     the residue with its complete real review, and the harvest then refuses it.
     The live verdict dies with the temp dir while the bundle says "NOT COMPLETED".
     Settle ownership by content/inode comparison against the bytes already read in
     `withdraw` (leaves.py:851-857): if the file at the path is no longer the dead
     attempt's, it is the live attempt's work and must be harvested. That satisfies
     criterion 3 without weakening criterion 5's refusal, so the two stop colliding.
     Test gap to close with it: every `lock=True` leg passes the default `live=""`
     (test_attempt_harvest.py:150,236,251,284) — no leg has a live attempt writing
     under a locked sandbox. Add that leg.

  2. The withdrawn residue is quoted with NO bound into a tracked bundle file.
     leaves.py:852 reads the whole artifact and :905-907 embeds it whole, once per
     attempt. Measured: a 3.2 MB artifact dying transiently three times yields a
     9.6 MB `check-review.error.log`, held in memory first, plus a `.partial`
     sibling — committed into project history, since `results/` is tracked and only
     `results/issue_selftest/` is ignored. Cap it head/tail with an elision line,
     exactly like the channel it mirrors (`progress.py:176`, `deque(maxlen=200)`).

  3. The unknown-status fallback demotes REAL findings (assemble.py:191).
     `leaf_status` matches the marker ANYWHERE in the artifact, so an artifact
     carrying a full verdict table and real `NEEDS-HUMAN [impl]` items — one merely
     QUOTING a marker with an unknown token — comes back labelled "leaf produced no
     verdict" for every item, losing the #264 `[impl]` routing. Pre-fix an unknown
     token gave "" and left the artifact alone. This is self-triggering in this repo
     and the brief never asked for it (criterion 4 is about the leaf-status LABEL,
     not about unrecognised markers). Either require the marker in the placeholder's
     own header region, or keep "" for an artifact that carries a verdict table —
     restoring the old behaviour while keeping the #541 label.

  Not in scope for the rebuild: the T5 dependency-ordering item is a publish-time
  concern, not a patch defect — the stack base (`pdca-integration/main`, on #540's
  `480fa6b`) is already correct.
- Full previous attempt preserved in `iteration-v1/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).

## Iteration 2 — carry-forward (from the previous attempt)
- Sign-off rationale: Rebuild for issue_541, round 3. The slice is right and the core landed again: all three harvest sites genuinely share one owner (criterion 6 — the point of this child), the retry budget is untouched (criterion 5), and the red→green is honest through the real entry points. Do NOT re-open the structure, do NOT re-slice, and keep everything else as built. Two of the three round-2 carry-forward remedies were only PARTIALLY closed, and the code review found a third defect inside the fix itself. Close these three, nothing more. 1. assemble.py:112 — the header-region remedy is defeated by an early fenced quote. `_LEAF_STATUS_HEADER_LINES = 8` (used at :122-131 and :211) classifies a REAL artifact as a placeholder when it quotes an unknown status token as a standalone line inside a fenced block that opens in the first 8 lines (fence at line 5, marker at line 6). Measured: two genuine `NEEDS-HUMAN [impl]` findings come back `human` prefixed "leaf produced no verdict (unrecognised leaf status …)" — the #264 `[impl]` routing is stripped, still a regression against the base, and self-triggering in this repo. The guard at tests/test_attempt_harvest.py:376 only misses the hole by construction (its fence sits at line 10+) and passes with the production change reverted, so C4 covers none of it. Prefer the OTHER remedy the round-2 carry-forward offered — keep "" for an artifact that carries a verdict table / findings — which is not subject to a line-position accident and holds in this case. Add a leg with the fence at line 5. 2. leaves.py:891-909 — `_live_attempt_overwrote_it` is digest-only; the carry-forward asked for content/INODE. Two measured cases still destroy a LIVE verdict (both regressions against the base), driven through `_run_review_sandboxed`: (a) a residue that could not be READ sets `_unreadable = True` permanently (:941-947, consumed at :856), so an attempt that writes its complete review atomically via temp file + `os.replace` and exits 0 is refused — "live verdict filed?" pre-fix True, post-fix False, with an un-owned placeholder in its place; (b) content equality cannot distinguish "nobody rewrote it" from "rewritten byte-identically" (:909) — a deterministic command-mode leaf writing identical bytes on attempt 2 has its verdict discarded. Record `st_ino` / `st_mtime_ns` at withdraw time and treat any stat change as the live attempt's file: that closes both, including the unreadable case, since the residue's identity is knowable even when its bytes are not. Existing guard at tests/test_attempt_harvest.py:263 cannot see (b) — its live text differs from the residue. 3. leaves.py:861-884 — `withdraw()` re-quotes the SAME un-removable residue for every subsequent dead attempt. Once one attempt's file cannot be unlinked (the patch's own `lock=True` shape), it is still at `self.produced` when the next attempt dies, and `withdraw()` has no "have I already accounted for this residue?" check: it reads it again, fails to unlink it again, and emits another `_record(attempt, …)` claiming THAT attempt left it — even though that invocation never wrote. `_drive(..., deaths=3, lock=True)` yields the same residue quoted three times, attributed to attempts 1, 2 and 3 — reintroducing "no notion of which attempt wrote it" one level down, inside the fix for it, plus tripling the read+sha256 on a large residue. `self._residues` is already populated for exactly this: return "" (or a "same as a prior attempt's" note, not a fresh "attempt N left…" block) when the file is unchanged from what a previous withdraw already recorded and failed to remove. The current test only asserts `assertIn(_DEAD_MARK, …)` plus the attempt count, so add a leg that asserts the residue is accounted for ONCE. Not defects against the brief, do not spend the round on them: the ~600 KB worst-case residue quoting (the head/tail cap asked for was delivered; the bound is per-read, not total), the UTF-8 split at the `readline` boundary in `_read_residue` (cosmetic, display text only), and the pre-existing `assemble.leaf_status()` readers at leaves.py:3333 / size_signal.py:240 (identical before and after this diff — Act candidate, not this child's). The T5 ordering item is a publish-time concern, not a patch defect: the stack base (`pdca-integration/main`, on #540) is already correct.
- Sign-off session carry-forward (captured live, before §9 flattened it):
  Rebuild for issue_541, round 3. The slice is right and the core landed again: all three
  harvest sites genuinely share one owner (criterion 6 — the point of this child), the retry
  budget is untouched (criterion 5), and the red→green is honest through the real entry points.
  Do NOT re-open the structure, do NOT re-slice, and keep everything else as built. Two of the
  three round-2 carry-forward remedies were only PARTIALLY closed, and the code review found a
  third defect inside the fix itself. Close these three, nothing more.

  1. assemble.py:112 — the header-region remedy is defeated by an early fenced quote.
     `_LEAF_STATUS_HEADER_LINES = 8` (used at :122-131 and :211) classifies a REAL artifact as a
     placeholder when it quotes an unknown status token as a standalone line inside a fenced
     block that opens in the first 8 lines (fence at line 5, marker at line 6). Measured: two
     genuine `NEEDS-HUMAN [impl]` findings come back `human` prefixed "leaf produced no verdict
     (unrecognised leaf status …)" — the #264 `[impl]` routing is stripped, still a regression
     against the base, and self-triggering in this repo. The guard at
     tests/test_attempt_harvest.py:376 only misses the hole by construction (its fence sits at
     line 10+) and passes with the production change reverted, so C4 covers none of it.
     Prefer the OTHER remedy the round-2 carry-forward offered — keep "" for an artifact that
     carries a verdict table / findings — which is not subject to a line-position accident and
     holds in this case. Add a leg with the fence at line 5.

  2. leaves.py:891-909 — `_live_attempt_overwrote_it` is digest-only; the carry-forward asked
     for content/INODE. Two measured cases still destroy a LIVE verdict (both regressions
     against the base), driven through `_run_review_sandboxed`:
     (a) a residue that could not be READ sets `_unreadable = True` permanently (:941-947,
         consumed at :856), so an attempt that writes its complete review atomically via temp
         file + `os.replace` and exits 0 is refused — "live verdict filed?" pre-fix True,
         post-fix False, with an un-owned placeholder in its place;
     (b) content equality cannot distinguish "nobody rewrote it" from "rewritten
         byte-identically" (:909) — a deterministic command-mode leaf writing identical bytes on
         attempt 2 has its verdict discarded.
     Record `st_ino` / `st_mtime_ns` at withdraw time and treat any stat change as the live
     attempt's file: that closes both, including the unreadable case, since the residue's
     identity is knowable even when its bytes are not. Existing guard at
     tests/test_attempt_harvest.py:263 cannot see (b) — its live text differs from the residue.

  3. leaves.py:861-884 — `withdraw()` re-quotes the SAME un-removable residue for every
     subsequent dead attempt. Once one attempt's file cannot be unlinked (the patch's own
     `lock=True` shape), it is still at `self.produced` when the next attempt dies, and
     `withdraw()` has no "have I already accounted for this residue?" check: it reads it again,
     fails to unlink it again, and emits another `_record(attempt, …)` claiming THAT attempt left
     it — even though that invocation never wrote. `_drive(..., deaths=3, lock=True)` yields the
     same residue quoted three times, attributed to attempts 1, 2 and 3 — reintroducing "no
     notion of which attempt wrote it" one level down, inside the fix for it, plus tripling the
     read+sha256 on a large residue. `self._residues` is already populated for exactly this:
     return "" (or a "same as a prior attempt's" note, not a fresh "attempt N left…" block) when
     the file is unchanged from what a previous withdraw already recorded and failed to remove.
     The current test only asserts `assertIn(_DEAD_MARK, …)` plus the attempt count, so add a leg
     that asserts the residue is accounted for ONCE.

  Not defects against the brief, do not spend the round on them: the ~600 KB worst-case residue
  quoting (the head/tail cap asked for was delivered; the bound is per-read, not total), the
  UTF-8 split at the `readline` boundary in `_read_residue` (cosmetic, display text only), and
  the pre-existing `assemble.leaf_status()` readers at leaves.py:3333 / size_signal.py:240
  (identical before and after this diff — Act candidate, not this child's). The T5 ordering item
  is a publish-time concern, not a patch defect: the stack base (`pdca-integration/main`, on
  #540) is already correct.
- Full previous attempt preserved in `iteration-v2/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).

## Iteration 3 — carry-forward (from the previous attempt)
- Sign-off rationale: REPLAN — re-author this ONE brief. Do NOT split: the human ruled at sign-off that this stays a single slice (it is already depth 3 of the #536 split, siblings #540/#537, and does not need deepening again). Return to Plan because the remaining work needs SPECIFYING, not because the slice is too big. WHY PLAN AND NOT A REBUILD: the remaining defect is no longer "tighten a matching rule" but a redesign of the leaf-status mechanism, and three consecutive rounds have shown Do cannot author it from a carry-forward paragraph. Round 2 shipped "match the marker anywhere", holed by a quoted marker. Round 3 shipped an 8-line header window, holed by a fenced block opening at line 5. Round 4 made `unowned-empty` a recognised token, which self-triggers on any artifact that quotes it — including any advisory reviewing this very issue. Each round closed the previous hole and opened a new one in the same mechanism, because each round was given the destination and left to guess the route. The replanned brief must specify the route. WHAT THE REPLANNED BRIEF KEEPS — criteria 1, 2, 3, 5, 6 are MET by the patch in this bundle and must be carried forward as "keep as built", not re-derived. All three lenses confirm it; the code-review lens found no correctness bug at all. Specifically: all three harvest sites share one owner and `_LeafHarvest.run` is the only caller of `_invoke_leaf_resilient`, so a fourth site cannot grow its own copy (criterion 6, stronger than the brief asked); the retry contract is untouched, `_runs() == 3` under a locked sandbox (criterion 5); the residue de-dup accounts for an un-removable residue exactly once across three deaths; the residue quote is head/tail bounded; the red->green is honest through the real entry points and was independently re-reproduced by both advisory lenses. Do not re-open the structure and do not re-slice. WHAT THE REPLANNED BRIEF RE-SPECIFIES — criterion 4 only (the leaf-status label / marker). DESIGN CHOSEN BY THE HUMAN AT SIGN-OFF — this is the intent to specify, not an open question: invert the marker to a POSITIVE COMPLETION signal, written as the LAST LINE of the artifact, and written BY THE LEAF ITSELF. Its presence means the artifact closed successfully; its ABSENCE means something did not close, and those cases get surfaced and worked through one by one. WHY THIS BEATS THE ALTERNATIVES (record the reasoning, do not re-litigate it): - It removes the use/mention collision that has now defeated three implementations. Only the final line is consulted, so a real report may quote the marker anywhere in its body — which is exactly what any advisory reviewing this harness must do — with no effect. - A leaf-written trailer detects TRUNCATION, which is the actual defect class here (a dying attempt leaves a half-written report). A harness-written stamp applied on exit 0 would only re-assert "the process exited cleanly", which the harness already knows, and would still stamp a report whose generation stopped mid-way. QUESTIONS THE REPLAN MUST ANSWER IN THE BRIEF — leaving any of these to Do repeats the loop: 1. Non-cooperating leaves. Leaves are arbitrary external commands, including third-party ones; nothing can compel them to emit a trailer. Model-backed leaves can be INSTRUCTED via their prompt; non-model command leaves cannot. Specify per-leaf-kind behaviour, or a declared capability, so a leaf that cannot stamp is not permanently read as failing. 2. False "incomplete". A model leaf that finishes correctly but omits the trailer reads as a failure. Specify the tolerance — corroborate against the exit code and the ownership signal this bundle's `_LeafHarvest` already computes, rather than trusting the trailer alone. 3. Legacy migration. NO existing artifact in ANY bundle carries the trailer, so on the day this lands the entire back catalogue reads as "did not close successfully" — including every artifact the corpus / size-signal scripts read. Specify the legacy rule ("no trailer AND no recorded failure ⇒ legacy, stay quiet"), or state deliberately that history should flag. The human's "catch them one by one" was said of GOING FORWARD; confirm the scope at Plan. 4. The #278 contract. The existing guard (tests/test_leaf_status.py:194, `test_an_impl_tagged_finding_in_a_placeholder_cannot_smuggle_in_impl`) exists to stop findings being smuggled out of placeholders. An inverted marker must keep that property. 5. All THREE readers, not one. `leaf_status` is read at assemble.py:168, size_signal.py:240 and leaves.py:3057; this bundle's patch only goes near the first. The marker is WRITTEN at exactly one site today (leaves.py:2664, `_unavailable_classification` — the harness's own placeholder generator; no leaf writes it now), so the redesign adds a write site in the leaf path and must convert every reader together. Say so in the brief's scope. DECISIONS ALREADY TAKEN AT SIGN-OFF — carry into the replanned brief, do not re-open: - The metadata-only-touch hole is ACCEPTED and lived with (the reviewer's C3/C5 FAIL; identity at leaves.py:1074 includes st_mtime_ns/st_ctime_ns, so a live attempt that only chmods or utimes an artifact moves the tuple, the ownership lookup misses, and a dead attempt's artifact can still be harvested). The human accepted this knowingly, to see whether it occurs in practice; it is filed as an issue and recorded in SUMMARY §10. Do NOT change `_residue_identity`, do NOT remove `st_ctime_ns`, do NOT add a digest cross-check on a moved identity. If it is ever observed in the wild it returns as its own issue. - The related Validation / fitness-to-purpose question (may real leaves perform metadata-only permission repair) is answered by that same acceptance. - T5 dependency ordering on #540 is CONFIRMED as a publish-time concern, not a patch defect; `stack-base` already reads `pdca-integration/main`, which carries #540. EVIDENCE NOTE FOR THE REPLAN: the round-4 adversary measured the current defect against base on an artifact holding a fenced quote of the `unowned-empty` marker plus one genuine `[impl]` finding — base gave `impl` with autoiterate eligible, patched gave `human`, not eligible, with the finding's #264 routing stripped. The replanned brief must name that shape as a required test leg, and require it to be genuinely RED on the base: the existing guard (tests/test_attempt_harvest.py:449, token `some-future-status`) is green pre-fix and therefore proves nothing. More generally the adversary observed that the whole identity mechanism carries no red->green proof (tests/test_attempt_harvest.py:304,324,340 are green pre-fix as well as post), which is structurally how the round-4 hole survived into a fourth round.
- Sign-off session carry-forward (captured live, before §9 flattened it):
  REPLAN — re-author this ONE brief. Do NOT split: the human ruled at sign-off that this stays a
  single slice (it is already depth 3 of the #536 split, siblings #540/#537, and does not need
  deepening again). Return to Plan because the remaining work needs SPECIFYING, not because the
  slice is too big.

  WHY PLAN AND NOT A REBUILD: the remaining defect is no longer "tighten a matching rule" but a
  redesign of the leaf-status mechanism, and three consecutive rounds have shown Do cannot author
  it from a carry-forward paragraph. Round 2 shipped "match the marker anywhere", holed by a
  quoted marker. Round 3 shipped an 8-line header window, holed by a fenced block opening at line
  5. Round 4 made `unowned-empty` a recognised token, which self-triggers on any artifact that
  quotes it — including any advisory reviewing this very issue. Each round closed the previous
  hole and opened a new one in the same mechanism, because each round was given the destination
  and left to guess the route. The replanned brief must specify the route.

  WHAT THE REPLANNED BRIEF KEEPS — criteria 1, 2, 3, 5, 6 are MET by the patch in this bundle and
  must be carried forward as "keep as built", not re-derived. All three lenses confirm it; the
  code-review lens found no correctness bug at all. Specifically: all three harvest sites share
  one owner and `_LeafHarvest.run` is the only caller of `_invoke_leaf_resilient`, so a fourth
  site cannot grow its own copy (criterion 6, stronger than the brief asked); the retry contract
  is untouched, `_runs() == 3` under a locked sandbox (criterion 5); the residue de-dup accounts
  for an un-removable residue exactly once across three deaths; the residue quote is head/tail
  bounded; the red->green is honest through the real entry points and was independently
  re-reproduced by both advisory lenses. Do not re-open the structure and do not re-slice.

  WHAT THE REPLANNED BRIEF RE-SPECIFIES — criterion 4 only (the leaf-status label / marker).

    DESIGN CHOSEN BY THE HUMAN AT SIGN-OFF — this is the intent to specify, not an open question:
    invert the marker to a POSITIVE COMPLETION signal, written as the LAST LINE of the artifact,
    and written BY THE LEAF ITSELF. Its presence means the artifact closed successfully; its
    ABSENCE means something did not close, and those cases get surfaced and worked through one by
    one.

    WHY THIS BEATS THE ALTERNATIVES (record the reasoning, do not re-litigate it):
    - It removes the use/mention collision that has now defeated three implementations. Only the
      final line is consulted, so a real report may quote the marker anywhere in its body — which
      is exactly what any advisory reviewing this harness must do — with no effect.
    - A leaf-written trailer detects TRUNCATION, which is the actual defect class here (a dying
      attempt leaves a half-written report). A harness-written stamp applied on exit 0 would only
      re-assert "the process exited cleanly", which the harness already knows, and would still
      stamp a report whose generation stopped mid-way.

    QUESTIONS THE REPLAN MUST ANSWER IN THE BRIEF — leaving any of these to Do repeats the loop:
    1. Non-cooperating leaves. Leaves are arbitrary external commands, including third-party
       ones; nothing can compel them to emit a trailer. Model-backed leaves can be INSTRUCTED via
       their prompt; non-model command leaves cannot. Specify per-leaf-kind behaviour, or a
       declared capability, so a leaf that cannot stamp is not permanently read as failing.
    2. False "incomplete". A model leaf that finishes correctly but omits the trailer reads as a
       failure. Specify the tolerance — corroborate against the exit code and the ownership
       signal this bundle's `_LeafHarvest` already computes, rather than trusting the trailer
       alone.
    3. Legacy migration. NO existing artifact in ANY bundle carries the trailer, so on the day
       this lands the entire back catalogue reads as "did not close successfully" — including
       every artifact the corpus / size-signal scripts read. Specify the legacy rule ("no trailer
       AND no recorded failure ⇒ legacy, stay quiet"), or state deliberately that history should
       flag. The human's "catch them one by one" was said of GOING FORWARD; confirm the scope at
       Plan.
    4. The #278 contract. The existing guard (tests/test_leaf_status.py:194,
       `test_an_impl_tagged_finding_in_a_placeholder_cannot_smuggle_in_impl`) exists to stop
       findings being smuggled out of placeholders. An inverted marker must keep that property.
    5. All THREE readers, not one. `leaf_status` is read at assemble.py:168, size_signal.py:240
       and leaves.py:3057; this bundle's patch only goes near the first. The marker is WRITTEN at
       exactly one site today (leaves.py:2664, `_unavailable_classification` — the harness's own
       placeholder generator; no leaf writes it now), so the redesign adds a write site in the
       leaf path and must convert every reader together. Say so in the brief's scope.

  DECISIONS ALREADY TAKEN AT SIGN-OFF — carry into the replanned brief, do not re-open:
  - The metadata-only-touch hole is ACCEPTED and lived with (the reviewer's C3/C5 FAIL; identity
    at leaves.py:1074 includes st_mtime_ns/st_ctime_ns, so a live attempt that only chmods or
    utimes an artifact moves the tuple, the ownership lookup misses, and a dead attempt's
    artifact can still be harvested). The human accepted this knowingly, to see whether it occurs
    in practice; it is filed as an issue and recorded in SUMMARY §10. Do NOT change
    `_residue_identity`, do NOT remove `st_ctime_ns`, do NOT add a digest cross-check on a moved
    identity. If it is ever observed in the wild it returns as its own issue.
  - The related Validation / fitness-to-purpose question (may real leaves perform metadata-only
    permission repair) is answered by that same acceptance.
  - T5 dependency ordering on #540 is CONFIRMED as a publish-time concern, not a patch defect;
    `stack-base` already reads `pdca-integration/main`, which carries #540.

  EVIDENCE NOTE FOR THE REPLAN: the round-4 adversary measured the current defect against base on
  an artifact holding a fenced quote of the `unowned-empty` marker plus one genuine `[impl]`
  finding — base gave `impl` with autoiterate eligible, patched gave `human`, not eligible, with
  the finding's #264 routing stripped. The replanned brief must name that shape as a required
  test leg, and require it to be genuinely RED on the base: the existing guard
  (tests/test_attempt_harvest.py:449, token `some-future-status`) is green pre-fix and therefore
  proves nothing. More generally the adversary observed that the whole identity mechanism carries
  no red->green proof (tests/test_attempt_harvest.py:304,324,340 are green pre-fix as well as
  post), which is structurally how the round-4 hole survived into a fourth round.
- Full previous attempt preserved in `iteration-v3/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).
