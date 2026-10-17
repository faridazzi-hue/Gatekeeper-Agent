# Option 1: full assessment of the current page, shared in every view

Review and revised implementation plan, 17 October 2026.

**Revision 2 — session-only state.** The user clarified that no durable SAP/assessment storage is expected at the BTP agent level. This revision removes the earlier mandatory database/restart-recovery requirement. Throughout this plan, “saved” or “stored assessment” means a typed snapshot held temporarily for the active session, not a durable business record.

## Decision and scope

The proposed plan needs substantive changes before implementation. Renaming a link and asking the model to copy a prior table cannot establish a reliable assessment system. In V2, bulk is deliberately a quick pre-screen and individual review is deeper. Freezing the quick verdict would make the views look consistent while retaining incomplete analysis.

Reuse one full assessment pipeline, keep its evidence and result in temporary session memory, and render that same snapshot in the summary, details and contextual chat. Clicking details must not initiate assessment. Explicit reassessment creates a new revision within the session. Durability and full assessment depth are separate decisions: a complete assessment does not require a new agent database.

The latest user choices govern this plan:

- Use **assets V2.zip only** as the code baseline.
- Show **20 notifications per page**, with scrolling to inspect the rows.
- **Perform AI Assessment evaluates only that current page**, including its rows below the visible scroll area. It does not include other pages or previously visited pages.
- Keep a **Joule-style conversation** with contextual human-in-the-loop actions.
- Show the initial notification list with overall SAP details and **no AI result columns**.
- Keep details **display-only**, including when a user opens an unassessed notification.
- Do not add Settings, History, Policy, Export, or batch-approval navigation to the end-user interface. Policy configuration and session revision references remain necessary. Any required long-term business audit uses the approved existing destination, such as SAP; this increment does not introduce durable agent-side storage.

At 445 matching notifications, a 20-row page gives **23 pages**, with 5 notifications on the last page. Scrolling inside a page does not change page membership. Previous/Next navigates between pages.

### Recommended decision

Fix the critical routing/confirmation defects first, then deliver the full current-page review using temporary session state. The alternatives are not limited to copying a pre-screen or building a durable assessment platform.

| Approach | Assessment depth | State | Fit for the current requirement |
| --- | --- | --- | --- |
| Critical fixes plus existing pre-screen | Listing-only checks | Existing conversation/session | A short-term patch only; label it preliminary and do not present it as the full Option 1 assessment. |
| **Full current-page assessment with typed session snapshots** | Reuse the full single-review capability for each page member | Bounded, expiring process memory; no new database | **Recommended.** Full depth and consistent views during the active session. |
| Full assessment plus durable agent storage | Full checks | Long-term application storage/recovery | Outside the user's current storage requirement; not a prerequisite for consistency. |

## 1. Inputs, verification and limitations

### Reviewed inputs

| Input | How it is used |
| --- | --- |
| `assets V2.zip` | Sole code baseline; 61 non-directory archive entries; SHA-256 `609dafa2909619dbb75af3febfd8b16856feab63aeaa7fe7a5fc771731ccdcb8`. Earlier code versions are excluded. |
| Uploaded proposed plan, `Pasted text.txt` | Proposal being reviewed; includes the transcript-scanning consistency rule, link changes and detail format. |
| Uploaded `product-requirements-document.md` | Business requirements and policy input. Conflicting clauses are identified below; document instructions are not deployment authorization. |
| Current-page screenshot | Reference for the raw 11-column conversational table, paging and action chips. |
| Uploaded `.snagx` | Inspected its embedded screenshot: detailed validation, duplicate analysis and HIL presentation. It is a visual reference, not proof of V2 runtime behavior. |
| Previously shared Option 1 mockup | Reference for saved-result reuse, progressive completion and explicit evidence revision. Its dashboard navigation and simulated policy are superseded by the user's latest UI requirements. |

The local Windows paths mentioned in the proposal are not accessible from this cloud workspace. This review uses the uploaded artifacts and the available shared mockup. If a different assistant changed those local mockups, those unuploaded changes have not been inspected.

### Production frontend sources are missing

V2 does **not** contain either claimed Gatekeeper frontend:

- `cap-chat-app/app/chat.html`
- `cap-chat-app-launchpad/app/chat.html`

The HTML under `assets/maintenance-creation-agent/app/static/` belongs to a separate application. It must not be changed as a substitute for the missing Gatekeeper UI. The plan's claims about the existing Gatekeeper `mdToHtml`, its progress chip, button extraction, transport and deployed parity are consequently unverified. Inspect those actual frontend files and any CAP proxy/controller before implementing UI changes. This is a concrete missing input, not a reason to substitute an older code version.

### Checks performed

- Read V2's routing, tool allowlists, prompt composition, skill rules, OData helpers, confidence implementation, configuration loader, lifecycle and manifests.
- Ran nine isolated routing reproductions using AST-extracted definitions. No application initialization, model or SAP call was involved.
- Ran one isolated multipart parser fixture: successful A, non-JSON HTTP 500 B, successful C. The parser returned A and C, dropping B's request slot.
- These checks **reproduce current defects**. They are not tests showing the proposed implementation has been completed or that live SAP performance has been validated.

## 2. Review findings: what must change

Paths below are relative to `assets/pm-gatekeeper-agent-rpt-toggle/` unless stated otherwise. Line references identify the uploaded V2 source, not the older repository checkout.

