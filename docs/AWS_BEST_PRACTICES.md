# AWS Best Practices — Lean, High-Leverage, Low-Complexity

> Principles tailored for your stack: **ECS Fargate**, **API Gateway (HTTP)**,
> **Lambda (where it fits)**, **SNS→SQS**, **AppConfig**, **Parameter Store
> (SecureString)**, **CloudFormation**, **OpenTelemetry→X-Ray/CloudWatch**.

---

## 0. Core Principles

### Prefer SSM Parameter Store (SecureString) for secrets/config; use Secrets Manager only for auto-rotation

**Why:** Parameter Store provides encrypted configuration storage at no
additional cost for standard parameters, with fine-grained IAM control and audit
trails. SecureString parameters are encrypted with KMS keys you control. Secrets
Manager costs significantly more but provides automatic rotation capabilities,
making it ideal only when you need features like RDS password rotation. This
cost-conscious approach maintains security while optimizing spend.

### Publish events to SNS and subscribe with SQS (never produce to raw SQS)

**Why:** SNS provides fan-out capabilities that decouple publishers from
consumers, making your architecture more flexible and resilient. You can add new
consumers without modifying publishers. Raw SQS creates tight coupling between
services and makes it difficult to add new event consumers. SNS→SQS also
provides better error handling and retry capabilities through dead letter
queues.

### CloudFormation-first for all infrastructure; lint with cfn-lint + cfn-nag

**Why:** Infrastructure as Code ensures reproducible, version-controlled
deployments and prevents configuration drift. CloudFormation provides native AWS
integration and handles resource dependencies automatically. cfn-lint catches
syntax and logical errors before deployment, while cfn-nag identifies security
issues and compliance violations. This prevents costly mistakes and security
vulnerabilities in production.

### Observability by default: structured logs, metrics, traces

**Why:** Observability is essential for understanding system behavior, debugging
issues, and maintaining SLAs. Structured logs enable powerful querying and
filtering. Metrics provide quantitative insights into system health. Distributed
tracing helps understand request flows across microservices. OpenTelemetry
provides vendor-neutral instrumentation that works across different tools and
cloud providers.

### Per-service IAM roles; least privilege; tag everything for FinOps

**Why:** Per-service roles limit blast radius if credentials are compromised and
make it easier to audit access patterns. Least privilege reduces attack surface
and prevents accidental access to unrelated resources. Comprehensive tagging
enables cost allocation, resource management, and automated governance policies.
This is crucial for multi-team environments and cost optimization.

---

## 1. Config, Flags, Secrets

### Parameter Store for most app settings (namespace /org/service/env/key)

**Why:** Centralized configuration management with hierarchical namespacing
makes it easy to organize and manage settings across environments and services.
The namespace pattern prevents naming conflicts and makes it clear which service
owns which parameters. Parameter Store integrates with IAM for fine-grained
access control and provides audit trails for configuration changes.

```bash

# Example parameter structure
/myorg/user-service/prod/database_url
/myorg/user-service/prod/api_timeout
/myorg/user-service/staging/database_url
/myorg/payment-service/prod/stripe_webhook_secret
```

```yaml
# CloudFormation example
DatabaseUrlParameter:
  Type: AWS::SSM::Parameter
  Properties:
    Name: !Sub "/${OrganizationName}/${ServiceName}/${Environment}/database_url"
    Type: SecureString
    Value: !Sub "mysql://user:${DatabasePassword}@${DatabaseEndpoint}:3306/mydb"
    Description: "Database connection string for user service"
```

```python

# Python code to read parameters
import boto3

def get_config(service_name: str, env: str) -> dict:
    ssm = boto3.client('ssm')
    prefix = f"/myorg/{service_name}/{env}/"

    response = ssm.get_parameters_by_path(
        Path=prefix,
        Recursive=True,
        WithDecryption=True
    )

    return {
        param['Name'].replace(prefix, ''): param['Value']
        for param in response['Parameters']
    }
```

### AppConfig for feature flags + gradual rollouts; JSON schema validators

**Why:** AppConfig provides safe feature flag deployment with rollback
capabilities, gradual rollouts, and monitoring integration. JSON schema
validation prevents invalid configurations from breaking your application. This
enables continuous deployment with reduced risk, allowing you to test features
with small user groups before full rollout.

```json
// Feature flags configuration with schema
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "features": {
      "type": "object",
      "properties": {
        "new_checkout_flow": {
          "type": "object",
          "properties": {
            "enabled": { "type": "boolean" },
            "rollout_percentage": { "type": "number", "minimum": 0, "maximum": 100 }
          },
          "required": ["enabled", "rollout_percentage"]
        }
      }
    }
  }
}

// Example configuration
{
  "features": {
    "new_checkout_flow": {
      "enabled": true,
      "rollout_percentage": 25
    },
    "premium_features": {
      "enabled": false,
      "rollout_percentage": 0
    }
  }
}
```

