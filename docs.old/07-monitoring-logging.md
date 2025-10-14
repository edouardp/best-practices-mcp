# Monitoring and Logging Best Practices

## Application Logging

### Python Logging Configuration
```python
# logging_config.py
import logging
import logging.config
import json
from datetime import datetime
import sys

class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
        if hasattr(record, 'correlation_id'):
            log_entry['correlation_id'] = record.correlation_id
            
        return json.dumps(log_entry)

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': JSONFormatter,
        },
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'json',
            'stream': sys.stdout,
        },
        'file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'json',
            'filename': 'app.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
        },
    },
    'loggers': {
        '': {  # root logger
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'myapp': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'sqlalchemy.engine': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

def setup_logging():
    """Setup logging configuration."""
    logging.config.dictConfig(LOGGING_CONFIG)

# Usage example
logger = logging.getLogger('myapp.services')

def create_user(user_data, request_id=None):
    """Create a new user with proper logging."""
    logger.info(
        "Creating user",
        extra={
            'request_id': request_id,
            'user_email': user_data.get('email'),
            'action': 'user_creation'
        }
    )
    
    try:
        # User creation logic
        user = User.create(user_data)
        logger.info(
            "User created successfully",
            extra={
                'request_id': request_id,
                'user_id': user.id,
                'action': 'user_created'
            }
        )
        return user
    except Exception as e:
        logger.error(
            "Failed to create user",
            extra={
                'request_id': request_id,
                'error': str(e),
                'action': 'user_creation_failed'
            },
            exc_info=True
        )
        raise
```

### C# Logging with Serilog
```csharp
// Program.cs
using Serilog;
using Serilog.Events;
using Serilog.Formatting.Json;

var builder = WebApplication.CreateBuilder(args);

// Configure Serilog
Log.Logger = new LoggerConfiguration()
    .MinimumLevel.Information()
    .MinimumLevel.Override("Microsoft", LogEventLevel.Warning)
    .MinimumLevel.Override("System", LogEventLevel.Warning)
    .Enrich.FromLogContext()
    .Enrich.WithProperty("Application", "MyApp")
    .Enrich.WithProperty("Environment", builder.Environment.EnvironmentName)
    .WriteTo.Console(new JsonFormatter())
    .WriteTo.File(
        new JsonFormatter(),
        "logs/app-.log",
        rollingInterval: RollingInterval.Day,
        retainedFileCountLimit: 30,
        fileSizeLimitBytes: 10_000_000,
        rollOnFileSizeLimit: true)
    .CreateLogger();

builder.Host.UseSerilog();

var app = builder.Build();

// Add request logging middleware
app.UseSerilogRequestLogging(options =>
{
    options.MessageTemplate = "HTTP {RequestMethod} {RequestPath} responded {StatusCode} in {Elapsed:0.0000} ms";
    options.EnrichDiagnosticContext = (diagnosticContext, httpContext) =>
    {
        diagnosticContext.Set("RequestHost", httpContext.Request.Host.Value);
        diagnosticContext.Set("RequestScheme", httpContext.Request.Scheme);
        diagnosticContext.Set("UserAgent", httpContext.Request.Headers["User-Agent"].FirstOrDefault());
        
        if (httpContext.User.Identity?.IsAuthenticated == true)
        {
            diagnosticContext.Set("UserId", httpContext.User.FindFirst("sub")?.Value);
        }
    };
});

app.Run();

// Service example with structured logging
public class UserService
{
    private readonly ILogger<UserService> _logger;
    
    public UserService(ILogger<UserService> logger)
    {
        _logger = logger;
    }
    
    public async Task<User> CreateUserAsync(CreateUserDto userDto, string correlationId)
    {
        using var scope = _logger.BeginScope(new Dictionary<string, object>
        {
            ["CorrelationId"] = correlationId,
            ["Action"] = "CreateUser"
        });
        
        _logger.LogInformation("Creating user with email {Email}", userDto.Email);
        
        try
        {
            var user = new User
            {
                Name = userDto.Name,
                Email = userDto.Email,
                CreatedAt = DateTime.UtcNow
            };
            
            await _repository.CreateAsync(user);
            
            _logger.LogInformation("User created successfully with ID {UserId}", user.Id);
            
            return user;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to create user with email {Email}", userDto.Email);
            throw;
        }
    }
}
```