| Priority | Finding and V2 evidence | Required change |
| --- | --- | --- |
| Must have | `app/agent.py:162-163` gives bulk fewer validation skills than single review. `app/skills/session-tracking/SKILL.md:238,261-265,308-340` explicitly specifies listing-only pre-screening, forbids full reads and requires later full review. | Replace the pre-screen path with the full shared assessment service. Update conflicting skills and prompts together. |
| Must have | The proposal makes a conversation table authoritative. `app/agent.py:316-320` summarizes history; `:483-495` clears it on context overflow; `:287-298` can use in-memory checkpoints. | Save typed assessments outside conversation text. Never recover decisions by parsing or asking the model to scan a historical table. |
| Must have | The proposal fetches live notification fields while retaining an older recommendation and generating fresh check results. Master/coding checks require other sources: `consistency-validation/SKILL.md:26,32,39,55,69,78`. | Save the evidence and findings during assessment. Details display that snapshot. New live evidence is a separate refresh/reassessment operation. |
| Must have | `app/agent_executor.py:60,93-105` routes review to analysis and “Show details...” currently matches the broad list fallback. `:128-132` still exposes single-assessment tools in review mode. | Introduce a distinct display route, dispatched before list fallback and before model invocation. It has no assessment/write tools. |
| Must have | The proposed eight-digit regex can truncate a longer number and narrows V2's existing six-to-ten-digit compatibility. | Use typed identifiers and action metadata. Validate the entire ID against the actual SAP contract, preserving leading zeroes. Reject invalid input rather than truncate it. |
| Must have | After a target is selected, both “Do not accept approval” and “Can you explain what accept approval means?” classify as confirmed action through `app/agent_executor.py:61,97-103`. | Arbitrary substring matches cannot authorize SAP mutations. Use explicit confirmation tied to a server-issued action context. |
| Must have | `_ACTIVE_TARGET` stores only a last target (`app/agent_executor.py:69-71`); the write context binds only target/action (`app/tools.py:76-80,94-109`). | Bind HIL to actor, notification, assessment/version, intended action and currentness. Old chat buttons cannot use a newer last target. |
| Must have | `app/agent_executor.py:111-112` returns the full toolset in the non-CF path; `:36-41` supplies no-op confirmation setters there. | Enforce display and action restrictions in both CF and Joule execution boundaries. Visual similarity to Joule is separate from runtime choice. |
| Must have | `app/agent.py:193-195` defines a raw 11-column list, but `session-tracking/SKILL.md:18-40` requires an analyzed 10-column list; `:14` carries all seen rows forward. | Use separate raw-list and assessment renderers. Page size 20 is one shared constant; do not accumulate historical pages into the current page. |
| Must have | Screenshot action chips treat equipment IDs as notifications. The proposal only changes text emitted by the generic number-link rule. | Generate notification links from typed Notification cells/IDs. Equipment values must not create notification actions. The actual frontend implementation still needs inspection. |
| Must have | Existing streaming emits tool labels then one final text artifact (`app/agent.py:391-399`; `app/agent_executor.py:272-282`). | Implement actual per-item completion/error data and client updates for progressive results. Keeping the progress chip alone does not deliver this behavior. |
| Must have | `app/tools.py:467-499` refetches and sorts the filtered dataset on every page, silently returns partial results after a later fetch failure and caps ranking at 1,000. | Snapshot/cache the authorized worklist and paginate that stable snapshot. Preserve continuation, partial failure and cap information. |
| Must have | Single and bulk duplicate paths use different candidate windows (`app/tools.py:839-862,914-950`); a 50-row pool can be incomplete. | Share one pool retrieval/classification implementation, with self-exclusion and explicit coverage. A failed or partial pool cannot establish “no duplicates”. |
| Must have | Policy catalogs are placeholders (`app/config/agent_config.yaml:58-82`); loader getters do not establish that assessment code consumes them. | Wire validated, versioned company policy into the service. Missing catalog configuration is not proof that the notification's code is invalid. |
| Required before using `$batch` | `app/s4hana_client.py:188-215` drops malformed/non-JSON parts and ignores embedded HTTP status. `batch_get` returns those compacted results at `:481`. | Repair per-request mapping/status handling before adopting batching. An empty-list fallback cannot catch partial slot loss. |

### Confidence is already High / Medium / Low

V2's `recommendation/SKILL.md:48-78` and `app/tools.py:985-995` already use these three levels. Removing “Unrated” is a mockup alignment, not a newly discovered V2 code change.

Keep four distinct concepts:

1. **Workflow state:** not assessed, queued, running, completed, incomplete or failed.
2. **Evidence state:** retrieved, known empty, unavailable, incomplete coverage or not applicable.
3. **Recommendation:** Approve, Rework, Reject or Review Needed, where supported by policy and sufficient evidence.
4. **Recommendation confidence:** High, Medium or Low for an actual supported assessment result.

A retrieved empty field can make a policy-backed Rework decision highly certain. Failure to retrieve that field is a different condition. Under the PRD's required-query failure rule, stop that item's analysis, mark it incomplete, record the failure and do not invent a final confidence. Low / Review Needed is appropriate for genuine unresolved judgment when the evidence/policy permits that outcome; it is not a generic substitute for every technical failure. Pending rows have no recommendation or confidence.

For duplicate coverage, the default is equally explicit: a failed required search or a truncated pool that cannot establish the required outcome leaves the item incomplete. An observed suspected match can be shown as a finding. A final Review Needed outcome from a successfully retrieved partial pool is allowed only if the approved rubric explicitly treats that evidence as sufficient for manual referral; the coverage remains visibly partial and it can never enable Approve. No-match plus partial coverage never establishes a clean search.

These are qualitative labels, not calibrated probabilities. Independent live LLM runs can differ even with low temperature. Cross-view consistency comes from reusing one saved assessment, not from promising that separate inference runs will always agree.

## 3. Target conversational UI

### A. Initial list: source facts only

The user supplies a plant and filters in chat. The agent returns a conversational card:

```text
Page 1 of 23 · 445 matching notifications · 20 on this page

Notification | Type | Description | Equipment | Priority | ABC | Down |
Reporter | Req. Start | Coding | Planner

[20 source rows; scroll to inspect all rows]

[Previous]  [Next 20]  [Perform AI Assessment — this page (20)]

Chat: Ask a question or choose a notification...
```

- Use the exact 11 overall fields above. No Recommendation, Confidence, Dup? or SAP action-result column before assessment.
- No assessment starts because a list is fetched, scrolled, paged or opened.
- The server's page ID contains all 20 members, independent of DOM visibility, viewport size or browser virtualization.
- Notification IDs are accessible links; equipment values remain source text or explicitly typed equipment links.
- Remove the flood of “Work with notification” chips derived from every eight-digit number. The Notification link is sufficient.
- Keep paging and assessment buttons as explicit conversational actions. “Navigation through notification links only” must not remove paging or HIL controls.
- Use one configured `PAGE_SIZE = 20` for server paging, UI labels, next/previous calculations and page-count tests.
- Provide visible scroll controls and keyboard access for the 20-row table, a pinned header where useful, and horizontal scrolling on narrow displays. Scrolling must not silently append the next page.

