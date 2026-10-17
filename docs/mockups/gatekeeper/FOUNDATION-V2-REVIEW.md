# Gatekeeper assessment foundation v2 — re-review

17 October 2026. Verdict: **the supplied regressions are fixed, but a few remaining foundation paths need correction before live wiring**.

## Verified claims

- All five SHA-256 prefixes supplied by the user match the uploaded files.
- Standard-library/local imports only: confirmed.
- Original suite: **12/12 pass**, exit 0.
- Bundled reviewer suite: **14/14 pass**, exit 0.
- The reviewer suite is byte-for-byte identical to the original reviewed file, SHA-256 `41420dace24476b3d276a36022a92efe43efdce5e55c96866b9db7b794871fb6`. Its assertions were not weakened.
- Assessment publication/getters now use defensive copies; resetting the returned nonce flag no longer replays it. The old scope-generation reuse and current-record-cap test cases also pass.
- No source changes, app wiring, SAP/model calls or deployment occurred during this review.

The uploaded archive contains six files. Its identity and full per-file hashes are recorded in `manifest-verified.json`.

This review does **not** reopen the explicitly deferred integration items: actual tool-outcome reconciliation, real model/checkpoint isolation, authorized page admission, aggregate resource limits, policy provenance, async progress, HIL business eligibility and SAP-driven remaining-list refresh. Those still need staged integration tests later, as the README correctly states.

## Fix status

| Earlier finding | Re-review status |
| --- | --- |
| F1 — fail-open result parsing | Previously tested omissions/types fixed. Missing nested evidence fields still get affirmative defaults; unavailable duplicate sources can still yield a completed verdict. Some malformed enum shapes raise instead of yielding incomplete. |
| F2 — wrong notification identity | Previously reported identity mismatch now correctly yields incomplete. |
| F3 — mutable assessment/nonce state | Previously tested assessment/action reference mutations are fixed. Worklist snapshots remain mutable through their store boundary; see R6. |
| F4 — expiry/publication fencing | Unique generations and page publication checks fix the supplied cases. Rejected publication still mutates session lifecycle, and standalone calls do not fully enforce the fence; see R2. |
| F5 — duplicate run execution | Different run IDs sharing an idempotency key correctly join. Repeated submission of the same run ID bypasses joining; see R3. |
| F6 — cancellation/timeout | The supplied cancelled-item case is fixed and a timeout exists. Cancelling a page still leaves semaphore-waiting rows queued; see R4. |
| F7 — memory cap | Current/index record caps now work for the supplied case. Superseded-record action cleanup remains a lower-priority improvement. |

## Remaining corrections

### R1 — Required nested evidence fields still default to safe values

**Priority: P1.** `assessment_service.py:179,201,204`.

The strict parsers use the following defaults:

- missing `evidence_available` -> `True`;
- missing `candidate_ids` -> `[]`;
- missing `pool_capped` -> `False`.

A payload declaring `execution_completeness="complete"`, a Pass finding without an availability flag, and `duplicate={"coverage":"complete"}` is still accepted as **Approve / High**. This is the remaining part of F1: an absent fact is treated as affirmative evidence rather than as an invalid result contract. It does not depend on adding real SAP telemetry to the foundation.

**Correction:** require these fields explicitly and validate their exact types before a completed record is accepted. Missing required nested fields must yield incomplete/no recommendation/no confidence. Do not silently infer zero candidates or a successful uncapped search from omission.

Two related contract corrections:

1. `coverage="unavailable"` with model-declared completeness `complete` currently becomes **completed / Review Needed / High** (`assessment_service.py:195-211,274-284`). Under the selected required-source-failure contract, unavailable duplicate evidence means incomplete/no verdict/no confidence. Successfully retrieved partial coverage and an observed suspected match are a separate policy case; this finding does not require resolving every partial-coverage policy now.
2. JSON lists/objects supplied for `recommendation`, `confidence` or finding `result` raise `TypeError` at `assessment_service.py:264,267,177`. These values are tested for membership in a frozenset before their string type is checked. This fails closed against approval but does not produce the promised incomplete record. Validate types first and normalize expected contract errors explicitly.

### R2 — Publication fencing is still incomplete outside the tested page path

**Priority: P1.** `assessment_session.py:224-230`; `assessment_service.py:317-333`.

Three deterministic cases remain:

1. **A rejected stale publication changes lifecycle state.** `publish()` calls `_write_bucket()` before comparing the generation. At a scope capacity of one, an old worker's publication returns `False` but recreates its obsolete scope and evicts another user's live scope. It can also extend a newer scope's TTL merely by being rejected.
2. **A standalone lock waiter adopts a new generation.** A queued `assess_one()` captures its generation after acquiring the item lock. If the scope is invalidated during the wait, the old request publishes into the new generation.
3. **Standalone publication rejection is ignored.** `assess_one()` still returns a complete Approve / High record when `publish()` returns `False`. `run_page` now catches this by looking up the canonical result, but a standalone caller receives an unpublished actionable-looking assessment.

**Corrections:**

