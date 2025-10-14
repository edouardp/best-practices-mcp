# .NET Best Practices (8/9/10) — APIs, BFFs, Workers on AWS

> Defaults: ASP.NET Core Minimal APIs, **DI everywhere**, **interfaces for behavior, records for data**, **AwesomeAssertions** (never FluentAssertions), **Dapper + DbUp**, **MySqlConnector**, **Serilog + OTEL**, **Polly**, **xUnit**, **Reqnroll**, **Testcontainers**, **TimeProvider**, **no keyed services**.

---

## 0. Golden Rules

### Register everything via built-in DI; no service locators
**Why:** Service locators create hidden dependencies that make code harder to test and understand. The built-in DI container forces explicit dependency declaration, making your code more maintainable and testable. It also eliminates the need for additional dependencies and reduces complexity.

### No keyed services — use explicit interfaces and factories
**Why:** Keyed services create magic strings that can break at runtime and make dependencies unclear. Explicit interfaces and factories make your intent obvious, provide compile-time safety, and make it easier to understand what implementations are available. Factories also give you more control over object creation lifecycle.

### Records for pure data; interfaces for behaviors. Immutability by default
**Why:** Records provide value equality, immutability, and concise syntax for data transfer objects. Interfaces for behaviors enable testability through mocking and allow for multiple implementations. Immutability prevents accidental state changes that can cause bugs in concurrent scenarios.

### Replace DateTime.UtcNow with TimeProvider; test with FakeTimeProvider
**Why:** DateTime.UtcNow creates a hidden dependency on system time, making time-dependent code impossible to test reliably. TimeProvider allows you to control time in tests, making them deterministic and fast. This is crucial for testing timeouts, scheduling, and time-based business logic.

### Warnings-as-errors; analyzers on; zero warnings in CI
**Why:** Warnings often indicate potential bugs or code quality issues. Treating them as errors prevents technical debt accumulation and forces developers to address issues immediately. Analyzers catch common mistakes and enforce consistent coding standards across the team.

### REST-first, OpenAPI published; generate typed clients
**Why:** REST provides a well-understood, stateless communication pattern. OpenAPI documentation ensures your API is self-documenting and enables automatic client generation, reducing integration errors and development time. Typed clients provide compile-time safety and better developer experience.

### Coverage ≥ 90% on domain assemblies; enforce gate in CI
**Why:** High test coverage on domain logic ensures your core business rules are protected against regressions. Domain assemblies contain your most critical code, so they deserve the highest level of testing. CI gates prevent untested code from reaching production.

---

## 1. Architecture

### Composition root in Program.cs only
**Why:** Having a single composition root makes dependency registration predictable and prevents scattered service registrations throughout your codebase. This makes it easier to understand what services are available and how they're configured. It also prevents circular dependencies and makes startup behavior more predictable.

### Config via IOptions<T> + .ValidateDataAnnotations().ValidateOnStart()
**Why:** IOptions provides strongly-typed configuration with change notification support. Data annotations validation catches configuration errors at startup rather than at runtime, preventing production failures. ValidateOnStart ensures configuration is valid before your application starts accepting requests, following the "fail fast" principle.

### Logging: ILogger<T> + Serilog (JSON to stdout)
**Why:** ILogger<T> provides structured logging with category-based filtering and is the .NET standard. Serilog offers rich structured logging capabilities with excellent performance. JSON output to stdout integrates seamlessly with container orchestration platforms and log aggregation systems like CloudWatch or ELK stack.

### Observability: OpenTelemetry + X-Ray exporter
**Why:** OpenTelemetry is the industry standard for observability, providing vendor-neutral telemetry collection. X-Ray integration gives you distributed tracing across AWS services, helping you identify performance bottlenecks and understand request flows in microservice architectures.

### Validation: FluentValidation for DTOs; central ProblemDetails middleware
**Why:** FluentValidation provides expressive, testable validation rules that are easier to maintain than data annotations. Central ProblemDetails middleware ensures consistent error responses across your API, improving client integration and debugging experience.

