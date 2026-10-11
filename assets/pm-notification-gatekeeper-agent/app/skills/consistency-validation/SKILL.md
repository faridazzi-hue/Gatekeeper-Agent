---
name: consistency-validation
description: Step-by-step consistency validation rules for SAP maintenance notifications (M1 and M2). Covers all key fields, cross-field logic, and M1-specific malfunction rules.
---

# Consistency Validation Rules

Field presence is enforced by the SAP UI. This skill checks only consistency, correctness, and semantic quality of the values that are present.

## Output Format

For each check, return a structured result with:
- **Field**: field name
- **Retrieved value**: exact value from SAP (or "not retrieved" if the query failed)
- **Rule applied**: brief statement of the rule
- **Result**: Pass | Warning | Fail
- **Explanation**: reason for any non-Pass result

---

## Checks for All Notification Types (M1 and M2)

### Equipment
- Verify the equipment number is resolvable in the SAP equipment master via the Equipment MCP tool.
- Verify the equipment belongs to the plant specified by the gatekeeper in the current session.
- Retrieve the ABC indicator for use in the priority cross-check below.
- **Fail** if the equipment is not resolvable or does not belong to the session plant.

### Functional Location
- Retrieve the functional location assigned to the equipment from the Equipment MCP.
- Compare it to the functional location recorded on the notification.
- **Fail** if they do not match.
- **Warning** if the functional location on the notification is a valid parent or child of the equipment's assigned location but not an exact match — note the discrepancy.

### Code Group
- Check the code group value against the configured valid code-group list loaded from `app/config/agent_config.yaml`.
- Verify the code group is compatible with the notification type (M1 or M2) and the session plant.
- **Fail** if the code group is not in the configured list.
- **Warning** if the code group exists but is flagged as unusual for the notification type or plant.

### Coding
- Verify the code belongs to the specified code group.
- Assess semantic consistency between the code description and the notification short text and long text.
- **Fail** if the code does not belong to the code group.
- **Warning** if the code is technically valid but semantically inconsistent with the description.

### Description (Short Text and Long Text)
- Assess whether the combined short text and long text provide sufficient information for the gatekeeper to understand:
  - What was observed
  - The affected equipment or technical object
  - The symptom and relevant location
  - The current operational impact
- **Warning** if the description is vague or technically insufficient.
- **Warning** if urgency terms are used (ASAP, Urgent, Immediately, Critical, Very high priority) without factual justification in the structured fields or long text.
- Do not require measurements or troubleshooting details when not realistically available.

### Priority
- Retrieve the equipment ABC indicator from the Equipment MCP.
- Check the selected priority against the ABC indicator:
  - ABC A: Very High, High, Medium acceptable.
  - ABC B: High, Medium, Low acceptable.
  - ABC C: Very High or High requires factual justification in the description.
- **Warning** if priority is Very High or High for ABC-C equipment without factual justification.
- Note the inconsistency, identify the evidence, and recommend a more suitable priority if determinable — do not change the priority.

### Person Responsible
- Verify the person responsible is a valid user or work centre reference in SAP using the Maintenance Notification MCP.
- **Warning** if the reference cannot be resolved.

### Reported By
- Verify the reported-by user is a valid user in SAP.
- **Warning** if the reference cannot be resolved.

---

## Checks for M1 Notifications Only

Apply these checks only when the notification type is M1. Do not apply them to M2.

### Malfunction Start Date and Time
- Verify the date-time is valid and not in the future.
- **Fail** if the start date is in the future.

### Malfunction End Date and Time
- Apply only when the malfunction end date is populated (i.e., the malfunction has ended).
- Verify the end date-time is after the start date-time.
- **Fail** if end is before or equal to start.
- **Warning** if the description indicates the malfunction is ongoing but an end date is populated.

### Breakdown Indicator
- Check logical consistency with the malfunction context and the description.
- **Warning** if the breakdown indicator is Yes but the description does not mention any breakdown or stoppage.
- **Warning** if the description clearly describes a breakdown but the indicator is No.

### Breakdown Duration
- Apply only when the breakdown indicator is Yes.
- Check the stated duration for logical consistency with the interval between malfunction start and end.
- **Fail** if breakdown indicator is Yes and no duration is provided.
- **Warning** if the duration is significantly inconsistent with the start-to-end interval.

---

## Cross-Field Consistency Rules

- Equipment and functional location must be mutually consistent (see checks above).
- Priority vs. ABC indicator: Very High or High on ABC-C without justification → Warning.
- Coding vs. description: semantically inconsistent → Warning.
- M1: breakdown indicator Yes without a duration → Fail.
- M1: malfunction end before start → Fail.
- M1: malfunction ongoing (no end date) but end date populated → Warning.
