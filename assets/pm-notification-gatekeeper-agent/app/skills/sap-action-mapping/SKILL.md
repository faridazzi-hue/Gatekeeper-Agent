---
name: sap-action-mapping
description: Mapping of gatekeeper decisions to SAP Maintenance Notification API actions and expected status transitions. Covers action selection, result verification, and human-in-the-loop gate rules.
---

# SAP Action Mapping

## Action-to-Status Mapping

Load the action-to-status mapping from `app/config/agent_config.yaml`. Do not hardcode mappings.

Default pilot mapping (may be overridden by configuration):

| Gatekeeper Decision | SAP API Action | Expected Resulting Status |
|--------------------|---------------|--------------------------|
| Approve | `ApproveMaintWorkRequest` | NOPR (notification in process) |
| Reject (duplicate) | `RejectMaintWorkRequest` | NOCO (notification completed — rejection closes the notification) |
| Rework / Info required | `SetMaintNotifToInfoRequired` | NOPO (notification postponed) |
| Place in process | `SetMaintNotifToInProcess` | NOPR |
| Complete | `CompleteMaintNotification` | NOCO |

## Execution Rules

1. **Load mapping from configuration** — never hardcode action-to-status mappings in agent logic.
2. **Gate**: No action may be executed until the gatekeeper selects Accept, Override, or Request more information.
3. **Execute the action** using the corresponding Maintenance Notification MCP tool.
4. **Verify the result** — after executing the action, re-read the notification status from SAP via the Maintenance Notification MCP. Never infer the resulting status from the action name alone.
5. **Report the actual verified status** to the gatekeeper.
6. **On failure** — if the API action fails, report the error verbatim and record the failure in the audit entry. Do not claim the status changed.

## Human-in-the-Loop Gate

After presenting every recommendation, wait for the gatekeeper to select one of:

1. **Accept agent recommendation** — execute the proposed SAP action.
2. **Override agent recommendation** — require a mandatory written justification before proceeding. Do not execute any action if justification is absent or empty. Record the original recommendation, the gatekeeper's selected outcome, and the justification in the audit entry.
3. **Request more information** — identify the exact missing or unclear information. Apply `SetMaintNotifToInfoRequired` after gatekeeper confirmation. Present the information-required email draft.

## Low-Confidence Guardrail

If overall confidence is **Low**, the gatekeeper must explicitly acknowledge the low confidence before any SAP write action is executed — even on the Accept path. Present the low confidence prominently and require explicit confirmation.

## Post-Action Steps

After the SAP action is confirmed and executed:

1. Report the actual resulting status (from SAP, not inferred).
2. Write the full audit record.
3. Generate the applicable email draft (Rework or Reject only) — present for gatekeeper review, never send automatically.