## Distributed Tracing

### Python OpenTelemetry Setup
```python
# tracing.py
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
import os

def setup_tracing(app):
    """Setup distributed tracing for Flask application."""
    
    # Create resource
    resource = Resource.create({
        "service.name": "python-app",
        "service.version": "1.0.0",
        "deployment.environment": os.getenv("ENVIRONMENT", "development")
    })
    
    # Set up tracer provider
    trace.set_tracer_provider(TracerProvider(resource=resource))
    tracer = trace.get_tracer(__name__)
    
    # Configure Jaeger exporter
    jaeger_exporter = JaegerExporter(
        agent_host_name=os.getenv("JAEGER_AGENT_HOST", "localhost"),
        agent_port=int(os.getenv("JAEGER_AGENT_PORT", "6831")),
    )
    
    # Add span processor
    span_processor = BatchSpanProcessor(jaeger_exporter)
    trace.get_tracer_provider().add_span_processor(span_processor)
    
    # Auto-instrument frameworks
    FlaskInstrumentor().instrument_app(app)
    RequestsInstrumentor().instrument()
    SQLAlchemyInstrumentor().instrument()
    
    return tracer

# Usage in service
class UserService:
    def __init__(self, tracer):
        self.tracer = tracer
    
    def create_user(self, user_data):
        with self.tracer.start_as_current_span("create_user") as span:
            span.set_attribute("user.email", user_data.get("email"))
            span.set_attribute("operation", "user_creation")
            
            try:
                # Validate user data
                with self.tracer.start_as_current_span("validate_user_data"):
                    self._validate_user_data(user_data)
                
                # Save to database
                with self.tracer.start_as_current_span("save_user_to_db") as db_span:
                    user = User.create(user_data)
                    db_span.set_attribute("user.id", user.id)
                
                # Send welcome email
                with self.tracer.start_as_current_span("send_welcome_email"):
                    self._send_welcome_email(user.email)
                
                span.set_attribute("user.id", user.id)
                span.set_status(trace.Status(trace.StatusCode.OK))
                
                return user
                
            except Exception as e:
                span.record_exception(e)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                raise
```