```python

# Python code to use AppConfig
import boto3
import json
from typing import Dict, Any

class FeatureFlags:
    def __init__(self, application: str, environment: str, configuration: str):
        self.client = boto3.client('appconfig')
        self.application = application
        self.environment = environment
        self.configuration = configuration
        self._config = {}
        self._session_token = None

    def refresh_config(self):
        response = self.client.start_configuration_session(
            ApplicationIdentifier=self.application,
            EnvironmentIdentifier=self.environment,
            ConfigurationProfileIdentifier=self.configuration
        )
        self._session_token = response['InitialConfigurationToken']

        config_response = self.client.get_configuration(
            Application=self.application,
            Environment=self.environment,
            Configuration=self.configuration,
            ClientId='my-service-instance',
            ClientConfigurationVersion=self._session_token
        )

        self._config = json.loads(config_response['Content'].read())

    def is_feature_enabled(self, feature_name: str, user_id: str = None) -> bool:
        feature = self._config.get('features', {}).get(feature_name, {})
        if not feature.get('enabled', False):
            return False

        # Simple percentage-based rollout
        if user_id:
            user_hash = hash(user_id) % 100
            return user_hash < feature.get('rollout_percentage', 0)

        return True
```

### Secrets Manager only where rotation automation exists

**Why:** Secrets Manager's primary value is automatic rotation of credentials,
which is crucial for database passwords and API keys that need regular rotation.
For static secrets that don't require rotation, Parameter Store SecureString
provides the same encryption and access control at lower cost. This approach
optimizes costs while maintaining security.

### Cache config locally; periodic refresh; fail closed for critical toggles

**Why:** Local caching reduces API calls and improves application performance
while providing resilience against Parameter Store outages. Periodic refresh
ensures applications get configuration updates without restart. Failing closed
for critical toggles (like kill switches) ensures safe defaults when
configuration is unavailable, preventing system failures.

---

## 2. Messaging & Async

### SNS → SQS fan-out; message attributes for routing; DLQs for each consumer

**Why:** SNS fan-out enables loose coupling between publishers and consumers,
making it easy to add new consumers without modifying publishers. Message
attributes provide efficient routing without parsing message bodies. Dead Letter
Queues capture failed messages for analysis and prevent infinite retry loops,
improving system reliability and debuggability.

### SQS FIFO for ordered, per-entity processing; set visibility timeout and redrive policy

**Why:** FIFO queues ensure message ordering when required (like financial
transactions or state changes), while standard queues provide higher throughput
for order-independent processing. Proper visibility timeout prevents message
duplication while allowing sufficient processing time. Redrive policies
automatically handle failed messages after retry attempts.

### EventBridge when you need decoupled domains + schema registry

**Why:** EventBridge provides advanced routing capabilities with content-based
filtering and integrates with many AWS services out of the box. Schema registry
enables contract-first development and prevents breaking changes. Use
EventBridge for complex routing scenarios and cross-domain events, but prefer
SNS→SQS for simpler use cases due to lower cost and complexity.

### Step Functions for orchestration only; never for core business logic

**Why:** Step Functions excel at coordinating multiple services, handling
retries, and managing complex workflows with branching and parallel execution.
However, business logic should remain in your application code where it's easier
to test, version, and maintain. Step Functions should orchestrate calls to
services that contain the actual business logic.

**CloudFormation (SNS→SQS sketch):**

```yaml
# Complete SNS→SQS setup with DLQ
OrderEventsTopic:
  Type: AWS::SNS::Topic
  Properties:
    TopicName: !Sub "${ServiceName}-order-events"
    KmsMasterKeyId: alias/aws/sns

OrderProcessingQueue:
  Type: AWS::SQS::Queue
  Properties:
    QueueName: !Sub "${ServiceName}-order-processing"
    FifoQueue: true
    ContentBasedDeduplication: true
    MessageRetentionPeriod: 1209600 # 14 days
    VisibilityTimeoutSeconds: 300
    RedrivePolicy:
      deadLetterTargetArn: !GetAtt OrderProcessingDLQ.Arn
      maxReceiveCount: 3
    KmsMasterKeyId: alias/aws/sqs

OrderProcessingDLQ:
  Type: AWS::SQS::Queue
  Properties:
    QueueName: !Sub "${ServiceName}-order-processing-dlq"
    FifoQueue: true
    MessageRetentionPeriod: 1209600

OrderProcessingSubscription:
  Type: AWS::SNS::Subscription
  Properties:
    TopicArn: !Ref OrderEventsTopic
    Protocol: sqs
    Endpoint: !GetAtt OrderProcessingQueue.Arn
    FilterPolicy:
      event_type: ["order_created", "order_updated"]
    RawMessageDelivery: false

# IAM policy for SNS to write to SQS
QueuePolicy:
  Type: AWS::SQS::QueuePolicy
  Properties:
    Queues:
      - !Ref OrderProcessingQueue
    PolicyDocument:
      Statement:
        - Effect: Allow
          Principal:
            Service: sns.amazonaws.com
          Action: sqs:SendMessage
          Resource: !GetAtt OrderProcessingQueue.Arn
          Condition:
            ArnEquals:
              aws:SourceArn: !Ref OrderEventsTopic
```

---

## 3. Compute

### ECS Fargate for APIs/workers: linux/arm64, non-root, read-only fs, healthchecks, awsvpc

**Why:** Fargate eliminates server management overhead while providing container
orchestration. ARM64 (Graviton) offers 20-40% better price-performance than x86.
Running as non-root follows security best practices and limits attack surface.
Read-only filesystems prevent runtime modifications that could indicate
compromise. Health checks enable automatic recovery and proper load balancing.

