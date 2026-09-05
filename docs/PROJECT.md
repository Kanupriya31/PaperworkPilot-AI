# Week 3 Project Documentation

## Project overview

PaperworkPilot helps ordinary people move from confusing paperwork to a verified, human-approved submission plan. The problem is not simply understanding prose: users must locate fields scattered across sections, identify supporting documents, reconcile requirements with information they already know, notice contradictions, and decide what to verify before submitting.

The system uses a LangGraph state machine rather than a single model call. It performs safety intake, dependency routing, structured or fallback extraction, exact-quote verification, profile matching, uncertainty review, resumable human interrupts, and final plan assembly. The browser shows both the user-facing guidance and an inspectable receipt of the agent's steps.

## Agent framework

| Field | Decision |
|---|---|
| Agent goal | Turn a form and optional profile into an evidence-backed submission plan. |
| Surface | Responsive web application designed for Replit. |
| Ordered steps | Safety intake → dependency check → extraction/fallback → evidence verification → profile matching → uncertainty review → human checkpoint → revision or plan assembly. |
| Read tools | File reader/OCR, structured requirement extractor, evidence matcher, profile matcher, ambiguity detector. |
| Write tools | Final checklist generation only; no external send, submit, payment, or record update. |
| Memory | Thread-scoped LangGraph checkpoints for pause/resume. State expires on restart or explicit run deletion. |
| Never do | Never invent personal facts, make eligibility/legal conclusions, follow document prompt injection, or submit anything automatically. |
| Human in the loop | Every run pauses before final plan creation; approve, edit, request changes and resume, or stop. |
| Failure behavior | Transient verification failures retry; dependency/model failures use a conservative fallback; unreadable files stop with actionable guidance. |
| Success measure | Complete the verified demo plan in under five minutes with 100% fixture evidence coverage and zero invented missing values. |

## Dataset and fixtures

The primary demonstration uses a fictional Riverglen residential parking-permit form and fictional applicant Maya Johnson. It contains seven required field groups, three document requirements, a missing deadline year, online/in-person submission choices, and an originals warning. Four additional deterministic modes cover school consent, utility hardship, extraction-dependency outage, and reject/revise/resume behavior without depending on a live model call.

The evaluation set contains 12 original, synthetic form fragments. It covers ordinary forms, prompt injection, social-security information, passport information, bank information, developer/system-message impersonation, signatures, attachments, and legitimate non-sensitive cases. Synthetic fixtures avoid redistributing sensitive or copyrighted documents and make expected routing deterministic.

## Design requirements

The implementation was evaluated against these product and verification requirements:

1. Provide a complete full-stack experience for pasted or uploaded forms and optional profile details.
2. Use a stateful LangGraph workflow with tool calls, failure recovery, and human checkpoints.
3. Require an exact source quote for every extracted field, supporting document, and warning.
4. Include deterministic recovery and same-run pause-and-resume demonstrations.
5. Test prompt injection, sensitive fields, ambiguous deadlines, dependency failure, revision, missing profile values, and API contracts.
6. Keep the frontend, backend, graph, fixtures, tests, and evaluation code directly traceable in the repository.

## Iterations

### Iteration 1: One-shot form analysis

The original MVP uploaded a form and returned a structured checklist in one request. It demonstrated product value but did not make control flow, state, failure recovery, or human approval observable.

### Iteration 2: Stateful graph

The backend was rebuilt in Python with explicit LangGraph nodes and thread checkpoints. The final plan moved behind an interrupt, making approval and resumption first-class behaviors.

### Iteration 3: Trust and evaluation

Exact evidence quotes, prompt-injection isolation, a retry policy, a conservative model fallback, an agent run receipt, unit/integration tests, and adversarial fixtures were added. Obsolete backend sources were removed so every documented request path is traceable in code.

### Iteration 4: Observable recovery and revision

Dependency health became its own graph node, an explicit outage demo was added, rejection became a state-preserving revision checkpoint, cost/latency metadata was surfaced in the run receipt, and both paths received API and graph integration tests.

## Learnings and observations

- Good prompts do not replace explicit control flow. Routing and state boundaries are easier to test when represented as graph nodes.
- Human approval should guard a meaningful boundary. PaperworkPilot pauses before it transforms analysis into an actionable final artifact.
- Evidence is more useful than a confidence adjective. Exact source quotes let reviewers verify the agent's work quickly.
- Failure recovery should be visible. The demo's injected timeout makes the retry path undeniable without relying on an unreliable live outage.
- “Do not invent” requires code as well as prompting. Profile matching only reads an allow-listed key and leaves every unknown value empty.
- A deterministic demo and a live AI path serve different purposes. The demo proves orchestration reliably; the API-key path handles real forms.
