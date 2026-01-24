# Python Best Practices (3.13) — AWS-Native, Lambda & Services

> Opinionated, production-focused checklist for your repos. Defaults: **uv**,
> **ruff**, **mypy (strict)**, **pytest**, **structlog**, **OpenTelemetry**,
> **AWS SDK (boto3)**, **Lambda Powertools**, **S3/SQS/AppConfig/Parameter
> Store**, **CloudFormation**.

---

## 0. Golden Rules

### Prefer Python 3.13; pin exact versions and commit lockfiles

**Why:** Python 3.13 includes performance improvements, better error messages,
and security fixes. Pinning exact versions ensures reproducible builds across
environments and prevents "works on my machine" issues. Committed lockfiles
guarantee that all team members and CI/CD systems use identical dependency
versions, preventing subtle bugs from version drift.

### Use uv for env & dependency management; direnv optional

**Why:** uv is significantly faster than pip and provides better dependency
resolution. It creates reproducible environments and handles virtual environment
management automatically. direnv can automatically activate environments when
entering project directories, reducing context switching overhead and preventing
accidental package installation in the wrong environment.

```bash

# Initialize project with uv
uv init myproject
cd myproject

# Add dependencies
uv add boto3 structlog opentelemetry-sdk
uv add --dev pytest mypy ruff

# Install and sync (creates .venv automatically)
uv sync

# Optional: .envrc for direnv
echo "source .venv/bin/activate" > .envrc
direnv allow
```

### Treat warnings as errors in CI; fail on lints/format/type errors

**Why:** Warnings often indicate potential bugs or code quality issues that will
become problems later. Treating them as errors in CI prevents technical debt
accumulation and forces developers to address issues immediately. This maintains
code quality standards and prevents the gradual degradation that occurs when
warnings are ignored.

### Structured logs (structlog) everywhere; include trace_id, request_id, correlation_id

**Why:** Structured logging enables powerful querying and filtering in log
aggregation systems like CloudWatch Logs Insights. Including correlation IDs
allows you to trace requests across multiple services and Lambda functions,
making debugging distributed systems much easier. JSON format integrates
seamlessly with modern observability tools.

```python
import structlog
from aws_lambda_powertools import Logger

# Configure structlog
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Usage with context
def process_order(order_id: str, customer_id: str):
    log = logger.bind(
        order_id=order_id,
        customer_id=customer_id,
        trace_id=get_trace_id(),
        service="order-processor"
    )

    log.info("Processing order started")
    try:
        # Business logic here
        log.info("Order processed successfully", status="completed")
    except Exception as e:
        log.error("Order processing failed", error=str(e), status="failed")
        raise
```

### OpenTelemetry traces/metrics by default (export to X-Ray/CloudWatch)

**Why:** OpenTelemetry provides vendor-neutral observability that works across
different cloud providers and tools. X-Ray integration gives you distributed
tracing across AWS services, helping identify performance bottlenecks and
understand request flows. This is crucial for debugging microservices and
serverless architectures.

### Prefer SSM Parameter Store (SecureString) for secrets/config; use Secrets Manager only for auto-rotation

**Why:** SSM Parameter Store is cost-effective for most configuration needs and
integrates well with IAM for access control. SecureString parameters are
encrypted with KMS. Secrets Manager costs more but provides automatic rotation
capabilities, making it ideal for database passwords and API keys that need
regular rotation.

### For Lambda: small handlers, import discipline, arm64, layers for heavy deps; use aws-lambda-powertools

**Why:** Small handlers reduce cold start times and make functions easier to
test and debug. Import discipline (importing heavy libraries inside functions)
reduces initialization time. ARM64 provides better price-performance on AWS
Graviton. Layers allow sharing heavy dependencies across functions while keeping
deployment packages small. Lambda Powertools provides battle-tested utilities
for logging, tracing, and common patterns.

---

## 1. Project Layout

### Use src layout to avoid implicit imports

**Why:** The src layout prevents accidentally importing your package from the
project root during development, which can hide import errors that would occur
in production. This ensures your package is properly installable and that tests
run against the installed version, not the development version.

### Keep modules < 400 lines; one responsibility per file

**Why:** Smaller modules are easier to understand, test, and maintain. The
400-line limit is a practical threshold where cognitive load becomes
significant. Single responsibility per file makes it easier to locate
functionality and reduces merge conflicts in team environments.

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

---

## 2. Tooling & Config

### uv: lock, sync, no pip in CI

**Why:** uv provides deterministic dependency resolution and is significantly
faster than pip. Using `uv sync` instead of pip ensures exact reproduction of
the development environment in CI. Avoiding pip prevents version conflicts and
ensures consistent behavior across all environments.

### ruff: lint + format (ruff check --fix, ruff format)

**Why:** ruff is extremely fast (written in Rust) and combines multiple tools
(flake8, isort, black) into one. It catches common Python mistakes, enforces
consistent formatting, and can automatically fix many issues. The speed
improvement makes it practical to run on every save and in pre-commit hooks.

### mypy: --strict; add type hints for public funcs/classes

**Why:** Static type checking catches bugs before runtime and improves code
documentation. Strict mode enables all type checking features, providing maximum
safety. Type hints on public interfaces make APIs self-documenting and enable
better IDE support with autocomplete and refactoring.

### pytest: -q --maxfail=1 --disable-warnings -x; AAA test structure; Given_When_Should naming

**Why:** These flags make test runs faster and stop on first failure for quicker
feedback. AAA (Arrange, Act, Assert) structure makes tests readable and
maintainable. Given_When_Should naming clearly communicates test scenarios and
expected outcomes, making test failures easier to understand.

### coverage: pytest --cov=src --cov-fail-under=90 (domain code gate)

**Why:** High test coverage on domain logic ensures your core business rules are
protected against regressions. The 90% threshold balances thoroughness with
practicality. Focusing on src/ directory excludes test code from coverage
calculations.

### pre-commit: run ruff, mypy (fast), markdownlint, yaml-lint; use rumdl for markdown