### C# OpenTelemetry Setup
```csharp
// Program.cs
using OpenTelemetry;
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;
using OpenTelemetry.Metrics;
using System.Diagnostics;

var builder = WebApplication.CreateBuilder(args);

// Add OpenTelemetry
builder.Services.AddOpenTelemetry()
    .WithTracing(tracerProviderBuilder =>
    {
        tracerProviderBuilder
            .AddSource("MyApp")
            .SetResourceBuilder(ResourceBuilder.CreateDefault()
                .AddService("csharp-app", "1.0.0")
                .AddAttributes(new Dictionary<string, object>
                {
                    ["deployment.environment"] = builder.Environment.EnvironmentName
                }))
            .AddAspNetCoreInstrumentation(options =>
            {
                options.RecordException = true;
                options.EnrichWithHttpRequest = (activity, request) =>
                {
                    activity.SetTag("http.request.header.user_agent", request.Headers.UserAgent.ToString());
                };
                options.EnrichWithHttpResponse = (activity, response) =>
                {
                    activity.SetTag("http.response.status_code", response.StatusCode);
                };
            })
            .AddHttpClientInstrumentation()
            .AddEntityFrameworkCoreInstrumentation()
            .AddJaegerExporter(options =>
            {
                options.AgentHost = builder.Configuration["Jaeger:AgentHost"] ?? "localhost";
                options.AgentPort = int.Parse(builder.Configuration["Jaeger:AgentPort"] ?? "6831");
            });
    });

var app = builder.Build();

// Service with tracing
public class UserService
{
    private static readonly ActivitySource ActivitySource = new("MyApp");
    private readonly ILogger<UserService> _logger;
    
    public UserService(ILogger<UserService> logger)
    {
        _logger = logger;
    }
    
    public async Task<User> CreateUserAsync(CreateUserDto userDto)
    {
        using var activity = ActivitySource.StartActivity("CreateUser");
        activity?.SetTag("user.email", userDto.Email);
        activity?.SetTag("operation", "user_creation");
        
        try
        {
            // Validate user data
            using (var validateActivity = ActivitySource.StartActivity("ValidateUserData"))
            {
                await ValidateUserDataAsync(userDto);
            }
            
            // Save to database
            User user;
            using (var saveActivity = ActivitySource.StartActivity("SaveUserToDatabase"))
            {
                user = new User
                {
                    Name = userDto.Name,
                    Email = userDto.Email,
                    CreatedAt = DateTime.UtcNow
                };
                
                await _repository.CreateAsync(user);
                saveActivity?.SetTag("user.id", user.Id.ToString());
            }
            
            // Send welcome email
            using (var emailActivity = ActivitySource.StartActivity("SendWelcomeEmail"))
            {
                await _emailService.SendWelcomeEmailAsync(user.Email);
            }
            
            activity?.SetTag("user.id", user.Id.ToString());
            activity?.SetStatus(ActivityStatusCode.Ok);
            
            return user;
        }
        catch (Exception ex)
        {
            activity?.SetStatus(ActivityStatusCode.Error, ex.Message);
            activity?.RecordException(ex);
            _logger.LogError(ex, "Failed to create user");
            throw;
        }
    }
}
```

## Health Checks

### Python Health Checks
```python
# health.py
from flask import Flask, jsonify
import psycopg2
import redis
import requests
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class HealthChecker:
    def __init__(self, app: Flask):
        self.app = app
        self.checks = {
            'database': self._check_database,
            'redis': self._check_redis,
            'external_api': self._check_external_api,
        }
    
    def _check_database(self):
        """Check database connectivity."""
        try:
            conn = psycopg2.connect(self.app.config['DATABASE_URL'])
            cursor = conn.cursor()
            cursor.execute('SELECT 1')
            cursor.fetchone()
            cursor.close()
            conn.close()
            return {'status': 'healthy', 'response_time_ms': 0}
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {'status': 'unhealthy', 'error': str(e)}
    
    def _check_redis(self):
        """Check Redis connectivity."""
        try:
            r = redis.from_url(self.app.config['REDIS_URL'])
            r.ping()
            return {'status': 'healthy'}
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {'status': 'unhealthy', 'error': str(e)}
    
    def _check_external_api(self):
        """Check external API connectivity."""
        try:
            response = requests.get(
                'https://api.external-service.com/health',
                timeout=5
            )
            if response.status_code == 200:
                return {'status': 'healthy', 'response_time_ms': response.elapsed.total_seconds() * 1000}
            else:
                return {'status': 'unhealthy', 'status_code': response.status_code}
        except Exception as e:
            logger.error(f"External API health check failed: {e}")
            return {'status': 'unhealthy', 'error': str(e)}
    
    def check_health(self):
        """Perform all health checks."""
        results = {
            'timestamp': datetime.utcnow().isoformat(),
            'status': 'healthy',
            'checks': {}
        }
        
        overall_healthy = True
        
        for check_name, check_func in self.checks.items():
            try:
                check_result = check_func()
                results['checks'][check_name] = check_result
                
                if check_result['status'] != 'healthy':
                    overall_healthy = False
                    
            except Exception as e:
                logger.error(f"Health check {check_name} failed: {e}")
                results['checks'][check_name] = {
                    'status': 'unhealthy',
                    'error': str(e)
                }
                overall_healthy = False
        
        results['status'] = 'healthy' if overall_healthy else 'unhealthy'
        return results

# Flask routes
def register_health_routes(app: Flask):
    health_checker = HealthChecker(app)
    
    @app.route('/health')
    def health():
        """Liveness probe - basic health check."""
        return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()})
    
    @app.route('/health/ready')
    def ready():
        """Readiness probe - comprehensive health check."""
        health_result = health_checker.check_health()
        status_code = 200 if health_result['status'] == 'healthy' else 503
        return jsonify(health_result), status_code
```