```yaml
# ECS Task Definition
TaskDefinition:
  Type: AWS::ECS::TaskDefinition
  Properties:
    Family: !Sub "${ServiceName}-api"
    NetworkMode: awsvpc
    RequiresCompatibilities:
      - FARGATE
    Cpu: 512
    Memory: 1024
    RuntimePlatform:
      CpuArchitecture: ARM64
      OperatingSystemFamily: LINUX
    ExecutionRoleArn: !Ref TaskExecutionRole
    TaskRoleArn: !Ref TaskRole
    ContainerDefinitions:
      - Name: api
        Image: !Sub "${AWS::AccountId}.dkr.ecr.${AWS::Region}.amazonaws.com/${ServiceName}:latest"
        Essential: true
        ReadonlyRootFilesystem: true
        User: "1001:1001"  # Non-root user
        PortMappings:
          - ContainerPort: 8080
            Protocol: tcp
        HealthCheck:
          Command:
            - CMD-SHELL
            - "curl -f http://localhost:8080/health/ready || exit 1"
          Interval: 30
          Timeout: 5
          Retries: 3
          StartPeriod: 60
        LogConfiguration:
          LogDriver: awslogs
          Options:
            awslogs-group: !Ref LogGroup
            awslogs-region: !Ref AWS::Region
            awslogs-stream-prefix: api
        Environment:
          - Name: PORT
            Value: "8080"
          - Name: ENV
            Value: !Ref Environment
        MountPoints:
          - SourceVolume: tmp
            ContainerPath: /tmp
            ReadOnly: false
    Volumes:
      - Name: tmp
        Host: {}

# ECS Service with auto-scaling
Service:
  Type: AWS::ECS::Service
  Properties:
    ServiceName: !Sub "${ServiceName}-api"
    Cluster: !Ref ECSCluster
    TaskDefinition: !Ref TaskDefinition
    LaunchType: FARGATE
    DesiredCount: 2
    NetworkConfiguration:
      AwsvpcConfiguration:
        SecurityGroups:
          - !Ref ServiceSecurityGroup
        Subnets:
          - !Ref PrivateSubnet1
          - !Ref PrivateSubnet2
        AssignPublicIp: DISABLED
    LoadBalancers:
      - ContainerName: api
        ContainerPort: 8080
        TargetGroupArn: !Ref TargetGroup
    HealthCheckGracePeriodSeconds: 120
```

```dockerfile

# Dockerfile example
FROM public.ecr.aws/docker/library/node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

FROM public.ecr.aws/docker/library/node:18-alpine

# Create non-root user
RUN addgroup -g 1001 -S appgroup && \
    adduser -u 1001 -S appuser -G appgroup

WORKDIR /app
COPY --from=builder /app/node_modules ./node_modules
COPY --chown=appuser:appgroup . .

# Switch to non-root user
USER appuser

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health/ready || exit 1

CMD ["node", "server.js"]
```

### Lambda for small event-driven tasks; arm64; Powertools; reserved concurrency for isolation

**Why:** Lambda is ideal for event-driven workloads with variable traffic
patterns, providing automatic scaling and pay-per-use pricing. ARM64 provides
better price-performance. Lambda Powertools provides battle-tested utilities for
logging, tracing, and common patterns. Reserved concurrency prevents one
function from consuming all available concurrency and affecting other functions.

### Auto-scaling signals on SQS depth, latency SLOs, or CPU/memory where appropriate

**Why:** Different workloads require different scaling signals. SQS depth
indicates backlog for queue-based workers. Latency SLOs ensure user experience
requirements are met. CPU/memory metrics work for compute-intensive workloads.
Using appropriate signals prevents over-provisioning while maintaining
performance and user experience.

---

## 4. Networking & Delivery

### API Gateway (HTTP) in front of BFF/APIs; request validation; WAF; access logs on

**Why:** API Gateway provides managed API hosting with built-in features like
throttling, caching, and monitoring. HTTP APIs offer better performance and
lower cost than REST APIs for most use cases. Request validation prevents
invalid requests from reaching your backend. WAF protects against common web
attacks. Access logs provide audit trails and debugging information.

### CloudFront + S3 (OAC) for SPA/static; cache immutable assets; WAF at edge

**Why:** CloudFront CDN improves global performance by serving content from edge
locations closer to users. Origin Access Control (OAC) ensures S3 buckets aren't
directly accessible, improving security. Caching immutable assets (with hash
filenames) enables aggressive caching while ensuring users get updates. Edge WAF
provides protection closer to attackers.

### VPC Endpoints for SSM, S3, SQS, STS; IMDSv2 only for EC2/ECS tasks

**Why:** VPC endpoints keep AWS API traffic within your VPC, improving security
and potentially reducing data transfer costs. They also provide better
reliability by avoiding internet routing. IMDSv2 requires session tokens,
preventing SSRF attacks that could access instance metadata. This is crucial for
container security.

### PrivateLink only when crossing account/VPC boundaries that require it

**Why:** PrivateLink provides secure connectivity between VPCs and AWS services
without internet routing, but adds cost and complexity. Use it only when you
need to connect across account boundaries or when security requirements mandate
private connectivity. For same-account scenarios, VPC endpoints are usually
sufficient and more cost-effective.

---

## 5. Data & Storage

### RDS/Aurora MySQL 8: UTC only, strict SQL mode, slow query logs + alarms, backups & PITR

