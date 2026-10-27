Bash was unavailable in this run (sandbox failed with `apply-seccomp: … Permission denied`); review done with Read/Grep/Glob only.

# Plan review — fold-builds-a-per-bundle-base

- NEEDS-HUMAN — **Thread record not checkable.** The sandbox has only `brief.md`. There is no `notes.json`, no `sources/` and no `dependency-state.json` (Glob of cwd). So I could not check the problem statement against the tracker thread: #463 "Done when", #630's comment, or the 2026-10-15 sign-off carry-forward that the brief cites as the source for (5)/(6). The prerequisites 672/673/693/694/695 could not be resolved either. Either the bundle was handed over incomplete, or the brief relies on records the reviewer cannot see.

- NEEDS-HUMAN — **The target lacks the prerequisites, and the brief's citations point at a tree that doesn't exist on `main`.** The target is `eduralph/pdca-harness @ main`. In `$PDCA_TARGET`:
  - `integration_branch` is at `integrate.py:99` (brief says `:126`).
  - `_flatten_base` is at `:127` (brief: `:154`).
  - `fold` is at `:300` (brief: `:327`).
  - `integ_lock` is at `:253` (brief: `:280`).
  - `_merge_published` is at `:608` (brief: `:810`).
  - The "declare the conflict / re-order" message is at `:630-631` (brief: `:842`).

  Grep finds no `#672`, `#673`, `#693`, `#694` or `#695` anywhere under `template/`. Criterion (4) needs "#623 / 673's check", and the brief itself says the work "must still build on" those five, which "must be merged into `main` first" if driven standalone. Yet it declares no `Depends on` / `Stacks on`, and says "A split child may name only siblings here". The result is a bundle whose base, as given, cannot satisfy its own criterion (4). Its "Citations expected" anchors are also off by 27 to 212 lines. Either set the target to the run's line (or 489e5fb, which the Repro line names) or declare the prerequisites in a way the driver enforces.

- NEEDS-HUMAN — **Criterion (6) as worded refuses legitimate builds.** It says to raise if "any commit of `<base>..<excluded head>` would end up on the result". In this harness, later-wave bundles are cut from the run's line (module docstring `integrate.py:12-16`; `test_integrate_stack_bases.py:268` cuts B from `origin/{LINE}`). So an excluded later-wave bundle's `<base>..<head>` contains every earlier member's commits. Take criterion (1)'s own scenario and add any non-member C cut from the line after wave 0. Building B's base from `[A]` with C excluded would raise, because A's commits are in `base..C`. The check needs to be "commits reachable from the excluded head but not from the base or any member head". That is exactly the shape of the existing `foreign_commit` (`integrate.py:225-236`, `rev-list --no-merges tip --not base_ref *heads`). The brief doesn't mention that it exists. Add a red→green case where an excluded bundle stacks on a member and must NOT raise.

- NEEDS-HUMAN — **Criterion (3)'s "plain push" half can't be falsified as stated.** It proves "creating the branch is a plain push" by having "an origin with `receive.denyNonFastForwards = true` accept it". Creating a ref has no old value, so a `--force` create is accepted too. The existing suite says so: `test_integrate_stack_bases.py:276-277` ("receive.denyNonFastForwards ACCEPTS a forced push that happens to fast-forward, so the flag itself is what this pins"), and it checks the argv with `self._pushes(...)` (`:281-283`). The criterion should pin the push flags (no `--force` on create, `--force` on rebuild) with that helper. As written, a force-always implementation passes. The "refused push" leg also needs a stated way to provoke the refusal (e.g. `receive.denyNonFastForwards` plus a pre-existing divergent branch).

- NEEDS-HUMAN — **A hidden design choice is pushed onto Do.** The scope says "a new `fold` keyword or a sibling function … Do picks". These differ in review surface. A `fold` keyword touches `fold`'s ~260-line body (`integrate.py:300-566`), which already has `folded_this_run`, `carried`, `held_out` and `wave` interactions. All of these would need a defined meaning under the new mode: is `held_out` allowed? Is `folded_this_run` ignored? Criterion (7) only catches regressions in existing tests, not undefined combinations. Either pick one, or list which existing keywords are rejected or ignored in per-bundle mode.

- NEEDS-HUMAN — **Criterion (2) leaves the name format open, and the fallback sits on an unverifiable base.** "Line name plus a fixed suffix carrying `B`'s id" is checkable for prefix-freeness only once the format is fixed: does a suffix separator like `-b<id>` collide with the `-r<key>` / `-h` / `-s` escapes (`integrate.py:107-115`, `:128-135`)? The brief should state the format so the "never a path prefix / injective" test has a concrete oracle. Separately, the brief points Do at `iteration-v1/patch.diff` as reference, but that diff was cut against a base Do won't have (see the finding on the target above).

> **pdca:** Bash was unavailable to this reviewer. The vendor sandbox could not start on this host, so every Bash call it made failed before running (`apply-seccomp: write /proc/self/setgroups (nested userns is capability-restricted; caller must provide CAP_SYS_ADMIN): Permission denied`) and it ran no commands; this review was delivered without Bash.

<!-- pdca:leaf-complete -->
