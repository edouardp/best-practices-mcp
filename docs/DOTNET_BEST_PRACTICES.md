# .NET Best Practices (8/9/10) — APIs, BFFs, Workers on AWS

> Defaults: ASP.NET Core Minimal APIs, **DI everywhere**, **interfaces for
> behavior, records for data**, **AwesomeAssertions** (never FluentAssertions),
> **Dapper + DbUp**, **MySqlConnector**, **Serilog + OTEL**, **Polly**,
> **xUnit**, **Reqnroll**, **Testcontainers**, **TimeProvider**, **no keyed
> services**.

---

## 0. Golden Rules

### Register everything via built-in DI; no service locators

**Why:** Service locators create hidden dependencies that make code harder to
test and understand. The built-in DI container forces explicit dependency
declaration, making your code more maintainable and testable. It also eliminates
the need for additional dependencies and reduces complexity.

```csharp
// ❌ Bad - Service locator pattern
public class OrderService
{
    public void ProcessOrder(Order order)
    {
        var emailService = ServiceLocator.Get<IEmailService>(); // Hidden dependency
        var paymentService = ServiceLocator.Get<IPaymentService>();
    }
}

// ✅ Good - Explicit dependencies via constructor injection
public class OrderService
{
    private readonly IEmailService _emailService;
    private readonly IPaymentService _paymentService;

    public OrderService(IEmailService emailService, IPaymentService paymentService)
    {
        _emailService = emailService;
        _paymentService = paymentService;
    }
}
```

### No keyed services — use explicit interfaces and factories

**Why:** Keyed services create magic strings that can break at runtime and make
dependencies unclear. Explicit interfaces and factories make your intent
obvious, provide compile-time safety, and make it easier to understand what
implementations are available. Factories also give you more control over object
creation lifecycle.

```csharp
// ❌ Bad - Keyed services with magic strings
services.AddKeyedScoped<INotificationService, EmailNotificationService>("email");
services.AddKeyedScoped<INotificationService, SmsNotificationService>("sms");

public class OrderService([FromKeyedServices("email")] INotificationService emailService) { }

// ✅ Good - Explicit interfaces and factory
public interface INotificationServiceFactory
{
    INotificationService Create(NotificationType type);
}

public class NotificationServiceFactory : INotificationServiceFactory
{
    public INotificationService Create(NotificationType type) => type switch
    {
        NotificationType.Email => new EmailNotificationService(),
        NotificationType.Sms => new SmsNotificationService(),
        _ => throw new ArgumentException($"Unknown notification type: {type}")
    };
}
```

### Records for pure data; interfaces for behaviors. Immutability by default

**Why:** Records provide value equality, immutability, and concise syntax for
data transfer objects. Use records instead of classes when you only need
properties without behavior. Interfaces for behaviors enable testability through
mocking and allow for multiple implementations. Immutability prevents accidental
state changes that can cause bugs in concurrent scenarios.

```csharp
// ❌ Bad - Class for pure data
public class OrderRequest
{
    public string CustomerId { get; set; }
    public decimal Amount { get; set; }
    public List<string> Items { get; set; }
}

// ✅ Good - Record for pure data
public record OrderRequest(
    string CustomerId,
    decimal Amount,
    IReadOnlyList<string> Items
);

// ✅ Good - Interface for behavior
public interface IOrderService
{
    Task<Order> CreateOrderAsync(OrderRequest request);
}
```

### Replace DateTime.UtcNow with TimeProvider; test with FakeTimeProvider

**Why:** DateTime.UtcNow creates a hidden dependency on system time, making
time-dependent code impossible to test reliably. TimeProvider allows you to
control time in tests, making them deterministic and fast. This is crucial for
testing timeouts, scheduling, and time-based business logic.

```csharp
// ❌ Bad - Direct DateTime usage
public class OrderService
{
    public Order CreateOrder(OrderRequest request)
    {
        return new Order
        {
            CreatedAt = DateTime.UtcNow, // Hard to test
            ExpiresAt = DateTime.UtcNow.AddHours(24)
        };
    }
}

// ✅ Good - TimeProvider injection
public class OrderService
{
    private readonly TimeProvider _timeProvider;

    public OrderService(TimeProvider timeProvider)
    {
        _timeProvider = timeProvider;
    }

    public Order CreateOrder(OrderRequest request)
    {
        var now = _timeProvider.GetUtcNow();
        return new Order
        {
            CreatedAt = now,
            ExpiresAt = now.AddHours(24)
        };
    }
}

// Test with FakeTimeProvider
[Test]
public void CreateOrder_SetsCorrectTimestamps()
{
    var fakeTime = new DateTimeOffset(2024, 1, 1, 12, 0, 0, TimeSpan.Zero);
    var timeProvider = new FakeTimeProvider(fakeTime);
    var service = new OrderService(timeProvider);

    var order = service.CreateOrder(new OrderRequest());

    order.CreatedAt.Should().Be(fakeTime);
    order.ExpiresAt.Should().Be(fakeTime.AddHours(24));
}
```

### Warnings-as-errors; analyzers on; zero warnings in CI

**Why:** Warnings often indicate potential bugs or code quality issues. Treating
them as errors prevents technical debt accumulation and forces developers to
address issues immediately. Analyzers catch common mistakes and enforce
consistent coding standards across the team.

### REST-first, OpenAPI published; generate typed clients

**Why:** REST provides a well-understood, stateless communication pattern.
OpenAPI documentation ensures your API is self-documenting and enables automatic
client generation, reducing integration errors and development time. Typed
clients provide compile-time safety and better developer experience.

### Coverage ≥ 90% on domain assemblies; enforce gate in CI

**Why:** High test coverage on domain logic ensures your core business rules are
protected against regressions. Domain assemblies contain your most critical
code, so they deserve the highest level of testing. CI gates prevent untested
code from reaching production.

---

## 1. Architecture

### Composition root in Program.cs only

**Why:** Having a single composition root makes dependency registration
predictable and prevents scattered service registrations throughout your
codebase. This makes it easier to understand what services are available and how
they're configured. It also prevents circular dependencies and makes startup
behavior more predictable.

### Config via IOptions<T> + .ValidateDataAnnotations().ValidateOnStart()

**Why:** IOptions provides strongly-typed configuration with change notification
support. Data annotations validation catches configuration errors at startup
rather than at runtime, preventing production failures. ValidateOnStart ensures
configuration is valid before your application starts accepting requests,
following the "fail fast" principle.

```csharp
// Configuration class with validation
public class DatabaseOptions
{
    [Required]
    [MinLength(1)]
    public string ConnectionString { get; set; } = string.Empty;

    [Range(1, 300)]
    public int CommandTimeoutSeconds { get; set; } = 30;

    [Range(1, 100)]
    public int MaxPoolSize { get; set; } = 10;
}

// Registration in Program.cs
builder.Services.Configure<DatabaseOptions>(builder.Configuration.GetSection("Database"));
builder.Services.AddOptions<DatabaseOptions>()
    .ValidateDataAnnotations()
    .ValidateOnStart();

// Usage in service
public class OrderRepository
{
    private readonly DatabaseOptions _options;

    public OrderRepository(IOptions<DatabaseOptions> options)
    {
        _options = options.Value;
    }

    public async Task<Order> GetOrderAsync(int id)
    {
        using var connection = new MySqlConnection(_options.ConnectionString);
        // Use _options.CommandTimeoutSeconds, etc.
    }
}
```