**Why:** MySQL 8 provides better performance, security, and features compared to
older versions. UTC-only timestamps prevent timezone-related bugs and simplify
global applications. Strict SQL mode catches data truncation and other issues
that could lead to data corruption. Slow query logs with alarms help identify
performance issues before they impact users. Automated backups and Point-in-Time
Recovery protect against data loss.

### S3: versioning, SSE-KMS, lifecycle policies; object tagging for lineage; Object Lambda if transformations help

**Why:** Versioning protects against accidental deletion or corruption of
critical data. SSE-KMS provides encryption with keys you control and audit
trails. Lifecycle policies automatically transition data to cheaper storage
classes and delete old data, optimizing costs. Object tagging enables data
lineage tracking and automated governance. Object Lambda allows data
transformation without duplicating storage.

### Idempotency & retries: standard headers, DLQs, and compensating actions defined in runbooks

**Why:** Idempotency prevents duplicate operations when clients retry requests
due to network issues or timeouts. Standard headers (like Idempotency-Key)
provide a consistent approach across services. Dead Letter Queues capture failed
operations for analysis. Compensating actions in runbooks ensure teams know how
to handle failures and maintain data consistency.

---

## 6. Security

### IAM: per-service roles; scoped policies; no wildcard on resource where possible

**Why:** Per-service roles implement the principle of least privilege and limit
blast radius if credentials are compromised. Scoped policies prevent accidental
access to unrelated resources and make it easier to audit permissions. Avoiding
wildcards on resources provides more granular control and better security
posture, though wildcards on actions may be acceptable for related operations.

```yaml
# Service-specific IAM role
UserServiceRole:
  Type: AWS::IAM::Role
  Properties:
    RoleName: !Sub "${ServiceName}-${Environment}-role"
    AssumeRolePolicyDocument:
      Version: "2012-10-17"
      Statement:
        - Effect: Allow
          Principal:
            Service: ecs-tasks.amazonaws.com
          Action: sts:AssumeRole
    ManagedPolicyArns:
      - arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
    Policies:
      - PolicyName: ServiceSpecificPolicy
        PolicyDocument:
          Version: "2012-10-17"
          Statement:
            # ✅ Good - Scoped to specific resources
            - Effect: Allow
              Action:
                - ssm:GetParameter
                - ssm:GetParameters
                - ssm:GetParametersByPath
              Resource:
                - !Sub "arn:aws:ssm:${AWS::Region}:${AWS::AccountId}:parameter/myorg/${ServiceName}/${Environment}/*"

            # ✅ Good - Specific S3 bucket access
            - Effect: Allow
              Action:
                - s3:GetObject
                - s3:PutObject
                - s3:DeleteObject
              Resource:
                - !Sub "${UserDataBucket}/*"
            - Effect: Allow
              Action:
                - s3:ListBucket
              Resource:
                - !Ref UserDataBucket
              Condition:
                StringLike:
                  s3:prefix:
                    - !Sub "${ServiceName}/*"

            # ✅ Good - Scoped SQS access
            - Effect: Allow
              Action:
                - sqs:ReceiveMessage
                - sqs:DeleteMessage
                - sqs:GetQueueAttributes
              Resource:
                - !GetAtt UserProcessingQueue.Arn

            # ✅ Good - Scoped SNS publish
            - Effect: Allow
              Action:
                - sns:Publish
              Resource:
                - !Ref UserEventsTopic

# ❌ Bad example - overly permissive
BadPolicy:
  PolicyDocument:
    Statement:
      - Effect: Allow
        Action: "*"  # Too broad
        Resource: "*"  # Too broad
      - Effect: Allow
        Action:
          - s3:*
        Resource: "*" # Should be scoped to specific buckets
```

### KMS: envelope encryption (GenerateDataKey); Sign/Verify for payload signatures

**Why:** Envelope encryption with GenerateDataKey provides better performance
and security than encrypting data directly with KMS keys. It reduces KMS API
calls and enables local encryption/decryption. Sign/Verify operations provide
digital signatures for data integrity and authenticity, which is crucial for
financial transactions and audit trails.

