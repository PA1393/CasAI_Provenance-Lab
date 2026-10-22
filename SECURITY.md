# Security policy

CasAI Provenance Lab is currently a concept demonstration for synthetic, public
or intentionally non-sensitive data. It is not approved for customer-private
research or clinical use.

## Reporting a vulnerability

Do not include credentials, private research data or exploit details in a public
issue. Use GitHub private vulnerability reporting when it is available for this
repository. Otherwise, contact the repository owners privately and provide only
the minimum information needed to reproduce the problem.

Include the affected commit or version, impact, reproduction steps, and whether
you believe a credential or private artifact was exposed. Do not test against
systems or data you do not own or have permission to assess.

## Supported scope

Security fixes target the current `main` branch and active release branch. The
demo has request limits, explicit CORS configuration, conservative response
headers, content-addressed local artifacts, integrity checks, and automated code,
dependency and secret scanning. Those controls do not provide authentication,
tenant isolation, row-level security or production privacy compliance.

## Exposed credential response

If a credential may have been exposed:

1. Disable or revoke it at the provider before editing repository history.
2. Create a replacement with the minimum required scope.
3. Update the backend or CI secret store; never place the value in source code,
   build logs, browser variables, desktop bundles or issue comments.
4. Redeploy affected services and verify the old credential no longer works.
5. Review provider and application audit logs for unauthorized activity.
6. Record the incident timeline, affected systems, containment and follow-up.

This applies to Supabase service-role keys, OpenAI keys, update/signing material,
deployment tokens and database administration credentials. Removing a secret
from the latest commit does not revoke it or remove it from Git history.