**Why:** Pre-commit hooks catch issues before they reach CI, saving time and
preventing broken builds. Running fast checks locally provides immediate
feedback. Including documentation linting ensures consistent documentation. For
Python projects, use `uvx rumdl check .` to lint markdown files without
additional dependencies—rumdl is fast, opinionated, and integrates seamlessly
with uv-based workflows
quality.

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

### structlog JSON logger; add context via processors; never print() in production

**Why:** structlog provides structured logging that's queryable in log
aggregation systems. Processors allow you to add consistent context (timestamps,
service info) to all log entries. JSON format integrates seamlessly with
CloudWatch Logs Insights and other tools. print() statements are not captured by
logging systems and lack context.

**Context Logging is Critical:** Adding context into the call stack (or
equivalent in async code) is essential for producing meaningful logs. When a
line is logged, we should see the context (what operation, which user, what
request) as structured properties, not just the log message.

```python
import structlog
import contextvars
import traceback
import uuid
from typing import Any, Dict
from aws_lambda_powertools import Logger

# Context variables for async context propagation
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar('request_id')
user_id_var: contextvars.ContextVar[str] = contextvars.ContextVar('user_id')
operation_var: contextvars.ContextVar[str] = contextvars.ContextVar('operation')

# Custom processors (equivalent to Serilog enrichers)
def add_request_context(logger, method_name, event_dict):
    """Add request context to all log entries"""
    try:
        event_dict['request_id'] = request_id_var.get()
    except LookupError:
        pass

    try:
        event_dict['user_id'] = user_id_var.get()
    except LookupError:
        pass

    try:
        event_dict['operation'] = operation_var.get()
    except LookupError:
        pass

    return event_dict

def add_exception_context(logger, method_name, event_dict):
    """Enhanced exception logging with full context"""
    if 'exception' in event_dict:
        exc = event_dict['exception']
        event_dict.update({
            'exception_type': exc.__class__.__name__,
            'exception_module': exc.__class__.__module__,
            'exception_traceback': traceback.format_exception(type(exc), exc, exc.__traceback__),
            'exception_cause': str(exc.__cause__) if exc.__cause__ else None,
            'exception_context': str(exc.__context__) if exc.__context__ else None,
        })
    return event_dict

def add_service_context(logger, method_name, event_dict):
    """Add service-level context"""
    import os
    event_dict.update({
        'service_name': os.getenv('SERVICE_NAME', 'unknown'),
        'service_version': os.getenv('SERVICE_VERSION', '1.0.0'),
        'environment': os.getenv('ENVIRONMENT', 'development'),
        'aws_region': os.getenv('AWS_REGION', 'us-east-1'),
    })
    return event_dict

# Configure structlog with comprehensive processors
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        add_service_context,  # Custom processor
        add_request_context,  # Custom processor
        add_exception_context,  # Custom processor
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Context manager for operation context
from contextlib import contextmanager

@contextmanager
def log_context(**kwargs):
    """Add context that flows through the entire operation"""
    tokens = []
    for key, value in kwargs.items():
        if key == 'request_id':
            tokens.append(request_id_var.set(value))
        elif key == 'user_id':
            tokens.append(user_id_var.set(value))
        elif key == 'operation':
            tokens.append(operation_var.set(value))

    try:
        yield
    finally:
        for token in tokens:
            try:
                token.var.reset(token)
            except LookupError:
                pass

# Service implementation with context logging
class OrderService:
    def __init__(self):
        self.logger = structlog.get_logger(__name__)

    async def process_order(self, order_data: dict, user_id: str) -> dict:
        request_id = str(uuid.uuid4())

        # Set context for the entire operation
        with log_context(
            request_id=request_id,
            user_id=user_id,
            operation="process_order"
        ):
            # Bind additional context to this logger instance
            log = self.logger.bind(
                order_amount=order_data.get('amount'),
                item_count=len(order_data.get('items', [])),
                payment_method=order_data.get('payment_method')
            )

            log.info("Starting order processing",
                    user_id=user_id,
                    amount=order_data.get('amount'))

            try:
                # Validate order
                await self._validate_order(order_data, log)

                # Process payment
                payment_result = await self._process_payment(order_data, log)

                # Create order
                order = await self._create_order(order_data, payment_result, log)

                log.info("Order processed successfully",
                        order_id=order['id'],
                        final_amount=order['amount'])

                # Log business event
                self._log_business_event("order_created", {
                    "order_id": order['id'],
                    "amount": order['amount'],
                    "user_id": user_id
                })

                return order

            except ValidationError as e:
                log.warning("Order validation failed",
                           validation_errors=e.errors,
                           exception=e)
                raise
            except PaymentError as e:
                log.error("Payment processing failed",
                         payment_error_code=e.error_code,
                         exception=e)
                raise
            except Exception as e:
                log.error("Unexpected error processing order",
                         exception=e,
                         exc_info=True)
                raise

    async def _validate_order(self, order_data: dict, log):
        """Validate order with context logging"""
        with log_context(operation="validate_order"):
            validation_log = log.bind(validation_step="order_validation")

            validation_log.debug("Starting order validation")

            if not order_data.get('items'):
                validation_log.warning("Order validation failed: no items")
                raise ValidationError("Order must contain at least one item")

            if order_data.get('amount', 0) <= 0:
                validation_log.warning("Order validation failed: invalid amount")
                raise ValidationError("Order amount must be positive")

            validation_log.debug("Order validation completed successfully")

    async def _process_payment(self, order_data: dict, log):
        """Process payment with context logging"""
        with log_context(operation="process_payment"):
            payment_log = log.bind(
                payment_method=order_data.get('payment_method'),
                payment_amount=order_data.get('amount')
            )

            payment_log.info("Processing payment")

            # Simulate payment processing
            payment_result = {
                'id': str(uuid.uuid4()),
                'status': 'completed',
                'amount': order_data['amount']
            }

            payment_log.info("Payment processed successfully",
                           payment_id=payment_result['id'])

            return payment_result

    def _log_business_event(self, event_name: str, event_data: dict):
        """Log business events with special context"""
        business_log = self.logger.bind(
            event_type="business",
            event_name=event_name
        )

        business_log.info(f"Business event: {event_name}", **event_data)

# Lambda handler with context
from aws_lambda_powertools import Logger as PowertoolsLogger
from aws_lambda_powertools.utilities.typing import LambdaContext

# Combine structlog with Lambda Powertools
powertools_logger = PowertoolsLogger()

def lambda_handler(event: dict, context: LambdaContext) -> dict:
    request_id = context.aws_request_id

    # Set up context for the entire request
    with log_context(
        request_id=request_id,
        operation="lambda_handler"
    ):
        log = structlog.get_logger().bind(
            lambda_request_id=context.aws_request_id,
            function_name=context.function_name,
            remaining_time_ms=context.get_remaining_time_in_millis()
        )

        log.info("Lambda invocation started")

        try:
            # Extract user context
            user_id = event.get('requestContext', {}).get('authorizer', {}).get('userId')

            if user_id:
                with log_context(user_id=user_id):
                    order_service = OrderService()
                    result = await order_service.process_order(event['body'], user_id)

                    log.info("Lambda invocation completed successfully")
                    return {
                        'statusCode': 200,
                        'body': json.dumps(result)
                    }
            else:
                log.warning("No user ID found in request context")
                return {
                    'statusCode': 401,
                    'body': json.dumps({'error': 'Unauthorized'})
                }

        except Exception as e:
            log.error("Lambda invocation failed",
                     exception=e,
                     exc_info=True)
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'Internal server error'})
            }

### Log comprehensive startup metadata on boot and daily

**Why:** Startup logging provides critical debugging information when issues occur days or weeks after deployment. For systems with log rotation, daily logging ensures metadata is always available even if the service runs longer than log retention periods.

```python
import os
import sys
import platform
import socket
import json
from datetime import datetime
import boto3
import structlog

