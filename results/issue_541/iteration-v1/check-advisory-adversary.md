# Adversary — refutation attempts (#541)

Evidence re-run independently in a throwaway copy of `$PDCA_TARGET` (never the target
itself): `PYTHONPATH=src python3 -m unittest tests.test_attempt_harvest` is **green** with
the patch (9/9) and **red** with `assemble.py` + `leaves.py` stashed back to the pre-fix
base (9 failures + 2 errors, the same tracebacks as `gate-logs/C4-verify.log`). Every leg
drives the real `leaves._run_review_sandboxed` / `_run_advisory_sandboxed` /
`_run_plan_advisory_sandboxed`, so the red→green is not a parallel re-implementation. What
follows is what survived that.

- NEEDS-HUMAN — the un-owned refusal at `template/src/pdca_harness/leaves.py:836-841`
  destroys a LIVE verdict it could prove is live, and the patch's tests never cover that
  combination. `unlink()` needs write permission on the *directory*, while `open(path,"w")`
  needs it only on the *file* — so the exact scenario the patch's own leg builds (the dying
  attempt does `os.chmod(".", 0o500)`) still lets the NEXT attempt overwrite the residue
  with its own complete review. Driven against the real reviewer site with the stub writing
  `| C4 | PASS | LIVEMARK real verdict |` on attempt 2, `_degrade` fires with
  `self.produced.read_text()` equal to the LIVE attempt's full verdict: the bundle gets
  `# Advisory review — NOT COMPLETED`, the error log holds only the dead attempt's text, and
  the live verdict dies with the `tempfile.TemporaryDirectory` at
  `template/src/pdca_harness/leaves.py:2697`. So criterion 2 ("a real verdict must not be
  destroyed while the operator is told none was produced") is violated for the LIVE
  attempt's verdict by the code that enforces it for the dead one's, and criterion 3 ("the
  live attempt's own artifact is harvested exactly as today") fails in this corner. The
  harness already read the dead bytes in `withdraw`
  (`template/src/pdca_harness/leaves.py:851-857`), so a content/inode comparison would
  settle ownership without weakening the refusal. Left for the human rather than routed to
  Do because the brief's criterion 5 *ordered* "refuse to HARVEST on the success branch" —
  the collision between criteria 3 and 5 is the human's to rule on. Note the test gap either
  way: `template/tests/test_attempt_harvest.py:236,251,284` all pass `lock=True` with the
  default `live=""` (`:150`), so no leg ever has a live attempt writing under a locked
  sandbox.

- NEEDS-HUMAN [impl] — the withdrawn residue is quoted with NO bound into a tracked bundle
  file: `template/src/pdca_harness/leaves.py:852` reads the whole artifact and `:905-907`
  embeds it whole, once per attempt (`:746-751`). Measured against the real reviewer site: a
  stub that writes a 3.2 MB `check-review.md` and dies transiently on all three attempts
  yields a **9,600,536-byte `check-review.error.log`** in the bundle — held entirely in
  memory first, plus a `.check-review.error.log.partial` sibling copy. The channel this
  deliberately mirrors is bounded (`template/src/pdca_harness/progress.py:176`,
  `err_tail: deque[str] = deque(maxlen=200)`), and `results/` is tracked (only
  `results/issue_selftest/` is ignored, `template/.gitignore.jinja:16`), so this commits
  multi-MB logs into project history where today's code commits nothing at all. A head/tail
  cap with an elision line, exactly like `err_tail`'s, closes it.

- NEEDS-HUMAN [impl] — the new unknown-status fallback at
  `template/src/pdca_harness/assemble.py:191` demotes REAL findings. It maps *any*
  unrecognised marker token to `_UNKNOWN_LEAF_STATUS_LABEL`, and `leaf_status` matches the
  marker ANYWHERE in the artifact. Run against the patched `assemble`, an artifact carrying
  a full verdict table and two `- NEEDS-HUMAN [impl] —` findings, one of which merely
  *quotes* a marker with an unknown token (an advisory leaf discussing, say,
  `pdca:leaf-status some-future-status`), comes back as
  `NeedsHumanItem(text='leaf produced no verdict (unrecognised leaf status …) — off-by-one
  at foo.py:12', kind='human')` for BOTH items: §6 now says the leaf produced no verdict
  when it produced one, and the #264 `[impl]` routing is lost. Pre-fix the same artifact was
  untouched (unknown token → label `""`). It is self-triggering in this repo — an adversary
  artifact reviewing this patch has to avoid writing the marker verbatim, as this one does —
  and it is not asked for by the brief (criterion 4 is about the leaf-status *label*, not
  about unrecognised markers), so it is extra surface on a "one logical fix". Requiring the
  marker in the placeholder's own header region, or keeping `""` for an artifact that
  carries a verdict table, restores the old behaviour without giving up the #541 label.

Attempted and could **not** refute: (a) that a site was left behind — all three are
converted, `_invoke_leaf_resilient` has exactly one caller left
(`template/src/pdca_harness/leaves.py:828`), and there is no fourth `copy2` harvest; (b)
that the new `unowned-empty` status breaks an enumerating reader — the only two
`leaf_status` consumers (`leaves.py:3238`, `size_signal.py:240`) test truthiness, and
`_LEAF_STATUS_LABEL` has an entry, so `_items_from_artifact` still forces HUMAN and the
auto-iterate path stays closed; (c) that the retry contract narrowed — an un-withdrawable
residue still costs no attempt (3 observed); (d) that #540's four `*.error.log` readers are
made false — every degrade path writes its placeholder artifact, and `review_never_ran` /
`run_advisory_leaves(only_missing=True)` / `_missing_review_text` /
`driver._resume_interrupted_check` all key on artifact-exists *or* a SETTLED log, while
`_preserve` writes an unsettled record (`leaves.py:893`); (e) that a leg could pass for the
wrong reason — all 9 fail on the pre-fix base. One behaviour change I judged harmless and do
not file: a leaf that recovers from a transient blip and then writes nothing now leaves an
unsettled `check-review.error.log` behind where today it leaves none (`leaves.py:873-897`);
no reader misreads it, and the placeholder gains only a "See `check-review.error.log`"
pointer.
