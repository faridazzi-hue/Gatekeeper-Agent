# PM Notification Gatekeeper Agent — Roadmap

## Overview

This document tracks the current live capabilities of the PM Notification Gatekeeper Agent and the planned improvements approved for implementation. It is maintained alongside [ARCHITECTURE.md](ARCHITECTURE.md).

---

## Current Live Features

The following capabilities are deployed and running on SAP BTP Cloud Foundry.

| Feature | Description |
|---|---|
| Notification listing | Lists phase-1 notifications (no order, no rejection) with count and pagination |
| Per-notification review | Fetches full notification details and runs consistency validation |
| Duplicate detection | Automatically checks for other open non-completed notifications on the same technical object during every review |
| Recommendations | Approve / Rework / Reject / Duplicate Candidate — each with confidence (High / Medium / Low) and rationale |
| Human-in-the-loop | No SAP write action executes without explicit gatekeeper confirmation |
| SAP actions | Approve, Rework (SetMaintNotifToInfoRequired), Reject (RejectMaintWorkRequest), Complete/Duplicate (CompleteMaintNotification) |
| Audit trail | Structured gatekeeper comment written to SAP long text after every action |
| Retry on lock | All function imports retry up to 3× on HTTP 423 (entity locked) |
| Session tracking | Tracks how many notifications have been reviewed and actioned in the current session |
| 7-column listing table | Notification · Description · Equipment · Priority · ABC · Coding · Phase |
| 9-column review table | + Recommendation · Confidence · Action |

---

## Planned Improvements

### 1. M1-Specific Field Validation

**Business need:** M1 is a malfunction report and requires specific fields that M2 (general maintenance request) does not. Currently both types are treated equally.

**What it adds:**
- For M1 notifications only: validate malfunction start date/time (mandatory), malfunction end date/time (must be ≥ start if present), breakdown indicator (mandatory Y/N), and breakdown duration (mandatory when breakdown = Y, must be consistent with start/end difference).
- Logical consistency checks: end not before start, ongoing malfunction not shown as ended.
- Result per field: Pass / Warning / Fail with explanation.
- A Fail on any M1 field pushes the recommendation toward Rework.
- M2 notifications skip the entire M1 section.

---

### 2. Email Draft Generation

**Business need:** For Rework and Reject outcomes, the gatekeeper needs to notify the notification creator. Currently no draft is produced.

**What it adds:**
- After a Rework recommendation: a ready-to-copy email listing all required corrections, missing fields, and inconsistencies found.
- After a Reject/Duplicate recommendation: a ready-to-copy email citing the reference notification number, its description, and the evidence for the duplicate classification.
- Both emails follow the agreed template (Dear Team · notification details · corrections or duplicate evidence · Kind regards).
- The draft appears before the HIL choices so the gatekeeper can review it as part of the decision.
- The draft is never sent automatically — it is always copy-paste by the gatekeeper.
- Only verified SAP data is used in the email body — no invented values.

---

### 3. Post-Action Status Verification

**Business need:** Currently the agent reports the outcome of the SAP API call but does not confirm the resulting notification status in SAP. The requirements state the agent must verify the actual backend result.

**What it adds:**
- After every successful SAP write (Approve / Rework / Reject / Complete), the agent re-reads the notification from SAP.
- Reports the confirmed resulting status (e.g. "SAP confirmed new status: NOPR — In Process").
- If the status did not change as expected, the discrepancy is reported clearly and the agent does not claim success.

---

### 4. Urgency Language Detection

**Business need:** Descriptions containing words like ASAP, urgent, immediately, critical, or emergency without factual justification inflate the perceived priority and make the gatekeeper's assessment harder.

**What it adds:**
- Detects urgency words in notification short text and long text.
- If urgency language is present but priority is Medium or Low: flags as Inconsistency — urgency language conflicts with stated priority.
- If urgency language is present and priority is already High or Very High: verifies that the description contains factual technical evidence (measurements, observed symptoms, operational impact). If not: flags as Warning — urgency claim not supported by factual evidence.
- Never changes the priority automatically — recommends Rework and states the specific finding.

---

### 5. Planner Group Validation

**Business need:** A notification without an assigned Planner Group cannot be routed to the correct maintenance team for execution. This is a mandatory field before a notification can proceed.

**What it adds:**
- Checks whether `MaintenancePlannerGroup` is assigned and non-empty.
- If missing: flags as a Rework reason — "Planner Group not assigned. A responsible planner group must be set before the notification can proceed."

---

### 6. Stronger Semantic Relevance Check

**Business need:** Generic descriptions like "equipment stopped" or "machine making noise" pass basic completeness checks but are not useful because they could describe any piece of equipment. The agent should verify that the description is specific to the actual equipment in the notification.

**What it adds:**
- Extends the existing description-quality check with a stricter test: would this description make sense specifically for THIS piece of equipment and not for a completely different machine?
- A description that could apply to any equipment is flagged as Rework with a specific finding: "Description is too generic — add the observed symptom, affected component, and operational impact specific to [equipment description]."
- A concise but equipment-specific description is sufficient — the check does not require excessive detail.

---

## Out of Scope for the Initial Pilot

The following items were explicitly excluded from the initial pilot scope in the requirements document.

- Autonomous approval, rework, rejection, or completion without gatekeeper confirmation
- Automatic email sending
- Attachment content analysis
- Comparison of original vs resubmitted versions of a notification
- Escalation when a creator does not rework a notification
- Multilingual user experience beyond English
- Event-driven triggering via n8n or similar
- Creation or modification of maintenance orders, work orders, or task lists
- Fabrication or supplementation of missing SAP values
