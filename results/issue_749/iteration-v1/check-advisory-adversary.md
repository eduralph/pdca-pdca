# Adversarial review — issue #749 (stranded line bundle after a moved base)

**Bottom line:** the red→green proof holds up. I found one concrete input where the fix holds a bundle with advice that does not work, where the old code stopped. That case, plus two smaller points, is below.

## Evidence (attempted to refute; could not)

- **The red→green proof is real.** I re-ran it in sandbox copies of `$PDCA_TARGET/template`, one as-is and one with only `flow.py` and `integrate.py` put back to `HEAD`.
  - With the fix: `test_flow_cross_wave_stranded_holds` plus `test_flow_cross_wave_fold_holds` give 16/16 OK.
  - Without it: 6 FAIL — the 5 new hold cases and the flipped `test_a_clash_with_a_partner_whose_head_no_longer_fits_the_base_holds_it` (`template/tests/test_flow_cross_wave_fold_holds.py:404`), each ending in `STOPPING`. The two guards stay green, as the brief says they should.
  - This matches `gate-logs/C4-verify.log`.
  - The tests drive the production path: `flow._drive_and_act` on real git, importing modules only (`template/tests/test_flow_cross_wave_stranded_holds.py:61`). They stub only the build/publish leaves and `gh`. They are not a copy of the production logic.
  - Case (4) still stops (`kind == "base"` never reaches `_held_by_move`, `integrate.py:1878`), and the T3 log shows 2632 tests OK.
- **Attacks that did not land:**
  - *Stranded hold with no own-change clash.* The trial where the line's side wins (`integrate.py:1987`) catches any clash of the held branch's own change with line work. A clash that only P and R make together (P renames `shared.txt`, R rewrites it), with no other partner, still stops: `mine` stays empty (`integrate.py:2001`).
  - *Dry runs and the carry.* Both pass `moved=None` (`flow.py:3161`; `integrate.py:673`).
  - *`Conflicts with` partner wording.* `flow.py:863` uses the moved wording only when the partner is in `held_moved`.
  - *"Past" advice.* It is tried before it is given: the branch is updated from the base, then merged onto the line (`integrate.py:1977-1982`).

## Findings

- NEEDS-HUMAN [impl] — **The "own" sub-case of a stranded hold has no check that the named bundles explain the whole clash. A run that used to stop now holds with advice that does not work.** `integrate.py:1989-2005` (`_held_by_move`):
  - It names `own` from single-bundle trials only (`_partners` on `held`, plus each stranded bundle rebuilt). It never runs #748's `_together` and never runs an acceptance trial like `_explains`.
  - That breaks the promise in `fold`'s docstring (`integrate.py:496`): "one the named bundles do not explain — raises, as before".
  - **Failing case (run as a probe on the patched copy):**
    - Base has `shared.txt` = TEN and `b.txt` = `b0`.
    - Wave 0: A adds `a.txt`; B sets `b.txt` to `B's`; P renames `shared.txt` → `moved.txt`; R rewrites `shared.txt` lines 1-7 (the P/R recipe from `test_flow_cross_wave_joint_holds.py:270`); Z adds `z.txt`.
    - W (`Depends on: Z`) adds `w.txt`, sets `b.txt` to `W's`, and edits `shared.txt` line 10. V (`Depends on: W`).
    - After fold 1, main gets its own `a.txt`.
  - **Result with the fix:** W is held, naming only A (stranded) and B (own). It says "(conflicts in a.txt, b.txt, shared.txt)", but nothing is named for `shared.txt`. The end-of-run line says: "rebuild issue_A's branch on the new origin/main. Proposed … declare `Conflicts with: B` … rebuild issue_W on a base that holds issue_B."
  - **Following that advice still fails:** main + A rebuilt on main + B + P + R + (W merged with B) conflicts at W, in `shared.txt`. Without P and R it merges clean.
  - **Without the fix:** `STOPPING`.
  - **Suggested fix:** before returning `own`, run an acceptance trial with the stranded bundles rebuilt and the `own` partners treated as #747 treats them. Or run `_together` on `held` over the bundles that are not lost. Return None (stop) when the head still conflicts. Add this case as a still-stops (or names-P-and-R) test.
- NEEDS-HUMAN [impl] — **The "own change merges onto the base it holds" guard can never fire.** `integrate.py:1975-1976`, with its docstring at `:1939-1940`.
  - `held` is `git merge-base head base_ref`, and every `lead` rev is `git merge-base head <bundle>`. All of them are ancestors of `head`, so `_trial(held, [*lead, head])` is clean by construction. It can only fail if the `lead` revs clash with each other, which says nothing about the head's own change.
  - The brief's rule (ii) condition (`_trial(S, [head])` clean) has the same problem: it is always true. What actually separates "stranded" from an ordinary overlap is the trial where the line's side wins (`:1987`).
  - If the reviewer counted rule (ii) as a real guard, that credit is not earned. Drop the dead check, or replace it, and fix the docstring so it does not describe a case that cannot happen.
- NEEDS-HUMAN [impl] — **Minor wording error.** `flow.py:1635-1637` says the stranded bundle "does not merge cleanly onto origin/main, which issue_W's branch holds". `base` is the *current* `base_ref`, so when main moved again after W was built and A fails on both, W does not hold `origin/main` as it is now. Say "the origin/main issue_W's branch holds", as the `past` wording at `:1629` already does.
- NEEDS-HUMAN [human] — **The patch adds a fourth outcome the brief's (i)-(iii) do not define.** That outcome is the `past` hold: update the held branch from the base (`integrate.py:1971`, `:1977-1982`; `flow.py:1626-1632`).
  - It runs where child-1's rule (d) does **not** fail. In case (3b), A merges onto `origin/main` as it is now, so `now` is empty.
  - The brief scoped the re-try to "where child-1's rule (d) fails" and said "(iii) anything else stops as today". The brief did leave (3b)'s path to Do, though.
  - The advice is trial-checked and I found no input that makes it wrong. Still, it turns a class of stops into holds, which the brief did not spell out. Accept it at sign-off on purpose, not by default.

<!-- pdca:leaf-complete -->
