# Build notes — issue 506 (iteration 4)

Target: `eduralph/pdca-harness` @ `main` (base `acb214a`). All paths/lines below are the
**post-patch** worktree (`$PDCA_WORKTREE`).

Iteration 3 was rejected on three implementation findings, with an explicit instruction to
KEEP the rest of the mechanism (marker-anchored matcher, sticky transient, per-attempt error
log flush, `_has_content`, the `capture` guard, derived `memory_log`). I started from v3's
patch applied to the base and changed **only** what the sign-off named, plus the same defect
class where it also existed on the arm the sign-off did not check (see §1c).

Everything asserted about the vendor below was read out of the binary the harness actually
spawns — `/home/eddie/.local/share/claude/versions/2.1.233` (`claude --version` → 2.1.233).
Snippets are quoted verbatim so a reviewer can `grep -a` for them.

---

## 1. Defect 1 — a real mid-response connection loss under kind `unknown`

**Reproduced.** The mapper's tail (search the binary for `sie.has(o.code)`):

```js
let o = lj(e);
if (o && (sie.has(o.code) || gde.has(o.code)))
  return Yd({content:`${Uw}: Connection to the API was lost (${o.code}). This is usually
             temporary — try again.`, error:"server_error"});
if (e instanceof Error) return Yd({content:`${Uw}: ${e.message}`, error:"unknown"});
return Yd({content: Uw, error:"unknown"});
```

and the two sets:

```js
gde = new Set(["ECONNREFUSED","ConnectionRefused","ENOTFOUND","ENETUNREACH","ENETDOWN",
               "EHOSTUNREACH","EHOSTDOWN","EAI_AGAIN","FailedToOpenSocket","ERR_PROXY_TUNNEL"]),
sie = new Set(["ECONNRESET","EPIPE","ConnectionClosed","ETIMEDOUT","ECONNABORTED",
               "ERR_SOCKET_CLOSED","StreamSuspended"]);
```

Neither holds any `UND_ERR_*`, and `lj()` only ever returns the cause's **code** — it is never
written into the message. So undici's canonical mid-body abort (`TypeError: terminated`, cause
`SocketError{code:"UND_ERR_SOCKET"}`) reaches the stream as `is_api_error_message` + `error:
"unknown"` + text `API Error: terminated`, and v3's `_TRANSIENT_CAUSE_RE` matched none of it.

**Fix** (`progress.py:473-503`): added `\bterminated\b`, `other side closed`,
`socket (connection) (was) closed`, `stream disconnected|idle timeout`, and
`connection was closed|lost|reset`; **removed** the `UND_ERR_[A-Z_]+` alternative, which the
sign-off correctly called unreachable (the code lives in the JS error's `cause`, never in the
text — there is nothing to read it from on the stream, so it was coverage-shaped and empty).
The constant's docstring now records exactly this (`progress.py:463-472`).

This cannot re-open iteration 1's false-positive arm: the regex runs only on text the CLI
itself flagged as its API-error message (`progress.py:544-550`), and the two precision legs
(a substantive death opening with "Error … 500", a builder quoting the incident line) still
pass — `test_leaf_resilience.py:416, :426`.

While in there I also grounded the kind set: 2.1.233's mapper emits `server_error`,
`rate_limit`, `invalid_request`, `authentication_failed`, `billing_error`, `model_not_found`,
`unknown` — no `overloaded`. `overloaded` stays in `_CLAUDE_TRANSIENT_ERROR_KINDS` because the
CLI's own transient predicate names it (`isTransient: t.apiErrorIsTransient===!0 ||
t.error==="overloaded" || t.error==="server_error"`), and the docstring now says so rather than
implying 2.1.233 emits it (`progress.py:452-460`). `apiErrorIsTransient` itself is **not**
forwarded to the stream by either emitter, which is why the set mirrors the predicate minus the
flag.

## 2. Defect 2 — the `result`-branch `api_error_status` arm was dead

**Reproduced.** The engine builds exactly three result records (verbatim, one line unwrapped):

```js
_t = jt===null && Xr===void 0 && Ue
   ? ite({common:{...bt,is_error:!0}, variant:{subtype:"error_max_turns",
       errors:[`Reached maximum number of turns (${Ue.maxTurns})`]}})
   : Jr!==null
   ? ite({common:{...bt,is_error:!0}, variant:{subtype:"error_during_execution", errors:Jr}})
   : ite({common:{...bt,is_error:Ze}, variant:{subtype:"success", api_error_status:gt,
       result:Ze?Dt:qe, …}});
