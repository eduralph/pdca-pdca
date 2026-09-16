- **Slug:** a-leafs-own-account-of-its-death-is-kept
- **Defect / goal:** `progress.run_with_heartbeat` reads every event a leaf's stream emits and
  keeps none of it. The drain parses stdout for a session flag and a tool label, then discards
  the line (`progress.py:150-159`); what it retains is a bounded **stderr** tail (`:143`,
  `:162-168`), and with `capture` off `output` is that stderr tail alone (`:255`, `:257`). The
  CLI's own API-error report arrives as a stream *text* event on **stdout**, so it is displayed
  and dropped, and `_format_leaf_attempt` falls back to `(no output captured)` (`leaves.py:729`)
  — verbatim what the reported incident's `build.error.log` contained. The cause of an 18-minute
  death was legible only in the CLI's session transcript under `~/.claude/projects/`, which no
  post-mortem reads. `leaves.py:641-647` already states the rule this breaks: `(no output
  captured)` is "a post-mortem artifact that explains nothing".
- **Success criterion:** With the patch: (i) when a leaf's stream carried the CLI's **own marked
  terminal error report** — the message the vendor itself flags as its API-error report — that
  text is in the leaf's `*.error.log`, reaching it by the same route the stderr tail takes
  (appended to what `run_with_heartbeat` returns as `output`), so a post-mortem explains the
  failure without opening `~/.claude/projects/`; (ii) retention is **unconditional** — every
  marked report is kept whatever its cause, *including* one the session then recovered from,
  because a harness holding the text must never file `(no output captured)`; (iii) a report the
  CLI forwarded for a **sub-agent** (the Task's `parent_tool_use_id`, or `isSidechain` in the
  persisted-transcript spelling) is kept **labelled as such**, never presented as the leaf's own
  death — a log that confidently names the wrong death is worse than the silence it replaces;
  (iv) where a stream carries several candidate records, the one nearest the leaf's own death
  wins and a farther one (a `result` wrap-up naming only the effect, a sub-agent's report) cannot
  bury it, in either arrival order; (v) **nothing is classified** — `produced`,
  `LeafError.transient` and the retry counts are byte-identical to today for every input: a leaf
  retried 3 times today is retried 3 times after this, and one retried 0 times still is;
  (vi) nothing else changes — `capture` still returns the child's raw stdout unmodified (confirm
  the appended text cannot leak into a gate's evidence line: the leaf spawn at `leaves.py:657` is
  the only caller that does not pass `capture=True` — the other three, `gates.py:559`,
  `publish.py:833` and `leaves.py:752`, all do), the
  codex/gemini stream formats degrade to today's behaviour, a stream-less family is untouched, a
  leaf that exits 0 is spawned and reported exactly as today, and the #420 memory-telemetry
  post-mortem (`leaves.py:663-666`) still rides `output` into the same log.
