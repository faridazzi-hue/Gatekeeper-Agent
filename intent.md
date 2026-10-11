# Plant Maintenance Notification Gatekeeper Agent

Plant Maintenance Notification Gatekeeper — AI agent for screening, validating, and routing SAP plant maintenance notifications with human-in-the-loop control.

## Business challenge

Approximately 100 maintenance notifications are created per week in SAP across one or more plants (notification types M1 and M2). A dedicated gatekeeper manually reviews each notification for completeness, field consistency, failure coding accuracy, and duplicate occurrences before approving, reworking, or rejecting it. This process is time-consuming, inconsistently applied, and creates a bottleneck that can delay notification processing beyond the two-day review expectation. The organisation needs an AI agent that reduces gatekeeper manual effort while improving notification quality, duplicate detection, and decision traceability. The plant is provided by the gatekeeper at runtime via the chat interface, making the agent usable across multiple plants without configuration changes.

## Business Goals & Success Criteria

| Metric | Baseline | Target | Timeline | Process / Capability | Source |
|--------|----------|--------|----------|----------------------|--------|
| Gatekeeper manual review time per notification | — | 50% reduction | End of pilot | Notification screening | user |
| Notification completeness rate (all mandatory fields present) | — | 95% | End of pilot | Mandatory field validation | user |
| Duplicate detection accuracy (precision) | — | 90% | End of pilot | Duplicate detection | user |
| Review completion within 2-day SLA | — | 100% within 2 days | End of pilot | Gatekeeper worklist management | user |
| False rejection rate (valid notifications incorrectly rejected) | — | < 2% | End of pilot | Reject recommendation | user |

## Key Milestones

1. **Worklist retrieval** — Agent prompts gatekeeper for the target plant, then retrieves pending OSNO notifications for the specified plant (M1, M2) and presents a prioritized gatekeeper worklist.
2. **Notification validation** — Agent completes all configured validation checks (mandatory fields, description quality, priority vs. ABC indicator, M1/M2 rules, coding, attachments) for a single notification.
3. **Duplicate detection** — Agent queries open notifications, evaluates semantic similarity, and classifies duplicate likelihood with supporting evidence.
4. **Human-in-the-loop confirmation** — Agent presents structured recommendation, gatekeeper selects Accept / Override / Request more info, and agent records the decision.
5. **SAP action execution and audit** — Agent executes the confirmed SAP action via API, verifies the result, records the full audit trail, and prepares the applicable email draft.

## Business Architecture (RBA)

### End-to-End Process

Acquire to Decommission

### Process Hierarchy

```
Acquire to Decommission
└── Operate to Maintain (generic)
    └── Execute asset maintenance (generic)
        └── Perform asset maintenance
    └── Plan asset maintenance (generic)
        └── Define maintenance plans and rules
        └── Plan asset maintenance tasks and resources
└── Plan to Optimize Assets (generic)
    └── Optimize asset maintenance (generic)
        └── Analyze assets and maintenance performance
        └── Define asset maintenance strategies
```

### Summary

Plant maintenance notification screening and gatekeeper review map to the Acquire to Decommission E2E process, specifically the Operate to Maintain phase covering Execute and Plan Asset Maintenance activities. The AI agent introduces intelligent quality control and routing at the point where notifications enter the maintenance execution workflow.

## Fit Gap Analysis

| Requirement (business) | Standard asset(s) found | API ORD ID | MCP Server ORD ID | MCP Server Version | Webhook API ORD ID | Data Product ORD ID | Gap? | Notes / assumptions |
|------------------------|-------------------------|------------|-------------------|--------------------|--------------------|---------------------|------|---------------------|
| Retrieve and update maintenance notifications (approve, reject, rework, status) | SAP S/4HANA — Maintenance Execution (SC5061) | `sap.s4:apiResource:API_MAINTNOTIFICATION:v1` | — | — | — | — | Yes | No MCP server available; API must be wrapped via MCP translation file |
| Retrieve equipment master data (ABC indicator, criticality) | SAP S/4HANA — Maintenance Execution (SC5061) | `sap.s4:apiResource:API_EQUIPMENT:v1` | — | — | — | — | Yes | No MCP server available; API must be wrapped via MCP translation file |
| Retrieve functional location data | SAP S/4HANA — Maintenance Execution (SC5061) | `sap.s4:apiResource:API_FUNCTIONALLOCATION:v1` | — | — | — | — | Yes | No MCP server available; API must be wrapped via MCP translation file |
| AI-driven notification screening and recommendation | No standard SAP product | — | — | — | — | — | Yes | Requires custom AI agent (Python, A2A protocol) |
| Human-in-the-loop confirmation before SAP action | No standard SAP product | — | — | — | — | — | Yes | Implemented as part of agent conversation flow |
| Duplicate detection across open notifications | No standard SAP product | — | — | — | — | — | Yes | Agent performs semantic similarity analysis on retrieved notifications |
| Audit trail for every screened notification | No standard SAP product | — | — | — | — | — | Yes | Agent generates and stores structured audit record per review |

