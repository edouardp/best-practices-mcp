# SDLC Advice — Pragmatic, High-Signal Engineering Workflow

> Goals: **fast flow**, **safety nets**, **low toil**, **high signal gates**. Works across .NET, Python, and UI repos.

---

## 0. Principles

### Trunk-based development; short-lived branches; fast CI
**Why:** Trunk-based development reduces merge conflicts and integration issues by keeping branches short-lived (typically less than 2 days). This enables continuous integration in the truest sense, where code is integrated frequently rather than in large batches. Fast CI provides rapid feedback, enabling developers to fix issues quickly while the context is still fresh. This approach reduces the cost of change and enables faster delivery.

### Definition of Done includes comprehensive quality checks
**Why:** A clear Definition of Done prevents incomplete work from being considered finished and ensures consistent quality across the team. Including tests prevents regressions, updated documentation keeps knowledge current, ADRs capture important decisions for future reference, telemetry enables observability from day one, and runbook updates ensure operational readiness. This comprehensive approach prevents technical debt accumulation.

### Quality gates: warnings-as-errors; coverage thresholds; security scans; infra linting
**Why:** Automated quality gates prevent quality degradation by catching issues before they reach production. Treating warnings as errors prevents technical debt accumulation. Coverage thresholds ensure critical code paths are tested. Security scans catch vulnerabilities early when they're cheaper to fix. Infrastructure linting prevents misconfigurations that could cause outages or security issues.

### Everything observable: logs, metrics, traces from day one
**Why:** Observability must be built in from the beginning because adding it retroactively is expensive and often incomplete. Day-one observability enables faster debugging, better understanding of system behavior, and proactive issue detection. This is especially critical in distributed systems where understanding request flows across services is essential for troubleshooting.

### Blameless postmortems; action items tracked and verified
**Why:** Blameless postmortems focus on system improvements rather than individual blame, encouraging honest reporting and learning. Tracking and verifying action items ensures that lessons learned actually result in system improvements. This creates a culture of continuous improvement and prevents the same issues from recurring.

---

## 1. Planning & Design

### Keep ADRs in-repo; 1–2 page max; decision, options, consequences
**Why:** Architecture Decision Records (ADRs) capture the context and reasoning behind important technical decisions. Keeping them in-repo ensures they're versioned with the code and easily discoverable. The 1-2 page limit forces concise, focused documentation that people will actually read. Including options and consequences helps future developers understand why alternatives were rejected and what trade-offs were made.

### Threat model (STRIDE) for new external surfaces
**Why:** Threat modeling identifies security risks early in the design phase when they're cheaper to address. STRIDE (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege) provides a systematic framework for identifying threats. Focusing on external surfaces prioritizes the most critical attack vectors where systems are exposed to untrusted input.

### Define SLIs/SLOs & error budgets with Product at design time
**Why:** Service Level Indicators (SLIs) and Objectives (SLOs) align engineering and product teams on what "good" looks like for user experience. Defining these at design time ensures systems are built with reliability requirements in mind. Error budgets provide a framework for balancing feature velocity with reliability, giving teams permission to move fast when reliability is good and forcing focus on reliability when budgets are exhausted.

### Feature flags for risky changes (AppConfig) and safe rollouts
**Why:** Feature flags enable safe deployment by decoupling code deployment from feature activation. This allows teams to deploy code to production without immediately exposing users to new functionality. AppConfig provides safe flag management with rollback capabilities and gradual rollouts. This reduces the blast radius of issues and enables faster recovery when problems occur.

---

## 2. CI/CD

### Pipeline stages: lint → test → coverage → build → scan → deploy → smoke
**Why:** This pipeline structure provides fast feedback by running quick checks first (linting) and expensive operations later (deployment). Early failure saves time and compute resources. The progression from static analysis to dynamic testing to deployment ensures quality gates are enforced at each stage. Smoke tests after deployment verify that the system is working in the target environment.

