Bash was unavailable in this run (`apply-seccomp: write /proc/self/setgroups … Permission denied`); this review used Read, Grep and Glob only.

# Plan advisory — plan-reviewer — issue 728 (flow-carry-through-patchless-finished-bundles)

I tried to fault the root cause, the success criterion, the scope and the dependencies. The root cause holds up against the target source:
- `_carry_finished` builds `dependents` only from direct edges onto `_fold_candidates` (`flow.py:1252-1259`).
- `_fold_candidates` requires a patch (`integrate.py:247-248`).
- `_cascade_not_clean` keeps only prerequisites that are in `ids` (`flow.py:1195-1197`).
- `_runnable` holds only a dependency named directly in `held` (`flow.py:803-806`).
- `_closure_members` seams on a finished id (`flow.py:947-949`).

All cited anchors and test helpers resolve at the stated lines (`_finished :66`, `_held :158`, `_on_base :176`, `:300`, `_finished_on :391`, `_not_carried :405`, `:412`, imports `:38-43`). `Depends on: 727` resolves (`dependency-state.json`: exists, COMPLETE). Adding the patchless node to `held_finished` is enough to hold `D` through `_runnable`'s existing branch. `N` has no patch, so `cand` is `[]` (`flow.py:777-780`), and the call falls through to `flow.py:803-806`. So the claim that `_runnable` stays unchanged is plausible. I could not fault the root cause, the target or the dependencies. Two findings remain:

- NEEDS-HUMAN — **The thread's "false-stop" repro has no guard in the narrowed criteria.** The issue lists, inside part (b), "(3) **Resume through a finished patchless bundle (false-stop repro).** Run `[A, N, P, D]`, `P Depends on N`, `D Depends on P` … `D` is COMPLETE and contains `A` and `P`; no `STOPPING` line" (notes.json). The brief's (3) covers only the *closed*-`A` variant of that graph. Its (4a) guard covers `D → N → A` with no patched id between them. Nothing pins the *clean* case `A (OPEN) ← N ← P (cut from fix/A) ← D`.

  This is exactly the case the new cascade-through-`N` code could wrongly make not clean. `P`'s branch holds `A`'s commit, and an over-eager walk or `foreign_commit` accounting change (`flow.py:1287-1289`) would hold `P`/`D`, or refuse the line. At baseline it passes: `D → P` triggers the target, and every candidate is judged (`flow.py:1260-1261`). So it would be a cheap green-before-and-after guard, and it is the repro the thread itself names.

  Suggested revision: add a (4c) — `A` OPEN, `N` patchless (`Depends on: A`), `P` via `_finished_on("P", "A")` with its brief restated to `Depends on: N`, planned `D` (`Depends on: P`). Assert that both `A` and `P` are carried, `D` is COMPLETE holding `fix/A` and `fix/P`, and there is no `STOPPING` or "is not carried" line. Alternatively, record in the brief why the human dropped it.

- NEEDS-HUMAN — **The patchless node's own stderr output is not specified, so Do and Check can disagree.** The Scope says "A patchless node is held for a cause it reaches; it is not itself 'not carried' for a PR reason". It does not say whether `N` gets its own stderr line, or what that line looks like.

  Today the held/print loop runs only over `ids`, the fold candidates (`flow.py:1333-1345`). So putting `N` into `held` means either a new line shape or silence. Silence leaves `D`'s only hold message as `_runnable`'s generic "skipped — prerequisite(s) not ready (N)" (`flow.py:826-828`). Criteria (2) and (3) assert only on `A`'s and `P`'s lines. That leaves Do free to emit a new "`issue_N` … is not carried … holding issue_D" line, which contradicts the Scope sentence. Do is equally free to print nothing for `N`.

  Suggested revision: state the expected outcome for `N`. Either no line of its own, or a defined line that reuses the `built_on` hint. Then add one assertion to (2), for example "no line starts with `flow: issue_N (finished in an earlier run) is not`", or the defined line.

> **pdca:** Bash was unavailable to this reviewer. The vendor sandbox could not start on this host, so every Bash call it made failed before running (`apply-seccomp: write /proc/self/setgroups (nested userns is capability-restricted; caller must provide CAP_SYS_ADMIN): Permission denied`) and it ran no commands; this review was delivered without Bash.

<!-- pdca:leaf-complete -->
