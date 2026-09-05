# Technical Architecture

## End-to-end request path

```text
Browser FormData
  → FastAPI validation and file reading
  → LangGraph thread created with run_id
  → safety_intake
  → dependency_check
  → extract_requirements OR local conservative fallback
  → verify_evidence [retry policy]
  → match_profile
  → review_uncertainty
  → human_checkpoint [interrupt + checkpoint]
  → POST /resume with same run_id
  → assemble_plan OR request_revision [second interrupt] OR stop_safely
  → browser renders run receipt and checklist
```

## State

`PaperworkState` carries the run ID, source text, source name, allow-listed profile, mode, failure scenario, dependency status, fallback flag, model-call count, safety flags, extraction, matched fields, documents, warnings, ambiguities, evidence coverage, human decision, append-only review history, final analysis, status, error, and an append-only trace.

The source file bytes are not checkpointed. Text and normal PDFs are converted to text before graph invocation. Images and scanned PDFs are transcribed through a stateless OpenAI call, then only the resulting text enters graph state.

## Nodes and control flow

1. `safety_intake` treats all document content as untrusted and detects AI-directed instructions.
2. `dependency_check` records extractor availability and selects a primary or local recovery path.
3. `extract_requirements` uses a deterministic fixture in demo mode, the OpenAI Responses API with a strict schema in live mode, or the conservative local extractor on dependency failure.
4. `verify_evidence` checks each quote against normalized source text. A LangGraph `RetryPolicy` recovers transient connection failures.
5. `match_profile` maps only five allow-listed profile keys. Unknown values remain empty.
6. `review_uncertainty` routes ambiguous deadlines, low evidence, and sensitive fields to human review.
7. `human_checkpoint` calls LangGraph `interrupt()` and saves the current thread state.
8. Approval/edit routes to `assemble_plan`; request-changes routes to `request_revision`, which interrupts again; stop routes to `stop_safely`.

## API contract

- `GET /api/health` — configuration and architecture status
- `GET /api/demo` — fictional sample form and profile
- `POST /api/runs` — create and execute a graph until interruption/completion
- `POST /api/runs/{run_id}/resume` — approve, edit, request changes, or stop a paused graph
- `GET /api/runs/{run_id}` — retrieve saved run state
- `DELETE /api/runs/{run_id}` — discard session state

## Model boundary

Live extraction uses `gpt-5.4-mini` by default through the OpenAI Responses API with strict JSON Schema output. API calls set `store: false`. The model sees profile fields as unverified suggestions and cannot directly write to external systems.

## Failure strategy

| Failure | Response |
|---|---|
| Temporary verifier failure | LangGraph retries with backoff. |
| Model/API failure | Conservative heuristic fallback, reduced-confidence warning, mandatory review. |
| Missing API key | Pasted text uses the conservative local extractor; images/scanned PDFs return actionable guidance. |
| Unreadable/empty file | Safe 400 response requesting a clearer upload or pasted text. |
| Invalid schema | Pydantic validation fails and activates the conservative fallback. |
| Human change request | State is preserved at a second interrupt; an edited instruction resumes the same run. |
| Human stop | Graph routes to safe stop; no final artifact or external action. |
| Process restart | Session expires by design; user starts a new analysis. |

## Production hardening beyond the demo

Use encrypted durable checkpoints, authenticated user isolation, retention controls, rate limiting, malware scanning, an abuse review, a formal privacy policy, and domain-specific escalation before accepting sensitive production paperwork.
