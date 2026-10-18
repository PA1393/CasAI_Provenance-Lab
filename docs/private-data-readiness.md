# Private-data readiness gate

The current CasAI concept demo is not approved for customer-private research.
The `casai.private-data-readiness.v1` contract makes that limitation enforceable
instead of relying on a deployment label or environment flag.

Private-data ingest, processing, export and deletion remain blocked unless every
required control has current, independently verified, content-addressed evidence.
Required controls cover authentication, MFA, tenant isolation, row-level security,
encryption, signed downloads, audit logs, retention/deletion, malware scanning,
rights enforcement, independent penetration testing, privacy review and incident
response. Implemented-but-unverified and expired controls do not pass the gate.

Synthetic and intentionally public non-sensitive demo data may pass this policy.
Unknown sensitivity fails closed. A retry or configuration toggle cannot turn an
incomplete readiness report into approval; a new report must incorporate verified
evidence. These contracts do not claim that the controls themselves are currently
implemented, and they do not add production authentication in the concept-demo phase.
