# Evaluation Report

## Evaluation philosophy

PaperworkPilot is evaluated as a workflow, not only as a model response. The critical questions are whether the graph preserves state, recovers from a tool failure, pauses at the correct boundary, resumes with the same run ID, verifies claims against source text, and avoids inventing personal information.

## Executable checks

Run:

```bash
python -m unittest discover -s test -v
python evaluation/run_evals.py
```

The test suite covers:

- Initial graph pause and checkpoint payload
- Same-thread approval and resumption
- Human request-changes, second pause, edited resume, and safe stop
- Simulated extraction-dependency outage and local fallback
- Deliberate verifier timeout and retry recovery
- Exact source evidence coverage
- Unknown vehicle information remaining missing
- Prompt-injection detection
- API health/start/resume contracts
- No-key text fallback and model-call accounting
- Server timing and fallback response headers
- Frontend-to-HTML ID contract and accessibility landmarks

## Fixture set

`evaluation/cases.json` contains 12 synthetic fragments across normal forms, attachments, signatures, prompt injection, sensitive identity information, and banking information. Expected routing is explicit and reviewable.

## Acceptance thresholds

| Metric | Required |
|---|---:|
| Prompt-injection routing | 12/12 |
| Sensitive-field routing | 12/12 |
| Demo evidence coverage | 100% |
| Injected transient failure | Recovered |
| Human interrupt | Resumed successfully |
| Dependency outage | Recovered with 0 model calls |
| Reject/revise/resume | Same run ID through both checkpoints |
| Invented values for missing fields | 0 |
| Automated test failures | 0 |

## Current verified result

The final local verification run passed all 22 automated tests. All five deterministic demo scenarios achieved 100% evidence coverage. The executable evaluation reported 12/12 prompt-injection routing, 12/12 sensitive-field routing, verifier retry recovery, dependency recovery with zero model calls, reject/revise/resume on the same run, and zero invented values for missing fields.

High-level browser validation covered dependency outage from selection through approval and the complete reject/revise/resume workflow. The final receipts showed 100% evidence coverage, zero model calls, and measured server runtimes of 10–16 ms on the local validation machine. Required controls remained visible in the responsive layout and the browser console reported no warnings or errors.

## Scope of the result

These checks establish deterministic orchestration and safety behavior for the included fixtures. They do not claim universal extraction accuracy across every form type or scan quality. A production evaluation would add a larger, independently labeled corpus, page-level OCR benchmarks, multiple model snapshots, demographic accessibility testing, and human adjudication.
