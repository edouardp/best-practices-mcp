# Python Best Practices (3.13) — AWS-Native, Lambda & Services

> Opinionated, production-focused checklist for your repos. Defaults: **uv**, **ruff**, **mypy (strict)**, **pytest**, **structlog**, **OpenTelemetry**, **AWS SDK (boto3)**, **Lambda Powertools**, **S3/SQS/AppConfig/Parameter Store**, **CloudFormation**.

---

## 0. Golden Rules

- ✅ Prefer **Python 3.13**; pin exact versions and commit lockfiles.
- ✅ Use **uv** for env & dependency management; **direnv** optional.
- ✅ Treat **warnings as errors** in CI; fail on lints/format/type errors.
- ✅ Structured logs (`structlog`) everywhere; include `trace_id`, `request_id`, `correlation_id`.
- ✅ **OpenTelemetry** traces/metrics by default (export to X-Ray/CloudWatch).
- ✅ Prefer **SSM Parameter Store (SecureString)** for secrets/config; use **Secrets Manager only** when using its auto-rotation.
- ✅ For Lambda: small handlers, import discipline, arm64, layers for heavy deps; use **aws-lambda-powertools**.

---

## 1. Project Layout

```
repo/
├─ pyproject.toml        # uv + PEP 621
├─ uv.lock               # committed
├─ src/
│  └─ mypkg/             # package code
├─ tests/                # pytest tests
├─ scripts/              # admin/ops scripts
└─ infra/                # CloudFormation, templates
```

- Use **src layout** to avoid implicit imports.
- Keep modules < 400 lines; one responsibility per file.

---

## 2. Tooling & Config

- **uv**: lock, sync, no `pip` in CI.
- **ruff**: lint + format (`ruff check --fix`, `ruff format`).
- **mypy**: `--strict`; add type hints for public funcs/classes.
- **pytest**: `-q --maxfail=1 --disable-warnings -x`; **AAA** test structure; `Given_When_Should` naming.
- **coverage**: `pytest --cov=src --cov-fail-under=90` (domain code gate).
- **pre-commit**: run ruff, mypy (fast), markdownlint, yaml-lint.

`pyproject.toml` sketch:
```toml
[project]
name = "mypkg"
requires-python = ">=3.13"

[tool.uv]
dev-dependencies = ["pytest", "pytest-cov", "mypy", "ruff", "types-requests"]

[tool.ruff]
lint.select = ["E","F","I","UP","B","SIM","N","PL","RUF"]
line-length = 100

[tool.mypy]
python_version = "3.13"
strict = true
```

---

## 3. Logging & Observability

- `structlog` JSON logger; add context via processors; never print() in production paths.
- Include: service name, version, env, trace ids, customer/account id (if safe).
- OTEL:
  - `opentelemetry-sdk`, `opentelemetry-instrumentation-boto3`, `opentelemetry-exporter-otlp` or AWS X-Ray exporter.
  - Always propagate context across threads and async tasks.

---

## 4. AWS Conventions

- **Config**: read from **SSM Parameter Store** at boot, cache in-memory; refresh on a timer.
- **Feature Flags**: **AppConfig** with JSON schema validators; stage-aware.
- **Queueing**: **SNS → SQS** (never raw SQS); FIFO for ordered work + DLQ.
- **KMS**: use `GenerateDataKey` and `Sign/Verify`; never manage raw keys.
- **S3**: set bucket policies, SSE-S3 or SSE-KMS; object versioning on critical data.
- **IAM**: per-service roles, least privilege; VPC endpoints for AWS APIs where possible.

---

## 5. Lambda Guidance

- Runtime: `python3.13`, **arm64**; keep handler tiny.
- Imports: move heavy imports behind functions; use layers for scientific libs.
- Powertools: logger, tracer, metrics, idempotency utility, parser.
- Timeouts: set < 30s unless required; configure reserved concurrency.
- Retries & DLQ: configure per trigger (SQS/SNS/EventBridge).
- Use `asyncio` sparingly; Lambda concurrency is the scaler.

---

## 6. HTTP Clients & Retries

- Use `requests` **or** `httpx` (async). Set **timeouts** and **retries with jitter**:
```python
from tenacity import retry, stop_after_attempt, wait_exponential_jitter

@retry(stop=stop_after_attempt(5), wait=wait_exponential_jitter(0.2, 5))
def call_api(...): ...
```
- For AWS SDK: set `botocore.config.Config` (retries, timeouts, user_agent).

---

## 7. Testing

- Unit tests: pytest, AAA, Given_When_Should, isolate IO; use fakes not real AWS.
- Integration: **testcontainers** for MySQL/Redis; `moto` only for fast, non-critical mocks.
- Contract: **Pact** for consumer/provider contracts with BFF/API.
- Property-based: **hypothesis** for critical validators/parsers.
- Mutation: **mutmut** if needed (target domain modules).

---

## 8. Security

- `bandit` + `osv-scanner` (or `pip-audit`) in CI.
- No `pickle` or unsafe `yaml.load`; use `safe_load`.
- Secrets from env/SSM only; never in code, never in Git.
- Validate all inputs; centralize authN/authZ if building services.

---

## 9. Performance

- Prefer `dataclasses(slots=True)` or `attrs` for hot-path objects; but **Pydantic v2** when validation is required.
- Avoid global state; use dependency injection via constructors or providers.
- Profile with `py-spy` or `scalene` in containerized perf tests.

---

## 10. Checklists

- [ ] Python 3.13, uv lock committed
- [ ] ruff + mypy strict pass
- [ ] pytest coverage ≥ 90% domain
- [ ] structlog JSON, OTEL traces
- [ ] SSM for config; SecretsMgr only for auto-rotation
- [ ] SNS→SQS, DLQs, idempotency keys
- [ ] CloudFormation templates validated (cfn-lint/nag)
