# SCMD Pro Architectural Enforcement Contract

Path contract:
- Canonical Markdown source: `cursorrules.md`
- Cursor compatibility mirror: `.cursorrules`
- Invalid/non-existent repository path: `.cursorrules/cursorrules.md`

Version: 3.5.0-doc-normalized
Status: Active AI/code-generation governance contract

## 1. Authority hierarchy

When documents disagree, follow this order:

1. `DOCUMENTATION.md`
2. `WHITEPAPER.md`
3. `README.md`
4. `UI_SYSTEM_REFACTOR_SPEC.md`
5. This file and `.cursorrules`
6. Existing code, only where it does not conflict with higher documents

This file must not override the product, architecture, or security contracts above.

## 2. Product positioning

- Product name: `SCMD Pro`
- Parent company / legal / vendor name: `SCMD`
- Current system model: `single-organization hardened layered monolith`
- `tenant_id` in code is legacy organization-scope naming, not dynamic SaaS tenancy
- `/dashboard/` is the business operations cockpit
- `/admin/` is the technical admin console

Do not describe SCMD Pro as:

- a cyber dashboard
- a war-room UI
- a generic ERP product name
- a microservices system
- a true multi-tenant SaaS platform

## 3. Architecture contract

SCMD Pro is a pragmatic layered monolith.

Layers:

```text
Interface Layer       Django views, DRF endpoints, templates, consumers
Application Layer     Use cases, orchestration, transaction boundary
Domain Helpers        Pure Python rules and validators
Infrastructure Layer  Django ORM, Celery, Redis, Channels, storage, SMTP, integrations
```

Required:

- Views/API receive request, call use cases, and format response.
- Application layer owns multi-step orchestration and transaction boundaries.
- Domain helpers do not depend on request/session/template.
- Celery tasks call application-layer logic rather than duplicating it.
- Avoid duplicate models, duplicate managers, duplicate use cases, or duplicate identity generation.
- Do not use wildcard imports in `*/application/*.py`.

Forbidden:

- large business orchestration inside views/serializers/templates
- ORM queries inside templates
- application-layer code that depends on HTTP request objects
- large workflow logic hidden in model `save()` overrides
- broad refactors without first measuring the real bottleneck or defect cause

## 4. Organization scope and authorization

SCMD Pro currently serves one fixed organization.

Required:

- Resolve organization scope through `settings.SCMD_ORGANIZATION_ID`.
- Use the centralized organization-scoped manager SSOT in `core.managers.TenantAwareManager`.
- Use access-policy/queryset scoping for staff, site, shift, incident, inventory, payroll, export, and dashboard workflows.
- Enforce object-level authorization on sensitive reads and mutations.
- Scope caches by user/scope when cached data depends on visibility.

Forbidden:

- using `request.tenant`
- implementing dynamic SaaS tenant loading
- accepting arbitrary `tenant_id` from request payload/form/query string
- global unscoped querysets in user-facing sensitive workflows
- bypassing object-level authorization because UI already hid the action

## 5. Operational-truth and data-integrity rules

Treat attendance, GPS, photo, incident, payroll, deduction, inventory, export, and audit data as sensitive operational records.

Required:

- preserve auditability for sensitive changes
- protect payroll lock/paid invariants
- preserve incident identity and lifecycle rules
- preserve inventory ledger integrity
- preserve KPI correctness

Forbidden:

- silent rewrites of attendance/payroll source records without audit
- broad shared caches that mix user scope
- changing payroll, attendance, inventory, or incident rules without explicit need
- introducing misleading demo data into production dashboards

## 6. UI and frontend contract

Required:

- user-facing product name is `SCMD Pro`
- local Tailwind build and local assets only
- navy/blue/neutral business UI language
- Vietnamese operational wording with standard UTF-8 text
- mobile/PWA/login/admin/dashboard copy aligned to SCMD Pro

Forbidden:

- `cdn.tailwindcss.com` in production templates
- cyber / war-room / tactical / sentinel wording in business UI
- Python business code inside `static/` or `templates/`
- public shells that drift away from SCMD Pro brand language

## 7. Performance and change discipline

Required:

- measure bottlenecks before refactoring for performance
- prefer focused fixes over speculative rewrites
- use `select_related`, `prefetch_related`, aggregate/annotate, request-local caching, and short TTL per-scope cache only where justified
- keep permission and scope enforcement intact while optimizing

Forbidden:

- removing scope checks for speed
- broad caching that is not keyed by organization/user/scope when data visibility differs
- proposing microservices as a default answer

## 8. Verification expectations

Before closing work, run the smallest relevant verification set you can support in the environment, for example:

```bash
python manage.py check
python manage.py test
python manage.py showmigrations --plan
python manage.py collectstatic --dry-run --noinput
grep -R "cdn.tailwindcss.com" -n .
grep -RInE "War Room|WarRoom|Sentinel|Tactical|Cyber|SCMD ERP|ESP" -n templates static main dashboard users operations accounting clients
grep -R "from .* import \\*" -n */application/*.py
```

If environment limitations block runtime checks, state the blocker clearly and provide static verification instead.

## 9. Expected implementation notes

For non-trivial changes, report:

1. Which documents/contracts were read
2. What scope was changed
3. Root cause or reason for change
4. Risks to permission, scope, payroll, attendance, incident, inventory, export, or audit integrity
5. Verification commands run or still required
6. Any extra technical debt found but intentionally left untouched
