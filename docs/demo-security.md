# Demo API security boundaries

The current concept-demo API accepts only one explicit CORS origin. Wildcards and
multi-origin strings are rejected, and production configuration requires HTTPS.
This is a transport boundary, not tenant isolation or authorization.

All HTTP requests are capped by `MAX_REQUEST_BYTES` (12 MB by default), including
chunked bodies without a declared content length. Oversized requests receive a
bounded structured `413` response before route processing. API responses include
no-sniff, frame denial, restrictive permissions and content-security policies,
no-referrer behavior and `no-store`; production also enables HSTS.

Production configuration also requires a nonzero per-minute request limit. The
initial limiter uses the direct client address, bounded in-memory client buckets
and a standard `Retry-After` response. It is a single-worker demonstration
boundary, not a substitute for a distributed gateway limit in a scaled deployment.
Development keeps the limiter disabled by default so local checks are deterministic.

These controls improve the public synthetic-data demonstration. They do not make
the application suitable for private customer research. Authentication, MFA,
tenant isolation, row-level security, retention/deletion policy, malware scanning
and independent security review remain part of the private-data milestone.