### Logging: ILogger<T> + Serilog (JSON to stdout)

**Why:** ILogger<T> provides structured logging with category-based filtering
and is the .NET standard. Serilog offers rich structured logging capabilities
with excellent performance. JSON output to stdout integrates seamlessly with
container orchestration platforms and log aggregation systems like CloudWatch or
ELK stack.

**Context Logging is Critical:** Adding context into the call stack (or
equivalent in async code) is essential for producing meaningful logs. When a
line is logged, we should see the context (what operation, which user, what
request) as structured properties, not just the log message.

```csharp
// Program.cs - Serilog configuration with enrichers
using Serilog;
using Serilog.Enrichers.Span;
using Serilog.Exceptions;

Log.Logger = new LoggerConfiguration()
    .MinimumLevel.Information()
    .MinimumLevel.Override("Microsoft", LogEventLevel.Warning)
    .MinimumLevel.Override("System", LogEventLevel.Warning)
    .Enrich.FromLogContext()  // Critical for context logging
    .Enrich.WithEnvironmentName()
    .Enrich.WithMachineName()
    .Enrich.WithProcessId()
    .Enrich.WithThreadId()
    .Enrich.WithSpan()  // OpenTelemetry integration
    .Enrich.WithExceptionDetails()  // Rich exception logging
    .Enrich.With<CorrelationIdEnricher>()  // Custom enricher
    .WriteTo.Console(new JsonFormatter())
    .CreateLogger();

var builder = WebApplication.CreateBuilder(args);
builder.Host.UseSerilog();

// Custom enricher for correlation IDs
public class CorrelationIdEnricher : ILogEventEnricher
{
    public void Enrich(LogEvent logEvent, ILogEventPropertyFactory propertyFactory)
    {
        var correlationId = Activity.Current?.Id ??
                           Thread.CurrentThread.ManagedThreadId.ToString();

        logEvent.AddPropertyIfAbsent(propertyFactory.CreateProperty(
            "CorrelationId", correlationId));

        // Add user context if available
        if (logEvent.Properties.TryGetValue("UserId", out var userId))
        {
            logEvent.AddPropertyIfAbsent(propertyFactory.CreateProperty(
                "UserContext", $"User:{userId}"));
        }
    }
}

// Service implementation with context logging
public class OrderService
{
    private readonly ILogger<OrderService> _logger;

    public OrderService(ILogger<OrderService> logger)
    {
        _logger = logger;
    }

    public async Task<Order> ProcessOrderAsync(CreateOrderRequest request, string userId)
    {
        // Push context onto the log context stack
        using var context = LogContext.PushProperty("UserId", userId)
            .PushProperty("OrderAmount", request.Amount)
            .PushProperty("Operation", "ProcessOrder")
            .PushProperty("RequestId", Guid.NewGuid());

        _logger.LogInformation("Starting order processing for user {UserId} with amount {Amount:C}",
            userId, request.Amount);

        try
        {
            // Validate order
            await ValidateOrderAsync(request);

            // Process payment
            var paymentResult = await ProcessPaymentAsync(request);
            using var paymentContext = LogContext.PushProperty("PaymentId", paymentResult.Id);

            _logger.LogInformation("Payment processed successfully with ID {PaymentId}",
                paymentResult.Id);

            // Create order
            var order = await CreateOrderAsync(request, paymentResult);

            _logger.LogInformation("Order {OrderId} created successfully", order.Id);

            return order;
        }
        catch (ValidationException ex)
        {
            // Exception enricher will automatically add exception details
            _logger.LogWarning(ex, "Order validation failed for user {UserId}", userId);
            throw;
        }
        catch (PaymentException ex)
        {
            _logger.LogError(ex, "Payment processing failed for user {UserId}", userId);
            throw;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Unexpected error processing order for user {UserId}", userId);
            throw;
        }
    }

    private async Task ValidateOrderAsync(CreateOrderRequest request)
    {
        using var context = LogContext.PushProperty("ValidationStep", "OrderValidation");

        _logger.LogDebug("Validating order with {ItemCount} items", request.Items.Count);

        if (request.Items.Count == 0)
        {
            _logger.LogWarning("Order validation failed: No items in order");
            throw new ValidationException("Order must contain at least one item");
        }

        _logger.LogDebug("Order validation completed successfully");
    }
}

// Middleware for request context
public class RequestContextMiddleware
{
    private readonly RequestDelegate _next;
    private readonly ILogger<RequestContextMiddleware> _logger;

    public RequestContextMiddleware(RequestDelegate next, ILogger<RequestContextMiddleware> logger)
    {
        _next = next;
        _logger = logger;
    }

    public async Task InvokeAsync(HttpContext context)
    {
        var requestId = context.Request.Headers["X-Request-ID"].FirstOrDefault()
                       ?? Guid.NewGuid().ToString();

        // Add request context to all logs in this request
        using var logContext = LogContext.PushProperty("RequestId", requestId)
            .PushProperty("RequestPath", context.Request.Path)
            .PushProperty("RequestMethod", context.Request.Method)
            .PushProperty("UserAgent", context.Request.Headers["User-Agent"].FirstOrDefault());

        // Add to response headers for tracing
        context.Response.Headers.Add("X-Request-ID", requestId);

        var stopwatch = Stopwatch.StartNew();

        try
        {
            await _next(context);

            _logger.LogInformation("Request completed in {ElapsedMs}ms with status {StatusCode}",
                stopwatch.ElapsedMilliseconds, context.Response.StatusCode);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Request failed after {ElapsedMs}ms",
                stopwatch.ElapsedMilliseconds);
            throw;
        }
    }
}

// Extension methods for common logging patterns
public static class LoggerExtensions
{
    public static IDisposable BeginScope<T>(this ILogger<T> logger, string operation, object parameters = null)
    {
        var properties = new Dictionary<string, object>
        {
            ["Operation"] = operation,
            ["OperationId"] = Guid.NewGuid()
        };

        if (parameters != null)
        {
            foreach (var prop in parameters.GetType().GetProperties())
            {
                properties[prop.Name] = prop.GetValue(parameters);
            }
        }

        return logger.BeginScope(properties);
    }

    public static void LogBusinessEvent<T>(this ILogger<T> logger, string eventName, object eventData)
    {
        using var context = LogContext.PushProperty("EventType", "Business")
            .PushProperty("EventName", eventName);

        logger.LogInformation("Business event: {EventName} with data {@EventData}",
            eventName, eventData);
    }
}

// Usage in controllers
[ApiController]
[Route("api/[controller]")]
public class OrdersController : ControllerBase
{
    private readonly ILogger<OrdersController> _logger;
    private readonly OrderService _orderService;

    public OrdersController(ILogger<OrdersController> logger, OrderService orderService)
    {
        _logger = logger;
        _orderService = orderService;
    }

    [HttpPost]
    public async Task<IActionResult> CreateOrder([FromBody] CreateOrderRequest request)
    {
        var userId = User.FindFirst(ClaimTypes.NameIdentifier)?.Value;

        using var scope = _logger.BeginScope("CreateOrder", new { UserId = userId, Amount = request.Amount });

        try
        {
            var order = await _orderService.ProcessOrderAsync(request, userId);

            _logger.LogBusinessEvent("OrderCreated", new { OrderId = order.Id, Amount = order.Amount });

            return CreatedAtAction(nameof(GetOrder), new { id = order.Id }, order);
        }
        catch (ValidationException ex)
        {
            return BadRequest(new { Error = ex.Message });
        }
        catch (PaymentException ex)
        {
            return UnprocessableEntity(new { Error = "Payment processing failed" });
        }
    }
}
```