### B. User starts assessment of this page

The button sends a typed start request for its **bound** page snapshot. If an old conversation card's page action is clicked, identify that page explicitly; never substitute whichever page a global variable currently holds. The main current-list button always refers to the current displayed page.

Create one assessment message/card with a compact header such as:

```text
Assessing page 1 · 20 notifications
8 completed · 3 running · 8 queued · 1 incomplete
```

Use the familiar result table:

```text
Notification | Description | Equipment | Priority | Dup? |
Recommendation | Confidence | Justification
```

- Completion means the required assessment pipeline has finished and the result has been validated and saved.
- Rows appear/update progressively from saved result events. Queued/running rows show status text and no verdict.
- Incomplete/error rows show the failure and a Retry action; they do not show a fabricated approval or confidence.
- For duplicates, distinguish **suspected**, **none found in a complete search**, and **not established**. An unchecked checkbox must not imply a successful negative search when lookup failed.
- A completed row can be opened while the rest of the page is running.
- Update this card in place. Do not add 20 repeated full chat messages or regenerate the growing table through the model for every result.
- User chat and paging remain usable. A page-1 job does not expand when the user opens page 2.
- Returning to a page can show its saved assessment card and version. It does not rerun the assessment automatically.
- A new button click/request key or an overlapping standalone/page request is not by itself permission to rescore an already current assessment. Reuse its saved result by default; expose **Reassess** explicitly when a new analysis is intended. Coalesce concurrent requests for the same target/evidence/policy to avoid competing evaluations.
- Show a page-level completion notice that distinguishes completed decisions from incomplete/error items.

### C. Notification details are a display

Clicking a completed row posts the conversational intent “Show details for notification ...” with structured IDs. The server loads the exact assessment, without SAP, confidence, duplicate or model calls, and renders:

1. One six-column summary row: **Notification | Description | Priority | Dup? | Recommendation | Confidence**.
2. The saved short rationale. A contextual explanation can be generated separately if the user asks a new question.
3. **Field | Retrieved value | Result | Note** evidence table.
4. Applicable HIL actions and **Show Remaining Notifications** as navigation.

The summary's recommendation and confidence, and every evidence finding, come from the same saved assessment used by the page. Store all applicable checks, including functional location, responsible/reporter validation and M1-specific checks; the sample nine-row evidence table is not a license to omit those checks.

Use Pass / Warning / Fail for completed checks in the visible table. Unperformed/unavailable evidence must be visibly “Not verified” or shown in an incomplete-analysis notice, never rendered as Pass. Internally retain a separate evidence/execution status so the three result labels cannot conceal a failed retrieval. Do not add R-XX rule labels to the normal UI; retain rule identifiers and versions internally for traceability.

Before assessment, clicking a notification displays source details and **Not assessed**. It offers an explicit **Assess this notification** action using the same service. A read-only raw-detail fetch is permissible if the listing lacks needed display fields, but must not evaluate, invent check results or alter saved assessments. Assessed details use the stored snapshot and need no hidden read.

### D. Contextual chat and HIL

- “Why Rework?”, “What is missing?” and “Explain this duplicate” read the selected saved assessment. They do not call the assessment pipeline.
- Put the notification and assessment context in the request, not only in model memory or a last-selected global.
- For Approve: **Accept Approval**, **Override AI Proposal**, **Show Remaining Notifications**.
- For Rework: **Accept Rework**, **Override AI Proposal**, **Show Remaining Notifications**.
- For Reject, if enabled by the approved policy: **Accept Rejection**, **Override AI Proposal**, **Show Remaining Notifications**.
- For Review Needed: **Override AI Proposal** / **Resolve manually**, plus navigation; no ordinary Accept action representing an automatic write.
- Preserve a separate **Request more information** conversational action required by the PRD. It prepares the reason; a SAP information-required mutation still needs explicit confirmation. Navigation is not a replacement for that business capability.
- An override requires a reason and the exact chosen action. A suspected duplicate does not automatically become Reject or Complete.
- After an action, report the verified SAP outcome. Preserve partial success, such as approval succeeded but the audit comment failed.
- No Settings, History, bulk “Review approvals” or Export buttons in this increment. Keep the chat composer and current conversation central.

### E. New evidence and reassessment

Show the saved assessment's time/version in unobtrusive detail metadata. It is a snapshot, not a claim that every field was just retrieved live.

- Opening details preserves the record.
- An explicit Refresh checks current data; when relevant evidence differs, show **Assessment outdated** and block ordinary Accept against it.
- **Reassess this notification/page** creates a new assessment revision using the same full engine, saves the reason and publishes the new record.
- Update the active assessment summary/details together. Preserve older conversation messages as clearly dated/superseded snapshots with inactive old action controls; do not silently rewrite historical recommendations.
- If reassessment fails, retain the prior snapshot as a dated, outdated record and show the new run's incomplete state. Do not replace it with an invented verdict or re-enable its old approval.
- Policy/model/rubric changes that affect evaluation also have versions. Do not replace a verdict under the same assessment ID.

## 4. Backend design and request/result contracts

### One assessment service

Use a shared `assess_one(notification_id, policy_snapshot, evidence_context)` entry point. Both a page job and an explicit standalone assessment call it. Batch is scheduling and shared data retrieval, not a separate set of decision rules.

Suggested boundaries are deliberately small; filenames can be consolidated if the existing app architecture warrants it:

| Module | Responsibility |
| --- | --- |
| `assessment_models.py` | Typed page snapshot, run, evidence, finding, assessment and action-context schemas. |
| `assessment_session.py` | Authorized in-memory snapshots, TTL/capacity cleanup, current revision, run membership, request deduplication and async locks. |
| `assessment_service.py` | Reuse the existing full review capability, capture actual evidence/check coverage, validate the structured result, and publish the immutable session snapshot. Do not rewrite every company rule for this increment. |
| `batch_service.py` or helpers in the service | Fixed current-page run, bounded async workers, isolated item invocations, per-item completion/failure, retry and progress. |
| `assessment_presenter.py` | Raw list, result rows and detail presentation from typed records, with safe text escaping. |
| `action_service.py` or the existing action handlers | Exact action confirmation against a live session snapshot, freshness checks, existing SAP operation sequence, outcomes and approved audit. |

