# Design proposal — issue 401 / deferred-gate-row-for-default-open-t4

> The Plan artifact for the exception: this changes the **gate-result vocabulary**, which is
> normative in the vendored model spec (`04-validation-tooling.md` §Gate result vocabulary,
> `08-glossary.md:153`) and read by `assemble`, `revalidate`, `flow`, `cli` and the reviewer —
> a data-model change with real alternatives, so it is authored as a proposal. Do reads ONLY
> this file and implements it; Check runs the regular gated check on the code.

- **Slug:** deferred-gate-row-for-default-open-t4
- **Kind:** enhancement (design proposal)
- **Goal:** A bundle-scoped gate that ran its **default-open** path at Check — the audit it
  performs has no subject yet, because the artifacts it lints are drafted later — is recorded
  distinguishably from a substantive pass, so the Check matrix stops asserting a green nobody
  can reproduce and the reviewer stops escalating a by-design condition to §6 on every cycle.
- **Success criterion:** With the patch applied, a Check-time run of the T4 row on a bundle that
  has `patch.diff` but no `pr-description.md` records a result that is **not** `pass` and **not**
  `unverifiable` — a `deferred` row that (a) does not count toward `overall`, (b) is **not**
  lifted into `SUMMARY.md` §6 NEEDS-HUMAN, and (c) names in its evidence that the substantive
  audit runs at publish; while the same row on a bundle whose artifacts **are** drafted still
  records the substantive `pass`/`fail` exactly as today, and `publish._t4_passes` still hard-
  gates before any push (unchanged). Demonstrable by C4-verify alone: the named test module is
  red with the production hunks reverted and green with them applied.
- **Falsifiability:** RED is producible offline on the environment Do gets — the offline driver
  suite runs real gate rows against real bundle directories with deterministic shell/`cli`
  commands, no model, container or network (`template/tests/test_gates_unverifiable.py`,
  `test_gate_logs.py`). A test asserting `result == "deferred"` for a bundle with `patch.diff`
  and no `pr-description.md` fails on `origin/main` today: `cli._contribcheck` returns 0 at
  `template/src/pdca_harness/cli.py:1078-1079` and `_classify` records a plain `pass` with
  **empty** evidence — frozen proof in `results/issue_387/check-gates.json`
  (`"check": "T4 PR body has a user-impact opener + tracker id in both artifacts",
  "result": "pass", "path_line": ""`). The pdca-pdca C4 wrapper counts
  `template/src/pdca_harness/{gates,cli}.py` as production and `template/tests/*.py` as tests
  (`engine/scripts/run-verify.sh:39-53`), so reverting the production hunks gives a real red leg.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Depends on:** 402
- **Conflicts with:** 384
- **Ordering note:** wave 2. This edits `_classify`/`_finalize`/`render_md` in
  `template/src/pdca_harness/gates.py` — the same function 428 (marker provenance, wave 0) and
  402 (evidence line, wave 1) rewrite — and it should build on the settled notion of a
  **gate-declared** state rather than introduce a third one, hence `Depends on: 402` (which
  itself depends on 428). It also edits the T4 registration block in
  `template/pdca.toml.jinja` and `cli._contribcheck`, both of which **384** touches in wave 0,
  hence the declared conflict; the dependency chain already places this bundle later, so the
  conflict is satisfied.