**Key Enricher Benefits:**

- **FromLogContext()**: Enables context properties to flow through the call
  stack
- **WithExceptionDetails()**: Provides rich exception information including
  inner exceptions, stack traces, and custom properties
- **WithSpan()**: Integrates with OpenTelemetry for distributed tracing
  correlation
- **Custom Enrichers**: Add application-specific context like correlation IDs,
  user information, or business context

**Context Logging Best Practices:**

- Use `LogContext.PushProperty()` to add context that flows through the entire
  operation
- Implement request middleware to add request-level context
- Use structured logging with named parameters, not string interpolation
- Add business context (user ID, operation type, entity IDs) to make logs
  searchable
- Use scopes for operations that span multiple method calls

### Startup Logging: Log configuration, health checks, and critical initialization

**Why:** Startup logging helps diagnose deployment issues, configuration problems, and service dependencies. Logging configuration values (sanitized), health check results, and initialization timing helps operations teams quickly identify why services fail to start or perform poorly after deployment.

```csharp
// Program.cs - Startup logging with configuration validation
var builder = WebApplication.CreateBuilder(args);

// Configure Serilog early for startup logging
Log.Logger = new LoggerConfiguration()
    .MinimumLevel.Information()
    .WriteTo.Console(new JsonFormatter())
    .CreateLogger();

try
{
    Log.Information("Starting application {ApplicationName} v{Version}",
        builder.Environment.ApplicationName,
        Assembly.GetExecutingAssembly().GetName().Version);

    // Log environment and configuration (sanitized)
    Log.Information("Environment: {Environment}, Machine: {MachineName}",
        builder.Environment.EnvironmentName,
        Environment.MachineName);

    // Validate critical configuration early
    var connectionString = builder.Configuration.GetConnectionString("DefaultConnection");
    if (string.IsNullOrEmpty(connectionString))
    {
        Log.Fatal("Database connection string is missing or empty");
        throw new InvalidOperationException("Database connection string is required");
    }

    Log.Information("Configuration loaded successfully. Database: {DatabaseHost}",
        ExtractHostFromConnectionString(connectionString));

    // Configure services with timing
    var serviceConfigStart = Stopwatch.StartNew();
    
    builder.Services.AddHealthChecks()
        .AddMySql(connectionString, name: "database")
        .AddCheck<CustomHealthCheck>("custom-check");
    
    // Add other services...
    
    Log.Information("Service configuration completed in {ElapsedMs}ms",
        serviceConfigStart.ElapsedMilliseconds);

    var app = builder.Build();

    // Test critical dependencies at startup
    await ValidateStartupDependencies(app.Services);

    // Configure middleware with logging
    app.UseMiddleware<RequestContextMiddleware>();
    
    // Configure health checks with startup validation
    app.MapHealthChecks("/health/live", new HealthCheckOptions
    {
        Predicate = check => check.Name == "self"
    });
    
    app.MapHealthChecks("/health/ready", new HealthCheckOptions
    {
        Predicate = _ => true,
        ResponseWriter = async (context, report) =>
        {
            Log.Information("Health check executed. Status: {Status}, Duration: {Duration}ms, Checks: {@CheckResults}",
                report.Status, report.TotalDuration.TotalMilliseconds,
                report.Entries.ToDictionary(e => e.Key, e => new { Status = e.Value.Status.ToString(), Duration = e.Value.Duration.TotalMilliseconds }));
            
            await context.Response.WriteAsync(JsonSerializer.Serialize(new
            {
                Status = report.Status.ToString(),
                Checks = report.Entries.Select(e => new
                {
                    Name = e.Key,
                    Status = e.Value.Status.ToString(),
                    Duration = e.Value.Duration.TotalMilliseconds,
                    Description = e.Value.Description
                })
            }));
        }
    });

    // Validate health checks at startup
    await ValidateHealthChecksAtStartup(app.Services);

    Log.Information("Application startup completed successfully in {ElapsedMs}ms",
        Environment.TickCount);

    await app.RunAsync();
}
catch (Exception ex)
{
    Log.Fatal(ex, "Application startup failed");
    throw;
}
finally
{
    Log.CloseAndFlush();
}

// Startup dependency validation
static async Task ValidateStartupDependencies(IServiceProvider services)
{
    using var scope = services.CreateScope();
    var logger = scope.ServiceProvider.GetRequiredService<ILogger<Program>>();

    try
    {
        // Test database connectivity
        var dbContext = scope.ServiceProvider.GetRequiredService<ApplicationDbContext>();
        var canConnect = await dbContext.Database.CanConnectAsync();
        
        if (canConnect)
        {
            logger.LogInformation("Database connectivity verified successfully");
        }
        else
        {
            logger.LogError("Database connectivity check failed");
            throw new InvalidOperationException("Cannot connect to database");
        }

        // Test external service dependencies
        var httpClient = scope.ServiceProvider.GetRequiredService<HttpClient>();
        var externalApiUrl = scope.ServiceProvider.GetRequiredService<IConfiguration>()
            .GetValue<string>("ExternalApi:BaseUrl");

        if (!string.IsNullOrEmpty(externalApiUrl))
        {
            var response = await httpClient.GetAsync($"{externalApiUrl}/health");
            if (response.IsSuccessStatusCode)
            {
                logger.LogInformation("External API connectivity verified: {ApiUrl}", externalApiUrl);
            }
            else
            {
                logger.LogWarning("External API health check failed: {ApiUrl}, Status: {StatusCode}",
                    externalApiUrl, response.StatusCode);
            }
        }
    }
    catch (Exception ex)
    {
        logger.LogError(ex, "Startup dependency validation failed");
        throw;
    }
}

// Helper method to safely extract host from connection string
static string ExtractHostFromConnectionString(string connectionString)
{
    try
    {
        var builder = new MySqlConnectionStringBuilder(connectionString);
        return $"{builder.Server}:{builder.Port}";
    }
    catch
    {
        return "[connection string parsing failed]";
    }
}

// Validate health checks at startup
static async Task ValidateHealthChecksAtStartup(IServiceProvider services)
{
    using var scope = services.CreateScope();
    var healthCheckService = scope.ServiceProvider.GetRequiredService<HealthCheckService>();
    var logger = scope.ServiceProvider.GetRequiredService<ILogger<Program>>();

    try
    {
        logger.LogInformation("Running startup health check validation");
        var result = await healthCheckService.CheckHealthAsync();
        
        foreach (var check in result.Entries)
        {
            if (check.Value.Status == HealthStatus.Healthy)
            {
                logger.LogInformation("Health check '{CheckName}' passed in {Duration}ms",
                    check.Key, check.Value.Duration.TotalMilliseconds);
            }
            else
            {
                logger.LogWarning("Health check '{CheckName}' failed: {Status} - {Description}",
                    check.Key, check.Value.Status, check.Value.Description);
            }
        }

        if (result.Status != HealthStatus.Healthy)
        {
            logger.LogWarning("Some health checks failed at startup, but continuing (checks will be retried)");
        }
        else
        {
            logger.LogInformation("All health checks passed at startup");
        }
    }
    catch (Exception ex)
    {
        logger.LogError(ex, "Health check validation failed at startup");
        // Don't fail startup for health check issues - let the app start and retry
    }
}

// Custom health check example
public class CustomHealthCheck : IHealthCheck
{
    private readonly ILogger<CustomHealthCheck> _logger;

    public CustomHealthCheck(ILogger<CustomHealthCheck> logger)
    {
        _logger = logger;
    }

    public async Task<HealthCheckResult> CheckHealthAsync(
        HealthCheckContext context, 
        CancellationToken cancellationToken = default)
    {
        try
        {
            // Perform custom health check logic
            await Task.Delay(10, cancellationToken); // Simulate check
            
            _logger.LogDebug("Custom health check passed");
            return HealthCheckResult.Healthy("Custom check passed");
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Custom health check failed");
            return HealthCheckResult.Unhealthy("Custom check failed", ex);
        }
    }
}
```