### C# Health Checks
```csharp
// Program.cs
using Microsoft.Extensions.Diagnostics.HealthChecks;

var builder = WebApplication.CreateBuilder(args);

// Add health checks
builder.Services.AddHealthChecks()
    .AddNpgSql(
        builder.Configuration.GetConnectionString("DefaultConnection"),
        name: "database",
        tags: new[] { "db", "sql", "postgres" })
    .AddRedis(
        builder.Configuration.GetConnectionString("Redis"),
        name: "redis",
        tags: new[] { "cache", "redis" })
    .AddUrlGroup(
        new Uri("https://api.external-service.com/health"),
        name: "external-api",
        tags: new[] { "external" })
    .AddCheck<CustomHealthCheck>("custom-check");

var app = builder.Build();

// Configure health check endpoints
app.MapHealthChecks("/health", new HealthCheckOptions
{
    Predicate = _ => false // Exclude all checks for liveness
});

app.MapHealthChecks("/health/ready", new HealthCheckOptions
{
    Predicate = _ => true, // Include all checks for readiness
    ResponseWriter = async (context, report) =>
    {
        var result = new
        {
            timestamp = DateTime.UtcNow,
            status = report.Status.ToString(),
            checks = report.Entries.Select(entry => new
            {
                name = entry.Key,
                status = entry.Value.Status.ToString(),
                description = entry.Value.Description,
                duration = entry.Value.Duration.TotalMilliseconds,
                exception = entry.Value.Exception?.Message
            })
        };
        
        context.Response.ContentType = "application/json";
        await context.Response.WriteAsync(JsonSerializer.Serialize(result));
    }
});

// Custom health check
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
            var isHealthy = await PerformCustomCheckAsync();
            
            if (isHealthy)
            {
                return HealthCheckResult.Healthy("Custom check passed");
            }
            
            return HealthCheckResult.Unhealthy("Custom check failed");
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Custom health check failed");
            return HealthCheckResult.Unhealthy("Custom check exception", ex);
        }
    }
    
    private async Task<bool> PerformCustomCheckAsync()
    {
        // Custom logic here
        await Task.Delay(100);
        return true;
    }
}
```

## Alerting and Monitoring

### Prometheus Alert Rules
```yaml
# alert_rules.yml
groups:
- name: application.rules
  rules:
  - alert: HighErrorRate
    expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "High error rate detected"
      description: "Error rate is {{ $value }} errors per second"

  - alert: HighResponseTime
    expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High response time detected"
      description: "95th percentile response time is {{ $value }} seconds"

  - alert: DatabaseConnectionsHigh
    expr: active_connections > 80
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "High database connection count"
      description: "Database connections: {{ $value }}"

  - alert: PodCrashLooping
    expr: rate(kube_pod_container_status_restarts_total[15m]) > 0
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "Pod is crash looping"
      description: "Pod {{ $labels.pod }} in namespace {{ $labels.namespace }} is crash looping"

  - alert: HighMemoryUsage
    expr: (container_memory_usage_bytes / container_spec_memory_limit_bytes) > 0.9
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High memory usage"
      description: "Memory usage is {{ $value | humanizePercentage }}"

  - alert: HighCPUUsage
    expr: rate(container_cpu_usage_seconds_total[5m]) > 0.8
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High CPU usage"
      description: "CPU usage is {{ $value | humanizePercentage }}"
```

### Grafana Dashboard Configuration
```json
{
  "dashboard": {
    "title": "Application Monitoring",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ]
      },
      {
        "title": "Error Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total{status=~\"5..\"}[5m])",
            "legendFormat": "5xx errors"
          }
        ]
      },
      {
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          },
          {
            "expr": "histogram_quantile(0.50, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "50th percentile"
          }
        ]
      }
    ]
  }
}
```
