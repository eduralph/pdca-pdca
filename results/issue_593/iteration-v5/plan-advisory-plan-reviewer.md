Bash was unavailable in this run (every command failed with `apply-seccomp: ... Permission denied`); this review was done with Read/Grep/Glob only.

# Plan advisory — plan-reviewer (issue 593, iteration 2)

I tried to fault the root cause, the criterion, the scope and the target. The root cause holds:
the issue thread's two defects match the source. `checkout -B` happens off the base on every
fold (`integrate.py:209`), every patch is re-applied as a new commit (`:211-223`), the push is
`--force` (`:226`), and `pr_base = stack_branch if (stack_branch and own_repo)` (`publish.py:258-259`).
Most of the citations resolve. No `sources/` dir and no `dependency-state.json` are present, and
the brief declares no `Depends on`, so there is nothing to resolve there. Below are the concrete
faults I found:

- NEEDS-HUMAN — **(iv) contradicts (vi)/(vii) in dry-run.** (iv) says "`fold` itself stays
  fail-closed: called with such a bundle [non-empty patch, no published branch], it raises
  `IntegrationError` naming it, before any git step". But (iv) also says the hold "applies only
  outside dry-run, because the stubbed publisher records no branch". A dry-run publish returns
  before writing `publish.json` (`publish.py:311-324`), so in a dry-run flow **every** bundle
  reaches `fold` unpublished. The existing tests (vi) keeps green also fold bare bundles with no
  `publish.json`: `tests/test_integrate.py:80-88` and `:89-102`. (vii) and test 12 then need the
  dry-run to print "one merge line per bundle, naming the branch ref it would merge", and that ref
  has no record to come from. The brief has to say whether the fail-closed check is skipped under
  `dry_run=True`, and where the dry-run ref comes from (e.g. `publish._branch_name`, `publish.py:568-576`).
  Without that, Do must guess, and either test 12 or `test_dry_run_shells_nothing` goes red.

- NEEDS-HUMAN — **The `None` mode can't be honoured in dry-run.** (iii) says that with
  `folded_this_run=None`, the fold "continues the integration branch if origin has it, else
  starts from the base". (vii) requires dry-run to print "start" or "continue". But a dry-run
  must shell nothing: `test_dry_run_shells_nothing` asserts `subprocess.run` is never called
  (`tests/test_integrate.py:82-86`). So the dry-run cannot learn whether origin has the branch.
  The brief should say what a `None` dry-run prints, e.g. always "start", or a third "continue
  if present" line.

- NEEDS-HUMAN — **(iv)'s "unpublished" test also catches non-contributing bundles.** The brief
  defines the held case as "an accepted bundle with a non-empty `patch.diff` but no published
  branch". A patched bundle with **no** `Repo + branch target` also matches that: it publishes
  with rc 0 and writes no `publish.json` (`publish.py:130-132`, `:182-184`, flow passes
  `skip_if_no_target=True` at `flow.py:649`), and `fold` already drops it (`integrate.py:121-129`).
  Read literally, (iv) would newly skip dependents of such a bundle. Today `_runnable`
  (`flow.py:684`) builds them. The brief should restrict "unpublished" to bundles that
  `_resolve_target` gives a target, and add a test that dependents of a no-target patched bundle
  still build.

- NEEDS-HUMAN — **Scope: (iv) is a second behaviour change, not part of #593.** The issue thread
  (notes.json) asks for an append-only fold over the PR branches, a retarget to the real base,
  and signed-off merge commits. It says nothing about partial-failure policy. Today an unpublished
  bundle can't stop the run on its own: `fold` applies `patch.diff` whether or not the bundle was
  published. (iv) turns a new failure mode into a "hold dependents, keep going" policy that
  changes `_runnable`, the publish loop (`flow.py:1800-1822`) and the flow's stop semantics. The
  Notes record that this was a human decision ("reverses iteration 1's stop-all"). Even so, it is
  separable review surface, and it is behind two of the three findings above. The human should
  confirm it belongs in this bundle rather than in a follow-up where the fold simply fails closed.

- NEEDS-HUMAN — **The invariant claims more than the scope delivers.** "In stack mode no harness
  push rewrites a commit that an open PR's base or head depends on" is stated without limits. But
  publish still re-pushes a bundle's PR branch with `--force-with-lease` on a rebuilt re-publish
  (`publish.py:289-296`, #108), and that rewrites commits a dependent's head (cut from the line)
  depends on. The brief treats the cross-run case as out of scope (#616). Unless the invariant is
  limited to "within one run", sign-off can't check it, and a reviewer can point to the publish
  path to show it is false.

- NEEDS-HUMAN — **The `↑<base>` cue in (i) stops telling the reader anything.** (i) keeps
  `mode = "stacked-pr"` so that `cli._publish_flag` "keeps its `↑<base>` cue (now `↑main`)". That
  cue exists to say "this targets the integration branch, merge bottom-up" (`cli.py:1058-1061`).
  Once every PR targets `main`, `↑main` doesn't mark which PRs are stacked or which ones must
  merge first, and stacking was the reason for the cue. Either the cue should name the
  predecessor or stack (`publish.json` already records `stacks_on` only for `Stacks on` parents,
  `publish.py:392-393`), or the brief should say plainly that the cue's meaning is being given up.
  As written, "only the comment changes" hides a UX regression.

What I attempted and could not fault: the root cause of both defects; the red legs in
Falsifiability against `main` (the forced push at `integrate.py:226`, and `pr_base` at
`publish.py:259`); the single-chain diff-shrink claim in (v), where a `--no-ff` fold line gives a
single merge base after A merges; the call site `flow.py:1844`; and the file-overlap claims for
`integrate.py`, `publish.py` and the `flow.py` regions the brief cites.

> **pdca:** Bash was unavailable to this reviewer. The vendor sandbox could not start on this host, so every Bash call it made failed before running (`apply-seccomp: write /proc/self/setgroups (nested userns is capability-restricted; caller must provide CAP_SYS_ADMIN): Permission denied`) and it ran no commands; this review was delivered without Bash.