**ASP.NET Core Startup Logging Best Practices:**

- **Log early**: Configure logging before any other services to capture startup issues
- **Sanitize secrets**: Never log connection strings, API keys, or sensitive configuration
- **Time operations**: Log how long service configuration and startup takes
- **Validate dependencies**: Test database and external service connectivity at startup
- **Structured health checks**: Use detailed health check responses with timing information
- **Fail fast**: Log fatal errors and exit immediately if critical dependencies are unavailable
- **Environment context**: Always log environment name, version, and machine information

### Observability: OpenTelemetry + X-Ray exporter

**Why:** OpenTelemetry is the industry standard for observability, providing
vendor-neutral telemetry collection. X-Ray integration gives you distributed
tracing across AWS services, helping you identify performance bottlenecks and
understand request flows in microservice architectures.

### Validation: FluentValidation for DTOs; central ProblemDetails middleware

**Why:** FluentValidation provides expressive, testable validation rules that
are easier to maintain than data annotations. Central ProblemDetails middleware
ensures consistent error responses across your API, improving client integration
and debugging experience.

### Versioning: /v1/...; breaking-change policy & deprecations

**Why:** URL-based versioning is simple and explicit, making it easy for clients
to understand which version they're using. Having a clear breaking-change policy
and deprecation strategy allows you to evolve your API without breaking existing
clients.

### Idempotency: Idempotency-Key header pattern on writes

**Why:** Idempotency prevents duplicate operations when clients retry requests
due to network issues or timeouts. This is crucial for financial transactions,
order processing, and any operation that shouldn't be repeated. The header-based
approach is simple and widely understood.

---

## 2. HTTP & Resilience

### HttpClientFactory + Polly v8: timeouts, retry, circuit breaker, bulkhead

**Why:** HttpClientFactory manages HttpClient lifecycle properly, preventing
socket exhaustion and DNS issues. Polly provides battle-tested resilience
patterns that handle transient failures gracefully. Timeouts prevent hanging
requests, retries handle temporary failures, circuit breakers prevent cascading
failures, and bulkheads isolate failures to specific resources.

```csharp
// Registration in Program.cs
builder.Services.AddHttpClient<PaymentApiClient>(client =>
{
    client.BaseAddress = new Uri("https://api.payment-provider.com");
    client.Timeout = TimeSpan.FromSeconds(30);
})
.AddResilienceHandler("payment-api", builder =>
{
    builder
        .AddTimeout(TimeSpan.FromSeconds(10))
        .AddRetry(new RetryStrategyOptions
        {
            MaxRetryAttempts = 3,
            BackoffType = DelayBackoffType.Exponential,
            UseJitter = true
        })
        .AddCircuitBreaker(new CircuitBreakerStrategyOptions
        {
            FailureRatio = 0.5,
            SamplingDuration = TimeSpan.FromSeconds(30),
            MinimumThroughput = 10,
            BreakDuration = TimeSpan.FromSeconds(30)
        });
});

// Usage in service
public class PaymentApiClient
{
    private readonly HttpClient _httpClient;

    public PaymentApiClient(HttpClient httpClient)
    {
        _httpClient = httpClient;
    }

    public async Task<PaymentResult> ProcessPaymentAsync(PaymentRequest request, CancellationToken cancellationToken)
    {
        var response = await _httpClient.PostAsJsonAsync("/payments", request, cancellationToken);
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadFromJsonAsync<PaymentResult>(cancellationToken);
    }
}
```

### Pass CancellationToken everywhere; async end-to-end; never .Result/.Wait()

**Why:** CancellationTokens allow graceful cancellation of operations when
clients disconnect or timeouts occur, preventing wasted resources. Async
end-to-end prevents thread pool starvation and improves scalability. Blocking on
async operations with .Result/.Wait() can cause deadlocks and reduces
performance.

### Use concurrent collections for thread-safe shared state

**Why:** Concurrent collections provide thread-safe operations without explicit locking, reducing the risk of deadlocks and improving performance in multi-threaded scenarios. They're optimized for concurrent access patterns.

```csharp
// ❌ Bad - Regular collections with manual locking
public class CacheService
{
    private readonly Dictionary<string, object> _cache = new();
    private readonly object _lock = new();

    public void Set(string key, object value)
    {
        lock (_lock)
        {
            _cache[key] = value; // Risk of deadlocks, poor performance
        }
    }
}

// ✅ Good - Concurrent collections
public class CacheService
{
    private readonly ConcurrentDictionary<string, object> _cache = new();
    private readonly ConcurrentQueue<string> _recentKeys = new();

    public void Set(string key, object value)
    {
        _cache.TryAdd(key, value);
        _recentKeys.Enqueue(key);
    }

    public bool TryGet(string key, out object value)
    {
        return _cache.TryGetValue(key, out value);
    }
}
```

### Input/output compression; response caching (OutputCache in .NET 8)

**Why:** Compression reduces bandwidth usage and improves response times,
especially important for mobile clients or high-latency connections. Response
caching reduces server load and improves performance for frequently requested
data. OutputCache in .NET 8 provides better performance and more features than
previous caching solutions.

---

## 3. Data Access

### Dapper: parameterized queries only; command timeouts; prepared statements on hot paths

**Why:** Parameterized queries prevent SQL injection attacks, which are among
the most common security vulnerabilities. Command timeouts prevent long-running
queries from blocking resources indefinitely. Prepared statements on hot paths
improve performance by allowing the database to cache query execution plans.

```csharp
public class OrderRepository
{
    private readonly string _connectionString;

    public async Task<Order?> GetOrderAsync(int orderId, CancellationToken cancellationToken)
    {
        using var connection = new MySqlConnection(_connectionString);

        // ✅ Good - Parameterized query with timeout
        const string sql = "SELECT * FROM orders WHERE id = @orderId";
        var command = new CommandDefinition(
            sql,
            new { orderId },
            commandTimeout: 30,
            cancellationToken: cancellationToken);

        return await connection.QuerySingleOrDefaultAsync<Order>(command);
    }

    // For hot paths - prepare statements
    private static readonly CommandDefinition GetOrderByIdCommand = new(
        "SELECT * FROM orders WHERE id = @orderId",
        commandTimeout: 30,
        flags: CommandFlags.None);

    public async Task<Order?> GetOrderFastAsync(int orderId)
    {
        using var connection = new MySqlConnection(_connectionString);
        return await connection.QuerySingleOrDefaultAsync<Order>(
            GetOrderByIdCommand with { Parameters = new { orderId } });
    }
}

// ❌ Bad - String concatenation (SQL injection risk)
// var sql = $"SELECT * FROM orders WHERE id = {orderId}";
```

### DbUp: transactional migrations, schema version table, checksum verification, exclusive lock

