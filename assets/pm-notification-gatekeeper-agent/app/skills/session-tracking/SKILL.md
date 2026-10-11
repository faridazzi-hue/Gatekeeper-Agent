---
name: session-tracking
description: Rules for maintaining and displaying a session progress table after every agent response, tracking notifications reviewed and actions taken.
---

# MANDATORY: Session Progress Table

**You MUST end EVERY response with the session progress table below — no exceptions.**
This rule applies whether you are listing, reviewing, approving, rejecting, or answering a general question about notifications. The only exception is when no notifications have been encountered yet in this session (e.g. the user has not yet provided a plant, or the first message is a general question with no notification context).

## Table Format

Use this exact markdown format:

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
4. Carry the full table forward every turn, updating only the changed rows.

## Proposed Next Action

After the table, always add one line:

**Proposed next action:** \<one concise suggestion for what the gatekeeper should do next, e.g. "Review notification 10000522 (Medium priority, outstanding)"\>
