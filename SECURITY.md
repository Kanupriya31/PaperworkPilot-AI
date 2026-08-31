# Security and privacy

## Application boundaries

- Uploaded documents are treated as untrusted content.
- Instructions embedded in forms are isolated from application control flow.
- Unknown personal values remain empty instead of being inferred.
- The workflow pauses for human review before building the final plan.
- No form is submitted and no external write action is performed.
- Model requests use `store: false`.

## Secrets

Store `OPENAI_API_KEY` in Replit Secrets or a local `.env` file. Never commit the key. The repository contains only `.env.example` with placeholder values.

## Production note

Before handling real sensitive paperwork, add authentication, encrypted durable storage, retention controls, malware scanning, rate limiting, audit logging, and a documented privacy policy.
