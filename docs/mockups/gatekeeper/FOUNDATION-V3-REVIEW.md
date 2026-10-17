# Gatekeeper assessment foundation V3 — independent re-review

17 October 2026. **The six previous findings are closed. One completed-retry regression needs correction before enabling the page runner.** This is a focused change; the session-only design remains appropriate.

## Scope and identity

Reviewed `gatekeeper-assessment-foundation-v3.zip`, SHA-256:
`28eb5e2662118b8f11feb4aa1defef2c4ad9a73613ac7d98cd470721003354a5`.

Eight archive files; CRC and extraction checks passed. The three modules still import only Python's standard library and one another. `assessment_models.py` is byte-for-byte unchanged from foundation V2; the service and session store changed. The three bundled `review/` regression files are byte-for-byte identical to the previous review's originals. Full hashes are in `manifest-verified.json`.

No submitted module was modified, wired into the agent, or deployed. All tests use local fake assessors; no SAP or model requests were made. The underlying application baseline remains `assets V2.zip`.

## Previous findings: all closed

| Finding | Verified result | V3 source reference |
| --- | --- | --- |
| R1: nested affirmative defaults, malformed enums, unavailable duplicates | Missing required flags/lists produce incomplete; list/object enum values no longer raise; unavailable duplicate evidence produces no recommendation/confidence. | `assessment_service.py:174–215,269–284` |
| R2: lifecycle fencing and standalone publication | Fenced rejection does not create, revive, touch or evict a scope. Standalone generation is captured before waiting; rejected publication cannot return a complete verdict. | `assessment_session.py:229–253`; `assessment_service.py:344–368` |
| R3: simultaneous same-run submission | Concurrent submissions sharing a key, including the same run object, join one execution. | `assessment_service.py:398–416` |
| R4: parent cancellation | Semaphore waiters settle to terminal states; completed/incomplete rows are preserved. | `assessment_service.py:455–465` |
| R5: contradictory override rationale | Unsupported Approve receives a factual server-written referral explanation. Valid High-confidence manual referral remains possible. | `assessment_service.py:287–303` |
| R6: mutable worklist snapshots | Store input and output are deep-copied; original/returned membership mutations cannot change the canonical snapshot. | `assessment_session.py:360–375` |

The lower-priority superseded-action cleanup is also fixed at `assessment_session.py:275–277`.

## Must have: preserve completed-operation idempotency

**P2 — fix before enabling page assessment.** `assessment_service.py:398–407,462–465`; `assessment_session.py:332–357`.

Admission now checks only `_inflight`. Completion removes that entry, so a later submission with the **same idempotency key** runs the assessor again and replaces the saved assessment. This happens with either a new `PageRun` or the original run object. The completed run is still in the scope's `runs` dictionary, but admission does not consult it.

Reproduced with one notification, one live scope and the same operation key:

| Step | Expected | Observed |
| --- | --- | --- |
| First submission completes | One assessor call; revision 1 | Correct |
| Retry after completion | Reuse existing operation; still one assessor call and revision 1 | Two assessor calls; new assessment ID and revision 2 |

An HTTP retry after a lost response, reconnect, or repeated click after completion could therefore change the recommendation/confidence and invalidate the prior action context. It also repeats SAP/model work. A fake assessor returning different valid answers demonstrates **Approve / High → Rework / Medium** for the same operation key; this illustrates the consequence, not a claim about actual model frequency. Opening a stored detail record itself was not shown to rescore.

The README says explicit reassessment uses a **distinct key**, so a repeated key must remain a retry. V2's distinct-run-ID completed retry passed; V3 regresses that behavior while fixing simultaneous same-run joining.

**Required correction:**

1. Under the admission lock, check both in-flight ownership and retained completed operations in the current live scope/generation. Never replace an existing operation's completion event.
2. Same operation identity while running: join. Same completed operation with retained results: reuse its operation/result identity without calling the assessor or incrementing revisions.
3. Explicit reassessment: require a distinct key. Bind reuse to the same actor/scope, snapshot/page membership and assessment configuration; a mismatched reuse must not silently return another operation.
4. Keep lifecycle boundaries: expired, evicted or invalidated results are unavailable. Do not revive them, silently rescore an old operation, or replay stale action eligibility. This requires only temporary session memory.

The minimal fix can build on the existing `find_run_by_idempotency`; a new persistence layer or framework is unnecessary. Ensure lookup remains valid for the session generation and retained results rather than blindly returning any historical run.

Evidence: `review-checks/test_runner_lifecycle_v3.py` has two failing tests covering same/different run objects after completion. `runner-completed-retry-v2-control.log` records the passing V2 distinct-run control. `retry_observation.py` and its output illustrate changing decisions with a variable fake assessor.

## Nice to have

- **Make the packaged test commands directly runnable.** From the submitted source directory, `python -B review/models_repro.py` fails on a clean import path: the script inserts `source/source`, while the modules are one directory above it. The other two bundled review scripts have the same layout. Document `PYTHONPATH=.` explicitly, fix their path bootstrap, or package a working launcher. This is a test-packaging issue, not a product regression; the tests pass when pointed at the actual V3 modules.
- **Stop known-stale queued work early.** After obtaining an item lock, `assess_one` calls the assessor before checking whether its captured generation still matches. Publication correctly rejects stale results, but an invalidated page can continue spending SAP/model resources. A non-mutating fence check before invoking the assessor can avoid that waste; retain the publication check as well. Do not call a write-intent accessor that revives/touches the scope just to validate the fence.

The global `_inflight` registry also survives scope invalidation/eviction while a worker runs. A retry of that old key can join the retired operation and receive failed/no result. This fails safely and is not another release blocker; keep generation/lifecycle behavior explicit when fixing completed reuse.

## Verification

| Suite | Result |
| --- | --- |
| Supplied foundation suite | 17/17 pass |
| Prior bundled schema follow-ups (`models_repro.py`) | 5/5 pass |
| Prior bundled service follow-ups (`service_repro.py`) | 5/5 pass |
| Prior bundled session follow-ups | 3/3 pass |
| Original reviewer regressions, restored unchanged | 14/14 pass |
| Additional V3 schema checks | 4/4 pass, covering 30 subcases |
| Additional V3 session checks | 6/6 pass; three repeat prior session invariants |
| New completed-retry regressions | **0/2 pass; two assertion failures, one root cause** |

The first five rows total **44 passing baseline checks**. Additional checks overlap some earlier invariants and should not be interpreted as a unique quality score. Expected fault-injection logs do not constitute failed suites; exit codes and outputs are retained separately. The new retry failures are product assertions, not import failures.

The original 14-test reviewer's file remains SHA-256 `41420dace24476b3d276a36022a92efe43efdce5e55c96866b9db7b794871fb6`.

## Integration handoff

Close the completed-retry issue and rerun the tests, then proceed with staged integration. No need to rewrite the three modules or add durable BTP storage.

The explicitly deferred work remains deferred: real tool-outcome evidence reconciliation, per-notification LangGraph checkpoint isolation, authorized current-page admission, aggregate SAP/model limits, policy/model/prompt provenance, async progress/A2A callbacks, HIL business eligibility and fresh SAP Show-Remaining queries. The foundation tests do not demonstrate those live integrations or production UI behavior.

Keep the agreed product behavior: 20 notifications on the current scrollable page; full-depth assessment once; detail/chat display the same session record; expiry disables old actions; SAP remains authoritative for business status and the remaining list.