```

with `Ze = zt.isApiErrorMessage===!0`, `gt = zt.apiErrorStatus ?? null`, `Dt` = that message's
text, and `Jr = [thrown error] | ["[ede_diagnostic] turn aborted (…) stop_reason=…"]`. The SDK
result schemas agree (`success` variant declares `api_error_status`; the
`error_during_execution|error_max_turns|error_max_budget_usd|error_max_structured_output_retries`
variant declares `errors: string[]` and no status), and so does the CLI's own telemetry:
`api_error_status: ol.subtype === "success" ? ol.api_error_status ?? void 0 : void 0`.

v3 gated the arm on `subtype != "success"` **and** required an `api_error_status`, i.e. on the
one shape that can never carry it. **Fix** (`progress.py:551-557`): the branch now fires on
`is_error` for any subtype (retention — the max-turns sentence and the aborted-turn diagnostic
now reach `build.error.log` instead of `(no output captured)`), and classifies transient only
for `subtype == "success"` + a machine-set `api_error_status`, which is the CLI's own record of
"this session ended on my own API-error message". No prose matching in this branch, as the
sign-off asked.

The two impossible records are gone (v3's `test_a_result_the_cli_stamped_with_an_api_status_is_retried`
and `…_a_status_on_an_ending_the_session_owns…`), replaced by
`test_the_api_error_ending_is_classified_by_the_status_the_cli_attached`
(`test_leaf_resilience.py:483`), whose four legs (503/429 → retried, 400/`null` → not) all use
shapes 2.1.233 emits. `_CLAUDE_INFRA_RESULT_SUBTYPES` is deleted — it existed only for the dead
guard.

### 2c. The same defect on the arm the sign-off did not check

The **assistant** stream event carries neither `api_error_status` nor `api_error`: both emitters
write only

```js
{type:"assistant", message:n, session_id:qt(), parent_tool_use_id:null, uuid:r.uuid,
 timestamp:r.timestamp, error:r.error, …(r.isApiErrorMessage===!0 && {is_api_error_message:!0}), …}
