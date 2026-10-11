---
name: session-tracking
description: Rules for maintaining and displaying a session progress table after every agent response, tracking notifications reviewed and actions taken.
---

# MANDATORY: Session Progress Table

## Three rules — follow all of them

**Rule 1 — Table-first listing.** When you retrieve or list notifications, present them DIRECTLY in the session progress table. Do NOT use bullet points, numbered lists, or any other format for notification listings. The table IS the listing.

**Rule 2 — Always end with the table.** End every response with the full, up-to-date session progress table (all notifications seen so far). The only exception: no notifications have been encountered yet this session.

**Rule 3 — Carry forward.** Include the complete table in every response; update only the rows that changed.

## Table Format

The table ALWAYS has EXACTLY these 6 columns — never add, remove, or rename any column:

| Notification | Description | Priority | Recommendation | Action | SAP Status |
|---|---|---|---|---|---|
| 10000526 | Mechanical Inspection for Pump | High | Approve | ✅ Approved | APOK NOPR |
| 10000522 | Electrical fault in panel | — | — | ⏳ Pending | OSNO |

## Column Rules

- **Notification**: 8-digit notification number — always present
- **Description**: `NotificationText` short description (truncate to ~40 chars if needed); use `—` if empty
- **Priority**: `MaintPriorityDesc` if available, else the priority code; use `—` if not set
- **Recommendation**: Approve / Rework / Reject / `—` (if not yet reviewed)
- **Action**: one of the emoji values below — always present, default `⏳ Pending`
- **SAP Status**: `ConcatenatedActiveSystStsName` from the last known fetch; use `—` if unknown

**NEVER add extra columns** (no Technical Object, no Plant, no Type, no Equipment, no dates).
**NEVER remove columns** even if a value is unknown — use `—` as a placeholder.

## Action Emoji Values

| Emoji | Meaning | Triggered by |
|---|---|---|
| ⏳ Pending | No action taken yet | Default for all new entries |
| ✅ Approved | ApproveMaintWorkRequest succeeded | Gatekeeper accepted Approve recommendation |
| ❌ Rejected | RejectMaintWorkRequest succeeded | Gatekeeper accepted Reject recommendation |
| ℹ️ Info Required | SetMaintNotifToInfoRequired succeeded | Gatekeeper requested more information |
| 🔄 In Process | SetMaintNotifToInProcess succeeded | Gatekeeper placed notification in process |
| ✔️ Completed | CompleteMaintNotification succeeded | Gatekeeper completed the notification |
| ⚠️ Error | SAP action failed | API returned an error |

## Update Rules

1. Add a row the first time a notification is fetched or listed in this session.
2. Update the Recommendation column as soon as analysis is complete.
3. Update the Action and SAP Status columns only after a SAP write action is confirmed and its API response received — never infer the result.

## After the Table

Always add one line immediately after the table:

**Proposed next action:** <one concise suggestion for what the gatekeeper should do next>

---

## APPROVE ACTION — exact two-step sequence

When the gatekeeper confirms approval of a notification, execute these two steps IN ORDER. Do not skip or reorder them.

**Step 1 — Call `function_approvemaintworkrequest`**
- Input: `MaintenanceNotification` (the notification number, e.g. `10000522`)
- On success (200 OK): the response contains the full notification entity including:
  - `ConcatenatedActiveSystStsName` → new SAP status for the session table (e.g. `APOK NOPR`)
  - `APOK` = Approval: OK, `NOPR` = Notification in process
  - `EAMProcessSubPhaseCodeDesc` → confirms the new phase (e.g. `Accepted (Request)`)
- If error: stop immediately, report the error verbatim, do NOT proceed to Step 2.

**Step 2 — Call `add_notification_comment`**
- Input:
  - `MaintenanceNotification`: same notification number
  - `Action`: `"Approved"`
  - `Comment`: your full recommendation reasoning, priority assessment, and any gatekeeper notes
- On success: the SAP notification long text is permanently updated with an audit trail entry.
- If error: report it, but still update the session table (the status change in Step 1 already succeeded).

**After both steps:**
- Update session table: Action = ✅ Approved, SAP Status = value from Step 1 response (e.g. `APOK NOPR`)
- Report success confirming both: SAP status changed and comment logged.

**Rule 4 — Always log after every action.** After EVERY status action (approve, reject, complete, set to info required, set to in process), MUST call `add_notification_comment` to log the gatekeeper decision. This is mandatory — never skip it.