logger = structlog.get_logger()

def log_startup_metadata():
    """Log comprehensive startup metadata for debugging and operations."""
    
    # Runtime information
    runtime_info = {
        'python_version': sys.version,
        'platform': platform.platform(),
        'architecture': platform.machine(),
        'hostname': socket.gethostname(),
        'process_id': os.getpid(),
        'working_directory': os.getcwd(),
        'startup_time': datetime.utcnow().isoformat()
    }
    
    # Application metadata
    app_info = {
        'service_name': os.getenv('SERVICE_NAME', 'unknown'),
        'version': os.getenv('APP_VERSION', 'unknown'),
        'environment': os.getenv('ENVIRONMENT', 'unknown'),
        'build_commit': os.getenv('BUILD_COMMIT', 'unknown'),
        'build_time': os.getenv('BUILD_TIME', 'unknown')
    }
    
    # AWS metadata (if available)
    aws_info = {}
    try:
        # ECS metadata
        if os.getenv('ECS_CONTAINER_METADATA_URI_V4'):
            # Get ECS task metadata
            import requests
            metadata_uri = os.getenv('ECS_CONTAINER_METADATA_URI_V4')
            response = requests.get(f"{metadata_uri}/task", timeout=2)
            if response.status_code == 200:
                task_metadata = response.json()
                aws_info.update({
                    'ecs_cluster': task_metadata.get('Cluster'),
                    'ecs_task_arn': task_metadata.get('TaskARN'),
                    'ecs_family': task_metadata.get('Family'),
                    'ecs_revision': task_metadata.get('Revision'),
                    'availability_zone': task_metadata.get('AvailabilityZone')
                })
        
        # Lambda metadata
        if os.getenv('AWS_LAMBDA_FUNCTION_NAME'):
            aws_info.update({
                'lambda_function_name': os.getenv('AWS_LAMBDA_FUNCTION_NAME'),
                'lambda_function_version': os.getenv('AWS_LAMBDA_FUNCTION_VERSION'),
                'lambda_runtime': os.getenv('AWS_EXECUTION_ENV'),
                'lambda_memory_size': os.getenv('AWS_LAMBDA_FUNCTION_MEMORY_SIZE')
            })
        
        # General AWS metadata
        aws_info.update({
            'aws_region': os.getenv('AWS_REGION', os.getenv('AWS_DEFAULT_REGION')),
            'aws_account_id': boto3.client('sts').get_caller_identity().get('Account') if boto3 else None
        })
    except Exception as e:
        aws_info['metadata_error'] = str(e)
    
    # Environment variables (sanitized)
    env_vars = {
        k: v for k, v in os.environ.items() 
        if not any(secret in k.upper() for secret in [
            'PASSWORD', 'SECRET', 'KEY', 'TOKEN', 'CREDENTIAL'
        ])
    }
    
    # Log startup information
    logger.info(
        "Service startup",
        event_type="service_startup",
        runtime=runtime_info,
        application=app_info,
        aws=aws_info,
        environment_variables=env_vars
    )

def schedule_daily_metadata_logging():
    """Schedule daily metadata logging for log rotation systems."""
    import schedule
    import threading
    import time
    
    def daily_metadata_log():
        logger.info(
            "Daily metadata refresh",
            event_type="daily_metadata",
            timestamp=datetime.utcnow().isoformat(),
            uptime_seconds=time.time() - startup_time
        )
        log_startup_metadata()
    
    # Schedule for 00:00:01 daily
    schedule.every().day.at("00:00:01").do(daily_metadata_log)
    
    def run_scheduler():
        while True:
            schedule.run_pending()
            time.sleep(60)
    
    # Run scheduler in background thread
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()