```python

# Envelope encryption example
import boto3
import json
from cryptography.fernet import Fernet
from typing import Tuple, Dict, Any

class KMSEncryption:
    def __init__(self, key_id: str):
        self.kms = boto3.client('kms')
        self.key_id = key_id

    def encrypt_data(self, plaintext_data: Dict[Any, Any]) -> Dict[str, str]:
        """Encrypt data using envelope encryption"""
        # Generate data key
        response = self.kms.generate_data_key(
            KeyId=self.key_id,
            KeySpec='AES_256'
        )

        # Use plaintext key to encrypt data locally
        plaintext_key = response['Plaintext']
        encrypted_key = response['CiphertextBlob']

        fernet = Fernet(base64.urlsafe_b64encode(plaintext_key[:32]))
        encrypted_data = fernet.encrypt(json.dumps(plaintext_data).encode())

        return {
            'encrypted_data': base64.b64encode(encrypted_data).decode(),
            'encrypted_key': base64.b64encode(encrypted_key).decode()
        }

    def decrypt_data(self, encrypted_payload: Dict[str, str]) -> Dict[Any, Any]:
        """Decrypt data using envelope encryption"""
        # Decrypt the data key
        encrypted_key = base64.b64decode(encrypted_payload['encrypted_key'])
        response = self.kms.decrypt(CiphertextBlob=encrypted_key)
        plaintext_key = response['Plaintext']

        # Use plaintext key to decrypt data locally
        fernet = Fernet(base64.urlsafe_b64encode(plaintext_key[:32]))
        encrypted_data = base64.b64decode(encrypted_payload['encrypted_data'])
        decrypted_data = fernet.decrypt(encrypted_data)

        return json.loads(decrypted_data.decode())

# Digital signatures example
class KMSSignature:
    def __init__(self, signing_key_id: str):
        self.kms = boto3.client('kms')
        self.signing_key_id = signing_key_id

    def sign_payload(self, payload: Dict[Any, Any]) -> str:
        """Sign a payload for integrity verification"""
        message = json.dumps(payload, sort_keys=True).encode()

        response = self.kms.sign(
            KeyId=self.signing_key_id,
            Message=message,
            MessageType='RAW',
            SigningAlgorithm='RSASSA_PKCS1_V1_5_SHA_256'
        )

        return base64.b64encode(response['Signature']).decode()

    def verify_signature(self, payload: Dict[Any, Any], signature: str) -> bool:
        """Verify payload signature"""
        message = json.dumps(payload, sort_keys=True).encode()
        signature_bytes = base64.b64decode(signature)

        try:
            response = self.kms.verify(
                KeyId=self.signing_key_id,
                Message=message,
                MessageType='RAW',
                Signature=signature_bytes,
                SigningAlgorithm='RSASSA_PKCS1_V1_5_SHA_256'
            )
            return response['SignatureValid']
        except Exception:
            return False
```

```yaml
# KMS keys in CloudFormation
EncryptionKey:
  Type: AWS::KMS::Key
  Properties:
    Description: !Sub "Encryption key for ${ServiceName} data"
    KeyPolicy:
      Statement:
        - Effect: Allow
          Principal:
            AWS: !Sub "arn:aws:iam::${AWS::AccountId}:root"
          Action: "kms:*"
          Resource: "*"
        - Effect: Allow
          Principal:
            AWS: !GetAtt ServiceRole.Arn
          Action:
            - kms:Encrypt
            - kms:Decrypt
            - kms:ReEncrypt*
            - kms:GenerateDataKey*
            - kms:DescribeKey
          Resource: "*"

SigningKey:
  Type: AWS::KMS::Key
  Properties:
    Description: !Sub "Signing key for ${ServiceName} payload verification"
    KeyUsage: SIGN_VERIFY
    KeySpec: RSA_2048
    KeyPolicy:
      Statement:
        - Effect: Allow
          Principal:
            AWS: !Sub "arn:aws:iam::${AWS::AccountId}:root"
          Action: "kms:*"
          Resource: "*"
        - Effect: Allow
          Principal:
            AWS: !GetAtt ServiceRole.Arn
          Action:
            - kms:Sign
            - kms:Verify
            - kms:DescribeKey
          Resource: "*"
```

### WAF + Shield Standard on API/CloudFront; rate limits and IP blocks as needed

**Why:** WAF protects against common web attacks like SQL injection, XSS, and
DDoS. Shield Standard provides basic DDoS protection at no additional cost. Rate
limiting prevents abuse and protects against traffic spikes. IP blocking can
stop known malicious actors. These layers provide defense-in-depth security.

### ECR: image scanning, immutable tags; provenance signing (cosign) optional

**Why:** Image scanning identifies known vulnerabilities in container images
before deployment. Immutable tags prevent accidental overwrites and ensure
reproducible deployments. Provenance signing with tools like cosign provides
supply chain security by verifying image authenticity and integrity, though it
adds complexity.

### S3: Block Public Access; only OAC-based CloudFront access for public sites

**Why:** Block Public Access prevents accidental exposure of sensitive data
through misconfigured bucket policies. Using OAC (Origin Access Control) instead
of direct S3 access ensures all traffic goes through CloudFront, enabling
consistent security policies, caching, and monitoring. This prevents direct S3
access bypassing your security controls.

---

## 7. Observability

### Logs: JSON to CloudWatch; retention set per env; Insights queries documented

**Why:** JSON logs enable powerful querying and filtering in CloudWatch Logs
Insights. Setting appropriate retention periods balances compliance requirements
with cost optimization. Documenting common Insights queries helps teams quickly
troubleshoot issues and reduces mean time to resolution. Structured logs also
integrate better with log aggregation and analysis tools.

### Traces: OTEL SDK + AWS X-Ray exporter; propagate trace across services

**Why:** OpenTelemetry provides vendor-neutral instrumentation that works across
different tools and cloud providers. X-Ray integration gives you distributed
tracing across AWS services. Trace propagation enables understanding of request
flows across microservices, which is crucial for debugging performance issues
and understanding system behavior.