- **Falsifiability:** RED is reachable offline on the base toolchain — pure-stdlib Python ≥ 3.11
  + git, no vendor CLI, no network, no API key — in the target checkout Do is given.
  `template/tests/test_leaf_resilience.py:26-40` ships the harness shape to **copy** (do not
  import across modules): a stub "leaf" whose argv is `[sys.executable, "-c", script]`, emitting
  chosen stream events on stdout and exiting non-zero, plus a `$CNT` file counting invocations;
  `:58` shows the `attempts=3, backoff=0.0` spelling that keeps the suite fast. Drive it through
  `leaves._invoke_leaf_resilient` (resilient on **any** base, so no dependency on #537) and
  through `progress.run_with_heartbeat` directly. Today a leaf that emits a work event, then the
  CLI's marked report, then exits 1 with empty stderr writes an error log reading
  `----- attempt 1 — exit 1 -----` / `(no output captured) LeafError: …`, so every retention
  assertion fails pre-fix. That is the red. (v) is a guard, green on both legs by design: assert
  the invocation counts explicitly so a later change cannot silently move them.
  **Two gate traps, measured against this instance's C4 gate.** `run-verify.sh:131-137` counts
  only `tests/*.py` / `template/tests/*.py` as tests and `*.md` as non-behavioural, so a
  `…/fixtures/*.jsonl` is **production** and is reverted on the red leg (`:214-217`): a case that
  only replays a fixture goes red because the file is *gone* — a vacuous red. Construct at least
  one case per criterion **inline in the test module**, and make any fixture-replaying case
  `skipTest` (not error) when its fixture is absent. Second: the red leg keeps every
  `template/tests/*.py` hunk, so a **new** test file earns a genuine red *provided it imports no
  symbol this patch adds at module level* — a red-leg import failure is recorded
  `PDCA-UNVERIFIABLE`, not red (`run-verify.sh:231-233`). Import only pre-existing API
  (`from pdca_harness import progress, leaves`) and assert behaviourally.
- **Invariant to restore:** **The evidence of a failure is kept** — the retention half of "a
  failure is classified by what actually happened, and the evidence of it is kept". Stated over
  the category, not this incident: when the harness is already reading a child's own account of
  its death, it must retain that account in the artifact the cycle preserves, and must never
  attribute it to a death it does not describe. "No evidence" must never be filed as a verdict.
  Self-test: it cannot be met by guarding a single module — the reading happens in the stream
  drain, the keeping in what `output` carries, and the consumer is every `*.error.log` the harness
  writes. Source: internal project invariant (Tier C), the target's own written rules —
  `leaves.py:641-647` (`(no output captured)` is "a post-mortem artifact that explains nothing",
  #286 review), `progress.py:55-64`, `engine/README.md:44-68`. `docs/principles.md` §5/§6 are
  unfilled scaffolds in this instance, so no §6 category gate applies.
- **Repo + branch target:** eduralph/pdca-harness @ main (base `acb214a`; every `path:line` here
  was re-verified against it while this proposal was written)
- **Reproduction:** On a clean checkout of the target base, offline, from `template/`:
  1. `PYTHONPATH=src python3 -m unittest tests.test_leaf_resilience -v` — green today; read
     `:26-40` and `:58` for the stub-leaf harness, the `$CNT` counter and the fast-backoff
     spelling to copy.
  2. Read the drop at the lines cited in Defect above, plus `leaves.py:724-730` (the record
     format), and what the module already knows but does not use: `progress.py:55-64` and
     `_is_session_event` at `:359`/`:365-377`.
  3. The live incident is named in parent issue #506: getwyrd/wyrd-pdca `results/issue_717/`
     (`build.error.log`, `loop-telemetry.json`); an identical argv re-run minutes later succeeded.
- **Scope (one logical fix) / out of scope:** Read the CLI's own marked terminal error report out
  of the stream the drain already parses, decide **whose** death it describes and **which** record
  is nearest it, and keep that text so it reaches the leaf's `*.error.log` by the route the stderr
  tail already takes. **This child touches exactly one production file,
  `template/src/pdca_harness/progress.py`**, plus its own new test file and
  `template/tests/fixtures/`. **Out of scope — load-bearing, because three sibling bundles are
  live in the same run:** do **not** change `produced`, do **not** touch `LeafError.transient`
  (`leaves.py:104-107`), do **not** add a signal-death predicate, and do **not** add any notion of
  transient-vs-permanent cause, vendor error *kinds*, HTTP statuses, or a "the CLI recovered"
  clearing rule — that is child-2, which builds on this. Do **not** edit `leaves.py` or
  `assemble.py` **at all**: `_invoke_leaf_resilient`'s loop body, `_format_leaf_attempt`
  (`:724-730`) and the artifact harvests are #536's, `do_build` / `_build_prompt` /
  `_do_build_command` are #537's, and the prose restatements are child-2's. Also out: resuming a
  long session via the CLI's own session-resume; the gate-side transient (#371); issue #510; any
  new `pdca.toml` knob.
- **External dependencies:** none — the base toolchain suffices. Every leg is driven by a stub
  "leaf" that is a Python interpreter, so this builds and goes red→green with no vendor CLI, no
  API key, no network and no container. Grounding the event shape against the vendor is a
  *reading* step, not a build or verification input.
- **Test file:** `template/tests/test_terminal_error_retention.py` (**new**), plus
  `template/tests/fixtures/` for the pinned vendor records and a provenance note scoped to the
  claims THIS child depends on (the marker, the sub-agent spelling); child-2 appends its
  kind/status provenance to the same note on its own base. A **new** file, not an append:
  `engine/scripts/run-prod-path.py:88-90` keys C5 on *newly added* test files and prints "patch
  adds no new test file — nothing to assert" for an append. Do **not** touch
  `test_leaf_resilience.py`, `test_build_error_log.py`, `test_attempt_ownership.py` or
  `test_builder_retry.py` — the last three are #536/#537's, building in this same run, and a
  shared test file is the one place the patches would collide.
- **Difficulty:** medium — blast-radius is one production file, additive, no control-flow or
  classification change; beyond it a diff-reviewer holds the four `run_with_heartbeat` call sites
  and the #420 telemetry append. The *reasoning* depth here is vendor grounding, not reach — hence
  the `Do model` pin rather than a `high` tag.
- **Do model:** opus
- **Ordering note:** **No ordering field is set, and that is deliberate — not an omission.** This
  bundle touches exactly one production file, `template/src/pdca_harness/progress.py`, which the
  three sibling bundles live in this same run all place explicitly out of scope: **#536** and
  **#537** (issue #532's children) each state "do **not** touch `progress.py`", and sibling **#539**
  owns the classification half and declares `Depends on: 538`. So there is nothing to conflict
  with and nothing to build on, and this bundle runs in **wave k alongside #536**. The one thing
  that would break that: if this build strays into `leaves.py` or `assemble.py`, it collides with
  #536/#537 on a base neither was built against — which is why Scope forbids touching them at all.
- **Citations expected:** Do must cite `path:line` on the target branch for every change.
  Composition cues: `progress._is_session_event` (`:365-377`) is the existing per-family stream
  classifier — it dispatches on `stream_format`, parses JSON best-effort and defaults to `False`.
  The terminal-report reader belongs **beside it, in the same shape**, so codex/gemini degrade to
  today's behaviour instead of guessing. `:143` + `:162-168` show how a bounded tail is kept
  (`deque(maxlen=…)`) and `:255` how it becomes `output` — the retained report must reach
  `LeafError.output` by that same route, so `_format_leaf_attempt` (#536's file) needs no special
  case and this child need not touch it. `leaves.py:663-666` is the one existing precedent for
  appending to `output` on a failure (the #420 post-mortem) — mirror it rather than inventing a
  second shape. **Vendor grounding is the standard here:** two of parent #506's four rejected
  rounds were rejected for asserting an event shape the CLI cannot emit, and the round that held
  re-derived it from the shipped binary. Establish the marker and the sub-agent spelling from the
  installed `claude` CLI and/or a real transcript under `~/.claude/projects/`, and record beside
  the fixture which claims are **observed** and which **derived**. **Prior art, read selectively:**
  round 3's patch is archived at `results/issue_533/iteration-v3/patch.diff` (+ `build-notes.md`,
  `SUMMARY.md`); its mechanism was confirmed by reviewer and adversary and it was returned for
  slice size and the #532 boundary, **not** for approach. Read only its retention-side hunks — the
  matcher anchored on the vendor's own flag, `_is_subagent_event` used as the single predicate so
  the stream and persisted-transcript spellings cannot drift apart, the record-precedence table,
  the bounded report line. Re-verify what you take against the current base. Do **not** carry its
  classification hunks (kind sets, clearing rule, signal-death predicate) — that would recreate
  the oversized slice this split exists to undo.
- **Prior-art check (triage cycles):** By file path on `origin/main`: `progress.py` — `0881af9`
  (#420), `4091b94` (straggler sweep), `228e80b` (#368), `49f6611` (#286, "capture a stream-less
  leaf's stderr too"): the closest relative, and it extended **stderr** capture — the stream's own
  events have never been read for anything but a tool label. Open PRs #519-#525: none touches
  `progress.py`. Open issues searched for `transient`: #371 and #510 are adjacent and deliberately
  excluded, #509 is a different beat. Not previously attempted as its own slice; #533's round 3
  and parent #506's four rounds were returned on slicing, never on mechanism.
- **Disposition hint:** likely-fix

## Iteration 1 — carry-forward (from the previous attempt)
- Sign-off rationale: Auto-iterate (round 1): Check found implementation-level items only, no architectural judgment required — worth asking the builder to parse once per line and pass
- Full previous attempt preserved in `iteration-v1/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).
