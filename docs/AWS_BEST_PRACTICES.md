# AWS Best Practices — Lean, High-Leverage, Low-Complexity

> Principles tailored for your stack: **ECS Fargate**, **API Gateway (HTTP)**, **Lambda (where it fits)**, **SNS→SQS**, **AppConfig**, **Parameter Store (SecureString)**, **CloudFormation**, **OpenTelemetry→X-Ray/CloudWatch**.

---

## 0. Core Principles

### Prefer SSM Parameter Store (SecureString) for secrets/config; use Secrets Manager only for auto-rotation
**Why:** Parameter Store provides encrypted configuration storage at no additional cost for standard parameters, with fine-grained IAM control and audit trails. SecureString parameters are encrypted with KMS keys you control. Secrets Manager costs significantly more but provides automatic rotation capabilities, making it ideal only when you need features like RDS password rotation. This cost-conscious approach maintains security while optimizing spend.

### Publish events to SNS and subscribe with SQS (never produce to raw SQS)
**Why:** SNS provides fan-out capabilities that decouple publishers from consumers, making your architecture more flexible and resilient. You can add new consumers without modifying publishers. Raw SQS creates tight coupling between services and makes it difficult to add new event consumers. SNS→SQS also provides better error handling and retry capabilities through dead letter queues.

### CloudFormation-first for all infrastructure; lint with cfn-lint + cfn-nag
**Why:** Infrastructure as Code ensures reproducible, version-controlled deployments and prevents configuration drift. CloudFormation provides native AWS integration and handles resource dependencies automatically. cfn-lint catches syntax and logical errors before deployment, while cfn-nag identifies security issues and compliance violations. This prevents costly mistakes and security vulnerabilities in production.

### Observability by default: structured logs, metrics, traces
**Why:** Observability is essential for understanding system behavior, debugging issues, and maintaining SLAs. Structured logs enable powerful querying and filtering. Metrics provide quantitative insights into system health. Distributed tracing helps understand request flows across microservices. OpenTelemetry provides vendor-neutral instrumentation that works across different tools and cloud providers.

### Per-service IAM roles; least privilege; tag everything for FinOps
**Why:** Per-service roles limit blast radius if credentials are compromised and make it easier to audit access patterns. Least privilege reduces attack surface and prevents accidental access to unrelated resources. Comprehensive tagging enables cost allocation, resource management, and automated governance policies. This is crucial for multi-team environments and cost optimization.

---

## 1. Config, Flags, Secrets

### Parameter Store for most app settings (namespace /org/service/env/key)
**Why:** Centralized configuration management with hierarchical namespacing makes it easy to organize and manage settings across environments and services. The namespace pattern prevents naming conflicts and makes it clear which service owns which parameters. Parameter Store integrates with IAM for fine-grained access control and provides audit trails for configuration changes.

### AppConfig for feature flags + gradual rollouts; JSON schema validators
**Why:** AppConfig provides safe feature flag deployment with rollback capabilities, gradual rollouts, and monitoring integration. JSON schema validation prevents invalid configurations from breaking your application. This enables continuous deployment with reduced risk, allowing you to test features with small user groups before full rollout.

### Secrets Manager only where rotation automation exists
**Why:** Secrets Manager's primary value is automatic rotation of credentials, which is crucial for database passwords and API keys that need regular rotation. For static secrets that don't require rotation, Parameter Store SecureString provides the same encryption and access control at lower cost. This approach optimizes costs while maintaining security.

### Cache config locally; periodic refresh; fail closed for critical toggles
**Why:** Local caching reduces API calls and improves application performance while providing resilience against Parameter Store outages. Periodic refresh ensures applications get configuration updates without restart. Failing closed for critical toggles (like kill switches) ensures safe defaults when configuration is unavailable, preventing system failures.

---

## 2. Messaging & Async

### SNS → SQS fan-out; message attributes for routing; DLQs for each consumer
**Why:** SNS fan-out enables loose coupling between publishers and consumers, making it easy to add new consumers without modifying publishers. Message attributes provide efficient routing without parsing message bodies. Dead Letter Queues capture failed messages for analysis and prevent infinite retry loops, improving system reliability and debuggability.

### SQS FIFO for ordered, per-entity processing; set visibility timeout and redrive policy
**Why:** FIFO queues ensure message ordering when required (like financial transactions or state changes), while standard queues provide higher throughput for order-independent processing. Proper visibility timeout prevents message duplication while allowing sufficient processing time. Redrive policies automatically handle failed messages after retry attempts.

### EventBridge when you need decoupled domains + schema registry
**Why:** EventBridge provides advanced routing capabilities with content-based filtering and integrates with many AWS services out of the box. Schema registry enables contract-first development and prevents breaking changes. Use EventBridge for complex routing scenarios and cross-domain events, but prefer SNS→SQS for simpler use cases due to lower cost and complexity.