```python

# OpenTelemetry setup with X-Ray
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.propagators.aws import AwsXRayPropagator
from opentelemetry.instrumentation.boto3 import Boto3Instrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

# Configure tracing
trace.set_tracer_provider(TracerProvider(
    resource=Resource.create({
        "service.name": "user-service",
        "service.version": "1.0.0",
        "deployment.environment": "production"
    })
))

# Add X-Ray exporter
xray_exporter = OTLPSpanExporter(
    endpoint="http://localhost:2000",  # X-Ray daemon
    headers={"Content-Type": "application/x-protobuf"}
)
span_processor = BatchSpanProcessor(xray_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

# Set X-Ray propagator for AWS services
trace.set_tracer_provider(TracerProvider())
trace.get_tracer_provider().add_span_processor(span_processor)

# Auto-instrument libraries
Boto3Instrumentor().instrument()
RequestsInstrumentor().instrument()
SQLAlchemyInstrumentor().instrument()

tracer = trace.get_tracer(__name__)

# Manual instrumentation example
@tracer.start_as_current_span("process_user_order")
def process_user_order(user_id: str, order_data: dict):
    span = trace.get_current_span()
    span.set_attribute("user.id", user_id)
    span.set_attribute("order.amount", order_data.get("amount", 0))

    try:
        # Business logic here
        user = get_user(user_id)  # Auto-instrumented DB call
        payment_result = process_payment(order_data)  # Auto-instrumented HTTP call

        span.set_attribute("payment.status", payment_result["status"])
        span.add_event("Order processed successfully")

        return {"status": "success", "order_id": generate_order_id()}

    except Exception as e:
        span.record_exception(e)
        span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
        raise

# Context propagation across services
import requests
from opentelemetry.propagate import inject

def call_downstream_service(data: dict):
    headers = {}
    inject(headers)  # Inject trace context into headers

    response = requests.post(
        "https://payment-service.example.com/process",
        json=data,
        headers=headers  # Trace context propagated
    )
    return response.json()
```

```yaml
# CloudFormation for X-Ray daemon sidecar
TaskDefinition:
  Type: AWS::ECS::TaskDefinition
  Properties:
    ContainerDefinitions:
      - Name: app

        Image: !Sub "${AWS::AccountId}.dkr.ecr.${AWS::Region}.amazonaws.com/user-service:latest"
        Environment:
          - Name: AWS_XRAY_TRACING_NAME

            Value: user-service

          - Name: AWS_XRAY_DAEMON_ADDRESS

            Value: "xray-daemon:2000"
        DependsOn:
          - ContainerName: xray-daemon

            Condition: START

      - Name: xray-daemon

        Image: public.ecr.aws/xray/aws-xray-daemon:latest
        Cpu: 32
        Memory: 256
        PortMappings:
          - ContainerPort: 2000

            Protocol: udp
        LogConfiguration:
          LogDriver: awslogs
          Options:
            awslogs-group: !Ref LogGroup
            awslogs-stream-prefix: xray-daemon
```

### Metrics: SLIs (latency, error rate, saturation); Composite Alarms for clear paging

**Why:** Service Level Indicators (SLIs) provide quantitative measures of user
experience and system health. Latency, error rate, and saturation are the most
important metrics for most services. Composite Alarms reduce alert fatigue by
combining multiple conditions into meaningful alerts that warrant immediate
attention, improving on-call experience.

```yaml
# CloudWatch Alarms for SLIs
HighLatencyAlarm:
  Type: AWS::CloudWatch::Alarm
  Properties:
    AlarmName: !Sub "${ServiceName}-high-latency"
    AlarmDescription: "API latency is above acceptable threshold"
    MetricName: TargetResponseTime
    Namespace: AWS/ApplicationELB
    Statistic: Average
    Period: 300
    EvaluationPeriods: 2
    Threshold: 2.0 # 2 seconds
    ComparisonOperator: GreaterThanThreshold
    Dimensions:
      - Name: LoadBalancer
        Value: !GetAtt LoadBalancer.LoadBalancerFullName
    TreatMissingData: notBreaching

HighErrorRateAlarm:
  Type: AWS::CloudWatch::Alarm
  Properties:
    AlarmName: !Sub "${ServiceName}-high-error-rate"
    AlarmDescription: "Error rate is above acceptable threshold"
    MetricName: HTTPCode_Target_5XX_Count
    Namespace: AWS/ApplicationELB
    Statistic: Sum
    Period: 300
    EvaluationPeriods: 2
    Threshold: 10 # 10 errors in 5 minutes
    ComparisonOperator: GreaterThanThreshold
    Dimensions:
      - Name: LoadBalancer
        Value: !GetAtt LoadBalancer.LoadBalancerFullName

HighCPUAlarm:
  Type: AWS::CloudWatch::Alarm
  Properties:
    AlarmName: !Sub "${ServiceName}-high-cpu"
    AlarmDescription: "CPU utilization is high"
    MetricName: CPUUtilization
    Namespace: AWS/ECS
    Statistic: Average
    Period: 300
    EvaluationPeriods: 3
    Threshold: 80
    ComparisonOperator: GreaterThanThreshold
    Dimensions:
      - Name: ServiceName
        Value: !Sub "${ServiceName}-api"
      - Name: ClusterName
        Value: !Ref ECSCluster

# Composite Alarm - only page when multiple conditions are met
ServiceHealthCompositeAlarm:
  Type: AWS::CloudWatch::CompositeAlarm
  Properties:
    AlarmName: !Sub "${ServiceName}-service-unhealthy"
    AlarmDescription:
      "Service is experiencing issues requiring immediate attention"
    AlarmRule: !Sub |
      (ALARM("${HighLatencyAlarm}") AND ALARM("${HighErrorRateAlarm}"))
      OR
      (ALARM("${HighErrorRateAlarm}") AND ALARM("${HighCPUAlarm}"))
    ActionsEnabled: true
    AlarmActions:
      - !Ref PagerDutyTopic # Only page for composite alarm
    OKActions:
      - !Ref PagerDutyTopic
```
```python

# Custom metrics with OpenTelemetry
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.cloudwatch.metrics import CloudWatchMetricsExporter

# Configure metrics
metrics.set_meter_provider(MeterProvider(
    metric_readers=[
        PeriodicExportingMetricReader(
            CloudWatchMetricsExporter(
                namespace="MyApp/UserService",
                region_name="us-east-1"
            ),
            export_interval_millis=60000  # Export every minute
        )
    ]
))

meter = metrics.get_meter(__name__)

# Create metrics
request_counter = meter.create_counter(
    name="requests_total",
    description="Total number of requests",
    unit="1"
)

request_duration = meter.create_histogram(
    name="request_duration_seconds",
    description="Request duration in seconds",
    unit="s"
)

active_connections = meter.create_up_down_counter(
    name="active_connections",
    description="Number of active connections",
    unit="1"
)

# Usage in application code
import time
from contextlib import contextmanager

@contextmanager
def track_request(endpoint: str, method: str):
    start_time = time.time()
    active_connections.add(1)

    try:
        yield
        # Success
        request_counter.add(1, {"endpoint": endpoint, "method": method, "status": "success"})
    except Exception as e:
        # Error
        request_counter.add(1, {"endpoint": endpoint, "method": method, "status": "error"})
        raise
    finally:
        duration = time.time() - start_time
        request_duration.record(duration, {"endpoint": endpoint, "method": method})
        active_connections.add(-1)

# Usage
def handle_user_request():
    with track_request("/users", "GET"):
        # Handle request logic
        return get_users()
```