### Enforce conventional commits + generated CHANGELOG
**Why:** Conventional commits provide a standardized format that enables automated tooling and makes commit history more readable. Automated CHANGELOG generation saves developer time and ensures release notes are always up-to-date. This improves communication with stakeholders and helps with debugging by providing clear context about what changed in each release.

### SBOM (Syft/CycloneDX), image scan (Trivy), dependency audit
**Why:** Software Bill of Materials (SBOM) provides transparency into what components are included in your software, which is increasingly required for compliance and security. Image scanning catches known vulnerabilities in container images before deployment. Dependency audits identify vulnerable packages in your supply chain. These practices are essential for supply chain security and regulatory compliance.

### Canary or blue/green for risky releases; fast rollback plan documented
**Why:** Canary and blue/green deployments reduce the blast radius of issues by gradually exposing new versions to users or maintaining parallel environments. This enables quick detection of problems with minimal user impact. Having a documented rollback plan ensures teams can recover quickly when issues occur, reducing Mean Time to Recovery (MTTR).

### Per-PR ephemeral environments where feasible
**Why:** Ephemeral environments enable testing of changes in isolation without affecting shared environments. This improves testing quality, reduces conflicts between developers, and enables parallel development. While not always feasible due to cost or complexity, they significantly improve development velocity when implemented appropriately.

---

## 3. Testing Strategy

### Unit (fast, isolated) → Integration (Testcontainers) → Contract (Pact) → E2E smoke
**Why:** This testing pyramid balances speed, cost, and confidence. Unit tests are fast and provide immediate feedback but limited scope. Integration tests with Testcontainers test against real dependencies while remaining deterministic. Contract tests ensure service compatibility without the complexity of full integration. E2E smoke tests verify critical user journeys work end-to-end but are kept minimal due to their cost and fragility.

### Mutation testing (Stryker.NET) for critical domain modules
**Why:** Mutation testing validates the quality of your tests by introducing small changes (mutations) to your code and checking if tests catch them. This ensures tests actually verify the behavior they claim to test, not just achieve code coverage through execution. Focus on critical domain modules where business logic bugs would have the highest impact.

### Property-based (FsCheck/Hypothesis) for parsers/validators
**Why:** Property-based testing generates many test cases automatically, often finding edge cases that manual testing misses. This is especially valuable for parsers and validators that handle user input, where unexpected inputs can cause security vulnerabilities or data corruption. The automated generation of test cases provides broader coverage than manually written examples.

### Load/Soak (k6/NBomber) before high-impact releases
**Why:** Load testing identifies performance bottlenecks and capacity limits before they affect users. Soak testing reveals memory leaks and other issues that only appear over time. Running these tests before high-impact releases prevents performance regressions that could affect user experience or system stability during peak usage.

### Chaos (AWS FIS) exercises quarterly
**Why:** Chaos engineering proactively identifies weaknesses in system resilience by intentionally introducing failures. Quarterly exercises ensure teams practice incident response and verify that resilience mechanisms actually work. AWS Fault Injection Simulator (FIS) provides controlled chaos experiments that help build confidence in system reliability.

---

## 4. Security & Compliance

### Secret scanning (Gitleaks) and dependency audits in CI
**Why:** Secret scanning prevents accidental exposure of credentials, API keys, and other sensitive information in version control. Gitleaks catches secrets before they're committed, preventing security incidents and compliance violations. Dependency audits identify known vulnerabilities in third-party packages, enabling proactive security management. Running these in CI ensures consistent enforcement across all changes.

### SBOMs signed and archived; optional image provenance signing (cosign)
**Why:** Signed SBOMs provide tamper-evident records of software components, which is increasingly required for compliance and supply chain security. Archiving enables historical analysis and incident response. Image provenance signing with cosign provides cryptographic proof of image authenticity and build integrity, though it adds operational complexity and should be evaluated based on security requirements.