- For fenced publication, first perform a non-mutating lookup. Reject absent, expired or mismatched incarnations without creating a bucket, touching TTL or evicting another scope.
- Capture the standalone generation before the first lock wait, just as a page carries an admission-time generation. Recheck the fence before assessment/publication as appropriate.
- Treat rejected publication as an explicit expired/invalidated outcome or exception, not as a successfully produced canonical record. Let both page and standalone entry points use that same result contract.

The new monotonic generation counter is useful and should be retained. No durable store is needed for these fixes.

### R3 — Repeating the same run ID executes it twice

**Priority: P1 for the one-assessment/reuse requirement.** `assessment_service.py:359-365`.

The new admission logic joins an existing idempotency key only if `existing.run_id != run.run_id`. Two concurrent calls with the same `PageRun`/run ID and key therefore execute the assessor twice, overwrite the completion event and advance the assessment revision twice.

The bundled regression uses two different run IDs, which now works correctly. The additional positive control confirms that fix.

**Correction:** distinguish first admission/owner from any already-admitted execution, including an identical run ID. Return/join the existing operation without replacing its completion event or rescoring. An explicit reassessment should receive its own intentional operation context.

### R4 — Cancelling a page leaves queued rows nonterminal

**Priority: P2; resolve before enabling the page runner.** `assessment_service.py:378-390,410-416`.

The cancellation handler is inside `async with sem`. A worker cancelled while waiting for the semaphore never reaches that handler. With three rows and concurrency one, cancelling the page produces:

```text
1000: failed
1001: queued
1002: queued
run completion event: set
```

Thus a finished/cancelled run still contains nonterminal rows. This differs from the fixed test where the assessor itself raises cancellation after entering its worker.

**Correction:** include semaphore acquisition in cancellation cleanup or settle all remaining queued/running members during parent-run cancellation. Preserve already completed records, propagate cancellation deliberately, and make the final progress/result truthful.

### R5 — A guarded verdict can contradict its unchanged explanation

**Priority: P2; fix before displaying these records.** `assessment_service.py:272-283`.

For an unsupported Approve, the guard changes the recommendation to Review Needed but retains a rationale such as **“All checks passed; approve this notification.”** This recreates a visible inconsistency within the same record.

**Correction:** write a factual server-side reason explaining the guard's override, preserve the original model suggestion separately if needed, and validate confidence against the resulting decision/rubric. This does not require another routine LLM call. Do not blindly downgrade every case to Low: Review Needed can have High confidence when evidence unambiguously supports that referral.

### R6 — Worklist membership is still mutable through the store

**Priority: P2; fix before binding the current-page UI.** `assessment_session.py:331-342`.

`put_snapshot` keeps the caller's `WorklistSnapshot`, and `get_snapshot` returns that stored object. Appending an ID to the returned `ordered_ids` changes canonical worklist membership. This is separate from the deferred authorization/admission feature: it concerns retaining the stable snapshot already accepted by the store.

**Correction:** copy or deeply freeze worklist snapshots at both boundaries, including nested IDs. The live internal `PageRun` state and synchronization event can remain intentionally mutable; do not blindly deep-copy an active run/event to solve snapshot integrity.

### Lower-priority cleanup

When old superseded assessments leave the by-assessment index, their action contexts are not removed. With record cap two and ten revisions, the store retains ten actions, eight referencing forgotten records (`assessment_session.py:244-267`). Current-revision checks still reject those old actions, so this is cleanup/capacity work, not a demonstrated authorization bypass. Reuse `_forget_actions_for` when removing superseded index victims or define bounded token cleanup.

## Additional verification

Files in `review-checks/` include:

- `verified-suites.json` and suite stdout/stderr: original 12 + reviewer 14 tests pass.
- `models_repro.py`: five schema/explanation test methods; current implementation produces five failing assertions and six enum-parser TypeErrors across subtests.
- `service_repro.py`: five service tests, including one passing positive control and four remaining failures.
- `test_session_followups.py`: three failing expected-behavior tests for side-effect-free rejection and stable snapshots.
- `additional-followups.summary.json` / `.output.txt`: combined results, **13 additional methods**, 12 assertion failures and six product TypeErrors across subtests. One positive-control method passes. These targeted tests are not an overall quality score.
- `session_repro.py` and `.jsonl`: deterministic lifecycle, snapshot and cleanup observations.

All additional checks run locally without SAP, model calls or production code modification. The errors above come from malformed JSON reaching the submitted parser, not missing dependencies in the test harness.

Run the test files with Python 3, placing the six submitted files in `source/` next to `review-checks/`:

```sh
python3 -B review-checks/models_repro.py
python3 -B review-checks/service_repro.py
python3 -B review-checks/test_session_followups.py
```

These are expected-behavior regressions and currently exit nonzero. `session_repro.py` instead prints observations of the existing behavior. Public API changes may require adapting the tests, but keep the stated invariants rather than relaxing them to fit the current behavior.

## Handoff

Keep the successful fixes and the standard-library/session-memory design. Close R1-R4 before live integration; resolve R5 before presenting results and R6 before connecting page snapshots. Then rerun both supplied suites and these focused follow-ups. The staged integration list remains exactly the one explicitly deferred in the package; no new database, multi-agent framework or app-dependency rewrite is requested.
