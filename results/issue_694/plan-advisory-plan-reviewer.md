Bash was unavailable in this run (apply-seccomp: nested userns refused); this review was done with Read, Grep and Glob only.

# Plan review — issue 694 / reissue-after-conflict-hold-names-the-partner

I checked the root cause against the target first. Every `path:line` the brief cites resolves on the target as described:
- the `_CARRY_HINTS` "open" text is at `flow.py:991-993`;
- the `skipped` → "open" mapping is at `flow.py:1113`;
- the hold line is at `flow.py:1122-1132`;
- the "cross-wave overlap" text is at `integrate.py:628-631`;
- `_held_by`'s judgement against `pre` is at `integrate.py:884-908`;
- the stub returns an empty `headRefOid` at `test_flow_same_wave_conflict.py:116-117`.

The defect matches the issue thread. The findings below are about the criterion and the remedy text, not the diagnosis.

- NEEDS-HUMAN — **The required remedy text contradicts the brief's own invariant.** Criterion (1) requires run 2's line to say "rebuild `issue_11` on a base that holds `issue_10` … **or to merge `issue_10`'s PR first**". The invariant says the advice must match "whichever step reports it" and must never be "a step that cannot change the outcome". But the end-of-run line it is meant to match (`flow.py:1177-1180`) offers only "declare `Conflicts with` … then rebuild". Also, merging `issue_10` first does not make `issue_11` carryable: `issue_11`'s branch still changes the same line of `shared.txt`. Once the base holds `issue_10`, that becomes a conflict with the base, which is criterion (2)'s case. `docs/07-crosscutting.md:704-706` likewise says to rebuild, and to re-run the partner only after the rebuilt PR merges. The "or merge the partner first" wording comes from the issue's "Possible fix", but the brief adopts it without checking it. Either drop it from (1), or state what it achieves and add it to `_report_conflict_holds` too, so the two lines really match.
- NEEDS-HUMAN — **Criterion (2) has no set-up and may not be reachable through the carry as described.** It says the base "changed the same line after it was published", but gives no ids, no runs and no commands. In run 2 the carry continues origin's existing line from `tip` (`flow.py:1106-1107` → `integrate.py:488-499`: `start_ref = line` when not fresh). A base that moved after run 1 is therefore not on the line the carry merges onto, and the finished id would merge cleanly with no hold at all. The (2) conflict only appears if:
  - origin's line is absent, so the carry starts fresh off `base_remote/base` (`integrate.py:498-499`); or
  - the base is taken in mid-fold (`_take_in_base`).

  Specify the set-up, for example "delete the line on origin before run 2", and the expected stderr. Otherwise (2) is unfalsifiable, or Do invents a scenario that passes trivially.
- NEEDS-HUMAN — **The partner-finding rule is left to Do, but it decides whether (1) and (2) can be told apart.** The scope bans `_held_by` unchanged, correctly: `pre` is origin's line, which already holds `issue_10` from run 1. But the brief only says "Say in `build-notes.md` how the partner is found". The obvious replacement is "merges onto the base, fails onto base + finished id X". That needs the base ref and each finished id's head, which the carry has (`heads`, `base_ref` at `flow.py:1076-1078`). The brief should name the rule and its fallback. Two cases need a rule:
  - Run 2 has no fresh line, and the base also moved.
  - The partner is on origin's line but is not a requested id of run 2. `_finished_named` only covers `batch` ids (`flow.py:954-964`).

  Without a rule, Check cannot tell whether a green (1) is right or just names whatever is on the line.
- NEEDS-HUMAN — **The base and citations are for `d6057eb`, but the slice builds in wave 2 on top of 672 and 673.** Per the Ordering note, 672 edits `_carry_finished`'s skip handling and 673 edits the fold's merge loop near `_merge_published`'s conflict text. Those are exactly the hunks this brief cites (`flow.py:1104-1132`, `integrate.py:518-539`, `:628-632`). Every "Peer callsites" line number will have moved on the base Do actually gets. Also, 672's rewrite of the `skipped` → `why` mapping may already change the RED described under Falsifiability. No `dependency-state.json` was supplied, so I cannot confirm that 672 and 673 exist or what state they are in. Confirm the RED will be re-taken on the wave-2 base, not on `d6057eb`.
- NEEDS-HUMAN — **The repro depends on `issue_11` being COMPLETE after run 1 and on the carry being triggered.** `_finished_named` takes only COMPLETE ids (`flow.py:962`). The carry runs only when a drive-set bundle's plain `Depends on` names a fold candidate (`flow.py:1062-1067`). The brief says this was reproduced at Plan, which is credible. Still, criterion (1) should assert this precondition explicitly (`issue_11` COMPLETE with an OPEN PR after run 1). Otherwise a later change that stops marking held bundles COMPLETE would turn the test vacuously into "no carry line at all", and the "exactly one stderr line" assertion would fail for the wrong reason.

Scope check: one logical fix (the carry's hold advice for a finished-vs-finished conflict) plus the docs paragraph that goes with it. I found no hidden second change. The out-of-scope list (ordering, the in-run message, exit codes / 693) is explicit and matches the thread.

> **pdca:** Bash was unavailable to this reviewer. The vendor sandbox could not start on this host, so every Bash call it made failed before running (`apply-seccomp: write /proc/self/setgroups (nested userns is capability-restricted; caller must provide CAP_SYS_ADMIN): Permission denied`) and it ran no commands; this review was delivered without Bash.

<!-- pdca:leaf-complete -->