**Why:** Transactional migrations ensure database schema changes are atomic -
they either complete fully or roll back completely. Schema version tracking
prevents applying migrations out of order or multiple times. Checksum
verification detects if migration scripts have been modified after deployment.
Exclusive locks prevent concurrent migration runs that could corrupt the
database.

### MySqlConnector: async calls, proper pooling; UTF8MB4; UTC only; strict SQL mode

**Why:** Async calls prevent thread blocking and improve scalability. Connection
pooling reduces the overhead of creating new database connections. UTF8MB4
supports full Unicode including emojis and special characters. UTC-only
timestamps prevent timezone-related bugs. Strict SQL mode catches data
truncation and other issues that could lead to data corruption.

### Repository pattern: isolate database access, receive and return domain objects

**Why:** Repositories isolate database concerns from business logic, making code
more testable and maintainable. They should work with domain objects, not DTOs
or database models, to maintain clean separation of concerns.

```csharp
// Domain object
public record Order(
    int Id,
    string CustomerId,
    decimal Amount,
    DateTimeOffset CreatedAt
);

// Repository interface
public interface IOrderRepository
{
    Task<Order?> GetByIdAsync(int id);
    Task<Order> CreateAsync(Order order);
    Task UpdateAsync(Order order);
}

// Repository implementation
public class OrderRepository : IOrderRepository
{
    private readonly IDbConnection _connection;

    public OrderRepository(IDbConnection connection)
    {
        _connection = connection;
    }

    public async Task<Order?> GetByIdAsync(int id)
    {
        const string sql = "SELECT Id, CustomerId, Amount, CreatedAt FROM Orders WHERE Id = @Id";
        return await _connection.QuerySingleOrDefaultAsync<Order>(sql, new { Id = id });
    }

    public async Task<Order> CreateAsync(Order order)
    {
        const string sql = @"
            INSERT INTO Orders (CustomerId, Amount, CreatedAt) 
            VALUES (@CustomerId, @Amount, @CreatedAt);
            SELECT LAST_INSERT_ID();";
        
        var id = await _connection.QuerySingleAsync<int>(sql, order);
        return order with { Id = id };
    }
}
```

---

## 4. Testing

### xUnit + AwesomeAssertions; AAA; Given_When_Should names

**Why:** xUnit is the most popular .NET testing framework with excellent
performance and extensibility. AwesomeAssertions provides more readable and
informative assertion failures compared to FluentAssertions. AAA (Arrange, Act,
Assert) structure makes tests easier to understand and maintain.
Given_When_Should naming clearly communicates test scenarios and expected
outcomes.

```csharp
public class OrderServiceTests
{
    [Test]
    public async Task Given_ValidOrder_When_ProcessingOrder_Should_CreateOrderSuccessfully()
    {
        // Arrange
        var timeProvider = new FakeTimeProvider(new DateTimeOffset(2024, 1, 1, 12, 0, 0, TimeSpan.Zero));
        var mockPaymentService = new Mock<IPaymentService>();
        var service = new OrderService(mockPaymentService.Object, timeProvider);

        var request = new OrderRequest
        {
            CustomerId = 123,
            Items = [new OrderItem { ProductId = 1, Quantity = 2 }]
        };

        // Act
        var result = await service.CreateOrderAsync(request);

        // Assert
        result.Should().NotBeNull();
        result.CustomerId.Should().Be(123);
        result.CreatedAt.Should().Be(timeProvider.GetUtcNow());
        result.Items.Should().HaveCount(1);

        mockPaymentService.Verify(x => x.ProcessPaymentAsync(It.IsAny<Payment>()), Times.Once);
    }

    [Test]
    public async Task Given_InvalidCustomerId_When_ProcessingOrder_Should_ThrowValidationException()
    {
        // Arrange
        var service = new OrderService(Mock.Of<IPaymentService>(), TimeProvider.System);
        var request = new OrderRequest { CustomerId = 0 }; // Invalid

        // Act & Assert
        var exception = await Assert.ThrowsAsync<ValidationException>(() =>
            service.CreateOrderAsync(request));

        exception.Message.Should().Contain("CustomerId must be greater than 0");
    }
}
```

### Reqnroll for BDD specs

**Why:** Reqnroll (successor to SpecFlow) enables behavior-driven development by
allowing you to write tests in natural language that stakeholders can
understand. This bridges the gap between business requirements and technical
implementation, ensuring you're building the right features.

### WebApplicationFactory<T> + Testcontainers for integration tests

**Why:** WebApplicationFactory provides an in-memory test server that closely
mimics your production environment without external dependencies. Testcontainers
spin up real database and service instances in Docker, ensuring your integration
tests run against the same technology stack as production, catching integration
issues that mocks might miss.

**Vertical Slice Testing:** We prefer vertical slice testing that goes all the
way down to a real database running in TestContainers, even within our unit test
suites. This approach enhances our tests' ability to simulate real-world
production scenarios, catching data access issues, transaction behavior, and
database-specific logic that mocks cannot replicate.

