# PaperworkPilot AI — Live Demo

## Public application

https://paperwork-pilot-ai.replit.app/

## Fastest reproducible review

1. Open the public application.
2. Keep **Parking permit** selected in the flagship demo card.
3. Click **Run selected demo**.
4. At the saved human checkpoint, inspect the recovered verifier failure, 100% evidence coverage, and deadline uncertainty.
5. Click **Approve and resume agent**.
6. Review the agent run receipt, source-linked requirements, missing values, supporting documents, warnings, and ordered checklist.

## Reviewer-requested proof paths

- **Dependency outage recovery:** select it, run the demo, and inspect the orange **Dependency check** and **Requirement extraction** recovery events. Approve to show a final receipt with 0 model calls.
- **Reject, revise, resume:** select it, run the demo, choose **Request changes**, edit the reviewer note, then choose **Apply revision and resume agent**. The same run continues and the final receipt includes both human checkpoints.

The flagship scenario is fictional and deterministic, so it can be reviewed without an API key or personal paperwork. The separate live-analysis path supports pasted text and uploaded TXT, Markdown, PDF, PNG, JPG, and WEBP files.

![PaperworkPilot demo](assets/PaperworkPilot-Demo.gif)