- **Surfaces:** data
- **Difficulty:** high
- **Scope:** one logical change — add `deferred` to the gate-result vocabulary as a
  gate-declared, non-gating, non-§6 state, emit it from `contribcheck`'s default-open path, and
  render/consume it consistently (matrix, `overall`, §6 lift, revalidate comparison, the
  reviewer's contract text, the spec docs and the `pdca.toml.jinja` comment that currently
  promises "default-open … so Check-time gates pass").
  / **out of scope:** the publish-time T4 semantics under `--no-issue` (issue 384, wave 0 — do
  not touch `publish.publish`'s relax branch or `_t4_passes`); a general `phase` property for
  gate rows (the larger change #339 records for later — deferral here is declared by the
  checker, not modelled as a new scope); the `unverifiable` marker rule (428) and the evidence
  line (402); any change to what `publish` enforces before a push.
- **External dependencies:** none
- **Test file:** `template/tests/test_gate_deferred.py` — a new module for the new vocabulary
  member (a new file is fine: this project's C4 gate reverts the *production* hunks and keeps
  the patch's tests, `engine/scripts/run-verify.sh:70-81`; it does **not** classify on added
  test files, so either shape earns its red). Bring the existing assertions that encode the old
  behaviour into step in the same patch — `template/tests/test_gate_logs.py:111` (the row key
  set) and any contribcheck exit-code expectations in `template/tests/test_publish_slice.py`.
  The gate runs each changed test module as
  `cd template && PYTHONPATH=src python3 -m unittest tests.<module>`.
- **Citations expected:** Do must cite path:line on the target branch for every change.
  Composition cue — this is a composition slice: the codebase already has a gate-declared,
  non-gating state, and `deferred` must mirror it rather than invent a parallel mechanism.
  The peer is `unverifiable`: declared by the gate (`gates.py:596-621`), excluded from
  `overall` (`gates.py:633-637`), and lifted to §6 by
  `assemble._unverifiable_items` (`template/src/pdca_harness/assemble.py:361-367`, reached from
  `:197`). Do MAY open those callsites and follow the same shape — with the one deliberate
  difference that `deferred` is **not** lifted into §6. The default-open branch to change is
  `cli._contribcheck` (`template/src/pdca_harness/cli.py:1078-1079`), and the registration whose
  comment must stop promising a pass is `template/pdca.toml.jinja:920-938`.
- **Prior-art check (triage cycles):** by affected file path against `origin/main` @ `9fb4860`
  (fetched 2026-08-02). `git log --oneline origin/main -15 -- template/src/pdca_harness/gates.py`:
  `c6784ec` (#329) and `228e80b` (#368) both narrowed *when* `unverifiable` may be recorded —
  the same vocabulary, never extended. `gh search issues "contribcheck"` → #339 (closed — the
  `at_publish` re-gating this proposal leans on), #331 (closed), #384 (open, briefed in this
  batch — the publish-side sibling), and this issue. `gh pr list -R eduralph/pdca-harness
  --state open` → empty. Nothing in flight touches the row vocabulary.
- **Disposition hint:** likely-fix

## Motivation