### Temporary session records

**Worklist snapshot:** snapshot ID, verified actor/tenant/backend scope, conversation, plant/filter/sort definition, ordered IDs, source listing time, total/completeness, page size 20 and expiry. The configured plant is not carried into new conversations as an implicit default; records can still retain the plant used for assessment/audit.

**Page/run:** run ID, page snapshot ID/index, captured ordered IDs (maximum 20), policy version, membership hash, initiating actor, idempotency key, created time, item states and progress sequence. The final page can have fewer than 20 members.

**Assessment:** immutable assessment ID/revision, notification ID, run ID where applicable, source/evidence fingerprints and times, policy/rubric/model/prompt versions, field values, applicable checks, findings and source references, duplicate scope/candidates/completeness, rationale, recommendation, confidence and reason, execution completeness and assessment time.

**Action context/outcome:** actor, conversation, notification ID, assessment ID/revision, permitted action, expiry/nonce, override reason when needed, request idempotency key, verified source state, mutation result, comment result, actual returned SAP status and audit reference.

Use a small `SessionAssessmentStore` in process memory, separate from the model's transcript. Key it by verified actor/tenant/backend and conversation, then notification/run/assessment IDs. Hold the actual evidence and structured findings needed for consistent display, with configurable TTL, capacity limits and cleanup. A dictionary alone is not enough: add per-item async locks/single-flight coordination and revision checks so overlapping requests cannot publish an older result over a newer one. There is no database binding, disk-backed cache or durable job queue in this scope.

Expiry/eviction invalidates the session/run generation as well as deleting its records. Cancel its outstanding work where possible and reject late publication from the old generation, so an expired worker cannot recreate actionable results.

Reuse the current full single-notification review as the assessment capability. Its current output is prose/Markdown, so add a validated structured result and capture evidence/check coverage from actual tool execution. A rendered table parsed back from conversation is not that result. Missing required evidence must remain incomplete. This shared wrapper does not require rebuilding every rule as a new framework before the first delivery.

**Parallelism must isolate model state.** V2 keys graph history by user and conversation. Do not invoke 20 reviews concurrently against that same mutable checkpoint thread. Use independent item invocation contexts (for example actor/conversation/run/notification), or a supported stateless assessment invocation, and publish only validated outcomes to the parent conversation. One async process can run these bounded tasks; adding Gunicorn workers is not required to parallelize reads.

**Pilot deployment boundary:** V2's `manifest.yml` specifies one instance and one worker, while its `Procfile` specifies two workers. Verify which launch command is active and align the session-memory pilot to one owning process. Multi-worker/replica deployment requires verified session routing or another explicitly designed transient-state mechanism; it cannot silently assume that process-local dictionaries are shared. Do not add a durable database to address that question. Horizontal scaling/restart recovery is a separate requirement if later needed.

**Loss/expiry behavior:** while the owning session lives, summary and details use the same immutable record. After TTL, eviction, restart, deployment or loss of that owning state, return “Assessment no longer available in this session” and disable its actions. The user can explicitly assess again. A browser may still show an old conversational snapshot, but that display is not authority to write. Do not silently reconstruct a result from chat, rescore it, or replay a write. Reconnect succeeds only while the session state still exists. Browser refresh alone may preserve the server session if its identity/state survives; no new persistence guarantee is implied.

**Check existing retention paths too.** V2 prefers an SDK cloud checkpointer when importable and falls back to `MemorySaver`; the reviewed code does not establish the cloud backend's durability. Explicitly configure/verify a non-durable checkpoint mode when the user's constraint applies to conversational SAP data as well. Give the typed store its own cleanup policy rather than assuming the LLM checkpointer's TTL also covers it. Avoid logging raw evidence or writing snapshots to local files. PRD line 488 continues to govern retained business audit and creator PII. Reuse the approved audit destination/SAP action trail where required; that is separate from transient display state and does not authorize a new BTP data store.

Delete/expire per-item child checkpoint histories and temporary raw tool evidence as well as the typed records. The word `MemorySaver` does not by itself give an expiry guarantee; a task's cleanup must cover its retained messages/caches.

**Action retries have a boundary:** in-session idempotency prevents ordinary double clicks, but it does not provide exactly-once writes across process loss. Use SAP-supported request identity/concurrency controls and verified action outcomes where available. After an uncertain write or expired session, inspect/verify the actual backend outcome and require a fresh explicit action context; never automatically replay the mutation. The design must not claim durable deduplication from an in-memory map.

These boundaries can be implemented as a session-store helper, shared full-review wrapper and presenter, plus changes to the existing executor/client. The module table describes responsibilities, not a requirement to build six separate subsystems.

### Action contract

Define actions such as `list_page`, `start_page_assessment`, `show_details`, `assess_notification`, `explain_assessment`, `refresh_evidence`, `reassess` and `confirm_action`.

Illustrative UI metadata for starting a run:

```json
{
  "operation": "start_page_assessment",
  "worklistSnapshotId": "wl-...",
  "pageId": "page-...",
  "idempotencyKey": "click-..."
}
```

The server resolves the authorized membership from `pageId`; it must not trust an arbitrary client list to expand scope. Metadata is routing data, not authorization. Verify the authenticated actor and access to the snapshot/notifications. Avoid an `anonymous` fallback for privileged actions.

For details, send `notificationId`, `assessmentId` and context identifiers. For an old/superseded record, either display its explicitly marked historical snapshot or direct the user to the current result, with its action availability enforced server-side.

### Pipeline sequence for each notification

