# PR description

## Summary
**User impact:** anyone who enables Remote Control exactly the way the
configuration file's own comment tells them to gets the opposite of what they
asked for: Remote Control fails to start with only "check the debug log" to go
on, and the working session opens empty — the instructions it was supposed to
start with are silently gone. The failure looks like a Remote Control outage,
so the copied-verbatim example is the last place anyone suspects.

This PR fixes the shipped example and its documentation, and hardens the driver
so that no flag placed at the end of a session's command line can ever eat the
opening instructions again.

Reported in [#396](https://github.com/eduralph/pdca-harness/issues/396).

## What to look at
Two doc comments and a one-line spawn change. The configuration example now
puts `--remote-control` in the middle of the command line instead of at the
end, and explains why the end is unsafe; the driver now inserts a standard
"end of options" marker before the opening instructions when the session's
command-line tool supports one, so the guarantee no longer depends on where an
instance puts its flags.

To reproduce the defect on `main`: uncomment the Remote Control example in a
rendered instance's `pdca.toml` as-is (flag last) and run a flow to any
interactive step — Remote Control errors out and the session opens unseeded,
while `/remote-control` typed inside a session works fine on the same machine
(first hit in the field as eduralph/pdca-pdca#19).

## Root cause
The driver seeds every interactive leaf with `subprocess.run(argv + [seed])` —
the prompt is the final positional after whatever argv the instance configured
(`template/src/pdca_harness/leaves.py:379` on `main`). `--remote-control`
takes an optional `[name]` value, and the shipped example places it as the
argv-final token (`template/pdca.toml.jinja:551-552` on `main`), so the flag
greedily parses the entire seed prompt as the RC session name: RC fails to
start and the REPL gets no seed.

## Fix
- **`template/pdca.toml.jinja`** — the example becomes `["claude",
  "--remote-control", "--agent", "planner", …]` and the comment states the
  rule: the seed is appended as one positional after the argv, so no
  optional-value flag may sit last.
- **`template/docs/INTEGRATION.md.jinja`** — same rule in both family
  branches; the non-claude branch notes that families without a declared
  separator have no backstop, so placement is their only protection.
- **`template/src/pdca_harness/families.py`** — new profile field
  `seed_separator` (default `""` = no behavior change); the claude profile
  carries `"--"` (verified: `claude -p --version` prints the version,
  `claude -p -- --version` treats `--version` as the prompt — `--` terminates
  option parsing on claude 2.1.222 and 2.1.223).
- **`template/src/pdca_harness/leaves.py`** — the one interactive spawn site
  becomes `argv + sep + [seed]`, so for claude the seed always arrives as
  `claude … -- "<seed>"` and a trailing optional-value flag has nothing to
  swallow. The headless path (prompt via stdin) is untouched, and families
  without the bit keep a byte-identical spawn.

## Verification
- **Claim:** on `main`, the seed is a bare trailing positional that a final
  optional-value flag consumes.
  **Checked:** `template/src/pdca_harness/leaves.py:379` on `main` —
  `subprocess.run(argv + [seed], …)`; `template/pdca.toml.jinja:551-552` on
  `main` — the example ends in `--remote-control`.
- **Claim:** with the fix, the claude-family spawn is argv-independent: the
  exact defect argv (flag last) yields `argv + ["--", seed]`, and a family
  without the bit spawns byte-identically to before.
  **Test:** `template/tests/test_seed_spill.py` (`SeedSeparator`) — fails
  pre-fix (no separator in the spawned argv; no such profile field), passes
  post-fix. Only the terminal `subprocess.run` is recorded; profile
  resolution, seed handling and argv assembly run the production path.
- **Claim:** the shipped example never shows the flag last and the doc states
  the placement rule.
  **Test:** `template/tests/test_remote_control_docs.py`
  (`test_the_example_never_shows_the_flag_last`) — fails pre-fix against the
  current example, passes post-fix. It scans the real shipped file, not a
  fixture copy.
- **Suites:** template suite 1567 tests OK (2 skips), repo-root render/update
  suites 7 OK; docs link audit OK (22 pages).
- **Manual (irreducibly interactive — RC needs an enrolled device and a
  human):** `claude --remote-control -- "say SEEDED and stop"` → RC banner and
  a seeded REPL; negative control `claude --remote-control "say SEEDED and
  stop"` reproduces the defect (prompt taken as the session name).

Fixes #396
