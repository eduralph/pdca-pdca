# Build notes — issue 842, round 2

For the human at sign-off. The reviewer does not see this file.

## What changed

Line numbers are on `origin/main` (333990e) unless marked "after the patch". The worktree base
is f5321ab, the integration branch that adds 838 on top of main. It does not touch `config.py`
(same blob, 8da9640, on both), and the patch applies cleanly to `origin/main` (checked with
`git apply --cached --check` against a temporary index holding main).

- `template/src/pdca_harness/config.py:733` — the one line that kept any value is now lines
  733-740 after the patch: the comment, the read, the check and the raise.
- `template/tests/test_config_wave_mode.py` — new. One helper (`:27`) and three tests (`:43`,
  `:55`, `:76`), the shape the brief spells out.

What a user now sees for `wave_mode = "bogus"`, from a real process, on any subcommand:

```
pdca: invalid pdca.toml — [driver].wave_mode 'bogus' is not one of stack | merge
```

and exit 2. The prefix comes from the existing handler at `cli.py:452-454`. `cli.py` needed no
change, so the brief's claim about that handler holds.

## Decisions

**The check is `isinstance` first, then a tuple, as the brief requires.** One thing the brief
does not say: with a tuple, the `isinstance` is not strictly needed today. Tuple membership
compares with `==` and never hashes, so `["merge"] in ("stack", "merge")` is just `False`. I kept
it because the brief asks for it and it keeps the check safe if someone later swaps the tuple for
a set. The "bare set test" variant below shows the failure it guards against.

**The allowed values are written out in the check and the message, with no shared constant.** A
`_WAVE_MODES` tuple plus `" | ".join(...)` would add 1 constant line and lengthen the message
line for one reader. 843 adding `"none"` edits two strings on adjacent lines either way, and the
brief scopes this to one site. Not worth it for this slice.

**Exact match, no folding**, as the brief rules. The comment on the line says why, because a later
reader will be tempted to add `.strip().lower()`.

**One place the test differs from the brief's wording.** The brief says to hold the `StringIO` in
a local and read it after the `with`, so the caller can still read it after the raise. A local in
`_load` is gone once `_load` raises, so the buffer also stays on `self.err`
(`test_config_wave_mode.py:34`), set first thing on every call so a previous subtest's buffer
can't be read by mistake. The signature and return value are as the brief states. I did not use
a `redirect_stderr` in the caller instead: `_load`'s own redirect would replace it, so that buffer
would stay empty whatever `Config.load` printed, and the assertion would prove nothing. The
docstring records this. The "print AND raise" variant below shows the assertion does bite.

"One helper" is kept: the TOML header is a module constant (`BASE`, `:23`) and the CLI test writes
its own file inline.

**Prior-cycle material.** I did not read `iteration-v1/`, as the brief says. The bundle also held
a stale `test_config_wave_mode.py` from round 1. I overwrote it with `cp` from the worktree without
opening it.

## Left alone, as the brief scopes it

- `cli.py`: no change needed, see above.
- `template/.claude/hooks/handoff_guard.py:45`: still a traceback on a bad value, per the brief. I
  did not open it beyond confirming the line. `git grep 'Config\.load'` outside the tests finds
  exactly the three callers the brief lists: `cli.py:448`, `size-calibrate:599` (catches
  `ValueError` at `:600`) and this one.
- The note-and-substitute neighbours, and the comment at `config.py:735-737` that still argues for
  falling back. After this patch that comment sits directly under one that argues the opposite.
  The brief records this as your accepted call.
- `pdca.toml.jinja:115-138` and `docs/`: no wording change. `pdca.toml.jinja:138` renders `"stack"`,
  so a new render passes the check.

## Seen while here, not touched

These may be useful for your follow-up issue on the 2026-10-30 ruling:

1. **Other `[driver]` keys can still produce a traceback.** `int(driver_cfg.get("lanes", 1))` at
   `config.py:709` has no `try`, and `int([])` raises `TypeError`, which `cli.py:452` does not
   catch. `max_passes` (`:715`), `max_auto_iters` (`:726`) and `overflow` (`:731`) have the same
   shape. I confirmed the `TypeError` from `int()` on a parsed `lanes = []`, not through a full
   `pdca` run.
2. **Two stderr lines are still possible on a file with two bad keys.** `confirm_gating_fail`
   (`:600`) and `network_access` (`:674`) print their notes before line 733. A root with one of
   those wrong and a bad `wave_mode` gets the note and then the refusal. Criterion (c) is about a
   root where only `wave_mode` is wrong, and that gives one line.
3. **Keys after `wave_mode` are not reported until it is fixed**, because the raise stops the load.

## Behaviour change to expect

An instance with a typo in `wave_mode` works today as if it were `"stack"`. After upgrading, every
`pdca` command on it stops with exit 2 until the file is fixed. That is what the ruling asks for,
and the message says what to write. This instance is not affected: `pdca.toml:137` here has
`"stack"`.