# Call at application startup
startup_time = time.time()
log_startup_metadata()
schedule_daily_metadata_logging()
```

**Key Benefits:**
- **Debugging support**: Runtime versions, environment, and AWS context available in logs
- **Deployment tracking**: Build commit, version, and deployment time logged
- **Environment validation**: Confirms correct environment variables and AWS setup
- **Log rotation resilience**: Daily logging ensures metadata survives log retention periods
- **Security conscious**: Automatically filters sensitive environment variables

**For log rotation systems**: Daily metadata logging (scheduled for 00:00:01) ensures startup information is always available in logs, even for long-running services that exceed log retention periods.

# Middleware for web frameworks (FastAPI example)
from fastapi import FastAPI, Request
import time

app = FastAPI()

@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))

    with log_context(
        request_id=request_id,
        operation="http_request"
    ):
        log = structlog.get_logger().bind(
            method=request.method,
            url=str(request.url),
            user_agent=request.headers.get("user-agent"),
            client_ip=request.client.host
        )

        start_time = time.time()

        try:
            response = await call_next(request)

            duration_ms = (time.time() - start_time) * 1000

            log.info("Request completed",
                    status_code=response.status_code,
                    duration_ms=round(duration_ms, 2))

            response.headers["x-request-id"] = request_id
            return response

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000

            log.error("Request failed",
                     duration_ms=round(duration_ms, 2),
                     exception=e)
            raise
```

**Key Processor Benefits:**

- **add_request_context()**: Automatically adds request/user context to all log
  entries
- **add_exception_context()**: Provides rich exception information including
  cause chains and full tracebacks
- **add_service_context()**: Adds service-level metadata for better log
  aggregation
- **Context Variables**: Enable context to flow through async operations
  seamlessly

**Context Logging Best Practices:**

- Use `contextvars` for async-safe context propagation
- Implement custom processors to add consistent context
- Use `log_context()` context manager for operation-scoped context
- Bind additional context to logger instances for specific operations
- Log business events with special context for analytics and monitoring

### Include: service name, version, env, trace ids, customer/account id (if safe)

**Why:** Service name and version help identify which service and deployment
generated logs. Environment information prevents confusion between
dev/staging/prod logs. Trace IDs enable correlation across distributed systems.
Customer/account IDs help with support and debugging, but must be handled
carefully for privacy compliance.

### OpenTelemetry: SDK, instrumentation, exporters; propagate context across threads/async

**Why:** OpenTelemetry provides vendor-neutral observability that works across
different tools and cloud providers. Automatic instrumentation for boto3 and
other libraries reduces manual work. Context propagation ensures trace
continuity across async operations and thread boundaries, which is crucial for
understanding request flows in concurrent systems.

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.boto3 import Boto3Instrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

# Configure tracing
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

