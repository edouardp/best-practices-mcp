# SDLC Advice — Pragmatic, High-Signal Engineering Workflow

> Goals: **fast flow**, **safety nets**, **low toil**, **high signal gates**. Works across .NET, Python, and UI repos.

---

## 0. Principles

- **Trunk-based development**; short-lived branches; fast CI.
- **Definition of Done** includes: tests (unit+integration), docs updated, ADR considered, telemetry added, runbook touched.
- **Quality gates**: warnings-as-errors; coverage thresholds; security scans; infra linting.
- **Everything observable**: logs, metrics, traces from day one.
- **Blameless postmortems**; action items tracked and verified.

---

## 1. Planning & Design

- Keep **ADRs** in-repo; 1–2 page max; decision, options, consequences.
- Threat model (STRIDE) for new external surfaces.
- Define **SLIs/SLOs** & error budgets with Product at design time.
- Feature flags for risky changes (AppConfig) and safe rollouts.

---

## 2. CI/CD

- Pipeline stages: `lint` → `test` → `coverage` → `build` → `scan` → `deploy` → `smoke`.
- Enforce **conventional commits** + generated CHANGELOG.
- SBOM (Syft/CycloneDX), image scan (Trivy), dependency audit.
- Canary or blue/green for risky releases; fast rollback plan documented.
- Per-PR **ephemeral environments** where feasible.

---

## 3. Testing Strategy

- **Unit** (fast, isolated) → **Integration** (Testcontainers) → **Contract** (Pact) → **E2E smoke**.
- **Mutation testing** (Stryker.NET) for critical domain modules.
- **Property-based** (FsCheck/Hypothesis) for parsers/validators.
- **Load/Soak** (k6/NBomber) before high-impact releases.
- **Chaos** (AWS FIS) exercises quarterly.

---

## 4. Security & Compliance

- Secret scanning (Gitleaks) and dependency audits in CI.
- SBOMs signed and archived; optional image **provenance signing** (cosign).
- Least privilege IAM; periodic access review.
- PII logging policy; redaction built-in to logging middleware.

---

## 5. Operations & Support

- **Runbooks** per service; link from README.
- On-call rotation w/ clear escalation policy.
- Synthetic checks for critical user flows.
- Incident review template with actions + verification dates.

---

## 6. Documentation & DX

- `README.md` with purpose, local dev steps, env vars, health endpoints.
- `BEST_PRACTICES.md` per language; `PLAYBOOK.md` for AWS principles.
- Templates: repo skeletons, Buildkite pipeline, Directory.Packages.props.
- Developer onboarding checklist.

---

## 7. Checklists

- [ ] ADR written/updated
- [ ] Telemetry (logs/traces/metrics) added
- [ ] Tests (unit/integration/contract) passing, coverage gates met
- [ ] Security scans clean; SBOM archived
- [ ] Infra validated (cfn-lint, cfn-nag)
- [ ] Runbook updated
- [ ] Rollout & rollback plan defined