```

(the SDK schema declares the two fields `@internal`-optional, but nothing sets them). v3 read
both there, and pinned the status with a synthesised event — the same "green test for an event
that cannot exist" the sign-off rejected in the result branch. Both reads are removed
(`progress.py:544-550`) and the test that pinned them is deleted. Nothing is lost: the engine
folds that very status into the `result` wrap-up, which is where §2 now reads it.

## 3. Defect 3 — the stickiness rationale cited an ending never observed

`Execution error` appears nowhere in 2.1.233, and the pinned transcript has no result record at
all. Restated over the two endings that genuinely can follow an API-error message
(`progress.py:561-580`): the `success` variant restating the dead message (`is_error`, its text
in `result`, `api_error_status` **null** when the connection dropped before any response), and
`error_during_execution` carrying only `["[ede_diagnostic] turn aborted (…) stop_reason=…"]`.
Neither names the cause, so newest-wins overturns the report that did — which is exactly what
stickiness prevents. The fixture in the test moved with it: `_WRAP_UP` ("Execution error") is
replaced by `_WRAP_UP_RESTATES` / `_WRAP_UP_ABORTED` (`test_leaf_resilience.py:82-92`) and the
stickiness case now sweeps **both** (`:445`). The aborted-turn leg is the sharper one: its
wrap-up text differs from the API-error text, so the assertion that the log still holds the
cause proves the text stayed too, not just the verdict.

`tests/fixtures/README.md` gained a short section quoting the emitter, so the claim is checkable
rather than asserted (it is the file whose subject is provenance; no fixture bytes exist for a
`result` event, because transcripts do not record them).

---

## Refuting my own test (forced)

* **(a) Genuine red?** Yes — through the project's own gate:
  `PDCA_BUNDLE=… PDCA_WORKTREE=… ./engine/scripts/run-verify.sh` →
  `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`; the red leg ran 27 tests and
  reported 30 failures (subtests) with only the production hunks reverted, and the module still
  **imported** (no `unittest.loader._FailedTest`), so the red is a measurement, not a load error.
* **(b) Production path?** Yes. Every case spawns a real child through
  `leaves._invoke_leaf_resilient` → `leaves._invoke` → `progress.run_with_heartbeat` →
  `subprocess.Popen`, and the Do cases go through `leaves.do_build` itself. Nothing is mocked
  between the child's bytes and the assertion; the only patches are `leaves.time.sleep` (so the
  backoff costs no wall clock) and `os.environ` (to hand the child its markers). Markers reach
  the child via **env or a fixture file**, never argv, because `_format_leaf_attempt` echoes the
  argv into the log and an argv-borne marker would satisfy the assertion with no capture at all.
* **(c) Fixture includes the fault?** Yes. The incident's own record is replayed byte-for-byte
  on the leaf's stdout in both spellings (`tests/fixtures/claude_api_error_death.*.jsonl`), the
  child really exits non-zero after real work, and the retried-builder legs run with the dead
  attempt's residue (`patch.diff`) present rather than curated away.

**Beyond the minimum — mutation matrix.** Each mutation applied to the patched tree in turn,
module re-run, tree restored (all seven caught):

| mutation | caught by |
|---|---|
| drop `terminated` / `other side closed` from the cause set | 2 legs of `…read_from_its_text` |
| re-key the result arm on `subtype != "success"` (v3's dead guard) | 2 legs of `…status_the_cli_attached` |
| drop the sticky guard in `_note_terminal` | both legs of `…does_not_overturn_the_report…` |
| `_CLAUDE_TRANSIENT_ERROR_KINDS → frozenset()` | 3 (kind sweep + rate-limit) |
| make the whole `result` branch inert | 6 (retention + status sweep) |
| stop forcing `produced` back to False | 22 |
| stop appending the terminal report to `output` | 24 |

**Suites.** `template/tests`: 1780 tests OK (skipped 2). Target root suite: OK.
`./engine/scripts/run-suite.sh` (T3, render + update-compat + offline): `root suite OK, driver
suite OK`.

---

## Ruled out, with the cost

* **Single `json.loads` per drain line** (the sign-off's "optional if free"). Not free:
  `_is_session_event` and `_stream_tool_label` take a **string** and are pinned that way at
  **18 call sites** in `template/tests/test_progress.py:89-186`, several of which exist to
  assert the non-JSON path (`_stream_tool_label("not json at all")`). Threading a parsed event
  through means either rewriting those 17 assertions plus 4 production call sites, or adding a
  parallel `*_ev(ev: dict)` layer (~16 new production lines). Both are new surface for a
  micro-optimisation on a path that runs once per line of a leaf otherwise blocked on the
  network. Left alone; the comment cost is zero and the behaviour is identical.
* **A live-API red.** The one thing no offline leg can do is induce a genuine mid-response
  connection loss. Everything vendor-specific here is therefore read from the shipped binary
  (quoted above) or replayed from the pinned incident record. This remains the standing §6
  item from the last two sign-offs — it is a limit of the environment, not an untried option.
* **Session resume instead of a fresh re-invoke** (the brief asks Do to say so explicitly).
  Out of scope by the brief, and for this incident nothing would have been lost either way: the
  dead attempt had produced no bundle artifact, so a fresh `claude -p` re-invoke repeats only
  the reading it had already done. Resume would need `--resume <session_id>` plumbing, a place
  to keep the session id per attempt, and a policy for a session whose transcript is itself
  truncated — a slice of its own. The retry note (`leaves.py:1885`) is what makes a fresh
  re-invoke safe in the meantime.
* **The reviewer/advisory attempt-blind harvest** — flagged by the round-2 sign-off, and
  explicitly excluded again by round 3. Unchanged, and still true: widening the classification
  makes those leaves retryable *after* they produced work, and their harvest
  (`leaves.py:2653-2657`, and the two advisories at `:2986-2987`, `:3287-3288`) copies `check-review.md`
  out of the sandbox on the wrapper's success without knowing which attempt wrote it — so a
  truncated file from a dead attempt 1 can be harvested if attempt 2 exits 0 without rewriting
  it. Measured cost to close **here**: a `produced: Path | None` kwarg cleared at the top of
  each attempt in `_invoke_leaf_resilient` (~6 lines incl. docstring), threaded through 3 call
  sites (3 lines), plus 2 tests (~25 lines) ≈ **34 lines across two files**. Left for a separate
  issue as instructed.
* **Deleting the builder's residue on a transient death** (which would make a plain "re-run Do"
  message true). Rejected in iteration 2 and still rejected: destroying evidence to make a
  sentence true. `_transient_do_death` (`leaves.py:1843`) names the residue instead.

**Known trade-off in the sticky rule, stated so nobody has to find it.** If a leaf emits a
*transient* API-error report and then a *permanent* one with no work in between (a dropped
connection followed by a hard 400, say), stickiness keeps the transient verdict and the leaf is
re-invoked up to the attempt budget before it settles. Cost: two extra spawns, bounded. The
alternative — last-writer-wins — is precisely what classified the incident substantive and
retried it zero times, which is the failure this slice exists to end. Ambiguity therefore
resolves toward "retry", and only real work after a report clears it.

## Size

Final patch **92,086 B / 8 files** vs iteration 3's 88,126 B — **+3.9 KB**, against the
advisory 80 KB backstop it was already over. The sign-off asked that these three fixes not grow
it; they did, and here is the ledger so the human can judge it rather than take an adjective:

| change | Δ |
|---|---|
| `tests/fixtures/README.md` — the `result` emitter quote (the evidence for §2/§3) | ≈ +1.7 KB |
| new test legs: 2 wrap-up shapes, 2 undici causes, the 4-leg status sweep | ≈ +1.6 KB |
| widened cause set + its docstring, kind-set grounding, `2c` comment | ≈ +1.4 KB |
| removed: assistant-branch status/`api_error` reads, `_CLAUDE_INFRA_RESULT_SUBTYPES`, one whole test, v3's two impossible records | ≈ −1.3 KB |
| prose compaction across `progress.py` / the test header to offset the above | ≈ −0.5 KB |

I compacted where I could without dropping a claim and stopped there: the remaining growth is
vendor evidence and test legs the sign-off asked for. No new production surface was added — the
production diff is one branch re-keyed, two reads deleted, one constant deleted, four regex
alternatives added and one removed.

## Not done / carried

* No new `pdca.toml` knob; attempts/backoff defaults reused as they are.
* `flow_one`'s propagation, `flow._isolate`, #371, #510, #420 — untouched, as the brief scopes.
* The test ships **inside** `patch.diff` at `template/tests/test_leaf_resilience.py` (the brief
  says append to that suite), so the bundle carries no second copy of it.
* Commit-readiness: the target configures no formatter, linter or commit hook
  (`.pre-commit-config.yaml` absent, `core.hooksPath` unset, no ruff/flake8/black config); its
  CI is copier render + docs. I kept every touched line within the files' existing width
  convention (≤ 97 chars) and ran the render check via `run-suite.sh` (root suite OK).
