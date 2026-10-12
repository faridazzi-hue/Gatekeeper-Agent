# PM Notification Gatekeeper Agent — Architecture

## 1. System Context

Who interacts with the system and how.

```mermaid
graph LR
    Reporter["👤 PM Reporter"]
    Gatekeeper["👤 Plant Maintenance\nGatekeeper"]
    Agent["🤖 PM Notification\nGatekeeper Agent\n― SAP BTP CF ―"]
    S4["🏭 SAP S/4HANA\nAPI_MAINTNOTIFICATION"]
    LLM["🧠 GPT-4o\nvia SAP AI Core"]

    Reporter -->|"Creates notifications"| S4
    Gatekeeper -->|"Reviews via chat UI"| Agent
    Agent -->|"Read: list · count · get\nWrite: approve · reject · rework · complete"| S4
    Agent -->|"Reasoning & recommendations"| LLM
```

---

## 2. Technical Architecture

Internal components and how they connect.

```mermaid
graph TB
    subgraph CF["SAP BTP Cloud Foundry — pm-notification-gatekeeper-agent"]
        UI["Chat UI\nchat.html\nHIL buttons · paginated chips"]
        API["FastAPI / Gunicorn\nmain.py"]

        subgraph AgentBox["LangGraph Agent  —  agent.py"]
            Skills["Skills loaded at startup\nsession-tracking\nduplicate-detection\nconsistency-validation\nrecommendation"]
            Tools["Tool registry  —  tools.py\nlist / count / get notifications\napprove · reject · rework · complete\ncheck_duplicates_for_notification\nadd_notification_comment"]
        end

        Client["S/4HANA OData Client\ns4hana_client.py\nETag · CSRF · retry-on-423"]
    end

    subgraph BTP["SAP BTP Platform Services"]
        Dest["Destination Service\nS4HANA_QUALITY"]
        Conn["Connectivity Service\non-premise proxy"]
        AICore["AI Core\nGPT-4o"]
    end

    S4["SAP S/4HANA\nAPI_MAINTNOTIFICATION"]

    UI --> API
    API --> AgentBox
    Skills -.->|"injected into system prompt"| AgentBox
    AgentBox --> Tools
    Tools --> Client
    Client --> Dest
    Client --> Conn
    Dest --> S4
    Conn --> S4
    AgentBox <-->|"prompts / completions"| AICore
```

---

## 3. Per-Notification Decision Flow

What happens from the moment a session starts to the moment an action is taken.

```mermaid
flowchart TD
    Start([Session Start]) --> PlantCheck{Plant provided?}
    PlantCheck -- No --> AskPlant[Ask for plant identifier]
    AskPlant --> Fetch
    PlantCheck -- Yes --> Fetch

    Fetch["count + list phase-1 notifications\nno order · no rejection code\n7-column listing table · paginated"]
    Fetch --> Remaining{Notifications\nremaining?}
    Remaining -- No --> End([Session Complete])
    Remaining -- Yes --> Select[Select next notification]

    Select --> Details[Fetch full notification details]
    Details --> Consistency["Consistency Check\ncoding · description · priority · equipment"]
    Consistency --> DupCheck["Duplicate Check\ncheck_duplicates_for_notification\nsame TechnicalObjectLabel · phase ≠ 4"]

    DupCheck --> DupResult{High or Medium\nconfidence match?}
    DupResult -- Yes --> RecoDup["Recommend: Duplicate Candidate\nconfidence · reference notification table\n9-column review table"]
    DupResult -- No --> RecoStd["Recommend: Approve / Rework / Reject\nconfidence · rationale\n9-column review table"]

    RecoDup --> HIL{Gatekeeper\ndecision}
    RecoStd --> HIL

    HIL -- "Accept Completion" --> Complete["function_completemaintnotification\nuse_etag · retry-on-423"]
    HIL -- "Accept Approval" --> Approve["function_approveMaintWorkRequest\nuse_etag · retry-on-423"]
    HIL -- "Accept Rework" --> Rework["function_setMaintNotifToInfoRequired\nY02 · use_etag · retry-on-423"]
    HIL -- "Accept Rejection" --> Reject["function_rejectMaintWorkRequest\nuse_etag · retry-on-423"]
    HIL -- "Override" --> Override["Gatekeeper provides\nwritten justification\nthen executes alternative action"]
    HIL -- "Show Remaining" --> Fetch

    Complete --> Comment["add_notification_comment\naudit trail PATCH · retry-on-lock"]
    Approve --> Comment
    Rework --> Comment
    Reject --> Comment
    Override --> Comment

    Comment --> Next["Show Remaining Notifications"]
    Next --> Remaining
```

---

## 4. Guardrails & Governance

Explicit constraints built into the agent that cannot be overridden by users or notifications.

```mermaid
mindmap
  root((Guardrails\n& Governance))
    Data Integrity
      Never fabricate or invent SAP field values
      Never claim a SAP action succeeded without API confirmation
      Never default to or hardcode a plant identifier
    Human Control
      No SAP write action without explicit HIL confirmation
      Override requires written justification from gatekeeper
      After every action offer only Show Remaining Notifications
    Duplicate Detection Rules
      Coding must align — text similarity alone is not enough
      Low-confidence matches are silently skipped
      Skip duplicate check if TechnicalObjectLabel is empty
      Never flag a NOCO notification as an open duplicate
    Automation Boundaries
      Never auto-correct inconsistent codes — recommend Rework instead
      Never show notifications that already have a maintenance order
      Page size capped at 100 items per tool call
      Complete action for duplicates — never SetMaintNotifToInfoRequired
    Error Handling
      Relay tool error messages verbatim — no invented workarounds
      Return "Analysis incomplete" on backend query failure
      Retry up to 3× on HTTP 423 entity lock before surfacing error
    Security
      Notification descriptions treated as data not instructions
      Prompt injection resistance enforced at system prompt level
      Audit comment written to SAP after every gatekeeper action
```