### Step Functions for orchestration only; never for core business logic
**Why:** Step Functions excel at coordinating multiple services, handling retries, and managing complex workflows with branching and parallel execution. However, business logic should remain in your application code where it's easier to test, version, and maintain. Step Functions should orchestrate calls to services that contain the actual business logic.

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

### ECS Fargate for APIs/workers: linux/arm64, non-root, read-only fs, healthchecks, awsvpc
**Why:** Fargate eliminates server management overhead while providing container orchestration. ARM64 (Graviton) offers 20-40% better price-performance than x86. Running as non-root follows security best practices and limits attack surface. Read-only filesystems prevent runtime modifications that could indicate compromise. Health checks enable automatic recovery and proper load balancing.

### Lambda for small event-driven tasks; arm64; Powertools; reserved concurrency for isolation
**Why:** Lambda is ideal for event-driven workloads with variable traffic patterns, providing automatic scaling and pay-per-use pricing. ARM64 provides better price-performance. Lambda Powertools provides battle-tested utilities for logging, tracing, and common patterns. Reserved concurrency prevents one function from consuming all available concurrency and affecting other functions.

### Auto-scaling signals on SQS depth, latency SLOs, or CPU/memory where appropriate
**Why:** Different workloads require different scaling signals. SQS depth indicates backlog for queue-based workers. Latency SLOs ensure user experience requirements are met. CPU/memory metrics work for compute-intensive workloads. Using appropriate signals prevents over-provisioning while maintaining performance and user experience.

---

## 4. Networking & Delivery

### API Gateway (HTTP) in front of BFF/APIs; request validation; WAF; access logs on
**Why:** API Gateway provides managed API hosting with built-in features like throttling, caching, and monitoring. HTTP APIs offer better performance and lower cost than REST APIs for most use cases. Request validation prevents invalid requests from reaching your backend. WAF protects against common web attacks. Access logs provide audit trails and debugging information.

### CloudFront + S3 (OAC) for SPA/static; cache immutable assets; WAF at edge
**Why:** CloudFront CDN improves global performance by serving content from edge locations closer to users. Origin Access Control (OAC) ensures S3 buckets aren't directly accessible, improving security. Caching immutable assets (with hash filenames) enables aggressive caching while ensuring users get updates. Edge WAF provides protection closer to attackers.

### VPC Endpoints for SSM, S3, SQS, STS; IMDSv2 only for EC2/ECS tasks
**Why:** VPC endpoints keep AWS API traffic within your VPC, improving security and potentially reducing data transfer costs. They also provide better reliability by avoiding internet routing. IMDSv2 requires session tokens, preventing SSRF attacks that could access instance metadata. This is crucial for container security.

### PrivateLink only when crossing account/VPC boundaries that require it
**Why:** PrivateLink provides secure connectivity between VPCs and AWS services without internet routing, but adds cost and complexity. Use it only when you need to connect across account boundaries or when security requirements mandate private connectivity. For same-account scenarios, VPC endpoints are usually sufficient and more cost-effective.

---

## 5. Data & Storage

### RDS/Aurora MySQL 8: UTC only, strict SQL mode, slow query logs + alarms, backups & PITR
**Why:** MySQL 8 provides better performance, security, and features compared to older versions. UTC-only timestamps prevent timezone-related bugs and simplify global applications. Strict SQL mode catches data truncation and other issues that could lead to data corruption. Slow query logs with alarms help identify performance issues before they impact users. Automated backups and Point-in-Time Recovery protect against data loss.

### S3: versioning, SSE-KMS, lifecycle policies; object tagging for lineage; Object Lambda if transformations help
**Why:** Versioning protects against accidental deletion or corruption of critical data. SSE-KMS provides encryption with keys you control and audit trails. Lifecycle policies automatically transition data to cheaper storage classes and delete old data, optimizing costs. Object tagging enables data lineage tracking and automated governance. Object Lambda allows data transformation without duplicating storage.

### Idempotency & retries: standard headers, DLQs, and compensating actions defined in runbooks
**Why:** Idempotency prevents duplicate operations when clients retry requests due to network issues or timeouts. Standard headers (like Idempotency-Key) provide a consistent approach across services. Dead Letter Queues capture failed operations for analysis. Compensating actions in runbooks ensure teams know how to handle failures and maintain data consistency.

---

## 6. Security

### IAM: per-service roles; scoped policies; no wildcard on resource where possible
**Why:** Per-service roles implement the principle of least privilege and limit blast radius if credentials are compromised. Scoped policies prevent accidental access to unrelated resources and make it easier to audit permissions. Avoiding wildcards on resources provides more granular control and better security posture, though wildcards on actions may be acceptable for related operations.

### KMS: envelope encryption (GenerateDataKey); Sign/Verify for payload signatures
**Why:** Envelope encryption with GenerateDataKey provides better performance and security than encrypting data directly with KMS keys. It reduces KMS API calls and enables local encryption/decryption. Sign/Verify operations provide digital signatures for data integrity and authenticity, which is crucial for financial transactions and audit trails.