### Versioning: /v1/...; breaking-change policy & deprecations
**Why:** URL-based versioning is simple and explicit, making it easy for clients to understand which version they're using. Having a clear breaking-change policy and deprecation strategy allows you to evolve your API without breaking existing clients.

### Idempotency: Idempotency-Key header pattern on writes
**Why:** Idempotency prevents duplicate operations when clients retry requests due to network issues or timeouts. This is crucial for financial transactions, order processing, and any operation that shouldn't be repeated. The header-based approach is simple and widely understood.

---

## 2. HTTP & Resilience

### HttpClientFactory + Polly v8: timeouts, retry, circuit breaker, bulkhead
**Why:** HttpClientFactory manages HttpClient lifecycle properly, preventing socket exhaustion and DNS issues. Polly provides battle-tested resilience patterns that handle transient failures gracefully. Timeouts prevent hanging requests, retries handle temporary failures, circuit breakers prevent cascading failures, and bulkheads isolate failures to specific resources.

### Pass CancellationToken everywhere; async end-to-end; never .Result/.Wait()
**Why:** CancellationTokens allow graceful cancellation of operations when clients disconnect or timeouts occur, preventing wasted resources. Async end-to-end prevents thread pool starvation and improves scalability. Blocking on async operations with .Result/.Wait() can cause deadlocks and reduces performance.

### Input/output compression; response caching (OutputCache in .NET 8)
**Why:** Compression reduces bandwidth usage and improves response times, especially important for mobile clients or high-latency connections. Response caching reduces server load and improves performance for frequently requested data. OutputCache in .NET 8 provides better performance and more features than previous caching solutions.

---

## 3. Data Access

### Dapper: parameterized queries only; command timeouts; prepared statements on hot paths
**Why:** Parameterized queries prevent SQL injection attacks, which are among the most common security vulnerabilities. Command timeouts prevent long-running queries from blocking resources indefinitely. Prepared statements on hot paths improve performance by allowing the database to cache query execution plans.

### DbUp: transactional migrations, schema version table, checksum verification, exclusive lock
**Why:** Transactional migrations ensure database schema changes are atomic - they either complete fully or roll back completely. Schema version tracking prevents applying migrations out of order or multiple times. Checksum verification detects if migration scripts have been modified after deployment. Exclusive locks prevent concurrent migration runs that could corrupt the database.

### MySqlConnector: async calls, proper pooling; UTF8MB4; UTC only; strict SQL mode
**Why:** Async calls prevent thread blocking and improve scalability. Connection pooling reduces the overhead of creating new database connections. UTF8MB4 supports full Unicode including emojis and special characters. UTC-only timestamps prevent timezone-related bugs. Strict SQL mode catches data truncation and other issues that could lead to data corruption.

---

## 4. Testing

### xUnit + AwesomeAssertions; AAA; Given_When_Should names
**Why:** xUnit is the most popular .NET testing framework with excellent performance and extensibility. AwesomeAssertions provides more readable and informative assertion failures compared to FluentAssertions. AAA (Arrange, Act, Assert) structure makes tests easier to understand and maintain. Given_When_Should naming clearly communicates test scenarios and expected outcomes.

### Reqnroll for BDD specs
**Why:** Reqnroll (successor to SpecFlow) enables behavior-driven development by allowing you to write tests in natural language that stakeholders can understand. This bridges the gap between business requirements and technical implementation, ensuring you're building the right features.

### WebApplicationFactory<T> + Testcontainers for integration tests
**Why:** WebApplicationFactory provides an in-memory test server that closely mimics your production environment without external dependencies. Testcontainers spin up real database and service instances in Docker, ensuring your integration tests run against the same technology stack as production, catching integration issues that mocks might miss.

### Stryker.NET for mutation testing on domain assemblies
**Why:** Mutation testing validates the quality of your tests by introducing small changes (mutations) to your code and checking if tests catch them. This ensures your tests actually verify the behavior they claim to test, not just achieve code coverage through execution.

### PactNet for consumer-driven contract tests
**Why:** Contract tests ensure that service interfaces remain compatible as they evolve independently. Consumer-driven contracts put the consumer in control of what they need, preventing breaking changes and enabling confident independent deployments in microservice architectures.