# Add exporters
otlp_exporter = OTLPSpanExporter(endpoint="http://localhost:4317")
span_processor = BatchSpanProcessor(otlp_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

# Auto-instrument libraries
Boto3Instrumentor().instrument()
RequestsInstrumentor().instrument()

# Manual tracing
@tracer.start_as_current_span("process_payment")
def process_payment(payment_data: dict):
    span = trace.get_current_span()
    span.set_attribute("payment.amount", payment_data["amount"])
    span.set_attribute("payment.currency", payment_data["currency"])

    # Business logic here
    return {"status": "success"}

# Context propagation in async code
import asyncio
from opentelemetry.context import attach, detach

async def async_operation():
    token = attach(trace.set_span_in_context(trace.get_current_span()))
    try:
        # Async work here - context is preserved
        await asyncio.sleep(0.1)
    finally:
        detach(token)
```

- `structlog` JSON logger; add context via processors; never print() in
  production paths.
- Include: service name, version, env, trace ids, customer/account id (if safe).
- OTEL:
  - `opentelemetry-sdk`, `opentelemetry-instrumentation-boto3`,
    `opentelemetry-exporter-otlp` or AWS X-Ray exporter.
  - Always propagate context across threads and async tasks.

---

## 4. AWS Conventions

### Config: read from SSM Parameter Store at boot, cache in-memory; refresh on timer

**Why:** SSM Parameter Store provides centralized, encrypted configuration
management with fine-grained IAM control. Reading at boot reduces API calls and
improves performance. In-memory caching prevents repeated API calls during
request processing. Timer-based refresh allows configuration updates without
redeployment while maintaining performance.

```python
import boto3
import threading
import time
from typing import Dict, Any
from dataclasses import dataclass

@dataclass
class Config:
    database_url: str
    api_timeout: int
    feature_flags: Dict[str, bool]

class ConfigManager:
    def __init__(self, parameter_prefix: str = "/myapp/"):
        self.ssm = boto3.client('ssm')
        self.parameter_prefix = parameter_prefix
        self._config: Config = None
        self._lock = threading.Lock()
        self._refresh_thread = None
        self.refresh_config()
        self._start_refresh_timer()

    def refresh_config(self):
        """Refresh configuration from SSM Parameter Store"""
        try:
            response = self.ssm.get_parameters_by_path(
                Path=self.parameter_prefix,
                Recursive=True,
                WithDecryption=True
            )

            params = {p['Name'].replace(self.parameter_prefix, ''): p['Value']
                     for p in response['Parameters']}

            with self._lock:
                self._config = Config(
                    database_url=params.get('database_url', ''),
                    api_timeout=int(params.get('api_timeout', '30')),
                    feature_flags={
                        'new_feature': params.get('feature_flags/new_feature', 'false').lower() == 'true'
                    }
                )
        except Exception as e:
            logger.error("Failed to refresh config", error=str(e))

    def _start_refresh_timer(self):
        """Start background timer to refresh config every 5 minutes"""
        def refresh_loop():
            while True:
                time.sleep(300)  # 5 minutes
                self.refresh_config()

        self._refresh_thread = threading.Thread(target=refresh_loop, daemon=True)
        self._refresh_thread.start()

    @property
    def config(self) -> Config:
        with self._lock:
            return self._config

# Usage
config_manager = ConfigManager()

def get_database_connection():
    return create_connection(config_manager.config.database_url)
```

### Feature Flags: AppConfig with JSON schema validators; stage-aware

**Why:** AppConfig provides safe feature flag deployment with rollback
capabilities and gradual rollouts. JSON schema validation prevents invalid
configurations from breaking your application. Stage-aware flags allow different
behavior in dev/staging/prod environments, enabling safe testing of new
features.

### Queueing: SNS → SQS (never raw SQS); FIFO for ordered work + DLQ

**Why:** SNS provides fan-out capabilities and decouples publishers from
consumers, making your architecture more flexible. Raw SQS creates tight
coupling between services. FIFO queues ensure message ordering when required
(like financial transactions). Dead Letter Queues capture failed messages for
analysis and prevent infinite retry loops.

### KMS: use GenerateDataKey and Sign/Verify; never manage raw keys

**Why:** GenerateDataKey provides envelope encryption, which is more secure and
performant than encrypting data directly with KMS keys. Sign/Verify operations
provide digital signatures for data integrity. Managing raw keys increases
security risk and complexity - let AWS handle key management.

### S3: set bucket policies, SSE-S3 or SSE-KMS; object versioning on critical data

**Why:** Bucket policies provide defense-in-depth security beyond IAM roles.
Server-side encryption protects data at rest. SSE-KMS provides additional audit
trails and key rotation capabilities. Object versioning protects against
accidental deletion or corruption of critical data.

### IAM: per-service roles, least privilege; VPC endpoints for AWS APIs where possible

**Why:** Per-service roles limit blast radius if credentials are compromised.
Least privilege reduces attack surface and prevents accidental access to
unrelated resources. VPC endpoints keep AWS API traffic within your VPC,
improving security and potentially reducing data transfer costs.

---

## 5. Lambda Guidance

### Runtime: python3.13, arm64; keep handler tiny

**Why:** Python 3.13 provides the latest performance improvements and security
fixes. ARM64 (Graviton) offers 20% better price-performance compared to x86.
Tiny handlers reduce cold start times and make functions easier to test, debug,
and understand. Large handlers often indicate poor separation of concerns.

### Imports: move heavy imports behind functions; use layers for scientific libs

**Why:** Heavy imports during module initialization increase cold start times.
Moving imports inside functions (lazy loading) defers the cost until the
functionality is actually needed. Layers allow sharing large dependencies (like
numpy, pandas) across multiple functions while keeping individual deployment
packages small.

```python

# ❌ Bad - Heavy imports at module level
import pandas as pd
import numpy as np
import tensorflow as tf
from aws_lambda_powertools import Logger

logger = Logger()

def lambda_handler(event, context):
    # Function logic here
    pass

# ✅ Good - Lazy imports
from aws_lambda_powertools import Logger

logger = Logger()

def lambda_handler(event, context):
    event_type = event.get('type')

    if event_type == 'data_processing':
        # Only import when needed
        import pandas as pd
        import numpy as np
        return process_data_with_pandas(event['data'])

    elif event_type == 'ml_inference':
        # Heavy ML libraries only loaded when needed
        import tensorflow as tf
        return run_inference(event['input'])

    else:
        # Simple operations don't need heavy imports
        return {'status': 'success', 'message': 'Event processed'}

def process_data_with_pandas(data):
    import pandas as pd  # Import at function level
    df = pd.DataFrame(data)
    return df.to_dict()

# Layer structure for scientific libraries

# layers/

# └── python-scientific/

#     └── python/

#         └── lib/

#             └── python3.13/

#                 └── site-packages/

#                     ├── numpy/

#                     ├── pandas/

#                     └── scipy/
```

### Powertools: logger, tracer, metrics, idempotency utility, parser

**Why:** Lambda Powertools provides battle-tested utilities that handle common
patterns correctly. The logger integrates with CloudWatch and X-Ray. Tracer
provides distributed tracing. Metrics integrate with CloudWatch. Idempotency
utility prevents duplicate processing. Parser validates and transforms event
data safely.

```python
from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.utilities.idempotency import idempotent
from aws_lambda_powertools.utilities.parser import parse
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.metrics import MetricUnit
from pydantic import BaseModel

logger = Logger()
tracer = Tracer()
metrics = Metrics()

# Event parsing with validation
class OrderEvent(BaseModel):
    order_id: str
    customer_id: str
    amount: float
    currency: str

@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics
@idempotent(persistence_store=DynamoDBPersistenceLayer(table_name="idempotency"))
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    # Parse and validate event
    order_event = parse(event=event, model=OrderEvent)

    # Add custom metrics
    metrics.add_metric(name="OrderProcessed", unit=MetricUnit.Count, value=1)
    metrics.add_metric(name="OrderAmount", unit=MetricUnit.None, value=order_event.amount)

    # Add tracing metadata
    tracer.put_metadata(key="order_id", value=order_event.order_id)
    tracer.put_annotation(key="currency", value=order_event.currency)

    # Structured logging with context
    logger.info("Processing order", extra={
        "order_id": order_event.order_id,
        "customer_id": order_event.customer_id,
        "amount": order_event.amount
    })

    try:
        result = process_order(order_event)
        logger.info("Order processed successfully", extra={"result": result})
        return {"statusCode": 200, "body": result}

    except Exception as e:
        logger.exception("Order processing failed")
        metrics.add_metric(name="OrderProcessingError", unit=MetricUnit.Count, value=1)
        raise

@tracer.capture_method
def process_order(order: OrderEvent) -> dict:
    # Business logic here
    return {"status": "processed", "order_id": order.order_id}
```

### Timeouts: set < 30s unless required; configure reserved concurrency

**Why:** Short timeouts prevent runaway functions from consuming resources and
billing. Most business logic should complete quickly - long timeouts often
indicate architectural issues. Reserved concurrency prevents one function from
consuming all available concurrency and affecting other functions.

### Retries & DLQ: configure per trigger (SQS/SNS/EventBridge)

**Why:** Different event sources have different retry semantics and failure
modes. SQS provides built-in retry with visibility timeout. SNS retries are
limited. EventBridge has its own retry configuration. Dead Letter Queues capture
failed events for analysis and manual processing.

### Use asyncio sparingly; Lambda concurrency is the scaler

**Why:** Lambda's concurrency model handles scaling automatically by running
multiple instances. Adding asyncio complexity within a single Lambda often
provides minimal benefit while making code harder to debug. Use asyncio only
when you have genuine concurrent I/O within a single request.

---

## 6. HTTP Clients & Retries

### Use requests or httpx (async). Set timeouts and retries with jitter

**Why:** Both requests and httpx are mature, well-tested HTTP clients. Timeouts
prevent hanging requests that can exhaust connection pools and Lambda execution
time. Retries with exponential backoff and jitter handle transient failures
gracefully while avoiding thundering herd problems that can overwhelm downstream
services.

### For AWS SDK: set botocore.config.Config (retries, timeouts, user_agent)

**Why:** The default boto3 configuration may not be optimal for your use case.
Custom retry configuration handles AWS service throttling appropriately.
Timeouts prevent long-running AWS API calls from consuming Lambda execution
time. Custom user agents help AWS support identify your application in logs and
metrics.

```python
import boto3
from botocore.config import Config
from tenacity import retry, stop_after_attempt, wait_exponential_jitter

# Configure boto3 with custom settings
config = Config(
    retries={
        'max_attempts': 3,
        'mode': 'adaptive'  # or 'standard'
    },
    connect_timeout=5,
    read_timeout=10,
    user_agent_extra='MyApp/1.0.0'
)

s3_client = boto3.client('s3', config=config)
dynamodb = boto3.resource('dynamodb', config=config)

# HTTP client with retries and jitter
@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential_jitter(initial=0.2, max=5.0)
)
def call_external_api(url: str, data: dict) -> dict:
    import requests

    response = requests.post(
        url,
        json=data,
        timeout=(5, 30),  # (connect_timeout, read_timeout)
        headers={'User-Agent': 'MyApp/1.0.0'}
    )
    response.raise_for_status()
    return response.json()

