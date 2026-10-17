# Advisory code review — issue #727 (dependency-scoped bases)

Lens: bugs the patch adds, plus reuse / simpler / cheaper code. Grounded on the patched
tree at `$PDCA_TARGET`. Gates: C4 red→green, T3 suite OK (2576 tests), docs clean.

I found no correctness bug that needs a human or another build round. The closure walk
(`_closure_members`), base selection (`_bundle_bases`), the head bookkeeping
(`bases_took` / `line_cut` → `_heads_taken`) and the split rewrite / unchecked messages
check out against the brief. The guard flagged in round 1 (a partner built after the
member it is reached from) now has a test aimed at it
(`template/tests/test_flow_dependency_scoped_bases.py:303`). I read it but did not
re-run it with the guard deleted, so I have not confirmed it goes red without the guard. The round-2 points are
handled too: a patchless prerequisite is walked through
(`template/tests/test_flow_dependency_scoped_bases.py:274`), and a base build that stops
for a clash leaves the end-of-run check on
(`template/tests/test_flow_dependency_scoped_bases.py:506`). Small notes, none blocking:

- `template/src/pdca_harness/flow.py:1003` — the base-build error is renamed by assigning
  `exc.args` in place. That keeps the `_Rewritten` type, which the caller needs for
  `stop_named` (`flow.py:2706`). But `exc.cause` still holds the old text without the
  "could not build X's own base" prefix. Nothing reads `cause` on this path today
  (`flow.py:2704` prints `str(exc)`), so nothing breaks now. It is a trap if a later
  change reports `cause`. Optional fix: set `exc.cause` too, or add an `owner` field to
  the error.
- `template/src/pdca_harness/flow.py:996-1006` — every base in the wave is built and
  pushed before any bundle is pointed at one. So when a later base fails, the bases
  already pushed stay on origin and are not recorded in `bases_took`. No bundle is built
  on them (the loop breaks before `_drive_wave`), so no PR holds them and the end-of-run
  check does not need them. The only cost is leftover `pdca-integration/*` branches, and
  the brief puts per-bundle base cleanup out of scope. Recorded for context; nothing to do.
- `template/src/pdca_harness/integrate.py:1123-1125` — the in-run fold now also refuses
  a branch when only a head that some bundle's own base took is gone, even if the line's
  head is still on the branch. Example: a base took a fast-forward of the line's head,
  then the branch was rewritten back. That one PR is affected, but the whole run stops at
  the next fold. The brief asks for the #633 check to get each base's head and name it,
  so this is in scope. Calling it out because it adds a new reason a run can stop.
- Reuse nit: `template/src/pdca_harness/integrate.py:1148` (`_rewrite_stop`) and
  `template/src/pdca_harness/integrate.py:1287` (`_late_line_rewrite`) each build their
  own copy of the sentence "every PR this run cut from <line> after it took <head>
  (<owners>)". A small shared helper would keep the in-run and end-of-run wording from
  drifting apart. This is cosmetic.
- Efficiency: `_heads_taken` (`template/src/pdca_harness/flow.py:1030`) looks up the
  target of every accepted bundle each time it is called: once per wave, once per fold,
  and once at the end. Each lookup reads a brief file. That is cheap at batch sizes, so
  no change needed.

No NEEDS-HUMAN items.

<!-- pdca:leaf-complete -->