### Key findings

- SAP S/4HANA provides the transactional backbone (maintenance notifications, equipment master, functional locations) via available OData APIs, accessed through BTP destination `S4HANA_QUALITY`.
- No pre-built MCP servers exist for the three required APIs; all three must be wrapped using MCP translation files.
- The intelligent screening, recommendation, human-in-the-loop control, duplicate detection, and audit capabilities are not covered by any standard SAP product and require a custom AI agent.
- The agent architecture must be loosely coupled so that an n8n workflow or other automation layer can invoke it later without modifying core decision logic.
- All five pilot configuration inputs (mandatory fields, valid coding, action-to-status mapping, attachment rules, worklist prioritization) are externalized as agent configuration to support iterative refinement during the pilot.
- The plant is supplied by the gatekeeper at runtime; the agent is not restricted to a single plant, enabling use across multiple plants without code or configuration changes.

## Recommendations

### Plant Maintenance Notification Gatekeeper Agent

#### Executive Summary

Python AI agent wrapping SAP Maintenance Notification and Equipment APIs.

#### Recommended Solution

A pro-code Python AI agent built on the A2A protocol using the Joule Studio runtime. The agent exposes three MCP-wrapped SAP OData APIs (Maintenance Notification, Equipment, Functional Location) as its toolset. It implements all configured validation checks, duplicate detection, worklist prioritization, human-in-the-loop confirmation, SAP action execution, email draft generation, and structured audit recording. The solution is designed so that an n8n orchestration layer can be introduced later to trigger the agent automatically without changing the core decision logic.

#### Problem Statement

Manual notification review creates a bottleneck, inconsistency, and risk of delayed or incorrect routing. The gatekeeper lacks tool support for systematic completeness validation, coding consistency checks, semantic duplicate detection, and traceable decision recording.

#### Affected User Roles

- Plant maintenance gatekeeper (primary user)
- Maintenance notification creator (recipient of rework and rejection emails)
- Plant maintenance supervisor (consumer of audit records and pilot metrics)

#### Important factors

##### Structured validation with evidence

Every check produces a Pass / Warning / Fail result with the specific evidence used, so the gatekeeper can verify the agent's reasoning rather than trusting a black-box recommendation.

##### Human-in-the-loop as a hard control

No SAP action is taken without explicit gatekeeper confirmation. The agent distinguishes clearly between its recommendation and the gatekeeper's decision, and records both.

##### Extensibility for future automation

The agent is invoked manually in the pilot but is designed with a clean, stateless API surface so that an n8n workflow or event-driven trigger can call it later without redesigning the decision logic.

##### Configurable validation rules

Mandatory fields, valid coding lists, action-to-status mappings, and worklist prioritization weights are all supplied as agent configuration rather than hardcoded, enabling rapid adjustment during the pilot.

#### Potential risks

##### Incomplete SAP configuration inputs

If the mandatory field list, valid code groups, or action-to-status mappings are not supplied correctly, the agent will produce low-confidence or incomplete assessments. Mitigation: provide all configuration inputs before pilot go-live.

##### API availability on the on-premises system

The three required APIs must be activated and authorized on the on-premises SAP system. If any API is unavailable, the agent will report the limitation and not fabricate data.

##### Attachment analysis is deferred

Attachment content cannot be analyzed in the initial scope. The agent will flag missing or inaccessible attachments but cannot assess their content.

#### Recommended solution category

AI Agent

#### Intent fit
95%