```csharp
// NuGet packages needed
// <PackageReference Include="Testcontainers" Version="3.6.0" />
// <PackageReference Include="Testcontainers.MySql" Version="3.6.0" />
// <PackageReference Include="Testcontainers.Redis" Version="3.6.0" />
// <PackageReference Include="Testcontainers.LocalStack" Version="3.6.0" />

public class IntegrationTestBase : IAsyncLifetime
{
    private readonly MySqlContainer _mysqlContainer;
    private readonly RedisContainer _redisContainer;
    private readonly LocalStackContainer _localStackContainer;
    protected WebApplicationFactory<Program> Factory { get; private set; }

    public IntegrationTestBase()
    {
        _mysqlContainer = new MySqlBuilder()
            .WithDatabase("testdb")
            .WithUsername("testuser")
            .WithPassword("testpass")
            .WithPortBinding(3306, true)
            .Build();

        _redisContainer = new RedisBuilder()
            .WithPortBinding(6379, true)
            .Build();

        // LocalStack for AWS services in CI/CD
        // Note: Not all AWS features are available in the free version of LocalStack
        _localStackContainer = new LocalStackBuilder()
            .WithServices(LocalStackService.S3, LocalStackService.Sqs, LocalStackService.Sns)
            .WithPortBinding(4566, true)
            .Build();
    }

    public async Task InitializeAsync()
    {
        await _mysqlContainer.StartAsync();
        await _redisContainer.StartAsync();
        await _localStackContainer.StartAsync();

        Factory = new WebApplicationFactory<Program>()
            .WithWebHostBuilder(builder =>
            {
                builder.ConfigureTestServices(services =>
                {
                    // Replace database connection
                    services.RemoveAll<DbContextOptions<ApplicationDbContext>>();
                    services.AddDbContext<ApplicationDbContext>(options =>
                        options.UseMySql(_mysqlContainer.GetConnectionString(),
                            ServerVersion.AutoDetect(_mysqlContainer.GetConnectionString())));

                    // Replace Redis connection
                    services.RemoveAll<IConnectionMultiplexer>();
                    services.AddSingleton<IConnectionMultiplexer>(_ =>
                        ConnectionMultiplexer.Connect(_redisContainer.GetConnectionString()));

                    // Configure AWS services to use LocalStack
                    services.Configure<AWSOptions>(options =>
                    {
                        options.DefaultClientConfig.ServiceURL = _localStackContainer.GetConnectionString();
                        options.DefaultClientConfig.UseHttp = true;
                        options.DefaultClientConfig.AuthenticationRegion = "us-east-1";
                    });

                    // Override AWS credentials for LocalStack
                    services.AddSingleton<IAmazonS3>(_ => new AmazonS3Client(
                        new BasicAWSCredentials("test", "test"),
                        new AmazonS3Config
                        {
                            ServiceURL = _localStackContainer.GetConnectionString(),
                            UseHttp = true,
                            ForcePathStyle = true
                        }));
                });
            });

        // Run database migrations
        using var scope = Factory.Services.CreateScope();
        var context = scope.ServiceProvider.GetRequiredService<ApplicationDbContext>();
        await context.Database.MigrateAsync();
    }

    public async Task DisposeAsync()
    {
        await Factory.DisposeAsync();
        await _mysqlContainer.DisposeAsync();
        await _redisContainer.DisposeAsync();
        await _localStackContainer.DisposeAsync();
    }
}

// Vertical slice test example - tests entire feature stack
public class OrderProcessingTests : IntegrationTestBase
{
    [Fact]
    public async Task Given_ValidOrder_When_ProcessingOrder_Should_CreateOrderAndSendNotification()
    {
        // Arrange - Set up test data in real database
        using var scope = Factory.Services.CreateScope();
        var context = scope.ServiceProvider.GetRequiredService<ApplicationDbContext>();

        var customer = new Customer { Id = Guid.NewGuid(), Email = "test@example.com" };
        context.Customers.Add(customer);
        await context.SaveChangesAsync();

        var client = Factory.CreateClient();
        var orderRequest = new CreateOrderRequest
        {
            CustomerId = customer.Id,
            Items = new[] { new OrderItem { ProductId = 1, Quantity = 2, Price = 10.00m } }
        };

        // Act - Call the actual API endpoint
        var response = await client.PostAsJsonAsync("/api/orders", orderRequest);

        // Assert - Verify database state and side effects
        response.StatusCode.Should().Be(HttpStatusCode.Created);

        var order = await context.Orders
            .Include(o => o.Items)
            .FirstOrDefaultAsync(o => o.CustomerId == customer.Id);

        order.Should().NotBeNull();
        order.Items.Should().HaveCount(1);
        order.TotalAmount.Should().Be(20.00m);
        order.Status.Should().Be(OrderStatus.Pending);

        // Verify Redis cache was updated
        var redis = scope.ServiceProvider.GetRequiredService<IConnectionMultiplexer>();
        var db = redis.GetDatabase();
        var cachedOrder = await db.StringGetAsync($"order:{order.Id}");
        cachedOrder.Should().NotBeNull();

        // Verify AWS SNS message was sent (via LocalStack)
        var snsClient = scope.ServiceProvider.GetRequiredService<IAmazonSimpleNotificationService>();
        // Note: In real tests, you'd verify the message was published
        // LocalStack provides endpoints to check sent messages
    }
}

// Performance considerations for TestContainers
public class TestContainerPerformanceTests : IClassFixture<DatabaseFixture>
{
    private readonly DatabaseFixture _fixture;

    public TestContainerPerformanceTests(DatabaseFixture fixture)
    {
        _fixture = fixture;
    }

    [Fact]
    public async Task DatabaseOperations_Should_PerformWithinAcceptableTime()
    {
        // Reuse container across tests in the same class for better performance
        using var scope = _fixture.Factory.Services.CreateScope();
        var context = scope.ServiceProvider.GetRequiredService<ApplicationDbContext>();

        var stopwatch = Stopwatch.StartNew();

        // Test database operations
        var orders = await context.Orders.Take(100).ToListAsync();

        stopwatch.Stop();
        stopwatch.ElapsedMilliseconds.Should().BeLessThan(1000); // 1 second max
    }
}

// Shared fixture for better performance across test classes
public class DatabaseFixture : IntegrationTestBase
{
    // Container is shared across all tests in classes that use this fixture
    // Reduces container startup overhead
}
```

**LocalStack Integration Notes:**

- LocalStack provides AWS-compatible services for local development and testing
- Free version includes core services like S3, SQS, SNS, Lambda, DynamoDB
- Advanced features (Kinesis, ECS, RDS, etc.) require LocalStack Pro
- Perfect for CI/CD environments where you need AWS-like behavior without actual
  AWS costs
- Use for integration tests that need to verify AWS service interactions

**Performance Best Practices:**

- Use `IClassFixture<T>` to share containers across tests in the same class
- Consider `ICollectionFixture<T>` for sharing across multiple test classes
- Implement proper cleanup in `DisposeAsync()` to prevent resource leaks
- Use container health checks to ensure services are ready before running tests
- Consider parallel test execution limits when using multiple containers

### Stryker.NET for mutation testing on domain assemblies

**Why:** Mutation testing validates the quality of your tests by introducing
small changes (mutations) to your code and checking if tests catch them. This
ensures your tests actually verify the behavior they claim to test, not just
achieve code coverage through execution.

### PactNet for consumer-driven contract tests

**Why:** Contract tests ensure that service interfaces remain compatible as they
evolve independently. Consumer-driven contracts put the consumer in control of
what they need, preventing breaking changes and enabling confident independent
deployments in microservice architectures.

### Coverage gates with coverlet.collector (domain ≥ 90%)

**Why:** Code coverage metrics help identify untested code paths. Domain
assemblies contain your core business logic and deserve the highest coverage
standards. Automated gates prevent coverage regression and ensure new code is
properly tested.

---

## 5. Factories (instead of keyed services)

### Simple: inject Func<T>

**Why:** Func<T> delegates provide a clean way to defer object creation until
needed, which is useful for expensive objects or when you need multiple
instances. This is simpler and more explicit than keyed services while
maintaining compile-time safety.

```csharp
// Registration
services.AddScoped<ExpensiveService>();
services.AddScoped<Func<ExpensiveService>>(provider =>
    () => provider.GetRequiredService<ExpensiveService>());

// Usage - create only when needed
public class OrderProcessor
{
    private readonly Func<ExpensiveService> _expensiveServiceFactory;

    public OrderProcessor(Func<ExpensiveService> expensiveServiceFactory)
    {
        _expensiveServiceFactory = expensiveServiceFactory;
    }

    public async Task ProcessOrderAsync(Order order)
    {
        if (order.RequiresExpensiveProcessing)
        {
            var service = _expensiveServiceFactory(); // Create only when needed
            await service.ProcessAsync(order);
        }
    }
}
```

### Parameterized: Func<TParam, TResult> delegates

**Why:** When you need to create objects with runtime parameters, parameterized
delegates make the dependency explicit and testable. This is cleaner than
passing parameters through the DI container and provides better type safety.

### Strategy: IFactory<Enum, IService> returning concrete implementations

**Why:** Factory patterns with explicit enums make it clear what implementations
are available and provide compile-time safety. Using explicit switch statements
instead of keyed services makes the mapping obvious and prevents runtime errors
from typos in magic strings.

```csharp
public enum PaymentProvider
{
    Stripe,
    PayPal,
    Square
}

public interface IPaymentServiceFactory
{
    IPaymentService Create(PaymentProvider provider);
}

public class PaymentServiceFactory : IPaymentServiceFactory
{
    private readonly IServiceProvider _serviceProvider;

    public PaymentServiceFactory(IServiceProvider serviceProvider)
    {
        _serviceProvider = serviceProvider;
    }

    public IPaymentService Create(PaymentProvider provider) => provider switch
    {
        PaymentProvider.Stripe => _serviceProvider.GetRequiredService<StripePaymentService>(),
        PaymentProvider.PayPal => _serviceProvider.GetRequiredService<PayPalPaymentService>(),
        PaymentProvider.Square => _serviceProvider.GetRequiredService<SquarePaymentService>(),
        _ => throw new ArgumentException($"Unknown payment provider: {provider}")
    };
}

// Usage
public class OrderService
{
    private readonly IPaymentServiceFactory _paymentFactory;

    public async Task ProcessPaymentAsync(Order order)
    {
        var paymentService = _paymentFactory.Create(order.PaymentProvider);
        await paymentService.ProcessAsync(order.Payment);
    }
}
```