### Synthetic checks: CloudWatch Synthetics for critical endpoints; optional RUM for frontend

**Why:** Synthetic monitoring proactively checks critical user journeys and
catches issues before users report them. CloudWatch Synthetics can test API
endpoints, user flows, and availability from multiple regions. Real User
Monitoring (RUM) provides insights into actual user experience but adds
complexity and cost, so use it selectively for critical user-facing
applications.

---

## 8. EARS Requirements

**EARS (Easy Approach to Requirements Syntax) format for AWS development
requirements:**

### Ubiquitous Requirements

- The system SHALL use SSM Parameter Store SecureString for secrets and
  configuration
- The system SHALL publish events to SNS and subscribe with SQS (never raw SQS)
- The system SHALL use CloudFormation for all infrastructure with cfn-lint
  validation
- The system SHALL implement structured logging with JSON output to CloudWatch
- The system SHALL use per-service IAM roles with least privilege principles
- The system SHALL tag all resources with App, Env, Owner, CostCenter, and
  DataClass
- The system SHALL implement health checks at /health/live and /health/ready

### Event-Driven Requirements

- WHEN a message is published to SNS, the system SHALL include message
  attributes for routing
- WHEN a Lambda function is invoked, the system SHALL propagate trace context
  across services
- WHEN an ECS task starts, the system SHALL validate configuration and
  dependencies
- WHEN a deployment occurs, the system SHALL run smoke tests to verify
  functionality
- WHEN an alarm triggers, the system SHALL send notifications to the appropriate
  team

### Unwanted Behavior Requirements

- IF wildcard permissions are used in IAM policies, the system SHALL fail
  security review
- IF secrets are hardcoded in code or configuration, the system SHALL fail
  security scanning
- IF resources are untagged, the system SHALL fail governance checks
- IF public S3 access is enabled, the system SHALL fail security validation
- IF container images have critical vulnerabilities, the system SHALL prevent
  deployment

### State-Driven Requirements

- WHILE processing SQS messages, the system SHALL handle failures with DLQ and
  retry logic
- WHILE running in production, the system SHALL use ARM64 architecture for cost
  optimization
- WHILE handling sensitive data, the system SHALL use envelope encryption with
  KMS
- WHILE in multi-AZ deployment, the system SHALL distribute load across
  availability zones

### Optional Feature Requirements

- WHERE high availability is required, the system SHOULD implement blue/green
  deployments
- WHERE cost optimization is important, the system SHOULD use Spot instances for
  batch workloads
- WHERE compliance is required, the system SHOULD implement VPC endpoints for
  AWS services
- WHERE performance is critical, the system SHOULD use CloudFront for content
  delivery

### Complex Requirements

- WHEN an ECS service is deployed AND health checks fail, the system SHALL stop
  the deployment, maintain the previous version, alert the operations team, and
  provide rollback instructions
- WHEN a Lambda function processes an event AND the processing fails, the system
  SHALL retry with exponential backoff, log the failure with full context, and
  move to DLQ after max retries
- WHEN a CloudFormation stack update is initiated AND validation fails, the
  system SHALL prevent the update, preserve the current state, log the
  validation errors, and notify the deployment team

### Mandatory tags: App, Env, Owner, CostCenter, DataClass

**Why:** Consistent tagging enables cost allocation, resource management, and
automated governance policies. App and Env tags help identify resources and
their purpose. Owner tags enable accountability and contact information for
issues. CostCenter tags enable chargeback and budget allocation. DataClass tags
help implement appropriate security and compliance controls based on data
sensitivity.

