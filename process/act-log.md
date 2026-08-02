# Act log — pdca-pdca

> Append-only, cross-cycle (docs 02 §ACT). Each entry records which frozen
> bundles an Act review considered, what their records exposed, the concrete
> process deltas applied (each located by a path / rule ID / template field), and
> how the next review will judge whether the delta worked. Act never re-decides a
> contribution's disposition. Newest entries on top.

<!-- Template for a new entry:

# Act review — <date> — cycles considered: <issue_ids>

## What the cycles' records exposed
- <pattern across one or more cycles, citing SUMMARY §6/§7/§10>

## Process deltas
- Spec template: <field added/clarified/removed>            (path)
- Ruleset: <rule added/retired/relaxed/tightened>           (path:line)
- Gates: <check added/promoted/moved>                       (path:line)
- Agent role prompts: <agents/*.md / skill adjustment>      (path:line)

## Follow-ups routed (not process deltas — work handed to an owner)
- Another bug (project/component): filed <tracker> #NNNN    (link)
- Design issue: <name> → dedicated design phase, owner <who>
- Harness/driver issue: this repo's tracker | template feedback upstream  (link)
- Other open Act item: <item> → owner <who>, next step <…>

## How effectiveness will be judged
- The next Do phases should not recreate <specific issue>. Watch the next K cycles.
-->

# Act review — 2026-08-02 (second review of the day) — cycles considered: issue_356, issue_379, issue_380, issue_386, issue_387

Third Act review — five bundles frozen since the earlier 2026-08-02 review (the
index carried all 19; the 14 previously reviewed were considered only for
effectiveness follow-up, not re-reviewed). All five merged-wider.

## What the cycles' records exposed
- **A false-unverifiable in the gate classifier — new, filed as harness #428.**
  `_classify` honours the `PDCA-UNVERIFIABLE:` marker as a bare substring on *any*
  output line, with no check that the **gate itself** emitted it
  (`template/src/pdca_harness/gates.py:595`). #329 closed the `rc != 0` half; the
  exit-0 half is open. issue_387's frozen C4 row proves it fires: `result:
  "unverifiable"` on a **gating** row, with a reason that is a fragment of a code
  comment the bundle's test read back — ``"<reason>` and exit 77\n# (-> SUMMARY §6
  NEEDS-HUMAN, non-gating)…"``. Structural for this instance, because our target
  *is* the harness and its own suite echoes that literal as fixture data
  (`template/tests/test_gates_unverifiable.py:28,32,103`,
  `test_prod_path_gate.py:51-89`). Effect: the one gating correctness check stops
  being a verdict — `unverifiable` is not a failure and does not reach `overall`.
- **The "T3 fixture flake" is a misdiagnosis, and the red is already fixed.**
  Reproduced directly: `tests.test_split` is **green** (96 tests OK), and the
  `/tmp/…/issue_500/split-proposal.md` lines are *leaked stdout* printed after the
  summary — production CLI code (`cli.py:787`, `print(child)`) driven by tests that
  do not capture it, block-buffered under a pipe so it flushes last. The harness
  then files that last line as the gate's evidence. A full wrapper run against a
  current target: root suite `Ran 7 tests … OK`, driver suite `Ran 1468 tests …
  OK (skipped=2)`, **RC=0** — a *passing* gate whose recorded evidence reads like a
  failure path. The historical `T3-suite: fail` rows (311, 317, 340, 341, 368, 370,
  372, 376, 379, 380, 386, 387) were genuine and were resolved by #417/#418 — i.e.
  by this instance's own issue_369 and issue_372 cycles. What recurs in §6 now has
  no failure behind it at all.
- **#403 is a reachability + invocation-contract gap, not a seeding gap**
  (issue_386 §10). The wrappers exist at the instance root and require cwd + a set
  `$PDCA_WORKTREE` + the instance venv; the reviewer works from `$PDCA_TARGET`,
  where neither holds. Intermittent — same gates, same wrappers, cleared on
  issue_356 and escalated on 380/386/387 — which points at guidance, not machinery.
- **The 2026-08-01 T5 network delta (PR #25) is confirmed effective.** The
  "could not reach `api.github.com`" prior-art class appears in **0 of the 9**
  cycles frozen since it landed (317, 332, 356, 369, 370, 372, 379, 380, 386, 387).
  The earlier entry's criterion (absent over ~3 cycles) is met.
- **Known-open classes recurring — expected, no new delta.** T2/T3 oracles
  unreachable (380/386/387 → #403), vacuous T4 contribcheck green (all five → #401,
  whose evidence string is literally empty in issue_387's record), C4 stash
  reproduction (→ #419). All still OPEN upstream.
- **"C4 unverifiable on a test-only/docs-only patch" (379, 386, 387) has two
  halves.** The genuine one is by design — no production hunk to revert means no
  red→green, so #165 routes it to §6. The other half is #428 above. Only the
  second is a defect.

## Process deltas
- Gates (this repo, instance-owned): `engine/scripts/run-suite.sh:19-49` — the T3
  wrapper now runs both suites to completion, ends on a deterministic verdict line
  (`== T3: root suite OK, driver suite OK`) and exits with the preserved rc, so the
  harness's last-line evidence rule captures a verdict instead of whatever the
  suite leaked. Verified both ways: green tree → verdict last, `RC=0`; synthetic red
  tree that *prints a decoy* `/tmp/…/issue_500/split-proposal.md` → `== T3: root
  suite FAILED (rc 1), driver suite FAILED (rc 1)`, `RC=1`, decoy not captured.
  **Explicitly a stopgap, and marked so in the file:** the fix belongs upstream in
  #402: revert this block and take the upstream version once #402 lands.
- No spec-template, ruleset, or agent-skill delta warranted. The reviewer role
  prompt (the natural home for the #403 invocation contract) is copier-managed
  (`agents/` renders from the template), so a local edit would be clobbered on
  `copier update` — it belongs upstream.

## Follow-ups routed (not process deltas — work handed to an owner)
- Harness/driver issue (upstream, template machinery): the `PDCA-UNVERIFIABLE`
  marker is matched anywhere in captured output, flipping a green gating C4 to
  unverifiable → filed https://github.com/eduralph/pdca-harness/issues/428
- Harness/driver issue (upstream, correction to an open issue filed on a false
  premise): #402 says the `issue_500` fixture flakes; it does not and never failed.
  Posted the reproduction, the leak's origin (`cli.py:787`) and the last-line
  evidence rule →
  https://github.com/eduralph/pdca-harness/issues/402#issuecomment-5160169457
- Harness/driver issue (upstream, added evidence to open #403): the wrappers are
  present but the reviewer runs them from the wrong root without `$PDCA_WORKTREE`;
  cleared on 356, escalated on 380/386/387 →
  https://github.com/eduralph/pdca-harness/issues/403#issuecomment-5160031102
- Open Act item (carried from 2026-08-01, unchanged): triage rubric should state
  five buckets explicitly (issue_316 §10) → owner: next triage brief author; still
  no triage-class brief in this interval, so nothing to judge yet.
- Ledger: T5 network signal annotated **confirmed effective**; the C4-unverifiable
  signal annotated with its two halves (#165 structural / #428 defect); T4
  contribution signal left open pending #401 (process/act-ledger.json).

## How effectiveness will be judged
- The next frozen cycles' T3 rows should carry `== T3: root suite …, driver suite …`
  as their evidence, and the `/tmp/…/issue_500/split-proposal.md` string should
  disappear from §6 entirely. If it survives, the last-line assumption is wrong and
  the delta should be reverted rather than patched.
- #428: C4 rows should stop reading `unverifiable` on bundles that merely *mention*
  the marker. Until it lands, expect the class to keep appearing on harness-facing
  work — that is not evidence against the filing.
- When #402 lands, revert `engine/scripts/run-suite.sh:19-49` and confirm the
  upstream fix alone keeps the evidence line meaningful.
- T5 prior-art class: recorded confirmed effective this review; re-open only if it
  reappears.

---

# Act review — 2026-08-02 — cycles considered: issue_317, issue_332, issue_369, issue_370, issue_372

Second Act review — five bundles frozen since the 2026-08-01 review (the index
carried all 14; the nine previously reviewed were considered only for
effectiveness follow-up, not re-reviewed). Four merged-wider, one closed as a
split (issue_332).

## What the cycles' records exposed
- **Known upstream classes recurring while their fixes are still open — expected,
  no new delta.** T2/T3 oracle wrappers absent from the reviewer sandbox
  (317, 369, 370, 372 §6 → harness #403); T4 contribcheck vacuous/unreproducible
  at Check (317, 369, 370, 372 §6 → harness #401); the synthetic
  `issue_500/split-proposal.md` T3 fixture flake (317, 370, 372 §6 → harness
  #402). Per the 2026-08-01 entry's own effectiveness criteria, recurrence
  *before* those issues land is expected; recurrence after they ship via
  `copier update` is the signal to watch.
- **New recurring finding — reviewer sandbox git index is read-only, blocking
  C4 red→green reproduction** (issue_317 §6 C4: "Git stash could not write the
  read-only worktree index"; issue_372 §6 C4: "git stash could not run because
  this worktree's git index is read-only"). Distinct from #403: even with the
  oracles present, the reviewer cannot stash the patch to reproduce the pre-fix
  red, so C4 lands in §6 as a judgment call instead of a mechanical re-check.
- **Early effectiveness signal for the 2026-08-01 T5 delta (PR #25 network
  grant):** the "could not reach `api.github.com`" prior-art class appears in
  none of the five new cycles' §6. Tentative — same-day cycles, small sample —
  but the first evidence the delta worked. Keep watching.
- **The 4× "Validation — fitness-to-purpose — human sign-off must decide"
  recurring signal is structural, not a gap:** validation fitness is human-only
  by design (the sign-off contract), so this class will appear in §6 of every
  cycle and no process delta can or should remove it.
- **issue_332** (split close, no patch built) exposed nothing recurring — the
  split path produced a clean one-item §6 and a confirmable disposition.

## Process deltas
- None to this repo's spec template, ruleset, gates, or agent skills — agreed
  with the human. Every recurring finding is either already-filed upstream
  harness machinery (#401–#403, open) or structural (validation is human-only);
  a local change would paper over the former and mis-frame the latter.
- Ledger: "validation — fitness-to-purpose — human sign-off must decide" marked
  **structural** (by design, no delta possible) instead of open
  (process/act-ledger.json).

## Follow-ups routed (not process deltas — work handed to an owner)
- Harness/driver issue (upstream, sandbox machinery per the template-vs-instance
  boundary): reviewer sandbox's read-only git index blocks stash-based C4
  red→green reproduction (issue_317 + issue_372 §6 C4) → filed
  https://github.com/eduralph/pdca-harness/issues/419
- Open Act item (carried from 2026-08-01, unchanged): triage rubric should state
  five buckets explicitly (issue_316 §10) → owner: next triage brief author;
  no triage-class brief ran this interval, so nothing to judge yet.

## How effectiveness will be judged
- C4 stash-reproduction NEEDS-HUMAN (317/372 class) should stop recurring once
  upstream #419 lands and reaches this instance; recurrence after it ships is
  the signal.
- T5 prior-art network class: if it stays absent over the next ~3 cycles, record
  the PR #25 delta as confirmed effective at the next review.
- #401–#403 classes: continued recurrence is expected while open; re-check their
  status next review before drawing any conclusion.

---

# Act review — 2026-08-01 — cycles considered: issue_311, issue_316, issue_331, issue_340, issue_341, issue_359, issue_368, issue_375, issue_376

First Act review of the instance — nine frozen bundles, all merged-wider.

## What the cycles' records exposed
- **T5 prior-art check unresolvable — 6 of 9 cycles** (311, 316, 340, 359, 375,
  376 §6): the codex reviewer sandbox cannot reach `api.github.com`, so "confirm
  no closed/rejected work duplicates this" lands in §6 every time (the ledger's
  open recurring signal). Root cause: upstream pdca-harness#277 closed COMPLETED
  via PR #287, but the fix is an **opt-in** (`[leaves.sandbox] network_access`)
  this instance had never enabled — `pdca.toml` still carried it commented out.
- **T4 contribcheck vacuous/unreproducible at Check — 9 of 9 cycles** (§6
  everywhere; named by issue_341 §10): contribcheck is default-open before the
  publish artifacts exist (by design, re-gated at publish per harness #339), but
  the Check matrix records a plain green PASS the reviewer cannot reproduce, so
  it is escalated every cycle.
- **T3 advisory red on the synthetic `issue_500/split-proposal.md` fixture —
  6 of 9 cycles** (311, 331, 340, 341, 368, 376): a pre-existing driver-suite
  fixture flake, unrelated to any bundle's patch, at a transient `/tmp` path
  nobody can inspect; issue_311 §10 additionally showed the T3 evidence
  extractor capturing arbitrary fixture stdout as its evidence line.
- **T2/T3 oracles absent from the reviewer sandbox — 4 of 9 cycles** (331, 341,
  368, 375 §6): the gate runners the frozen records name
  (`engine/scripts/run-docs-check.sh`, `run-suite.sh`) are not in the reviewer's
  permitted target; issue_375 §10 also noted no preflight checks the sandbox
  interior (doctor checks the host).
- **One-off (issue_331 §10):** the deliberate-abandon escape hatch shipped as a
  raw `python3 .claude/hooks/handoff_guard.py --abandon` invocation — should be
  a rendered `/abandon` slash command.
- **One-offs (issue_316):** §10 — the triage rubric's "one of four" wording vs
  an accepted 5th (unclassified-remainder) bucket caused a sign-off ruling;
  §6 C5 — recurrence identity is keyword-derived (`triage.py:108`), so synonyms
  split what should be one signal.

## Process deltas
- Gates/config (this repo): enabled `[leaves.sandbox]` `network_access = true`
  (pdca.toml:676–677) so the codex reviewer leaf can reach `api.github.com` for
  the T5 closed/rejected-PR prior-art check. Trade-off accepted with the human:
  the codex network grant opens the network layer for every command in that
  leaf (no per-domain scoping); filesystem confinement unchanged. Shipped as
  draft PR https://github.com/eduralph/pdca-pdca/pull/25 (human marks
  ready/merges). Ledger signal "t5 judgment — confirm no closed or rejected"
  marked applied.
- No spec-template, ruleset, or agent-skill delta warranted this review — the
  remaining findings are harness-machinery issues, routed upstream below rather
  than papered over locally.

## Follow-ups routed (not process deltas — work handed to an owner)
- Harness/driver issue (upstream, template machinery): Check-matrix reporting of
  a default-open T4 as PASS → filed
  https://github.com/eduralph/pdca-harness/issues/401
- Harness/driver issue (upstream): `issue_500/split-proposal.md` suite-fixture
  flake + T3 evidence extractor capturing arbitrary fixture stdout → filed
  https://github.com/eduralph/pdca-harness/issues/402
- Harness/driver issue (upstream): reviewer sandbox lacks the T2/T3 gate
  oracles; no sandbox-interior preflight → filed
  https://github.com/eduralph/pdca-harness/issues/403
- Harness/driver issue (upstream, follow-up on open #331): render an `/abandon`
  slash command wrapping the handoff-guard escape hatch → filed
  https://github.com/eduralph/pdca-harness/issues/404
- Open Act item: triage rubric should state five buckets explicitly (issue_316
  §10) → owner: next triage brief author; revisit next review.
- Design issue (routed to human to schedule, outside the cycle): triage
  recurrence-identity representation — broad class vs class+keyword vs semantic
  slug (issue_316 §6 C5, `template/src/pdca_harness/triage.py:108`). Needs a
  design decision, not a bug fix; no brief authored.

## How effectiveness will be judged
- The T5 "confirm no closed or rejected work" NEEDS-HUMAN class should stop
  recurring once PR #25 merges — the ledger will flag the signal as
  likely-ineffective if it recurs after 2026-08-01.
- T4/T3/oracle §6 noise should drop as upstream #401–#403 land and reach this
  instance via `copier update`; if the same classes recur over the next ~3
  cycles with the issues still open, that is expected — recurrence *after* they
  ship is the signal to watch.

---

