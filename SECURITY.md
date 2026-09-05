# Security and Privacy

PaperworkPilot is a demonstration agent for workflow guidance. It does not submit forms, sign documents, make payments, determine eligibility, or provide legal advice.

## Data handling

- Uploaded content is processed only for the current run.
- API responses use `Cache-Control: no-store`.
- OpenAI requests use `store: false`.
- Raw upload bytes are not stored in LangGraph checkpoints.
- Checkpoint state is session-scoped and can be deleted through the API.
- Demo profiles and forms are fictional.

## Safety controls

- Uploaded documents are treated as untrusted content.
- AI-directed instructions inside forms are isolated as prompt injection.
- Profile matching uses an allow list and never fills unknown values.
- Sensitive labels trigger human review.
- Every run interrupts before final plan assembly.
- The service never performs an external write action.

## Deployment controls

- Secrets belong in Replit Secrets, never source files.
- The release sends restrictive content, referrer, permissions, and MIME-sniffing headers.
- Production should add authentication, encrypted durable checkpoints, tenant isolation, retention controls, malware scanning, rate limiting, audit logs, and a reviewed privacy policy before processing real sensitive paperwork.

## Reporting

Do not submit real personal paperwork when reporting a problem. Provide a synthetic reproduction through the repository issue tracker and avoid including API keys, account numbers, identity documents, or health information.