# Usage with proper error handling
def upload_to_s3(bucket: str, key: str, data: bytes):
    try:
        s3_client.put_object(
            Bucket=bucket,
            Key=key,
            Body=data,
            ServerSideEncryption='AES256'
        )
        logger.info("File uploaded successfully", extra={"bucket": bucket, "key": key})
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NoSuchBucket':
            logger.error("Bucket does not exist", extra={"bucket": bucket})
        else:
            logger.error("S3 upload failed", extra={"error": error_code})
        raise
```

```python
from tenacity import retry, stop_after_attempt, wait_exponential_jitter

@retry(stop=stop_after_attempt(5), wait=wait_exponential_jitter(0.2, 5))
def call_api(...): ...
```

---

## 7. Testing

### Unit tests: pytest, AAA, Given_When_Should, isolate IO; use fakes not real AWS

**Why:** pytest is the most popular Python testing framework with excellent
plugin ecosystem. AAA structure makes tests readable and maintainable.
Given_When_Should naming clearly communicates test scenarios. Isolating I/O
makes tests fast and reliable. Fakes provide predictable behavior without
external dependencies or costs.

```python
import pytest
from unittest.mock import Mock, patch
from dataclasses import dataclass
from typing import Protocol

# Test structure with AAA and Given_When_Should naming
class TestOrderProcessor:

    def test_given_valid_order_when_processing_should_return_success(self):
        # Arrange
        mock_payment_service = Mock()
        mock_payment_service.process_payment.return_value = {"status": "success"}

        processor = OrderProcessor(payment_service=mock_payment_service)
        order = Order(id="123", amount=100.0, currency="USD")

        # Act
        result = processor.process_order(order)

        # Assert
        assert result["status"] == "processed"
        assert result["order_id"] == "123"
        mock_payment_service.process_payment.assert_called_once_with(order.amount, order.currency)

    def test_given_payment_failure_when_processing_should_raise_payment_error(self):
        # Arrange
        mock_payment_service = Mock()
        mock_payment_service.process_payment.side_effect = PaymentError("Card declined")

        processor = OrderProcessor(payment_service=mock_payment_service)
        order = Order(id="123", amount=100.0, currency="USD")

        # Act & Assert
        with pytest.raises(PaymentError, match="Card declined"):
            processor.process_order(order)

# Fake implementations instead of mocks for complex behavior
class FakeS3Client:
    def __init__(self):
        self.objects = {}

    def put_object(self, Bucket: str, Key: str, Body: bytes):
        self.objects[f"{Bucket}/{Key}"] = Body

    def get_object(self, Bucket: str, Key: str):
        key = f"{Bucket}/{Key}"
        if key not in self.objects:
            raise ClientError({'Error': {'Code': 'NoSuchKey'}}, 'GetObject')
        return {'Body': Mock(read=lambda: self.objects[key])}

# Dependency injection for testability
class PaymentServiceProtocol(Protocol):
    def process_payment(self, amount: float, currency: str) -> dict: ...

@dataclass
class Order:
    id: str
    amount: float
    currency: str

class OrderProcessor:
    def __init__(self, payment_service: PaymentServiceProtocol):
        self.payment_service = payment_service

    def process_order(self, order: Order) -> dict:
        payment_result = self.payment_service.process_payment(order.amount, order.currency)
        if payment_result["status"] != "success":
            raise PaymentError("Payment failed")

        return {"status": "processed", "order_id": order.id}

# Property-based testing with hypothesis
from hypothesis import given, strategies as st

@given(
    order_id=st.text(min_size=1, max_size=50),
    amount=st.floats(min_value=0.01, max_value=10000.0),
    currency=st.sampled_from(["USD", "EUR", "GBP"])
)
def test_order_processing_with_various_inputs(order_id, amount, currency):
    mock_payment_service = Mock()
    mock_payment_service.process_payment.return_value = {"status": "success"}

    processor = OrderProcessor(payment_service=mock_payment_service)
    order = Order(id=order_id, amount=amount, currency=currency)

    result = processor.process_order(order)

    assert result["status"] == "processed"
    assert result["order_id"] == order_id