### Least privilege IAM; periodic access review
**Why:** Least privilege reduces the blast radius of compromised credentials and limits the potential for accidental damage. Starting with minimal permissions and adding only what's needed reduces attack surface. Periodic access reviews ensure permissions don't accumulate over time and that access is removed when no longer needed. This is essential for compliance and security hygiene.

### PII logging policy; redaction built-in to logging middleware
**Why:** PII (Personally Identifiable Information) in logs creates compliance risks and potential data breaches. Having a clear policy and built-in redaction prevents accidental logging of sensitive data. Building redaction into logging middleware ensures consistent enforcement across the application without relying on developer discipline. This is crucial for GDPR, CCPA, and other privacy regulations.

---

## 5. Operations & Support

### Runbooks per service; link from README
**Why:** Runbooks provide step-by-step procedures for common operational tasks, reducing Mean Time to Recovery (MTTR) during incidents. Having them per service ensures specific context and procedures are documented. Linking from README makes them easily discoverable when needed. This is especially important for on-call engineers who may not be familiar with every service.

### On-call rotation w/ clear escalation policy
**Why:** On-call rotations distribute operational burden and ensure someone is always available to respond to incidents. Clear escalation policies ensure issues are routed to the right people quickly and prevent incidents from being ignored or mishandled. This improves system reliability and reduces the stress on individual team members.

### Synthetic checks for critical user flows
**Why:** Synthetic monitoring proactively tests critical user journeys and catches issues before users report them. This enables faster incident response and better user experience. Focusing on critical flows ensures monitoring resources are used effectively while covering the most important functionality.

### Incident review template with actions + verification dates
**Why:** Structured incident reviews ensure consistent analysis and learning from failures. Including action items with verification dates ensures that lessons learned actually result in system improvements. This creates a culture of continuous improvement and prevents the same issues from recurring. The template ensures important aspects aren't overlooked during post-incident stress.

---

## 6. Documentation & DX

### README.md with purpose, local dev steps, env vars, health endpoints
**Why:** A comprehensive README reduces onboarding time and makes the codebase more accessible to new team members. Including purpose helps developers understand the service's role in the larger system. Local development steps enable quick setup and contribution. Environment variable documentation prevents configuration issues. Health endpoint information enables proper monitoring and debugging.

### BEST_PRACTICES.md per language; PLAYBOOK.md for AWS principles
**Why:** Language-specific best practices ensure consistent code quality and patterns across the team. Having them documented prevents knowledge silos and enables self-service learning. AWS playbooks capture cloud-specific patterns and decisions, ensuring consistent infrastructure approaches. This documentation scales team knowledge and reduces the need for repeated explanations.

### Templates: repo skeletons, Buildkite pipeline, Directory.Packages.props
**Why:** Templates accelerate new project creation and ensure consistency across repositories. Repo skeletons include all necessary boilerplate and configuration. Pipeline templates ensure consistent CI/CD practices. Package management templates (like Directory.Packages.props) ensure consistent dependency management. This reduces setup time and prevents configuration drift.

### Developer onboarding checklist
**Why:** A structured onboarding checklist ensures new team members get all necessary access, tools, and knowledge consistently. This reduces the time to productivity and ensures nothing important is forgotten. It also helps identify gaps in the onboarding process and improves the experience for future hires.

---

## 7. Checklists

**Why this checklist matters:** This checklist serves as a final verification that all critical SDLC practices are followed for each change. Each item represents a quality gate that significantly impacts system reliability, security, maintainability, or operational readiness. Regular checklist usage during code reviews and before releases helps ensure consistency across the team and prevents regression of important practices.

- [ ] ADR written/updated
- [ ] Telemetry (logs/traces/metrics) added
- [ ] Tests (unit/integration/contract) passing, coverage gates met
- [ ] Security scans clean; SBOM archived
- [ ] Infra validated (cfn-lint, cfn-nag)
- [ ] Runbook updated
- [ ] Rollout & rollback plan defined
