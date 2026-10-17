# Gatekeeper assessment UI prototype

The latest [V2 implementation plan](OPTION1-V2-IMPLEMENTATION-PLAN.md) specifies **20 notifications on the current page**, full assessment with saved display-only details, and a Joule-style conversation without Settings/History tabs. It includes code findings, file-by-file impact and acceptance checks. The older eight-record prototype below remains a workflow reference; its navigation and simulated policy are not the production requirements.

Open `Gatekeeper-options.html` in a web browser. It is a standalone offline mockup with embedded styles, scripts and simulated data; no installation is required.

## Selected direction: Option 1 — Complete batch

Choose **Complete batch**, then **Evaluate all 8**. Results appear progressively. Click a notification number to inspect the same saved result as the table.

Use **Reset demo** to start again. Choose either other card to compare workflows.

## Demonstrate consistent results

1. Evaluate the batch and open notification **10002195**.
2. Observe the saved **Approve / High** assessment.
3. Click **Simulate change** to remove the planner assignment in a new evidence snapshot. Approval becomes unavailable because the saved result is outdated.
4. Click **Re-evaluate changes** to create revision 2, **Rework / High**. Both views use the new saved assessment.

This is a UI reference using illustrative data and policy rules. It has no live SAP integration or live chat. It does not contain a production code impact analysis or implement the production assessment pipeline. Confidence labels and timings are illustrative.

Download [gatekeeper-mockup.zip](gatekeeper-mockup.zip?raw=true), extract it, and open `gatekeeper-mockup/Gatekeeper-options.html` in a browser. The ZIP includes editable source files, screenshots and browser check results.