### WAF + Shield Standard on API/CloudFront; rate limits and IP blocks as needed
**Why:** WAF protects against common web attacks like SQL injection, XSS, and DDoS. Shield Standard provides basic DDoS protection at no additional cost. Rate limiting prevents abuse and protects against traffic spikes. IP blocking can stop known malicious actors. These layers provide defense-in-depth security.

### ECR: image scanning, immutable tags; provenance signing (cosign) optional
**Why:** Image scanning identifies known vulnerabilities in container images before deployment. Immutable tags prevent accidental overwrites and ensure reproducible deployments. Provenance signing with tools like cosign provides supply chain security by verifying image authenticity and integrity, though it adds complexity.

### S3: Block Public Access; only OAC-based CloudFront access for public sites
**Why:** Block Public Access prevents accidental exposure of sensitive data through misconfigured bucket policies. Using OAC (Origin Access Control) instead of direct S3 access ensures all traffic goes through CloudFront, enabling consistent security policies, caching, and monitoring. This prevents direct S3 access bypassing your security controls.

---

## 7. Observability

### Logs: JSON to CloudWatch; retention set per env; Insights queries documented
**Why:** JSON logs enable powerful querying and filtering in CloudWatch Logs Insights. Setting appropriate retention periods balances compliance requirements with cost optimization. Documenting common Insights queries helps teams quickly troubleshoot issues and reduces mean time to resolution. Structured logs also integrate better with log aggregation and analysis tools.

### Traces: OTEL SDK + AWS X-Ray exporter; propagate trace across services
**Why:** OpenTelemetry provides vendor-neutral instrumentation that works across different tools and cloud providers. X-Ray integration gives you distributed tracing across AWS services. Trace propagation enables understanding of request flows across microservices, which is crucial for debugging performance issues and understanding system behavior.

### Metrics: SLIs (latency, error rate, saturation); Composite Alarms for clear paging
**Why:** Service Level Indicators (SLIs) provide quantitative measures of user experience and system health. Latency, error rate, and saturation are the most important metrics for most services. Composite Alarms reduce alert fatigue by combining multiple conditions into meaningful alerts that warrant immediate attention, improving on-call experience.

### Synthetic checks: CloudWatch Synthetics for critical endpoints; optional RUM for frontend
**Why:** Synthetic monitoring proactively checks critical user journeys and catches issues before users report them. CloudWatch Synthetics can test API endpoints, user flows, and availability from multiple regions. Real User Monitoring (RUM) provides insights into actual user experience but adds complexity and cost, so use it selectively for critical user-facing applications.

---

## 8. FinOps & Governance

### Mandatory tags: App, Env, Owner, CostCenter, DataClass
**Why:** Consistent tagging enables cost allocation, resource management, and automated governance policies. App and Env tags help identify resources and their purpose. Owner tags enable accountability and contact information for issues. CostCenter tags enable chargeback and budget allocation. DataClass tags help implement appropriate security and compliance controls based on data sensitivity.

### Budgets + anomaly detection; dashboard per product
**Why:** Budgets provide proactive cost control and prevent unexpected charges. Anomaly detection catches unusual spending patterns that might indicate issues or waste. Per-product dashboards enable teams to understand their cost drivers and optimize spending. This visibility is crucial for maintaining cost efficiency as systems scale.

### DORA metrics tracked; deployment frequency & MTTR in one place
**Why:** DORA (DevOps Research and Assessment) metrics provide objective measures of software delivery performance. Deployment frequency indicates how often you can deliver value. Mean Time to Recovery (MTTR) measures how quickly you can resolve issues. Tracking these metrics helps identify improvement opportunities and demonstrates the business value of DevOps practices.

### Resource TTLs for sandboxes; cleanup jobs
**Why:** Development and testing environments often accumulate unused resources that generate ongoing costs. Time-to-live (TTL) tags and automated cleanup jobs prevent resource sprawl and reduce waste. This is especially important for expensive resources like databases and compute instances that teams might forget to shut down after testing.

---

## 9. Checklists

**Why this checklist matters:** This checklist serves as a final verification that all critical AWS practices are implemented. Each item represents a decision that significantly impacts security, cost, reliability, or operational efficiency. Regular checklist reviews during architecture reviews and before production deployments help ensure consistency across projects and prevent regression of important practices.

- [ ] Parameter Store (SecureString) wired; SecretsMgr only with rotation
- [ ] SNS→SQS with DLQs; FIFO where needed
- [ ] OTEL traces→X-Ray, logs→CloudWatch, metrics→Alarms
- [ ] WAF enabled on API/CloudFront; Shield active
- [ ] ECS Fargate arm64, non-root, read-only FS
- [ ] CloudFormation validated (cfn-lint, cfn-nag)
- [ ] FinOps tags present; budgets/alerts configured
