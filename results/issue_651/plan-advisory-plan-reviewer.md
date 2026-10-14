Bash was unavailable in this run (every command failed with `apply-seccomp: ... Permission denied`); this review used Read, Grep and Glob only.

# Plan advisory — plan-reviewer — issue 651 / reword-stale-strict-levelling-comment

I tried to fault the root cause, the line relocation, the success criterion and the scope, and could not find a substantive fault. Checked against the target source:

- `flow.py:2141-2144` contains the stale claim word for word: "levelled first and strictly, exactly as before", "waves.py:243-246", and "adoption never relaxes it".
- `flow.py:2157-2159` (the #590 paragraph) and `flow.py:2160-2162` (`offered = _offered_by_seeds(...)`, `compute_waves(..., offered=offered)`) are where the brief says.
- `waves.py:74-80` (docstring) and `waves.py:95-96` (`if dn in offered and dep not in stacks: continue`) confirm the relaxation, and confirm that a `Stacks on` edge is still refused (it falls through to `cfg.bundle(dep)` and must be COMPLETE, `waves.py:102-103`).
- `waves.py:243-246` is now the body of `_cycle_members.visit`, so the old reference is stale. The quoted text "right for an explicit ``flow <ids>``" is at `waves.py:278-279`, inside the docstring that opens at `:277`.
- Grep finds no other "never relaxes" or `waves.py:2xx` reference in the repo, so no second stale copy is being left behind.
- The thread asks for a comment-only reword (it says it "can ride on PR #638 if that PR is still open"). The brief deals with that: #638 is closed and #590 landed via `29a7943`.

The remaining findings are small and the planner can act on them:

- NEEDS-HUMAN — **The success criterion could lose a fact the current comment gets right.** The brief's criterion asks the new text to say an offered `Depends on` edge "is accepted". The code is more specific: an offered edge "is resolvable and adds NO edge here — the child joins the schedule only at the seed splice, which re-levels with it in place, so that is where the edge orders anything" (`waves.py:76-79`; already reflected at `flow.py:2158-2159`). Scope lets Do rewrite the 2157-2159 paragraph too. A rewrite that keeps only "accepted" would suggest `compute_waves` orders the edge, which is a new inaccuracy. Suggested fix: add a clause to the criterion that the reworded block must still say the offered edge adds no edge in `compute_waves` and is ordered by the `k=-1` seed splice.
- NEEDS-HUMAN — **The Falsifiability citation for the gate cannot be checked in the target repo.** The brief cites `engine/scripts/run-verify.sh` and "the `TESTS`/`PROD` classification and the 'patch ships no test' exit". No `engine/scripts/` exists in the target tree. The only `run-verify.sh` in `eduralph/pdca-harness` is `template/engine/scripts/run-verify.sh`, an unimplemented stub that `exit 1`s (`:91-94`). Its header only describes the "nothing ran → 77" rule (`:61-78`); it contains no TESTS/PROD classifier. If the gating C4 script is the operator's (pdca-pdca) copy, the brief should say so. Otherwise a reviewer cannot confirm the claim that exit 77 routes to §6 instead of failing. If C4 actually exits 1 on this bundle, the run hits a hard gate fail rather than the expected §6 route.
- NEEDS-HUMAN — **Minor line-number drift in the brief.** The brief says the docstring text is at `waves.py:277-279`. Line 277 is the docstring's opening sentence ("Split ``bundles`` into …"); the quoted phrase is at `:278-279`. Either range is fine for Do to cite, and the brief already allows a symbol reference with no line number. Raised only because the brief requires every cited `path:line` to be exact.

No dependency-state.json is present. `Conflicts with: 674` is an ordering declaration, not a `Depends on`, so there is no prerequisite to resolve. The ordering note's anchor `flow.py:2134` (`held_unpushed`) is correct on the target.

> **pdca:** Bash was unavailable to this reviewer. The vendor sandbox could not start on this host, so every Bash call it made failed before running (`apply-seccomp: write /proc/self/setgroups (nested userns is capability-restricted; caller must provide CAP_SYS_ADMIN): Permission denied`) and it ran no commands; this review was delivered without Bash.

<!-- pdca:leaf-complete -->