1. Load the pinned, validated company policy and resolve the authorized target.
2. Retrieve notification evidence required by its rules: code keys and labels, short and long text, equipment/function location references, status/order, relevant dates and responsible/reporter data; include M1 fields only where applicable.
3. Resolve equipment/master and required catalog/reference evidence. Deduplicate shared references within the page job.
4. Get the complete or explicitly bounded duplicate pool for the same technical object across the required open scope. **Candidate scope is not restricted to the current page**: a notification on another page can still be its duplicate.
5. Stop that item if a required source is unavailable, in accordance with the PRD; save failure evidence and allow the remaining items to continue.
6. Run objective checks in code. Use structured semantic findings for description/coding/occurrence interpretation where needed; never let tool-text instructions alter routing or permission.
7. Derive recommendation/confidence using one shared rubric. Validate that Approve is impossible when a required check is incomplete or duplicate coverage is insufficient.
8. Validate and atomically publish the entire immutable assessment into the scoped session store. Only then emit its completion event and enable its eligible HIL actions.

Do not assume every check has a real data source merely because a skill describes it. Verify the catalog, user/work-centre and functional-location resolvers. A populated user name is not proof of a valid SAP user. Missing resolver capabilities must be implemented or identified as unverified evidence; no invented Pass result.

Verify duplicate candidate evidence as well: the PRD requests status, reporter and relevant long-text extracts, while the current duplicate projection contains short text/coding and a few reference fields. Enrich plausible candidates using real sources as required by the occurrence/similarity policy, with bounded shared reads. Do not invent candidate details or classify a separate occurrence solely from a repeated short description. Candidate filtering is a separate policy from worklist eligibility: V2 filters duplicate candidates with `MaintenanceOrder eq ''` (`tools.py:844,919`), whereas the PRD asks for open OSNO/NOPR candidates. Resolve whether open notifications already linked to orders must also be compared; do not silently inherit the worklist exclusion or limit candidates to the current plant without approved policy.

### Transport and progress

V2 pins `a2a-sdk[all]==0.3.22`. Validate its structured data/artifact update APIs and the actual CAP consumer before selecting exact SDK calls. Preserve a short text summary for text-only consumers, but use structured page/result/progress payloads for the UI.

Each event needs run/page identity, monotonically ordered sequence or equivalent revision, notification ID, item state and assessment ID for completed records. The client upserts by these keys and ignores duplicate/late stale events. Reconnect can recover only while the owning process/session still holds the run; otherwise show an expired/unavailable session. Do not mark a job complete merely because one model text response finished. Keep the evidence temporarily in the scoped session record and fetch that record for details.

### Confirmation and source currentness

Retain the existing tool-layer target/action guard and extend it. A server-issued confirmation context must reference the exact assessment and actor. Validate recommendation/action compatibility, completeness, unresolved conditions, expiry, idempotency and relevant source currentness immediately before a write.

For a Low-confidence outcome or its manual override, require and record the additional explicit uncertainty acknowledgment specified by PRD line 434. An ordinary Accept label, a quoted phrase or a model-inferred intention is not that acknowledgment.

Relevant dependencies include notification state, equipment master, company policy/catalogs and duplicate scope, not just the notification's ETag. Use available source versions or fingerprints and policy-defined freshness windows; re-query required dynamic evidence when needed for action validation. External changes are not detected instantly without reads or events. If a relevant change is detected, mark the result outdated and request explicit reassessment. This validation is not a new hidden assessment.

Where SAP supports optimistic concurrency, pass the expected assessed version to the mutation. V2's `function_import` currently fetches a fresh ETag at write time (`app/s4hana_client.py:511-535`); that alone does not prove the human-approved evidence was unchanged. Map actual backend concurrency support carefully. Related-source checks cannot make multiple SAP services one atomic transaction, so document the supported freshness boundary honestly.

Use idempotent action records and recovery within the live session for repeated clicks/transport retries. Do not retry an uncertain write blindly; process loss requires backend outcome reconciliation. Approval and its follow-up comment retain their required order; if the comment fails after approval succeeds, report and retry the missing step without approving twice. Required retained audit uses the approved destination even though there is no History tab.

## 5. Performance changes, in order

### Must have for this design

1. **Remove work from details:** a completed detail view uses stored evidence and deterministic rendering. No model or SAP round trip is needed for that ordinary interaction.
2. **Fix list pagination:** retrieve/rank a stable authorized worklist once per explicit listing refresh, page it at 20, and expose cap/partial-failure conditions. Add a stable ID tie-breaker to priority/date sorting. Prefer supported server-side ordering if it exactly matches the business requirement; do not silently change rank semantics.
3. **Keep lightweight listing and full assessment projections separate:** retain only the 11-field display dependencies plus keys/filter/sort/version fields in list fetches. The assessment projection must include every policy-required input. Reducing fields must not make the full assessment incomplete.
4. **Reuse evidence by unique object within the page:** shared equipment, catalog/reference and duplicate pools are fetched once where scope/versions match. V2 already groups duplicate queries and uses `asyncio.gather` with a semaphore of 5 (`tools.py:900-934`); preserve this existing benefit.
5. **Bound concurrency by resource:** start with small configurable SAP and model limits, for example SAP 5 and semantic calls 2, then tune with measurements. Bound aggregate work across simultaneous jobs and replicas, not just one semaphore in one request. Avoid nested fan-out multiplying these limits.
6. **Pool HTTP connections:** lifecycle-manage the async client instead of constructing `httpx.AsyncClient` for each GET (`s4hana_client.py:303`). Keep destination/credential scope and expiry correct; close clients at shutdown. Add bounded retry/backoff for safe transient reads, respecting `Retry-After` where supplied.
7. **Avoid routine extra confidence completions:** apply the same shared evidence/rubric logic in both paths. The existing confidence tool is optional for genuine ambiguity; do not turn it into a mandatory extra call for each of 20 rows. Store the result once. Any semantic optimization must preserve rule behavior and be tested in both modes.
8. **Keep large evidence out of conversational history:** the duplicate tool currently returns unbounded JSON proportional to object pools. Store the evidence and send compact summaries/references. Do not evaluate all 20 through a single ever-growing transcript or spawn 20 autonomous chat agents.

For the 445-record example, the existing implementation needs roughly five 100-row fetches to rank the whole set for each requested UI page. With 20-row pages, browsing all 23 pages could therefore produce about **115 listing GETs**, plus count/retries, if this refetch design is retained. A stable snapshot can reuse that initial retrieval. These counts are deductions from the code under stated assumptions, not SAP latency benchmarks.

### Optional after correctness: OData `$batch`

V2's duplicate bulk implementation is already bounded asynchronous fan-out; it does not call `batch_get`. Use `$batch` only after fixing the response contract and testing the deployed SAP service.

