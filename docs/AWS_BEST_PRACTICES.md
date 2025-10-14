# AWS Best Practices — Lean, High-Leverage, Low-Complexity

> Principles tailored for your stack: **ECS Fargate**, **API Gateway (HTTP)**, **Lambda (where it fits)**, **SNS→SQS**, **AppConfig**, **Parameter Store (SecureString)**, **CloudFormation**, **OpenTelemetry→X-Ray/CloudWatch**.

---

## 0. Core Principles

- ✅ Prefer **SSM Parameter Store (SecureString)** for secrets/config; use **Secrets Manager only** when you exploit its **auto-rotation integrations** (notably RDS admin).
- ✅ Publish events to **SNS** and subscribe with **SQS** (never produce to raw SQS) → add taps at runtime.
- ✅ **CloudFormation-first** for all infra; lint with `cfn-lint` + `cfn-nag`.
- ✅ Observability by default: **structured logs**, **metrics**, **traces** (OTEL→X-Ray/CloudWatch).
- ✅ Per-service IAM roles; least privilege; tag everything for FinOps.

---

## 1. Config, Flags, Secrets

- **Parameter Store** for most app settings (namespace `/org/service/env/key`).
- **AppConfig** for **feature flags** + gradual rollouts; JSON schema validators.
- **Secrets Manager** only where rotation automation exists; otherwise Parameter Store.
- Cache config locally; periodic refresh; fail closed for critical toggles (use kill-switch).

---

## 2. Messaging & Async

- **SNS → SQS** fan-out; message attributes for routing; DLQs for each consumer.
- **SQS FIFO** for ordered, per-entity processing; set visibility timeout and redrive policy.
- **EventBridge** when you need decoupled domains + schema registry.
- **Step Functions** for orchestration only (retry, wait, fan-out); never for core business logic.

**CloudFormation (SNS→SQS sketch):**
```yaml
Topic:
  Type: AWS::SNS::Topic

Queue:
  Type: AWS::SQS::Queue
  Properties:
    FifoQueue: true
    ContentBasedDeduplication: true

Subscription:
  Type: AWS::SNS::Subscription
  Properties:
    TopicArn: !Ref Topic
    Protocol: sqs
    Endpoint: !GetAtt Queue.Arn
```

---

## 3. Compute

- **ECS Fargate** for APIs/workers: `linux/arm64`, non-root, read-only fs, healthchecks, awsvpc.
- **Lambda** for small event-driven tasks; arm64; Powertools; reserved concurrency for isolation.
- **Auto-scaling** signals on SQS depth, latency SLOs, or CPU/memory where appropriate.

---

## 4. Networking & Delivery

- **API Gateway (HTTP)** in front of BFF/APIs; request validation; WAF; access logs on.
- **CloudFront + S3 (OAC)** for SPA/static; cache immutable assets; WAF at edge.
- **VPC Endpoints** for SSM, S3, SQS, STS; **IMDSv2** only for EC2/ECS tasks.
- **PrivateLink** only when crossing account/VPC boundaries that require it.

---

## 5. Data & Storage

- **RDS/Aurora MySQL 8**: UTC only, strict SQL mode, slow query logs + alarms, backups & PITR.
- **S3**: versioning, SSE-KMS, lifecycle policies; object tagging for lineage; Object Lambda if transformations help.
- **Idempotency & retries**: standard headers, DLQs, and compensating actions defined in runbooks.

---

## 6. Security

- **IAM**: per-service roles; scoped policies; no wildcard on resource where possible.
- **KMS**: envelope encryption (`GenerateDataKey`); `Sign/Verify` for payload signatures.
- **WAF + Shield Standard** on API/CFN; rate limits and IP blocks as needed.
- **ECR**: image scanning, immutable tags; provenance signing (cosign) optional.
- **S3**: Block Public Access; only OAC-based CloudFront access for public sites.

---

## 7. Observability

- Logs: JSON to CloudWatch; retention set per env; Insights queries documented.
- Traces: OTEL SDK + AWS X-Ray exporter; propagate trace across services.
- Metrics: SLIs (latency, error rate, saturation); **Composite Alarms** for clear paging.
- Synthetic checks: CloudWatch Synthetics for critical endpoints; optional **RUM** for frontend.

---

## 8. FinOps & Governance

- Mandatory tags: `App`, `Env`, `Owner`, `CostCenter`, `DataClass`.
- Budgets + anomaly detection; dashboard per product.
- DORA metrics tracked; deployment frequency & MTTR in one place.
- Resource TTLs for sandboxes; cleanup jobs.

---

## 9. Checklists

- [ ] Parameter Store (SecureString) wired; SecretsMgr only with rotation
- [ ] SNS→SQS with DLQs; FIFO where needed
- [ ] OTEL traces→X-Ray, logs→CloudWatch, metrics→Alarms
- [ ] WAF enabled on API/CloudFront; Shield active
- [ ] ECS Fargate arm64, non-root, read-only FS
- [ ] CloudFormation validated (cfn-lint, cfn-nag)
- [ ] FinOps tags present; budgets/alerts configured
