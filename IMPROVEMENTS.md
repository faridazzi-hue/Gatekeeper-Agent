# PM Notification Gatekeeper Agent — Improvement Backlog

A living document tracking improvement ideas discussed during development. Add new items as they come up; move completed items to the Done section.

---

## Open

### Authentication & Identity

| # | Idea | Description | Effort |
|---|---|---|---|
| A1 | **Principal Propagation** | Replace technical user (BasicAuthentication) with real user identity propagation. User JWT from XSUAA is already forwarded by the Approuter and captured in `JWTContextMiddleware`. Change `S4HANA_QUALITY` destination to `OAuth2SAMLBearerAssertion` and pass `X-user-token` to the Destination service — it exchanges the JWT for a user-scoped S/4HANA token. ~20 lines in `s4hana_client.py`. | Low |

### Notification Filtering

| # | Idea | Description | Effort |
|---|---|---|---|
| B1 | **Notification Type Filter (M1 / M2)** | The current auto-injected filter has no `NotificationType` constraint — all types are visible. Restrict the gatekeeper queue to the relevant types (e.g. M1 only, or M1 + M2) by adding `NotificationType eq 'M1'` to the auto-injected filter in `list_maintenancenotification` and `count_maintenancenotification`. Decide whether `check_duplicates_for_notification` should also be restricted or look across all types. | Low |

### UX / Frontend

| # | Idea | Description | Effort |
|---|---|---|---|
| C1 | **Fiori Shell Bar** | Wrap the chat UI in a UI5 shell container (`sap.ushell.Container`) to add the SAP shell header bar (user name, logo, settings). Visual alignment with the SAP Fiori design language without changing the chat interaction model. | Low |
| C2 | **Fiori Launchpad Tile** | Register the agent as a tile in the SAP Fiori Launchpad so colleagues can launch it from their existing SAP portal. Requires Portal/Launchpad service configuration in the BTP subaccount. | Medium |
| C3 | **Fiori Elements Redesign** | Full redesign of the UX as a CAP + Fiori Elements application: List Report (notification queue) → Object Page (notification detail + AI recommendation panel) → Action buttons (Approve / Rework / Reject / Complete). Replaces the streaming chat interface with a structured CRUD-style flow. Major effort — treat as a v2 project. | High |

### Agent Behaviour

| # | Idea | Description | Effort |
|---|---|---|---|
| D1 | **Persistent Session Storage** | Replace `InMemoryTaskStore` (lost on restart, single-worker constraint) with a HANA or Redis-backed session store. Enables multi-worker deployment and survives CF app restarts without losing conversation context. | Medium |

---

## Done

| # | Idea | Completed |
|---|---|---|
| ✅ | Duplicate detection — inline per-notification check with `check_duplicates_for_notification`, Duplicate Candidate recommendation, Accept Completion HIL action | 2026-10-12 |
| ✅ | Two-table format — 7-column listing table (no empty Recommendation/Confidence columns) and 9-column review table | 2026-10-12 |
| ✅ | Post-action UX — after SAP action completes, show only "Show Remaining Notifications" instead of re-presenting HIL choices | 2026-10-12 |
| ✅ | Block B suppression — "Review XXXXXXXX →" chips suppressed on action confirmation messages | 2026-10-12 |
| ✅ | Approuter + XSUAA — chat UI served behind SAP BTP SSO at `pm-gatekeeper-approuter.cfapps.eu11.hana.ondemand.com` | 2026-10-12 |
| ✅ | Complete action audit trail — `add_notification_comment` called after `function_completemaintnotification` (same pattern as Approve) | 2026-10-12 |