### Coverage gates with coverlet.collector (domain ≥ 90%)
**Why:** Code coverage metrics help identify untested code paths. Domain assemblies contain your core business logic and deserve the highest coverage standards. Automated gates prevent coverage regression and ensure new code is properly tested.

---

## 5. Factories (instead of keyed services)

### Simple: inject Func<T>
**Why:** Func<T> delegates provide a clean way to defer object creation until needed, which is useful for expensive objects or when you need multiple instances. This is simpler and more explicit than keyed services while maintaining compile-time safety.

### Parameterized: Func<TParam, TResult> delegates
**Why:** When you need to create objects with runtime parameters, parameterized delegates make the dependency explicit and testable. This is cleaner than passing parameters through the DI container and provides better type safety.

### Strategy: IFactory<Enum, IService> returning concrete implementations
**Why:** Factory patterns with explicit enums make it clear what implementations are available and provide compile-time safety. Using explicit switch statements instead of keyed services makes the mapping obvious and prevents runtime errors from typos in magic strings.

### Use ActivatorUtilities.CreateInstance<T> for DI + runtime args
**Why:** When you need both dependency injection and runtime parameters, ActivatorUtilities provides a clean way to create instances that satisfy both needs. This is more explicit and testable than complex factory patterns or service locators.

---

## 6. Serialization & Mapping

### System.Text.Json with source generators (JsonSerializerContext)
**Why:** System.Text.Json is faster and more memory-efficient than Newtonsoft.Json, and it's the .NET standard. Source generators provide compile-time serialization code generation, eliminating reflection overhead and enabling trimming/AOT scenarios. This results in better performance and smaller deployment sizes.

### Avoid Newtonsoft.Json in new code
**Why:** Newtonsoft.Json is slower, uses more memory, and relies heavily on reflection. System.Text.Json is actively developed by Microsoft and integrates better with modern .NET features like trimming and AOT compilation.

### Mapster for mapping (compile-time); avoid reflection-heavy AutoMapper
**Why:** Mapster generates mapping code at compile-time, providing better performance than reflection-based solutions like AutoMapper. Compile-time generation also enables better debugging and works with trimming/AOT scenarios. The generated code is easier to understand and optimize.

---

## 7. Health & Readiness

### /health/live and /health/ready with dependency checks
**Why:** Separate liveness and readiness probes allow orchestrators to make better decisions about your application. Liveness checks determine if the application should be restarted, while readiness checks determine if it should receive traffic. Dependency checks ensure your service only reports as ready when it can actually fulfill requests.

### ECS healthchecks point to /health/ready
**Why:** Using readiness checks for load balancer health ensures traffic is only routed to instances that can actually process requests. This prevents cascading failures when dependencies are unavailable and provides better user experience during deployments or scaling events.

---

## 8. Security

### Service-to-service auth via IAM SigV4
**Why:** IAM SigV4 provides strong authentication without managing shared secrets or certificates. It integrates seamlessly with AWS services and provides fine-grained access control. The signatures are time-limited and prevent replay attacks, making it more secure than API keys or basic authentication.

### Secrets via SSM Parameter Store (SecureString); Secrets Manager for auto-rotation
**Why:** SSM Parameter Store provides encrypted storage for configuration values at no additional cost for standard parameters. SecureString parameters are encrypted with KMS keys you control. Secrets Manager is used only when you need automatic rotation (like RDS passwords) because it costs more but provides additional rotation capabilities.

### HTTPS-only; HSTS; security headers
**Why:** HTTPS encrypts data in transit, preventing eavesdropping and man-in-the-middle attacks. HSTS prevents protocol downgrade attacks by forcing browsers to use HTTPS. Security headers like X-Content-Type-Options prevent MIME-type confusion attacks, and Referrer-Policy controls what information is sent to external sites.

### PII redaction; audit logs for admin actions
**Why:** PII redaction prevents sensitive data from appearing in logs, reducing compliance risks and potential data breaches. Audit logs for admin actions provide accountability and help with compliance requirements like SOX or GDPR. They also help with incident response and forensic analysis.