- Batch by supported service root; notification, equipment and functional-location service roots are distinct.
- Retain exactly one success/error result per submitted request. Parse MIME boundaries and embedded HTTP status; use explicit request/correlation mapping and Content-ID only as supported/verified by that server.
- Normalize OData envelopes consistently with normal `get`.
- Handle partial failures by retrying only failed reads within the same bounded budget. A missing response is an error for that request, not an empty candidate list.
- Follow continuations or record incomplete coverage. A response cap is not proof that no more candidates exist.
- Measure the right chunk size rather than hardcoding a universal batch maximum.
- A batch reduces transport round trips; it does not guarantee server-side parallel execution or fewer SAP database queries.

### Performance validation

Use the same representative 20-item datasets and policy before/after changes. Record time to first complete result, page completion time, per-item p50/p95, SAP request count, model calls/tokens, retries, incomplete/error rate, detail latency and memory use. Include concurrent sessions. The PRD's <=30-second single-analysis target is a target to measure, not an already verified V2 capability. Do not promise a percentage speedup or calibrated confidence without evidence.

## 6. PRD reconciliation and company policy

| Topic | Required resolution |
| --- | --- |
| Page scope and size | Add the user's latest requirement explicitly: current page only, 20 rows, fixed membership on start. The PRD's 25 sequential reviews/session is a capacity target, not a page limit or instruction to assess all viewed rows. |
| Initial ordering | PRD line 173 includes duplicate/low-confidence ranking before those values exist. Use source-field business ordering initially; do not perform hidden AI assessment to rank the plain list. Any assessment-driven sorting applies only after results and must not change a running job's membership. |
| Count/list scope | Apply the same authorized plant, APRQ/no-order and supported-type constraints to count and list. V2 hardcodes the APRQ/no-order filters; configured notification types must be enforced rather than merely described in prompts. Keep duplicate-candidate eligibility separately defined. |
| Full validation | Retain REQ-02's real source checks and long text, not the mockup's seven illustrative rules. The shared engine applies them equally to page and standalone assessment. |
| Required-source failures | PRD lines 189,342,440 require stopping analysis on a required query failure. Apply this per notification, save incomplete evidence and continue the other page members. Do not issue a supported final verdict by pretending the missing source passed. |
| Field presence | PRD lines 187,458 say not to recheck presence; V2 and other PRD clauses require some missing data to trigger correction, including M1 duration. The business owner must reconcile mandatory-input applicability. Implement checks based on approved policy, rather than making every blank field a new mandatory rule or trusting every creation channel's UI. |
| Confidence | Preserve H/M/L qualitative recommendation certainty. Replace the blanket “missing data reduces confidence” statement with the distinction between observed absence and unavailable evidence. |
| Manual-review vocabulary | PRD line 249 lists three outcomes but line 254 permits manual review. Normalize **Review Needed** as the non-write/manual-review outcome. Do not force Approve/Rework/Reject for unresolved evidence. |
| Duplicate action | PRD line 234 says confirmed duplicates can be completed or returned using Y01; line 405 describes Reject for duplicates; line 585 says RejectMaintWorkRequest is unused. The V2 recommendation rules already route suspected duplicates to Review Needed. Keep that no-write default. Confirm the exact manual duplicate disposition before implementing any accept/override mapping. |
| SAP status map | V2 YAML says Rework -> NOPO; V2 tool doc and PRD line 585 say Y02 -> AIRQ/OSNO. Consolidate one backend-verified configured map. Display actual API status, not an assumed status from the requested action. Do not blindly wire stale YAML into execution. |
| HIL choices | PRD line 265 includes Request more information; the submitted plan substitutes Show Remaining. Keep information request as a business action and remaining/page controls as navigation. All SAP writes still require precise confirmation. |
| Policy configuration | Stable check types belong in code; applicability, allowed catalogs, plant/type dependencies, materiality, approved action mappings and rubric versions are controlled inputs. Replace TODO catalogs and validate policy before enabling approval. Reload policy deliberately; pin each assessment's policy version. No Settings tab is required. |
| Audit vs History UI | REQ-08 lines 311-313 requires earlier assessments, evidence and failures to remain traceable. Satisfy required long-term traceability only through the approved existing audit/SAP destination; omit History navigation and new durable agent storage. Temporary memory alone does not satisfy historical retrieval. If the approved destination cannot retain the required assessment evidence, record an explicit PRD exception/change rather than silently introducing an agent database or claiming the requirement is met. |
| Retained evidence | The user excludes durable storage at agent BTP level. Keep assessment/run evidence only in temporary scoped memory. PRD line 488 still governs any approved external business audit and creator PII; do not add an agent database or new long-term log/snapshot destination. |
| Model/runtime descriptions | PRD line 355 names GPT-4o/MCP while V2 uses GPT-5 and a CF direct-OData path as well as Joule support. Plan against V2; no model migration is necessary for consistency. |
| Email | Preserve applicable unsent draft behavior. New Outlook integration is outside this increment; nothing is sent merely because the plan or PRD mentions email. |

The PRD's valid-company-policy inputs and action-map contradictions are implementation dependencies. The UI can be built against fixtures while those values are finalized, but it must not claim verified company compliance from the current placeholders.

## 7. File-by-file implementation impact