```

### Integration: testcontainers for MySQL/Redis; moto only for fast, non-critical mocks

**Why:** testcontainers spin up real database instances in Docker, ensuring your
integration tests run against the same technology as production. This catches
integration issues that mocks might miss. moto is useful for simple AWS service
mocking but doesn't perfectly replicate AWS behavior, so use it judiciously.

### Contract: Pact for consumer/provider contracts with BFF/API

**Why:** Contract tests ensure that service interfaces remain compatible as they
evolve independently. Pact enables consumer-driven contracts, putting the
consumer in control of what they need and preventing breaking changes. This is
crucial for microservice architectures where services are developed by different
teams.

### Property-based: hypothesis for critical validators/parsers

**Why:** Property-based testing generates many test cases automatically, often
finding edge cases that manual testing misses. This is especially valuable for
validators and parsers that handle user input, where unexpected inputs can cause
security vulnerabilities or data corruption.

### Mutation: mutmut if needed (target domain modules)

**Why:** Mutation testing validates the quality of your tests by introducing
small changes to your code and checking if tests catch them. This ensures your
tests actually verify the behavior they claim to test, not just achieve code
coverage through execution. Focus on domain modules where business logic is most
critical.

---

## 8. Security

### bandit + osv-scanner (or pip-audit) in CI

**Why:** bandit performs static analysis to find common security issues in
Python code like hardcoded passwords, SQL injection vulnerabilities, and unsafe
function usage. osv-scanner and pip-audit check for known vulnerabilities in
your dependencies. Running these in CI catches security issues before they reach
production.

### No pickle or unsafe yaml.load; use safe_load

**Why:** pickle can execute arbitrary code during deserialization, making it a
security risk when handling untrusted data. yaml.load has similar issues.
yaml.safe_load only loads basic YAML types, preventing code execution attacks.
These practices prevent remote code execution vulnerabilities.

```python
import yaml
import json
from typing import Any, Dict

# ❌ Bad - Unsafe deserialization
def load_config_unsafe(config_data: str) -> Dict[str, Any]:
    return yaml.load(config_data, Loader=yaml.Loader)  # Can execute code!

def deserialize_data_unsafe(data: bytes) -> Any:
    import pickle
    return pickle.loads(data)  # Can execute arbitrary code!

# ✅ Good - Safe deserialization
def load_config_safe(config_data: str) -> Dict[str, Any]:
    return yaml.safe_load(config_data)  # Only loads basic types

def deserialize_data_safe(data: str) -> Dict[str, Any]:
    return json.loads(data)  # Safe JSON parsing

# Example of safe configuration loading
def load_application_config(config_path: str) -> Dict[str, Any]:
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        # Validate config structure
        required_keys = ['database_url', 'api_key', 'timeout']
        for key in required_keys:
            if key not in config:
                raise ValueError(f"Missing required config key: {key}")

        return config

    except yaml.YAMLError as e:
        logger.error("Invalid YAML configuration", error=str(e))
        raise
    except FileNotFoundError:
        logger.error("Configuration file not found", path=config_path)
        raise

# Safe data serialization alternatives
from dataclasses import dataclass, asdict
import json

@dataclass
class UserData:
    user_id: str
    email: str
    preferences: Dict[str, Any]

def serialize_user_data(user: UserData) -> str:
    """Serialize using JSON instead of pickle"""
    return json.dumps(asdict(user))

def deserialize_user_data(data: str) -> UserData:
    """Deserialize safely from JSON"""
    user_dict = json.loads(data)
    return UserData(**user_dict)
```

### Secrets from env/SSM only; never in code, never in Git

**Why:** Hardcoded secrets in code can be accidentally exposed through version
control, logs, or error messages. Environment variables and SSM Parameter Store
provide secure ways to inject secrets at runtime. This follows the principle of
separating configuration from code and reduces the risk of credential exposure.

### Validate all inputs; centralize authN/authZ if building services

**Why:** Input validation prevents injection attacks, data corruption, and
unexpected application behavior. Centralizing authentication and authorization
logic makes it easier to maintain security policies consistently and reduces the
risk of security bugs from scattered auth code.

---

## 9. Performance

### Prefer dataclasses(slots=True) or attrs for hot-path objects; but Pydantic v2 when validation is required

**Why:** dataclasses with slots reduce memory usage and improve attribute access
speed by using a more efficient storage mechanism. attrs provides similar
benefits with more features. However, when you need data validation, Pydantic v2
provides excellent performance while ensuring data integrity. Choose the right
tool based on whether you need validation.

```python
from dataclasses import dataclass
from typing import Optional
import attrs
from pydantic import BaseModel, validator

# ✅ dataclasses with slots for performance-critical code
@dataclass(slots=True, frozen=True)
class Point:
    x: float
    y: float

    def distance_to(self, other: 'Point') -> float:
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5

# ✅ attrs for more features
@attrs.define(slots=True, frozen=True)
class User:
    id: str
    email: str
    age: Optional[int] = None

    @age.validator
    def _validate_age(self, attribute, value):
        if value is not None and (value < 0 or value > 150):
            raise ValueError("Age must be between 0 and 150")

# ✅ Pydantic v2 when validation is critical
class OrderRequest(BaseModel):
    order_id: str
    customer_id: str
    amount: float
    currency: str
    items: list[str]

    @validator('amount')
    def amount_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Amount must be positive')
        return v

    @validator('currency')
    def currency_must_be_valid(cls, v):
        valid_currencies = {'USD', 'EUR', 'GBP', 'JPY'}
        if v not in valid_currencies:
            raise ValueError(f'Currency must be one of {valid_currencies}')
        return v

# Performance comparison example
def process_many_points_fast():
    """Using slots=True dataclass for hot path"""
    points = [Point(x=i, y=i*2) for i in range(10000)]
    total_distance = 0.0

    for i in range(len(points) - 1):
        total_distance += points[i].distance_to(points[i + 1])

    return total_distance

def validate_order_data(raw_data: dict) -> OrderRequest:
    """Using Pydantic when validation is needed"""
    try:
        return OrderRequest(**raw_data)
    except ValidationError as e:
        logger.error("Invalid order data", errors=e.errors())
        raise
```

### Avoid global state; use dependency injection via constructors or providers

**Why:** Global state makes code harder to test, debug, and reason about. It can
cause issues in concurrent environments and makes it difficult to isolate
components. Dependency injection makes dependencies explicit, improves
testability, and makes code more modular and maintainable.

```python
from typing import Protocol
from dataclasses import dataclass

# ❌ Bad - Global state
DATABASE_CONNECTION = None
CACHE_CLIENT = None

