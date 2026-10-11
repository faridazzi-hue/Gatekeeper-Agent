---
name: recommendation
description: Rules for generating Approve, Rework, or Reject recommendations with confidence levels for SAP maintenance notifications.
---

# Recommendation and Confidence Rules

## Recommendation Outcomes

Recommend exactly one of: **Approve**, **Rework**, or **Reject**.

### APPROVE

Recommend Approve when ALL of the following are true:
- All consistency checks pass or produce only minor warnings with no material issue.
- M1 malfunction and breakdown fields are logically consistent (when applicable).
- Priority is credible relative to the equipment ABC indicator and the described circumstances.
- The description provides sufficient information for the gatekeeper to understand the issue.
- No High duplicate likelihood candidate is identified for the same equipment and same issue.
- No other material issue requires correction.

### REWORK

Recommend Rework when the notification may be valid but requires correction, clarification, or additional information. Examples include:
- One or more consistency checks produce a Fail result.
- One or more material Warnings that cannot be resolved without creator input.
- Description is vague, urgency-only without factual justification, or technically insufficient.
- Coding is semantically inconsistent with the description.
- Priority is unjustified for the equipment's ABC indicator.
- M1 malfunction or breakdown fields are incomplete or logically inconsistent.
- The agent cannot reach a reliable conclusion because essential evidence is missing.

### REJECT

Recommend Reject primarily when a High duplicate likelihood is confirmed:
- Another notification is still open (OSNO or NOPR).
- It concerns the same equipment.
- It describes the same issue.
- The new notification does not represent a clearly separate occurrence.

Do not recommend Reject based on text similarity alone.

### MANUAL REVIEW REQUIRED

Return "Manual review required" when:
- Evidence is insufficient to support any of the three outcomes.
- Backend data is unavailable or contradictory.
- The agent cannot determine confidence reliably.

---

## Confidence Levels

Assign exactly one confidence level: **High**, **Medium**, or **Low**. Never use a numeric percentage.

### HIGH
- All required evidence is available.
- Validation checks are conclusive.
- The recommendation is strongly supported.

### MEDIUM
- Most evidence is available.
- One or more uncertainties require gatekeeper attention.
- The recommendation is supported but not conclusive.

### LOW
- Essential information is missing.
- Evidence conflicts or is contradictory.
- Backend queries failed or returned incomplete data.
- Attachment content is required but cannot be assessed.
- The outcome cannot be determined reliably.

**All Low-confidence cases must be explicitly highlighted for closer manual review. Low confidence must never result in an autonomous SAP action.**

---

## Response Structure

Structure every recommendation response to clearly separate:

1. **Notification overview** — notification number, plant, type, equipment, status, creator, date, priority, ABC indicator.
2. **Recommended outcome** — Approve / Rework / Reject / Manual review required, with concise rationale.
3. **Overall confidence** — High / Medium / Low, with reason.
4. **Validation results** — one section per check (scope, consistency fields, description quality, priority vs. ABC, M1/M2 checks, coding, attachments).
5. **Duplicate analysis** — likelihood, candidates, evidence for and against.
6. **Required corrections** — exact corrections needed, missing information, recommended priority if applicable.
7. **Human-in-the-loop choices** — Accept / Override / Request more information.
8. **Proposed SAP action** — action name, expected outcome, proposed status, explicit statement that the action has NOT yet been executed.
9. **Proposed communication** — email draft for Rework or Reject (not for Approve unless requested).

---

## Evidence Rules

- Every conclusion must cite the specific SAP field value, check rule, and result.
- Distinguish facts (data retrieved from SAP) from interpretation (agent analysis).
- Do not hide contradictory evidence behind an overall score.
- Do not assert that a described symptom is physically impossible solely from general knowledge — flag it as potentially inconsistent and request gatekeeper review.