The tracker comment on #842 recording the ruling is still yours to add before publish, as the
brief says.

## Refuting the test

**(a) Genuine red? Yes.** `./engine/scripts/run-verify.sh` (the C4 gate, the per-fix check),
which really reverts the production hunk and re-runs the test:

```
== C4 green leg ... Ran 3 tests ... OK
== C4 red leg   ... Ran 3 tests ... FAILED (failures=9)
PDCA-EVIDENCE: C4 PASS — red without the fix, green with it
```

The 9 failures are the 8 refused values (`AssertionError: ValueError not raised`) and the CLI test
(`AssertionError: 0 != 2`). All are assertion failures, so the module loaded and the tests ran.
`test_known_values_and_absent_key_are_silent_and_kept` stays green on both legs, which is correct:
it guards leg (d), the behaviour that must not change.

I also ran 12 plausible wrong fixes through the same script, one at a time, restoring `config.py`
after each (the regenerated diff then matched `patch.diff` byte for byte). All 12 were caught:

| Wrong fix | Result |
|---|---|
| print and raise (loader writes to stderr) | 9 failures: all 8 values, CLI test |
| bare `not in {...}` set test | 2 errors: the array and the table (`TypeError`) |
| folds case and whitespace | 2 failures: `"Merge"`, `"merge "` |
| note and fall back (the shape rejected in round 1) | 9 failures |
| silent fall back | 9 failures |
| message without `!r` | 4 failures: the four strings |
| message without the allowed values | 9 failures |
| message without the key name | 9 failures |
| `sys.exit` instead of `ValueError` | 9 errors |
| `TypeError` for non-strings | 4 errors: `1`, `true`, array, table |
| refuses `"merge"` too | 1 error: the known-values test |
| drops the `"stack"` default | 1 error: the known-values test, absent key |

**(b) Production path? Yes.** The test imports the real `pdca_harness.config.Config` and
`pdca_harness.cli` and mocks nothing. `_load` calls `Config.load(root)` on a real file parsed by
`tomllib`. The CLI test calls `cli.main(["status"])`, which finds the file from the working
directory through `_find_root`. The C5 gate (`run-prod-path.py`) agrees: "1 added driver-suite
test(s) import the production package".

**(c) Fixture includes the fault? Yes.** Each fixture is a real `pdca.toml` holding the bad value.
Nothing is hand-built: no `Config(wave_mode=...)` constructor call, which would skip the check.

Beyond the test, real processes through the entry point the console script uses
(`sys.exit(main())`):

| `wave_mode` | exit | stderr lines | traceback |
|---|---|---|---|
| `"bogus"`, `"merge "`, `["merge"]`, `{ mode = "merge" }` | 2 | 1 | no |
| `"""two\nlines"""` (shown as `'two\nlines'`, `!r` keeps it on one line) | 2 | 1 | no |
| `2024-01-01` (a TOML date) | 2 | 1 | no |
| `"stack"`, `"merge"`, absent | 0 | 0 | no |

On a `"bogus"` root, `waves`, `doctor`, `flow 123`, `run 123` and the bare command, called as
`main([...])`, all exit 2 with one stderr line and nothing on stdout. The real `flow` entry
(`argv` is `None`) first re-executes itself under a suspend inhibitor at `cli.py:443-444`. I did
not run that path; it reaches the same `Config.load` afterwards.

## Whole suite

`./engine/scripts/run-suite.sh` (T3, both target suites) with the patch applied, exit 0:

```
== T3: template-repo suite (render + update-compat)
Ran 50 tests in 93.729s
OK
== T3: offline driver suite (template/tests, PYTHONPATH=src)
Ran 2700 tests in 99.284s
OK (skipped=2)
PDCA-EVIDENCE: root suite OK, driver suite OK
```

So no existing test or fixture relied on an unknown `wave_mode`. This ran on the worktree base
(f5321ab, main plus 838), not on bare `origin/main`. Check's T3 gate runs it again.

## Commit-ready

The target has no formatter or commit hook to run. No hooks in `.git/hooks` other than samples, no
`core.hooksPath`, no `.pre-commit-config.yaml`, no ruff/black config, no lint step in
`.github/workflows/`, and no mention of one in `CONTRIBUTING.md` or `pdca.toml`. What is left is
DCO sign-off, which publish adds. `git diff --check` is clean and the longest added line is 95
characters.

No external dependency was missing.

## A slip to report

To check that the patch applies to `origin/main` I used a temporary git index, which left one file
outside the roots I am meant to write to:
`/home/eddie/pdca/pdca-harness/.git/worktrees/pdca-harness.pdca-wt-l2/pdca-842-check.idx`. Nothing
reads it and it does not affect any checkout. It is inside this worktree's admin directory, so it
goes when the harness removes the worktree. I left it there because cleanup is the harness's job.
If this lane's worktree is kept and reused, it stays until someone deletes it.
