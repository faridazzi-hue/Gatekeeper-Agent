---
name: duplicate-detection
description: Rules for detecting duplicate SAP maintenance notifications. Covers query scope, comparison dimensions, classification levels, evidence presentation, and new-occurrence detection.
---

# Duplicate Detection Rules

## Query Scope

- Query open notifications for the same equipment using the Maintenance Notification MCP.
- Include notifications with status **OSNO** (outstanding) and **NOPR** (in process/released).
- **Exclude** notifications with status **NOCO** (completed) — they must never be treated as open duplicates.
- **Exclude** notifications that already have a maintenance order assigned — these are outside gatekeeper scope. Add `MaintenanceOrder eq ''` to the $filter when querying duplicate candidates.
- Limit results to a maximum of 100 per query.

## Comparison Dimensions

For each candidate notification, compare using all available dimensions:

| Dimension | Comparison approach |
|-----------|-------------------|
| Equipment number | Exact match required |
| Functional location | Same or hierarchically related |
| Short text | Semantic similarity — account for synonyms, abbreviations, plant terminology |
| Long text | Semantic similarity — extract key symptoms, locations, and failure descriptions |
| Code group | Same code group indicates related failure category |
| Coding | Same or semantically equivalent code |
| Failure / damage information | Matching failure mode or damage description |
| Creation date | Proximity — notifications created very close together are more likely duplicates |
| Current status | Open notifications (OSNO, NOPR) only |

## Classification Levels

Classify each candidate as one of:

- **High duplicate likelihood** — same equipment, same symptom/failure mode, same or very similar coding, no evidence of a new occurrence.
- **Medium duplicate likelihood** — same equipment, similar description, minor differences that could indicate either the same or a new occurrence.
- **Low duplicate likelihood** — same equipment, different symptom or coding, weak textual overlap.
- **Not a duplicate** — different equipment, clearly different issue, or evidence of a distinct new occurrence.

## Evidence Presentation

For every candidate classified as High or Medium, present:

- Notification number
- Status
- Creation date
- Reporter / creator
- Equipment
- Short description (exact text)
- Relevant long-text extract or summary
- Code group and coding
- Similarity level (High / Medium / Low / Not a duplicate)
- Specific explanation of the matching evidence

More than one suspected duplicate may be presented.

## New-Occurrence Detection

A repeated failure on the same equipment is **not** automatically a duplicate if:

- Timestamps indicate a clearly different event (e.g., the previous notification was created months ago and the description references a new malfunction date).
- The description explicitly references a new event, new breakdown, or new symptoms.
- The failure context (e.g., after maintenance, after a repair, after a planned shutdown) indicates a separate occurrence.

If the evidence indicates a clearly new occurrence, classify as **Not a duplicate** even if the equipment and code match.

If the evidence is ambiguous (same equipment, same code, similar timeframe), classify as **Medium duplicate likelihood** and flag for gatekeeper review.

## Rules

- **Never recommend Reject based on text similarity alone.** Equipment match, failure mode, and description semantics must all be considered.
- **Never fabricate a duplicate candidate.** Only present candidates returned by the SAP backend query.
- **Keep the duplicate assessment separate from consistency validation results** in the response.
- If the backend query fails, report the failure and do not proceed with duplicate assessment — record the failure in the audit entry.
