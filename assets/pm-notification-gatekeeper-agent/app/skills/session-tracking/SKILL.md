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

| Notification | Description | Priority | Recommendation | Action | SAP Status |
|---|---|---|---|---|---|
| 10000526 | Mechanical Inspection for Pump | High | Approve | ✅ Approved | APOK NOPR |
| 10000522 | Electrical fault in panel | Medium | — | ⏳ Pending | OSNO |

## Column Rules

- **Notification**: 8-digit notification number
- **Description**: `NotificationText` short description (truncate to ~40 chars if needed)
- **Priority**: `MaintPriorityDesc` or the priority code
- **Recommendation**: Approve / Rework / Reject / — (if not yet reviewed)
- **Action**: one of the emoji values below
- **SAP Status**: `ConcatenatedActiveSystStsName` from the last known fetch; leave blank if unknown

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