### Use ActivatorUtilities.CreateInstance<T> for DI + runtime args

**Why:** When you need both dependency injection and runtime parameters,
ActivatorUtilities provides a clean way to create instances that satisfy both
needs. This is more explicit and testable than complex factory patterns or
service locators.

---

## 6. Serialization & Mapping

### System.Text.Json with source generators (JsonSerializerContext)

**Why:** System.Text.Json is faster and more memory-efficient than
Newtonsoft.Json, and it's the .NET standard. Source generators provide
compile-time serialization code generation, eliminating reflection overhead and
enabling trimming/AOT scenarios. This results in better performance and smaller
deployment sizes.

```csharp
// Define serialization context
[JsonSerializable(typeof(Order))]
[JsonSerializable(typeof(OrderRequest))]
[JsonSerializable(typeof(List<Order>))]
[JsonSourceGenerationOptions(
    PropertyNamingPolicy = JsonKnownNamingPolicy.CamelCase,
    WriteIndented = false)]
public partial class OrderJsonContext : JsonSerializerContext
{
}

// Usage in API controller
[ApiController]
[Route("api/v1/orders")]
public class OrdersController : ControllerBase
{
    [HttpPost]
    public async Task<IActionResult> CreateOrder([FromBody] OrderRequest request)
    {
        // Deserialize with source-generated context
        var order = JsonSerializer.Deserialize(request, OrderJsonContext.Default.OrderRequest);

        // Process order...

        // Serialize response with source-generated context
        return Ok(JsonSerializer.Serialize(order, OrderJsonContext.Default.Order));
    }
}

// Configure in Program.cs
builder.Services.ConfigureHttpJsonOptions(options =>
{
    options.SerializerOptions.TypeInfoResolverChain.Insert(0, OrderJsonContext.Default);
});
```

### Avoid Newtonsoft.Json in new code

**Why:** Newtonsoft.Json is slower, uses more memory, and relies heavily on
reflection. System.Text.Json is actively developed by Microsoft and integrates
better with modern .NET features like trimming and AOT compilation.

### Mapster for mapping (compile-time); avoid reflection-heavy AutoMapper

**Why:** Mapster generates mapping code at compile-time, providing better
performance than reflection-based solutions like AutoMapper. Compile-time
generation also enables better debugging and works with trimming/AOT scenarios.
The generated code is easier to understand and optimize.

---

## 7. Health & Readiness

### /health/live and /health/ready with dependency checks

**Why:** Separate liveness and readiness probes allow orchestrators to make
better decisions about your application. Liveness checks determine if the
application should be restarted, while readiness checks determine if it should
receive traffic. Dependency checks ensure your service only reports as ready
when it can actually fulfill requests.

```csharp
// Program.cs
builder.Services.AddHealthChecks()
    .AddCheck("self", () => HealthCheckResult.Healthy())
    .AddMySql(connectionString, name: "database")
    .AddCheck<S3HealthCheck>("s3-bucket")
    .AddCheck<DownstreamApiHealthCheck>("payment-api");

var app = builder.Build();

// Separate endpoints for different purposes
app.MapHealthChecks("/health/live", new HealthCheckOptions
{
    Predicate = check => check.Name == "self" // Only basic liveness
});

app.MapHealthChecks("/health/ready", new HealthCheckOptions
{
    Predicate = _ => true, // All health checks for readiness
    ResponseWriter = UIResponseWriter.WriteHealthCheckUIResponse
});

// Custom health check example
public class S3HealthCheck : IHealthCheck
{
    private readonly IAmazonS3 _s3Client;
    private readonly string _bucketName;

    public S3HealthCheck(IAmazonS3 s3Client, IConfiguration config)
    {
        _s3Client = s3Client;
        _bucketName = config["S3:BucketName"];
    }

    public async Task<HealthCheckResult> CheckHealthAsync(HealthCheckContext context, CancellationToken cancellationToken = default)
    {
        try
        {
            await _s3Client.GetBucketLocationAsync(_bucketName, cancellationToken);
            return HealthCheckResult.Healthy("S3 bucket is accessible");
        }
        catch (Exception ex)
        {
            return HealthCheckResult.Unhealthy("S3 bucket is not accessible", ex);
        }
    }
}
```

### ECS healthchecks point to /health/ready

**Why:** Using readiness checks for load balancer health ensures traffic is only
routed to instances that can actually process requests. This prevents cascading
failures when dependencies are unavailable and provides better user experience
during deployments or scaling events.

---

## 8. Security

### Service-to-service auth via IAM SigV4

**Why:** IAM SigV4 provides strong authentication without managing shared
secrets or certificates. It integrates seamlessly with AWS services and provides
fine-grained access control. The signatures are time-limited and prevent replay
attacks, making it more secure than API keys or basic authentication.

### Secrets via SSM Parameter Store (SecureString); Secrets Manager for auto-rotation

**Why:** SSM Parameter Store provides encrypted storage for configuration values
at no additional cost for standard parameters. SecureString parameters are
encrypted with KMS keys you control. Secrets Manager is used only when you need
automatic rotation (like RDS passwords) because it costs more but provides
additional rotation capabilities.

### HTTPS-only; HSTS; security headers

**Why:** HTTPS encrypts data in transit, preventing eavesdropping and
man-in-the-middle attacks. HSTS prevents protocol downgrade attacks by forcing
browsers to use HTTPS. Security headers like X-Content-Type-Options prevent
MIME-type confusion attacks, and Referrer-Policy controls what information is
sent to external sites.

### PII redaction; audit logs for admin actions

**Why:** PII redaction prevents sensitive data from appearing in logs, reducing
compliance risks and potential data breaches. Audit logs for admin actions
provide accountability and help with compliance requirements like SOX or GDPR.
They also help with incident response and forensic analysis.

### Static analysis: dotnet list package --vulnerable, Trivy on containers

**Why:** Automated vulnerability scanning catches known security issues in
dependencies before they reach production. Regular scanning of both NuGet
packages and container images helps maintain security posture and enables quick
response to newly discovered vulnerabilities.

---

## 9. Performance & Packaging

### Build: dotnet publish -c Release -r linux-arm64 --self-contained false

**Why:** Release configuration enables optimizations and removes debug symbols,
reducing size and improving performance. ARM64 targeting takes advantage of AWS
Graviton processors which offer better price-performance. Framework-dependent
deployment reduces image size and startup time compared to self-contained
deployments when the runtime is available in the base image.

### Consider Native AOT for workers/Lambda to shrink cold starts

**Why:** Native AOT compilation produces native machine code that starts faster
and uses less memory than JIT-compiled code. This is especially beneficial for
Lambda functions and short-lived workers where cold start time significantly
impacts user experience. The trade-off is larger deployment size and some
runtime limitations.

### Enable trimming (PublishTrimmed); annotate reflection needs