def process_order(order_id: str):
    # Hidden dependencies on global state
    order = DATABASE_CONNECTION.get_order(order_id)
    cached_data = CACHE_CLIENT.get(f"order:{order_id}")
    # ... processing logic

# ✅ Good - Dependency injection via constructor
class DatabaseProtocol(Protocol):
    def get_order(self, order_id: str) -> dict: ...
    def save_order(self, order: dict) -> None: ...

class CacheProtocol(Protocol):
    def get(self, key: str) -> Optional[str]: ...
    def set(self, key: str, value: str, ttl: int = 300) -> None: ...

@dataclass
class OrderService:
    database: DatabaseProtocol
    cache: CacheProtocol
    logger: Logger

    def process_order(self, order_id: str) -> dict:
        # Dependencies are explicit and testable
        self.logger.info("Processing order", order_id=order_id)

        # Try cache first
        cached_order = self.cache.get(f"order:{order_id}")
        if cached_order:
            return json.loads(cached_order)

        # Fetch from database
        order = self.database.get_order(order_id)

        # Cache for future requests
        self.cache.set(f"order:{order_id}", json.dumps(order))

        return order

# Dependency provider pattern
class ServiceProvider:
    def __init__(self):
        self._database = self._create_database()
        self._cache = self._create_cache()
        self._logger = self._create_logger()

    def _create_database(self) -> DatabaseProtocol:
        # Database setup logic
        return PostgreSQLDatabase(connection_string=get_db_url())

    def _create_cache(self) -> CacheProtocol:
        # Cache setup logic
        return RedisCache(host=get_redis_host())

    def _create_logger(self) -> Logger:
        return structlog.get_logger()

    def create_order_service(self) -> OrderService:
        return OrderService(
            database=self._database,
            cache=self._cache,
            logger=self._logger
        )

# Usage in Lambda handler
provider = ServiceProvider()
order_service = provider.create_order_service()

def lambda_handler(event, context):
    order_id = event['order_id']
    return order_service.process_order(order_id)

# Easy testing with dependency injection
def test_order_service_uses_cache():
    # Arrange
    mock_db = Mock(spec=DatabaseProtocol)
    mock_cache = Mock(spec=CacheProtocol)
    mock_cache.get.return_value = '{"id": "123", "status": "pending"}'
    mock_logger = Mock()

    service = OrderService(
        database=mock_db,
        cache=mock_cache,
        logger=mock_logger
    )

    # Act
    result = service.process_order("123")

    # Assert
    assert result["id"] == "123"
    mock_cache.get.assert_called_once_with("order:123")
    mock_db.get_order.assert_not_called()  # Should use cache, not database
```

### Profile with py-spy or scalene in containerized perf tests

**Why:** py-spy provides low-overhead profiling that works in production
environments and doesn't require code changes. scalene provides detailed memory
and CPU profiling. Running performance tests in containers ensures profiling
results reflect production conditions. Regular profiling helps identify
performance regressions before they impact users.

---

## 10. EARS Requirements

**EARS (Easy Approach to Requirements Syntax) format for Python development
requirements:**

### Ubiquitous Requirements

- The system SHALL use Python 3.13 with pinned exact versions in lockfiles
- The system SHALL use uv for dependency management and virtual environments
- The system SHALL treat warnings as errors in CI builds
- The system SHALL use structured logging with JSON output via structlog
- The system SHALL implement OpenTelemetry tracing with X-Ray export
- The system SHALL use SSM Parameter Store for configuration and secrets
- The system SHALL validate all inputs using Pydantic models where validation is
  required

### Event-Driven Requirements

- WHEN a Lambda function is invoked, the system SHALL add request context to log
  scope
- WHEN an exception occurs, the system SHALL log structured exception details
  with full traceback
- WHEN a configuration parameter changes, the system SHALL refresh cached values
  within 5 minutes
- WHEN an AWS API call fails, the system SHALL retry with exponential backoff
  and jitter
- WHEN a feature flag is toggled, the system SHALL apply changes without service
  restart

### Unwanted Behavior Requirements

- IF pickle deserialization is used, the system SHALL reject the implementation
- IF global state is detected, the system SHALL fail code review
- IF test coverage falls below 90% for domain modules, the system SHALL fail the
  build
- IF unsafe yaml.load is used, the system SHALL prevent execution
- IF secrets are hardcoded, the system SHALL fail security scanning

### State-Driven Requirements

- WHILE processing requests, the system SHALL maintain correlation context using
  contextvars
- WHILE running integration tests, the system SHALL use testcontainers for real
  dependencies
- WHILE in Lambda execution, the system SHALL use lazy imports for heavy
  dependencies
- WHILE handling async operations, the system SHALL propagate trace context

### Optional Feature Requirements

- WHERE performance is critical, the system SHOULD use dataclasses with
  slots=True
- WHERE AWS services are needed in tests, the system SHOULD use LocalStack
- WHERE complex validation is required, the system SHOULD use Pydantic v2
- WHERE caching improves performance, the system SHOULD implement Redis caching

### Complex Requirements

- WHEN a Lambda function processes an SQS message AND the message is malformed,
  the system SHALL log the error with message context, move the message to DLQ,
  and continue processing other messages
- WHEN an API request is received AND authentication is required, the system
  SHALL validate the JWT token, extract user context, add user ID to log
  context, and proceed with request processing
- WHEN a background task fails AND retry attempts are exhausted, the system
  SHALL log the failure with full context, publish a failure event to SNS, and
  update task status in the database

---

## 11. Checklists

**Why this checklist matters:** This checklist serves as a final verification
that all critical practices are implemented. Each item represents a decision
that significantly impacts code quality, maintainability, security, or
performance. Regular checklist reviews during code reviews and before releases
help ensure consistency across projects and prevent regression of important
practices.

- [ ] ruff + mypy strict pass
- [ ] pytest coverage ≥ 90% domain
- [ ] structlog JSON, OTEL traces
- [ ] SSM for config; SecretsMgr only for auto-rotation
- [ ] SNS→SQS, DLQs, idempotency keys
- [ ] CloudFormation templates validated (cfn-lint/nag)