### Static analysis: dotnet list package --vulnerable, Trivy on containers
**Why:** Automated vulnerability scanning catches known security issues in dependencies before they reach production. Regular scanning of both NuGet packages and container images helps maintain security posture and enables quick response to newly discovered vulnerabilities.

---

## 9. Performance & Packaging

### Build: dotnet publish -c Release -r linux-arm64 --self-contained false
**Why:** Release configuration enables optimizations and removes debug symbols, reducing size and improving performance. ARM64 targeting takes advantage of AWS Graviton processors which offer better price-performance. Framework-dependent deployment reduces image size and startup time compared to self-contained deployments when the runtime is available in the base image.

### Consider Native AOT for workers/Lambda to shrink cold starts
**Why:** Native AOT compilation produces native machine code that starts faster and uses less memory than JIT-compiled code. This is especially beneficial for Lambda functions and short-lived workers where cold start time significantly impacts user experience. The trade-off is larger deployment size and some runtime limitations.

### Enable trimming (PublishTrimmed); annotate reflection needs
**Why:** Trimming removes unused code from the final deployment, significantly reducing application size. This improves deployment speed and reduces memory usage. Proper annotation of reflection usage ensures trimming doesn't remove code that's needed at runtime, maintaining application correctness while achieving size benefits.

---

## 10. Containers

### Multi-stage Dockerfile; run as non-root; read-only FS; /app workdir
**Why:** Multi-stage builds separate build dependencies from runtime dependencies, creating smaller, more secure final images. Running as non-root follows the principle of least privilege and prevents many attack vectors. Read-only filesystems prevent runtime modifications that could indicate compromise. Consistent workdir simplifies deployment and debugging.

### Healthcheck to /health/ready
**Why:** Container healthchecks allow orchestrators to automatically restart unhealthy containers and route traffic appropriately. Using the readiness endpoint ensures containers are marked healthy only when they can actually serve requests, improving overall system reliability.

### Minimal base images; prefer arm64 (Graviton)
**Why:** Minimal base images reduce attack surface, deployment size, and startup time by including only essential components. ARM64 images take advantage of AWS Graviton processors which offer 20-40% better price-performance compared to x86 instances, reducing infrastructure costs.

---

## 11. Code Style & Analyzers

### Nullable reference types, file-scoped namespaces, modern C# features
**Why:** Nullable reference types catch null reference exceptions at compile-time, preventing one of the most common runtime errors. File-scoped namespaces reduce indentation and improve readability. Modern C# features like target-typed new, pattern matching, and collection expressions make code more concise and expressive while maintaining readability.

### Roslyn + StyleCop analyzers; .editorconfig enforced; dotnet format in CI
**Why:** Static analysis catches potential bugs, security issues, and style violations before code review. Consistent code formatting reduces cognitive load and makes code reviews focus on logic rather than style. Automated formatting in CI ensures consistency across the team and prevents style-related merge conflicts.

### SourceLink and deterministic builds; embed git hash as assembly info
**Why:** SourceLink enables debugging into NuGet packages and provides better stack traces in production. Deterministic builds ensure identical inputs produce identical outputs, enabling reliable caching and security verification. Git hash embedding helps correlate deployed code with source control, crucial for incident response and auditing.

---

## 12. CI/CD Snippets

**Why these specific steps matter:**

### Lint and analyze step
**Why:** Running linting and analysis before tests catches style and potential logic issues early, preventing wasted time on test runs that would fail anyway. The -warnaserror flag ensures warnings don't accumulate as technical debt. Format verification prevents inconsistent code style from entering the main branch.

### Test step with coverage enforcement
**Why:** Collecting coverage during test runs provides immediate feedback on test completeness. The threshold enforcement prevents coverage regression and ensures new code is properly tested. Cobertura format enables integration with various reporting tools and CI systems.

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

**Why this checklist matters:** This checklist serves as a final verification that all critical practices are implemented. Each item represents a decision that significantly impacts code quality, maintainability, security, or performance. Regular checklist reviews during code reviews and before releases help ensure consistency across projects and prevent regression of important practices.

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
