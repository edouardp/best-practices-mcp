# .NET Best Practices (8/9/10) — APIs, BFFs, Workers on AWS

> Defaults: ASP.NET Core Minimal APIs, **DI everywhere**, **interfaces for behavior, records for data**, **AwesomeAssertions** (never FluentAssertions), **Dapper + DbUp**, **MySqlConnector**, **Serilog + OTEL**, **Polly**, **xUnit**, **Reqnroll**, **Testcontainers**, **TimeProvider**, **no keyed services**.

---

## 0. Golden Rules

- ✅ Register everything via **built-in DI**; no service locators.
- ✅ **No keyed services** — use explicit interfaces and factories (`Func<T>`, `IFactory<TIn,TOut>`).
- ✅ Records for pure data; interfaces for behaviors. Immutability by default.
- ✅ Replace `DateTime.UtcNow` with **TimeProvider**; test with `FakeTimeProvider`.
- ✅ Warnings-as-errors; analyzers on; zero warnings in CI.
- ✅ REST-first, OpenAPI published; generate typed clients.
- ✅ Coverage ≥ **90%** on domain assemblies; enforce gate in CI.

---

## 1. Architecture

- **Composition root** in `Program.cs` only.
- **Config** via `IOptions<T>` + `.ValidateDataAnnotations().ValidateOnStart()`.
- **Logging**: `ILogger<T>` + Serilog (JSON to stdout).
- **Observability**: OpenTelemetry (resource attrs: service.name, version, env) + X-Ray exporter.
- **Validation**: `FluentValidation` for DTOs; central ProblemDetails middleware.
- **Versioning**: `/v1/...`; breaking-change policy & deprecations.
- **Idempotency**: `Idempotency-Key` header pattern on writes.

---

## 2. HTTP & Resilience

- `HttpClientFactory` + **Polly v8**: timeouts, retry (exponential jitter), circuit breaker, bulkhead.
- Pass `CancellationToken` everywhere; async end-to-end; never `.Result`/`.Wait()`.
- Input/output compression where beneficial; response caching (`OutputCache` in .NET 8).

---

## 3. Data Access

- **Dapper**: parameterized queries only; command timeouts; prepared statements on hot paths.
- **DbUp**: transactional migrations, schema version table, checksum verification, exclusive lock to prevent concurrent runs.
- **MySqlConnector**: async calls, proper pooling; UTF8MB4; UTC only; strict SQL mode.

---

## 4. Testing

- **xUnit** + **AwesomeAssertions**; AAA; `Given_When_Should` names.
- **Reqnroll** for BDD specs.
- **WebApplicationFactory<T>** + **Testcontainers** (MySQL/Redis) for integration tests.
- **Stryker.NET** for mutation on domain assemblies.
- **PactNet** for consumer-driven contract tests (UI↔BFF, BFF↔API).
- Coverage gates with `coverlet.collector` (domain ≥ 90%).

---

## 5. Factories (instead of keyed services)

- Simple: inject `Func<T>`.
- Parameterized: `Func<TParam, TResult>` delegates.
- Strategy: `IFactory<Enum, IService>` returning concrete impls via explicit switch.
- Use `ActivatorUtilities.CreateInstance<T>` when you need DI + runtime args.

---

## 6. Serialization & Mapping

- **System.Text.Json** with source generators (`JsonSerializerContext`).
- Avoid Newtonsoft.Json in new code.
- **Mapster** for mapping (compile-time); avoid reflection-heavy AutoMapper.

---

## 7. Health & Readiness

- `/health/live` and `/health/ready` with dependency checks (DB, SQS, S3, downstream APIs).
- ECS healthchecks point to `/health/ready`.

---

## 8. Security

- Service-to-service auth via **IAM SigV4**.
- Secrets via SSM Parameter Store (SecureString); Secrets Manager only with auto-rotation (RDS admin).
- HTTPS-only; HSTS; security headers (`X-Content-Type-Options`, `Referrer-Policy`).
- PII redaction; audit logs for admin actions.
- Static analysis: `dotnet list package --vulnerable`, Trivy on containers.

---

## 9. Performance & Packaging

- Build: `dotnet publish -c Release -r linux-arm64 --self-contained false`.
- Consider **Native AOT** for workers/Lambda to shrink cold starts.
- Enable trimming (`PublishTrimmed`) where safe; annotate reflection needs (`DynamicallyAccessedMembers`).

---

## 10. Containers

- Multi-stage Dockerfile; run as non-root; read-only FS; `/app` workdir.
- Healthcheck to `/health/ready`.
- Minimal base images; prefer arm64 (Graviton).

---

## 11. Code Style & Analyzers

- `<Nullable>enable</Nullable>`, file-scoped namespaces, target-typed `new`, pattern matching, collection expressions.
- Roslyn + StyleCop analyzers; `.editorconfig` enforced; `dotnet format` in CI.
- SourceLink and deterministic builds; embed git hash as assembly info.

---

## 12. CI/CD Snippets

**Coverage and analyzers (Buildkite step sketch):**
```yaml
steps:
  - label: "lint+analyze"
    command: |
      dotnet restore
      dotnet build -warnaserror
      dotnet format --verify-no-changes
  - label: "tests"
    command: dotnet test --collect:"XPlat Code Coverage" /p:CollectCoverage=true /p:CoverletOutputFormat=cobertura /p:Threshold=90
```

---

## 13. Checklist

- [ ] DI everywhere; no keyed services
- [ ] TimeProvider injected; FakeTimeProvider in tests
- [ ] Dapper + DbUp + MySqlConnector
- [ ] Serilog JSON + OTEL tracing
- [ ] xUnit + AwesomeAssertions + Testcontainers
- [ ] PactNet contracts; Stryker.NET mutation
- [ ] System.Text.Json source-gen; Mapster
- [ ] Health endpoints, readiness checks
- [ ] IAM-auth S2S; SSM SecureString for secrets
- [ ] Coverage ≥ 90%; zero warnings
