# Security operations for the concept demo

## Backup and restoration

Back up the hosted database using the provider's supported encrypted backup and
point-in-time recovery features. Record the project, backup identifier, retention
window, encryption ownership and restoration test date without copying privileged
credentials into this repository.

The local `.casai-workspace` is a content-addressed demo workspace. Stop writers,
copy the whole directory to an access-controlled encrypted destination, and retain
directory structure and file bytes exactly. A valid restoration must be made into
a new empty directory and then opened through normal workspace loaders so every
manifest, artifact checksum and cross-reference is revalidated. Do not merge a
backup into a live workspace or use it to bypass immutable-object conflicts.

Run a restoration exercise before relying on a backup. Record who performed it,
the source backup, destination, objects sampled, integrity-check results, elapsed
time and any missing dependencies. Never put customer-private data into the demo
workspace; the private-data readiness gate remains fail-closed.

## Incident response

1. Triage the report privately and preserve relevant logs and immutable artifacts.
2. Contain access: revoke exposed credentials, disable affected integrations and
   isolate compromised deployment components.
3. Assess affected data, actors, time range, provenance events and downstream
   exports without altering original evidence.
4. Eradicate the cause, patch it on a reviewable branch and run security and
   regression checks.
5. Restore from a verified backup when integrity cannot be established in place.
6. Notify affected stakeholders according to applicable policy and law.
7. Document the timeline, decisions, evidence, limitations and corrective actions.

Do not claim an incident is resolved until revoked credentials are proven inactive,
the corrected deployment is verified, and restoration/integrity checks pass.

## CI security checks

The security workflow runs CodeQL for Python and TypeScript, audits Python
dependencies, performs Bandit static analysis, and scans changed Git history for
verified or unknown secrets. Findings require review; scanners are safeguards, not
evidence that the application is suitable for private data.