**Why:** Trimming removes unused code from the final deployment, significantly
reducing application size. This improves deployment speed and reduces memory
usage. Proper annotation of reflection usage ensures trimming doesn't remove
code that's needed at runtime, maintaining application correctness while
achieving size benefits.

---

## 10. Containers

### Multi-stage Dockerfile; run as non-root; read-only FS; /app workdir

**Why:** Multi-stage builds separate build dependencies from runtime
dependencies, creating smaller, more secure final images. Running as non-root
follows the principle of least privilege and prevents many attack vectors.
Read-only filesystems prevent runtime modifications that could indicate
compromise. Consistent workdir simplifies deployment and debugging.

```dockerfile

# Multi-stage Dockerfile example
FROM mcr.microsoft.com/dotnet/sdk:8.0-alpine AS build
WORKDIR /src
COPY ["MyApi/MyApi.csproj", "MyApi/"]
RUN dotnet restore "MyApi/MyApi.csproj"
COPY . .
WORKDIR "/src/MyApi"
RUN dotnet publish "MyApi.csproj" -c Release -o /app/publish \
    --no-restore --runtime linux-arm64 --self-contained false

FROM mcr.microsoft.com/dotnet/aspnet:8.0-alpine AS runtime

# Create non-root user
RUN addgroup -g 1001 -S appgroup && \
    adduser -u 1001 -S appuser -G appgroup

WORKDIR /app
COPY --from=build /app/publish .

# Set ownership and switch to non-root user
RUN chown -R appuser:appgroup /app
USER appuser

# Read-only filesystem (mount tmpfs for writable areas if needed)

# docker run --read-only --tmpfs /tmp myapi

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health/ready || exit 1

ENTRYPOINT ["dotnet", "MyApi.dll"]
```

### Healthcheck to /health/ready

**Why:** Container healthchecks allow orchestrators to automatically restart
unhealthy containers and route traffic appropriately. Using the readiness
endpoint ensures containers are marked healthy only when they can actually serve
requests, improving overall system reliability.

### Minimal base images; prefer arm64 (Graviton)

**Why:** Minimal base images reduce attack surface, deployment size, and startup
time by including only essential components. ARM64 images take advantage of AWS
Graviton processors which offer 20-40% better price-performance compared to x86
instances, reducing infrastructure costs.

---

## 11. Code Style & Analyzers

### Nullable reference types, file-scoped namespaces, modern C# features

**Why:** Nullable reference types catch null reference exceptions at
compile-time, preventing one of the most common runtime errors. File-scoped
namespaces reduce indentation and improve readability. Modern C# features like
target-typed new, pattern matching, and collection expressions make code more
concise and expressive while maintaining readability.

### Roslyn + StyleCop analyzers; .editorconfig enforced; dotnet format in CI

**Why:** Static analysis catches potential bugs, security issues, and style
violations before code review. Consistent code formatting reduces cognitive load
and makes code reviews focus on logic rather than style. Automated formatting in
CI ensures consistency across the team and prevents style-related merge
conflicts.

### SourceLink and deterministic builds; embed git hash as assembly info

**Why:** SourceLink enables debugging into NuGet packages and provides better
stack traces in production. Deterministic builds ensure identical inputs produce
identical outputs, enabling reliable caching and security verification. Git hash
embedding helps correlate deployed code with source control, crucial for
incident response and auditing.

---

## 12. EARS Requirements

**EARS (Easy Approach to Requirements Syntax) format for .NET development
requirements:**

### Ubiquitous Requirements

- The system SHALL use dependency injection for all service registrations
- The system SHALL treat compiler warnings as errors in CI builds
- The system SHALL use structured logging with JSON output
- The system SHALL implement health check endpoints at `/health/live` and
  `/health/ready`
- The system SHALL use parameterized queries for all database operations
- The system SHALL validate all external inputs using FluentValidation
- The system SHALL use TimeProvider instead of DateTime.UtcNow for testability

### Event-Driven Requirements

- WHEN a request is received, the system SHALL add correlation IDs to log
  context
- WHEN an exception occurs, the system SHALL log structured exception details
  with full context
- WHEN a database migration runs, the system SHALL use transactional execution
  with rollback capability
- WHEN a service starts, the system SHALL validate configuration using
  DataAnnotations
- WHEN an HTTP request fails, the system SHALL retry with exponential backoff
  and jitter

### Unwanted Behavior Requirements

- IF keyed services are used, the system SHALL reject the implementation
- IF global state is detected, the system SHALL fail code review
- IF test coverage falls below 90% for domain assemblies, the system SHALL fail
  the build
- IF unsafe deserialization is attempted, the system SHALL prevent execution
- IF secrets are hardcoded, the system SHALL fail security scanning

### State-Driven Requirements

- WHILE processing requests, the system SHALL maintain request context in log
  scope
- WHILE running integration tests, the system SHALL use TestContainers for real
  dependencies
- WHILE handling async operations, the system SHALL propagate CancellationTokens
- WHILE in production mode, the system SHALL disable debug logging levels

### Optional Feature Requirements

- WHERE performance is critical, the system SHOULD use prepared statements
- WHERE high availability is required, the system SHOULD implement circuit
  breakers
- WHERE data is sensitive, the system SHOULD use envelope encryption with KMS
- WHERE caching improves performance, the system SHOULD implement Redis caching

### Complex Requirements

- WHEN a user submits an order AND payment processing is required, the system
  SHALL validate the order, process payment with idempotency, create the order
  record, and publish order events
- WHEN an API endpoint is called AND the request contains invalid data, the
  system SHALL return HTTP 400 with structured error details AND log the
  validation failure with request context
- WHEN a background job fails AND retry attempts are exhausted, the system SHALL
  move the message to a dead letter queue AND alert the operations team

---

## 13. CI/CD Snippets

### Lint and analyze step

**Why:** Running linting and analysis before tests catches style and potential
logic issues early, preventing wasted time on test runs that would fail anyway.
The -warnaserror flag ensures warnings don't accumulate as technical debt.
Format verification prevents inconsistent code style from entering the main
branch.

### Test step with coverage enforcement

**Why:** Collecting coverage during test runs provides immediate feedback on
test completeness. The threshold enforcement prevents coverage regression and
ensures new code is properly tested. Cobertura format enables integration with
various reporting tools and CI systems.

**Coverage and analyzers (Buildkite step sketch):**

```yaml
steps:
  - label: "lint+analyze"

    command: |
      dotnet restore
      dotnet build -warnaserror
      dotnet format --verify-no-changes

  - label: "tests"

    command:
      dotnet test --collect:"XPlat Code Coverage" /p:CollectCoverage=true
      /p:CoverletOutputFormat=cobertura /p:Threshold=90
```

**Why these specific steps matter:**

---

## 14. Checklist

**Why this checklist matters:** This checklist serves as a final verification
that all critical practices are implemented. Each item represents a decision
that significantly impacts code quality, maintainability, security, or
performance. Regular checklist reviews during code reviews and before releases
help ensure consistency across projects and prevent regression of important
practices.

- [ ] DI everywhere; no keyed services
- [ ] Dapper + DbUp + MySqlConnector
- [ ] Serilog JSON + OTEL tracing
- [ ] xUnit + AwesomeAssertions + Testcontainers
- [ ] PactNet contracts; Stryker.NET mutation
- [ ] System.Text.Json source-gen; Mapster
- [ ] Health endpoints, readiness checks
- [ ] IAM-auth S2S; SSM SecureString for secrets
- [ ] Coverage ≥ 90%; zero warnings