The T4 contribution gate is bundle-scoped and **default-open before the publish artifacts
exist**: at Check time `commit-msg.txt` and `pr-description.md` have not been drafted, so
`cli._contribcheck` returns 0 with nothing linted (`cli.py:1078-1079`). That layering is
deliberate and documented — the substantive audit happens at publish via `at_publish`
re-gating (#339, `publish._t4_passes`, `publish.py:713`).

The Check matrix then records that non-event as a plain green **PASS**, indistinguishable from
a substantive one — and, in the frozen record, with an **empty** evidence string. The reviewer,
whose job is to independently reproduce every recorded green, cannot: the artifacts the gate
names are not among its inputs, because they do not exist yet. Its contract leaves it exactly
one move — mark the row provisional (`template/agents/reviewer.md.jinja`, "Can't re-run a gate?
Say so — don't rubber-stamp it") — so **T4 lands in SUMMARY §6 NEEDS-HUMAN every single cycle**:

- 9 of 9 frozen bundles in the pdca-pdca instance's 2026-08-01 Act review (#311, #316, #331,
  #340, #341, #359, #368, #375, #376);
- the recurring text is *"T4 Contribution — commit-msg.txt / pr-description.md were not
  supplied, so the recorded green cannot be independently confirmed"* (issue_317 and issue_316
  SUMMARY §6 carry it verbatim; issue_376's reviewer even diagnosed the cause correctly —
  *"the checker is intentionally default-open while the PR body is absent, so the recorded pass
  cannot be reconstructed"*);
- bundle issue_341 §10 named it: *"T4 contribcheck runs too early at Check (vacuous default-open
  pass before the publish artifacts exist) — reconsider when/how T4 is reported."*

A §6 item that fires on 100% of cycles and is cleared unread every time is worse than no signal:
it trains the human to tick §6 boxes, which is the guard C6 depends on. Worth doing now because
the same Act review is filing its siblings (402, 403, 428) and this is the only one of the four
where the honest answer requires the record to say something it currently cannot say.

## Design

**A fourth row result: `deferred`** — "this gate ran, found its subject absent by design, and
its substantive verdict is owed later".

1. **The checker declares it.** `cli._contribcheck`'s default-open branch stops returning a bare
   0 and *declares* the deferral, in the same gate-declares-its-own-state family as
   `PDCA-UNVERIFIABLE:` (`gates.py:596-621`) — a marker line naming the reason ("publish
   artifacts not drafted yet; re-gated at publish"). Use the declaration rule 428/402 settle;
   do **not** introduce a second notion of "the gate said this".
2. **`_classify` recognises it** and returns `("deferred", [reason])`.
3. **Deferral is legitimate only when the row is re-gated later.** A row may record `deferred`
   only if it will actually be re-run at publish — i.e. it is selected by
   `publish.publish_gates(cfg)` (`publish.py:668-711`: a bundle-scoped T4 row, or an explicit
   `at_publish = true`). A row that nothing re-gates has no later verdict to defer to and keeps
   today's behaviour. This is the guard that keeps `deferred` from becoming a way to opt out of
   scrutiny.
4. **`_finalize` ignores it** for `overall`, exactly as `unverifiable` is ignored
   (`gates.py:633-637`): a deferred row is neither a gating fail nor a green.
5. **`assemble` does NOT lift it into §6** — the one deliberate difference from `unverifiable`
   (`assemble._unverifiable_items`, `assemble.py:361-367`). The by-design condition stops
   producing a NEEDS-HUMAN row; C6's accept-guard is untouched for every other class.
6. **`render_md` shows it** in the matrix with its reason, so the human reading `check-gates.md`
   sees "deferred — re-gated at publish", not a green.
7. **The reviewer is told what it means** (`template/agents/reviewer.md.jinja` + the driver-side
   `_REVIEW_PROMPT`, `leaves.py:1472`): a `deferred` row is not a green to reproduce and not a
   finding — record it `N/A` with the reason, and do not escalate it.
8. **The written contract follows the code**: `04-validation-tooling.md` §Gate result
   vocabulary, `06-quality-cycle-guidelines.md:226`, `08-glossary.md:153`, and the
   `pdca.toml.jinja:920-938` comment that currently promises "default-open (so Check-time gates
   pass)".

**Invariant this restores:** a gate row records only a verdict the gate actually reached — a
check that did not run its substantive audit is never recorded as having passed it. Cited to the
target's own written rule: *"a gate with nothing to verify says so rather than manufacturing a
green"* (`template/PCDA/quality-cycle/04-validation-tooling.md:67`) — the existing sentence
already states the principle; today's T4 row is the case the vocabulary cannot express, because
the only "says so" channel routes to §6 and this condition must not.

## Alternatives considered

- **Reuse `unverifiable`.** Cheapest by diff, and wrong: `unverifiable` is *routed to §6 by
  design* (`assemble.py:197,361`), which is precisely the recurrence being removed. It would
  rename the symptom.
- **Reuse `none`.** `none` means "no gate configured" — the matrix-alignment cell for an element
  nothing scores (`gates.py:696-701`). Overloading it with "configured, ran, deferred" would
  make the two indistinguishable in the frozen record and in `revalidate`'s comparison, and lose
  the reason string.
- **Keep `pass`, fix only the evidence text** (e.g. `path_line = "default-open: artifacts not
  drafted"`). Least invasive, and it does address the empty-evidence part — but the row still
  *asserts a pass* the reviewer is contractually required to reproduce and cannot. It treats the
  reviewer's escalation as a reading error rather than a record that lies.
- **Make T4 publish-only** (a real `phase` property, so the row simply does not run at Check).
  The honest long-term model, explicitly recorded as the larger change in `publish.py:668-711`'s
  docstring (#339). Rejected *for now* on scope: `_applies` knows only `scope`/`target`, so this
  is a scheduling change across the gate runner with its own compatibility surface for rendered
  instances — and it would leave the 5/5/1 matrix with a silent T4 element, which needs its own
  answer anyway. This proposal is compatible with it: if `phase` later lands, `deferred` becomes
  the state a phase-aware row reports before its phase.
- **Do nothing.** The status quo is a 100%-firing §6 item; see Motivation.

## Impact & compatibility

- **`check-gates.json` gains a fourth `result` value.** Readers that test for `"fail"` /
  `"unverifiable"` are unaffected (a `deferred` row is neither). Every consumer that reasons over
  the value must be audited in this patch: `gates._finalize`/`render_md`, `assemble` (§5 evidence
  + §6 lift), `revalidate` (row comparison), `flow` (the between-waves integration re-gate reads
  `overall` only), `cli` exit codes, and the reviewer's contract text.
- **Frozen bundles are untouched** — nothing rewrites an existing `check-gates.json`. A
  `pdca revalidate` of an old COMPLETE bundle will legitimately report a changed row
  (`pass` → `deferred`); that is a true statement about the engine, and the docstring/release
  note should say so.
- **Rendered instances** pick this up on `copier update`; a project whose T4 checker is its own
  script keeps today's behaviour until it opts in by declaring the deferral — nothing regresses
  for an instance that declares nothing.
- **Safety:** the substantive T4 verdict is unchanged and still hard-gates the push
  (`publish._t4_passes`). Deferral is permitted only where a re-gate exists (design point 3), so
  no audit is silently dropped. Risk to weigh at sign-off: one class of §6 row stops reaching the
  human — accepted deliberately, because that class is by-design and its real verdict is enforced
  later by a gate that cannot be skipped.

## Open questions

- **The value's name.** `deferred` reads well in the matrix; `pending` and `n/a-yet` were
  considered. Settle at sign-off if the reviewer objects — it is a one-token change and the
  spec docs are updated in the same patch either way.
- **Should a deferred row still appear in `SUMMARY.md` §5 (evidence)?** Proposed: yes, as a
  visible row with its reason, so the human sees *what* is owed at publish — without it being a
  §6 checkbox.

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.
