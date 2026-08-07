# PR description

## Summary
**User impact:** when a batch is set up to merge each accepted fix automatically, a
fix can be merged into *another fix's* branch instead of the branch it was meant to
land on — and nothing says so. The run reports that everything landed, the next batch
builds on a branch that never received the work, and the change is quietly missing
from where it belonged. Because the failure looks exactly like success, it is usually
found much later, by noticing the fix simply isn't in the target branch.

This PR makes publishing stop before it can open such a pull request: in auto-merge
batches a fix may only target a branch that exists independently of the run, and
anything else is refused with a message naming both the branch the PR would have
gone to and the one it should have gone to.

Reported in [#411](https://github.com/eduralph/pdca-harness/issues/411).

## What to look at
The whole change is one guard inside `publish`, plus a small helper that reads what
the other bundles in the batch already published. Two situations now get refused, and
the message tells the operator how to recover (repoint the brief's branch target at
the shared base, or stay on the default batch mode).

To try it offline, no network or GitHub account needed:

```
cd template && PYTHONPATH=src python3 -m unittest tests.test_publish_slice
```

The four new cases in `MergeModeBaseGuard` set up a small batch on disk — one bundle
that already published a branch, one that would end up pointed at it — and run the
real `publish` entry point in dry-run mode. Two assert the refusal; two assert that
ordinary publishing, and the default mode's deliberate chaining, still work.

## Root cause
Under `[driver].wave_mode = "merge"`, `merge_wave` merges each accepted bundle's PR
"into its base" without ever inspecting what that base is
(`template/src/pdca_harness/merge.py:29-31`), and publish chose that base with no
check either — `pr_base = stack_branch if (stack_branch and own_repo) else base`
(`template/src/pdca_harness/publish.py:256-257`). Two routes put another bundle's
branch into it: the legacy `Stacks on:` wiring falls back to the prereq's own fix
branch when no integration branch is recorded
(`template/src/pdca_harness/publish.py:617-630`) — and merge mode never records one,
because `flow` fills the integration marker only on the stack path
(`template/src/pdca_harness/flow.py:566-580`, `:806-811`) — while a brief whose
`Repo + branch target` names a predecessor's branch (the documented practice for
chained stack-mode batches) resolves to that branch as its *own* target base, so
comparing the PR base against the target base sees nothing wrong at all.

## Fix
- **The guard** (`template/src/pdca_harness/publish.py:258-272` in this PR): under
  `wave_mode == "merge"` only, evaluated right after the PR base is computed and
  before the fetch/checkout/apply/push/PR steps are even built — so a refusal pushes
  nothing, opens no PR and writes no `publish.json`. It returns non-zero with a
  message on stderr, the same shape as publish's existing fail-closed stop for a
  stacked bundle whose prereq hasn't published.
- **Both routes** (`:648-694`): route 1 is a PR base that differs from the bundle's
  resolved target base — it can only have come from the run's own stacked chain.
  Route 2 is a PR base that *equals* the target base, but is a branch another bundle
  in this batch produced; the batch's existing `publish.json` records answer that
  offline, reusing the accessor already there. The bundle's own base is not re-parsed
  — it is passed in from `_resolve_target`, the single parse (#235/#262/#387).
- **Fail-closed on ambiguity:** a sibling record written without a `repo` field is
  treated as this repo's. A false refusal is recoverable in seconds; a silent wrong
  merge is not.
- **Refuse, never retarget.** The harness does not rewrite a PR's base for you, and
  the check lives at publish time rather than merge time on purpose: publish is
  interactive, with someone present who can fix the brief on the spot, whereas the
  batch merge runs unattended.
- **Docs** (`docs/07-crosscutting.md`, the wave-mode section): the rule and the
  recovery, next to where `[driver].wave_mode` is documented.
- **Known gap, stated rather than hidden:** a PR published by an *earlier* run (for
  example under stack mode, before a project switched to merge mode) never passes
  through publish again, so a later merge-mode run can still merge it as-is. The
  reported and normal case — publish and merge inside the same run — is covered.

The default `"stack"` mode is untouched in every respect, including its stacked-PR
chaining, which is correct there precisely because nothing is merged for you.

## Verification
- **Claim:** on current `main` nothing validates a PR's base before an auto-merge
  batch merges it, and in merge mode the legacy chain fallback is the only thing
  choosing that base. **Checked:** `template/src/pdca_harness/publish.py:256-257`
  (base taken, unchecked), `:617-630` (fallback to the prereq's fix branch),
  `template/src/pdca_harness/merge.py:29-31` (merges into whatever base the PR
  carries), `template/src/pdca_harness/flow.py:566-580` and `:806-811` (merge mode
  records no integration branch, so every bundle's marker is cleared).
- **Claim:** both wrong-base shapes are refused with nothing done — non-zero exit, no
  push, no PR, no recorded contribution. **Checked:** the guard sits at
  `template/src/pdca_harness/publish.py:258-272` in this PR, ahead of the step list
  (built at `:273`, executed at `:354`) and of the dry-run plan print (`:313`); the
  tests assert all three absences directly.
- **Claim:** the guard is not a blanket stop. **Checked:** a bundle targeting the
  shared base still publishes in merge mode with `--base main`, even with another
  bundle's branch recorded in the same batch; and under the default mode both refused
  shapes still publish, against `fix/PARENT-my-fix` and `fix/PRED-groundwork`.
- **Test:** `template/tests/test_publish_slice.py` — a new `MergeModeBaseGuard` case
  (4 tests) appended to the existing publish suite; standard library only, git/`gh`
  and the model leaves stubbed as the rest of the file already does. Fails pre-fix:
  with the production change reverted and the tests kept, both refusal tests fail on
  the return code of the public `publish.publish` (`AssertionError: 0 != 1`), not on
  a missing import or attribute. Passes post-fix, with all 62 tests in the publish
  suite green; the full offline driver suite and the docs lint / site link audit were
  run against the patched tree as well.

Fixes #411