```yaml
# CloudFormation template with consistent tagging
Parameters:
  App:
    Type: String
    Default: "user-service"
  Environment:
    Type: String
    AllowedValues: [dev, staging, prod]
  Owner:
    Type: String
    Default: "platform-team@company.com"
  CostCenter:
    Type: String
    Default: "engineering"
  DataClass:
    Type: String
    AllowedValues: [public, internal, confidential, restricted]
    Default: "internal"

# Global tags applied to all resources
Globals:
  Function:
    Tags:
      App: !Ref App
      Env: !Ref Environment
      Owner: !Ref Owner
      CostCenter: !Ref CostCenter
      DataClass: !Ref DataClass
      ManagedBy: "CloudFormation"

Resources:
  UserDatabase:
    Type: AWS::RDS::DBInstance
    Properties:
      # ... other properties
      Tags:
        - Key: App

          Value: !Ref App

        - Key: Env

          Value: !Ref Environment

        - Key: Owner

          Value: !Ref Owner

        - Key: CostCenter

          Value: !Ref CostCenter

        - Key: DataClass

          Value: "confidential" # Override for sensitive data

        - Key: BackupRequired

          Value: "true"

        - Key: Component

          Value: "database"

  UserDataBucket:
    Type: AWS::S3::Bucket
    Properties:
      # ... other properties
      Tags:
        - Key: App

          Value: !Ref App

        - Key: Env

          Value: !Ref Environment

        - Key: Owner

          Value: !Ref Owner

        - Key: CostCenter

          Value: !Ref CostCenter

        - Key: DataClass

          Value: !Ref DataClass

        - Key: Component

          Value: "storage"

        - Key: LifecyclePolicy

          Value: "enabled"
```

```python

# Python script for tag compliance checking
import boto3
from typing import List, Dict, Any

class TagComplianceChecker:
    def __init__(self):
        self.required_tags = ['App', 'Env', 'Owner', 'CostCenter', 'DataClass']
        self.ec2 = boto3.client('ec2')
        self.rds = boto3.client('rds')
        self.s3 = boto3.client('s3')

    def check_ec2_compliance(self) -> List[Dict[str, Any]]:
        """Check EC2 instances for required tags"""
        non_compliant = []

        response = self.ec2.describe_instances()
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                instance_id = instance['InstanceId']
                tags = {tag['Key']: tag['Value'] for tag in instance.get('Tags', [])}

                missing_tags = [tag for tag in self.required_tags if tag not in tags]
                if missing_tags:
                    non_compliant.append({
                        'ResourceId': instance_id,
                        'ResourceType': 'EC2Instance',
                        'MissingTags': missing_tags
                    })

        return non_compliant

    def auto_tag_resources(self, resource_ids: List[str], tags: Dict[str, str]):
        """Apply tags to resources automatically"""
        self.ec2.create_tags(
            Resources=resource_ids,
            Tags=[{'Key': k, 'Value': v} for k, v in tags.items()]
        )

# Cost allocation report query
def generate_cost_report_by_tags():
    """Generate cost report grouped by tags"""
    ce = boto3.client('ce')

    response = ce.get_cost_and_usage(
        TimePeriod={
            'Start': '2024-01-01',
            'End': '2024-01-31'
        },
        Granularity='MONTHLY',
        Metrics=['BlendedCost'],
        GroupBy=[
            {'Type': 'TAG', 'Key': 'App'},
            {'Type': 'TAG', 'Key': 'Env'},
            {'Type': 'TAG', 'Key': 'CostCenter'}
        ]
    )

    return response['ResultsByTime']
```

### Budgets + anomaly detection; dashboard per product

**Why:** Budgets provide proactive cost control and prevent unexpected charges.
Anomaly detection catches unusual spending patterns that might indicate issues
or waste. Per-product dashboards enable teams to understand their cost drivers
and optimize spending. This visibility is crucial for maintaining cost
efficiency as systems scale.

### DORA metrics tracked; deployment frequency & MTTR in one place

**Why:** DORA (DevOps Research and Assessment) metrics provide objective
measures of software delivery performance. Deployment frequency indicates how
often you can deliver value. Mean Time to Recovery (MTTR) measures how quickly
you can resolve issues. Tracking these metrics helps identify improvement
opportunities and demonstrates the business value of DevOps practices.

### Resource TTLs for sandboxes; cleanup jobs

**Why:** Development and testing environments often accumulate unused resources
that generate ongoing costs. Time-to-live (TTL) tags and automated cleanup jobs
prevent resource sprawl and reduce waste. This is especially important for
expensive resources like databases and compute instances that teams might forget
to shut down after testing.

---

## 9. FinOps & Governance

---

## 10. Checklists

**Why this checklist matters:** This checklist serves as a final verification
that all critical AWS practices are implemented. Each item represents a decision
that significantly impacts security, cost, reliability, or operational
efficiency. Regular checklist reviews during architecture reviews and before
production deployments help ensure consistency across projects and prevent
regression of important practices.

- [ ] SNS→SQS with DLQs; FIFO where needed
- [ ] OTEL traces→X-Ray, logs→CloudWatch, metrics→Alarms
- [ ] WAF enabled on API/CloudFront; Shield active
- [ ] ECS Fargate arm64, non-root, read-only FS
- [ ] CloudFormation validated (cfn-lint, cfn-nag)
- [ ] FinOps tags present; budgets/alerts configured