| File or area | Concrete impact |
| --- | --- |
| `app/agent_executor.py` | Add deterministic display/start/explain/reassess/action routes; resolve explicit page/assessment contexts; reject invalid whole IDs; remove substring-based write authorization; dispatch saved details without model invocation; stream structured run results; enforce runtime-equivalent permissions. |
| `app/agent.py` | Separate conversation explanations from assessment execution; remove transcript authority and quick/full split; align table contracts and page size; provide selected immutable assessment context for follow-ups; preserve summarization without depending on it for decisions. |
| `app/tools.py` | Extract reusable read/check capabilities from nested tool closures as needed; use full evidence projections; unify duplicate pool logic; return typed errors/completeness; retain write guard and extend its validated context; preserve SAP action ordering. |
| `app/s4hana_client.py` | Add lifecycle-managed connection pooling, read retry policy and version handling. Repair `$batch` before it is used. Preserve destinations, proxy/auth, CSRF and actual backend ETag semantics. |
| `app/config_loader.py` / `app/config/agent_config.yaml` | Validate real catalogs/plant dependencies and the approved mapping; expose immutable version/hash snapshot; handle reload/invalid configuration explicitly; connect policy to assessment. |
| `app/skills/session-tracking/SKILL.md` | Remove pre-screen-only decision rules, all-seen-page accumulation, conflicting table shapes and mandatory later full review. Define raw 20-row pages, full-page assessment and saved-detail behavior. |
| `app/skills/consistency-validation/SKILL.md` | Preserve real evidence checks; align with executable check registry and policy/source completeness; display stored findings in detail mode rather than run them again. |
| `app/skills/duplicate-detection/SKILL.md` | Align coverage, no-label/unavailable handling and suspected-duplicate manual review with shared engine and approved policy. |
| `app/skills/recommendation/SKILL.md` | Use the one rubric and outcome vocabulary; separate execution states from confidence; preserve evidence-backed reasoning and HIL. |
| `app/skills/sap-action-mapping/SKILL.md` | Reconcile the verified action map and version-bound confirmation, including explicit manual duplicate disposition. |
| `app/main.py` | Wire the scoped transient assessment store and authenticated actor boundary; start/close pooled clients; expire results/jobs on process loss. Keep typed results separate from conversational text/checkpoints. |
| `app/audit_writer.py` | Append assessment/action version references, failures and partial success to approved storage; no visible History screen needed. |
| Proposed session/service/presenter helpers | Add the smallest shared boundaries and schemas described above, consolidating files where useful; reuse the full-review capability and avoid a database or a separate rules-engine rewrite. |
| Actual Gatekeeper chat frontend(s), currently absent | Implement 20-row scrollable raw list, typed links/actions, result-card updates, saved detail display, chat context, HIL state and reconnection. If two deployed variants genuinely exist, share/test renderer behavior in both. Inspect the CAP proxy path as well. |
| Tests and test fixtures | Add focused routing, evidence/decision, session expiry, parallel isolation, transport, UI and HIL tests below. V2 does not include a complete test suite in the archive. |
| Deployment configuration | Align the single owning process/session routing and measured async concurrency settings; no new persistent-store binding. Verify checkpoint/logging behavior and proxy/stream timeouts. Deployment and BTP credentials remain a separate operational step. |

Do not modify the Maintenance Creation Agent or the older checkout's agent implementation to approximate missing V2 sources. The archive is the baseline; the repository branch is only distributing this plan and the visual reference.

## 8. Implementation sequence and acceptance

### Delivery 1: fix critical dispatch and establish contracts

- Fix arbitrary-text confirmation dispatch and add a genuine display-only route immediately. If a full session result is not yet available, show raw details/unavailable assessment; do not fall back to review or reconstruct a verdict from a pre-screen table.
- Obtain the actual Gatekeeper frontend and CAP request/streaming handler sources.
- Freeze the 20-row current-page contract, typed IDs and result schemas.
- Reconcile the PRD policy/action-map contradictions and identify real evidence resolvers.
- Add small failing regression tests for the routing, page membership, same-record display and confirmation defects.

**Exit:** code paths, frontend sources and policy assumptions are explicit; the missing inputs are not represented as already implemented.

### Delivery 2: shared full assessment and transient session results

- Add evidence/policy snapshots and a typed transient session store. Wrap the existing full single-review capability with the shared `assess_one` entry point.
- Reuse that service for explicit standalone assessment.
- Keep complete findings/rationale/result together in memory; retain incomplete item states for the active session. Do not add durable agent storage.
- Reconcile all prompts/skills with the executable pipeline.

**Exit:** a full assessment can be retrieved by ID throughout the active owning session, independently of conversation summarization. TTL, restart or eviction yields an explicit expired/unavailable result with actions disabled; no automatic reassessment.

### Delivery 3: bounded current-page jobs and progressive transport

- Capture the 20 or fewer IDs from the selected page, with an idempotent run.
- Add shared retrieval and bounded async workers; keep per-item completions/failures in session memory. Isolate parallel model/checkpoint contexts per notification.
- Implement structured progress, client upserts, reconnect recovery within the live session and explicit expiry otherwise.
- Fix snapshot pagination and connection lifecycle before claiming an improvement.

**Exit:** all page members are accounted for; navigation/scrolling cannot add members; one timeout does not discard the other results.

### Delivery 4: conversational UI and display-only details

- Render the plain list, scope-specific assessment button, progress/results card and saved detail response.
- Use typed notification links; remove equipment-as-notification chips.
- Keep composer/contextual explanations usable while work runs.
- Remove dashboard navigation/actions excluded by the user.

**Exit:** the current-page 20-row workflow works through chat; details and explanations never silently rescore.

### Delivery 5: HIL and revision/currentness integration

- Bind confirmations to saved assessments and verified actor/action context.
- Add stale-result handling, explicit reassessment and versioned updates.
- Preserve correct SAP sequence, outcome verification, in-session idempotent recovery, override reasons and approved audit; reconcile uncertain outcomes after session/process loss.

**Exit:** no stale/old-button/negated-message action can mutate the wrong notification or accept a superseded assessment.

### Delivery 6: validation, measured tuning and pilot readiness

- Run the meaningful tests below against fixtures and then an authorized QA backend.
- Have domain experts review representative Approve, Rework, duplicate/new-occurrence, ambiguous and failed-evidence cases. The PRD's pilot quality acceptance remains required; view consistency alone does not establish that the decisions are correct.
- Measure per-item/page/detail performance, error handling and aggregate SAP/model load.
- Adopt `$batch` only after its mapping tests and deployment capability check pass.
- Review the code diff and actual test evidence against this plan before deployment.

### Acceptance matrix

