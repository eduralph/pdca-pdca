# Advisory code review — issue 626

No correctness bug found that needs another build round, and no NEEDS-HUMAN items. Three small points follow. I found them by reading the code and did not reproduce them.

- `template/src/pdca_harness/flow.py:1307` and `template/src/pdca_harness/merged.py:112` — the `Onto branch` / legacy record test that decides whether to add "drop it from the brief" does not match the rule that later holds a dependent. `merged_into` also refuses a record whose `repo` differs from the dependent's target, but `other_base` looks only at the mode and base. A squash-merged P whose record has another repo would be told "re-issue without P", and a planned D naming P would stay held. The next run prints `merged_into`'s own explanation, so the user is not stuck. This needs a brief whose target changed after publish, so it is rare. Minor; fix it only if this code is touched again.
- `template/src/pdca_harness/flow.py:1307` and `template/src/pdca_harness/integrate.py:1445` — the same "other base" test is written twice, and the patch's own comment says the two sites must give the same advice. A small shared helper taking the record, the onto flag and the base would stop them drifting apart. Simplification only.
- `template/src/pdca_harness/flow.py:1448` and `template/src/pdca_harness/flow.py:1454` — a finished Q naming both a squash-merged P and another not-clean X gets one cause, the first in its brief order. With P first, Q's line says only "re-issue without P", and that next run holds Q again for X with the right advice. X's own line is printed in the same run, so nothing is wrong, but the way out can take one more run. This follows the existing one-cause design and needs no change unless you want every cause listed.

Checked and clean:

- **Clean paths:** the extra `mergeCommit` read happens only for a MERGED PR whose head is on neither the base nor the line. The tests pin this at both sites.
- **Fail-closed:** an empty or unreadable merge commit, or one the base lacks, keeps the old messages at the fold and the carry.
- **Hints:** `_CARRY_HINTS` formatting gets every field the new hints use (`name`, `base`, `cause`). `_cascade_not_clean` always fills `causes` for a `built_on_squashed` entry that `_hold_all` keeps.
- **Way out:** a run without P gets its own line, because `integration_branch` (`integrate.py:141`) keys the name on the batch. This matches the comment on `_hold_all`.
- **Publish:** each path warns at most once, and a dry run makes no `gh` call.
- **Offline suite:** I ran `template/tests` with a logging `gh` stand-in on PATH: 2750 tests OK (2 skipped), and no test reached a real `gh` for `mergeCommit`. So the new read does not make other tests call the host.

<!-- pdca:leaf-complete -->