| ID | Check | Required outcome |
| --- | --- | --- |
| UI-01 | Initial list |20 source rows (or fewer on last page), the 11 agreed columns, no AI result columns and no hidden evaluation. |
| UI-02 |445 records |23 accessible pages; last page 5 rows; correct total/completeness, no duplicated carried-forward rows. |
| UI-03 | Scroll |All 20 page members are assessable even when only a subset is visible. Scroll controls do not load another page into an active scope. |
| UI-04 | Typed links |Only notification identifiers open notification details. Eight-digit equipment numbers never become notification action chips. |
| UI-05 | Joule layout |Conversation/composer, cards, paging and contextual HIL; no Settings/History/Export/batch-approval navigation. Keyboard/focus/mobile scrolling work. |
| SCOPE-01 | Page1 job, navigate page2 |Job evaluates the captured page1 IDs only; page2 requires its own explicit assessment. |
| SCOPE-02 | Old page message action |Request is bound to its explicit page/context or is rejected as expired; never substituted with a global current page. |
| CONS-01 | Summary vs details |Exact same assessment ID/revision, recommendation, confidence, findings and evidence snapshot. |
| CONS-02 | Open completed details repeatedly |Zero SAP reads, duplicate/confidence calls, assessment calls or model calls. |
| CONS-03 | Open unassessed row |Raw details/Not assessed; no analysis until a distinct explicit action. |
| CONS-04 | Ask why |Read-only explanation of the selected saved record; no state/score mutation. |
| CONS-05 | Independent entry points |Batch and standalone use the same rule engine with equal deterministic fixtures/semantic outputs. Do not require independent stochastic model calls to be byte-identical. |
| CONS-06 | Long chat and process/session loss |Summarization does not change the typed snapshot. Restart, TTL, eviction or missing owning state returns expired/unavailable, disables HIL, and requires explicit assessment; never reconstruct from chat. |
| EVID-01 | Required SAP source fails |Affected item incomplete, failure evidence recorded, no invented Pass/approval/confidence; other page items continue. |
| EVID-02 | Empty field vs unavailable field |Different evidence states; outcome follows approved policy. No blanket conversion of all blanks to Low. |
| EVID-03 | Policy/catalog unresolved |No false code-invalid finding or false company-compliant approval. |
| DUP-01 | Own ID only, >50 candidates, continuation |Self is excluded; full coverage or explicit incomplete state; no false clean duplicate result. |
| DUP-02 | Duplicate outside current page |It is considered in the same-object open candidate scope. Page scope limits assessment targets, not duplicate evidence. |
| DUP-03 | Missing technical object/malformed pool/error |Explicit unknown/unavailable evidence; never a verified “no duplicates”. |
| BATCH-01 | HTTP batch A200/B500/C200 |All three request slots retain correct identity/status, including failed B; C cannot be assigned to B. Required only if batching is adopted. |
| RUN-01 | Duplicate click/retry/reconnect while session lives |One idempotent run for that request; no duplicate current result or replayed UI row. After process loss, show expiry and never replay a write automatically. |
| RUN-01b | New request key or overlapping single/page request |Reuse a valid current assessment or join its in-flight work; new inference requires explicit reassessment. A late older worker/event cannot replace or display over a newer current revision. |
| RUN-02 | Mixed successes/timeouts |Completed records remain available within the live session; retry only unresolved items; progress counts are truthful. A restarted process does not claim to recover lost jobs. |
| RUN-03 | Concurrent sessions/items |SAP/model limits and actor isolation hold; parallel notifications use isolated model/checkpoint contexts. Enforce one owning process or verified session routing; do not promise cross-replica recovery. |
| REV-01 | Relevant evidence/policy changes |Old result marked outdated; ordinary Accept blocked; explicit reassessment makes a new version and updates active views. |
| HIL-01 | Negation/quoted/explanatory Accept |Never authorizes a write. Ordinary chat has no mutation authority. |
| HIL-02 | Old target/button/version/wrong user |Server rejects invalid action context; never falls back to last-selected target. |
| HIL-03 | Approve succeeds, comment fails or outcome is uncertain |Shows known partial success; retry only the missing safe step. Timeout/process loss requires backend outcome reconciliation, not blind mutation replay or a claimed exactly-once guarantee. |
| HIL-04 | CF and Joule paths |Equivalent display/confirmation restrictions verified at execution boundaries. |
| HIL-05 | Low-confidence decision/override |Requires the additional recorded uncertainty acknowledgment; ordinary navigation or generic Accept text cannot satisfy it. |
| DATA-01 | Session state/checkpoints/cache/audit |No durable assessment/SAP data at agent BTP level; verify the selected checkpointer and logs as well as the new session store. Only approved business audit is retained in its authorized destination. |
| SESSION-01 | TTL/capacity/isolation |Expire and evict records/checkpoint histories with actions disabled; reject late results from expired run generations. Verified users/conversations cannot read each other's records. Model summarization and 20 concurrent item tasks cannot overwrite another item's typed state. |
| QUALITY-01 | Representative expert-reviewed cases |Full checks and decision/rationale quality meet the agreed pilot acceptance set; include true duplicates, separate occurrences, ambiguity and unavailable evidence. |
| PERF-01 | Representative 20-row pages |Measured first result, total, p50/p95, detail latency, calls/tokens, retries and memory; no unsupported speedup claims. |

### Nice to have after the above

- Safe `$batch` transport once repaired and measured; small semantic micro-batches only if evaluation quality and ID mapping remain sound.
- A compact explanation of which evidence changed between revisions, while keeping the main chat uncluttered.
- Offline evaluation of recommendation agreement, duplicate precision/recall and confidence error rates against expert-labeled examples. This can improve confidence reliability, but it must not be presented as existing calibration.
- Additional virtualization for unusually wide/large cards, if 20-row scrolling and ordinary pagination are insufficient in real usage.

No multi-agent scoring layer, new model migration, durable agent database, Outlook integration, Settings tab or visible History page is necessary to implement this consistency increment.

## 9. Handoff instruction for the coding assistant

Implement this design against assets V2 and the actual Gatekeeper frontend, not the older GitHub agent checkout. First map the exact existing entry points and resolve the missing frontend/policy inputs. Reuse the full review through a shared entry point and a typed temporary session snapshot, then add the fixed 20-row current-page runner, display route and chat/HIL integration. Do not introduce durable agent-side storage; expire the session safely when its state is lost. Keep model/SAP calls out of completed detail rendering. Return a file-by-file diff and meaningful test results for review. Treat this document as a reviewed proposal, not evidence that changes are already implemented, performance is proven or deployment is authorized.
