# Deployment and Infrastructure Best Practices

## Container Best Practices

### Multi-stage Python Dockerfile
```dockerfile
# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim as production

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder stage
COPY --from=builder /root/.local /home/appuser/.local

# Set up application directory
WORKDIR /app
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Add local bin to PATH
ENV PATH=/home/appuser/.local/bin:$PATH

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000
CMD ["python", "app.py"]
```

### Multi-stage C# Dockerfile
```dockerfile
# Build stage
FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src

# Copy csproj files and restore dependencies
COPY ["MyProject.Api/MyProject.Api.csproj", "MyProject.Api/"]
COPY ["MyProject.Core/MyProject.Core.csproj", "MyProject.Core/"]
COPY ["MyProject.Infrastructure/MyProject.Infrastructure.csproj", "MyProject.Infrastructure/"]

RUN dotnet restore "MyProject.Api/MyProject.Api.csproj"

# Copy source code and build
COPY . .
WORKDIR "/src/MyProject.Api"
RUN dotnet build "MyProject.Api.csproj" -c Release -o /app/build

# Publish stage
FROM build AS publish
RUN dotnet publish "MyProject.Api.csproj" -c Release -o /app/publish /p:UseAppHost=false

# Runtime stage
FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS final

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser

# Install curl for health checks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=publish /app/publish .

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:80/health || exit 1

EXPOSE 80
EXPOSE 443

ENTRYPOINT ["dotnet", "MyProject.Api.dll"]
```

## Kubernetes Deployment

### Python Kubernetes Manifests
```yaml
# python-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: python-app
  labels:
    app: python-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: python-app
  template:
    metadata:
      labels:
        app: python-app
    spec:
      containers:
      - name: python-app
        image: myregistry/python-app:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: database-url
        - name: REDIS_URL
          valueFrom:
            configMapKeyRef:
              name: app-config
              key: redis-url
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        securityContext:
          runAsNonRoot: true
          runAsUser: 1000
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
        volumeMounts:
        - name: tmp-volume
          mountPath: /tmp
      volumes:
      - name: tmp-volume
        emptyDir: {}
      securityContext:
        fsGroup: 1000

---
apiVersion: v1
kind: Service
metadata:
  name: python-app-service
spec:
  selector:
    app: python-app
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: ClusterIP

---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: python-app-ingress
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "100"
spec:
  tls:
  - hosts:
    - myapp.example.com
    secretName: python-app-tls
  rules:
  - host: myapp.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: python-app-service
            port:
              number: 80
```

### C# Kubernetes Manifests
```yaml
# csharp-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: csharp-app
  labels:
    app: csharp-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: csharp-app
  template:
    metadata:
      labels:
        app: csharp-app
    spec:
      containers:
      - name: csharp-app
        image: myregistry/csharp-app:latest
        ports:
        - containerPort: 80
        - containerPort: 443
        env:
        - name: ASPNETCORE_ENVIRONMENT
          value: "Production"
        - name: ConnectionStrings__DefaultConnection
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: connection-string
        resources:
          requests:
            memory: "256Mi"
            cpu: "200m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 80
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 80
          initialDelaySeconds: 5
          periodSeconds: 5
        securityContext:
          runAsNonRoot: true
          runAsUser: 1000
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
        volumeMounts:
        - name: tmp-volume
          mountPath: /tmp
        - name: app-data
          mountPath: /app/data
      volumes:
      - name: tmp-volume
        emptyDir: {}
      - name: app-data
        emptyDir: {}
      securityContext:
        fsGroup: 1000
```

## Helm Charts

### Python Helm Chart
```yaml
# charts/python-app/Chart.yaml
apiVersion: v2
name: python-app
description: A Helm chart for Python application
type: application
version: 0.1.0
appVersion: "1.0.0"

# charts/python-app/values.yaml
replicaCount: 3

image:
  repository: myregistry/python-app
  pullPolicy: IfNotPresent
  tag: ""

service:
  type: ClusterIP
  port: 80
  targetPort: 8000

ingress:
  enabled: true
  className: "nginx"
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
  hosts:
    - host: myapp.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: python-app-tls
      hosts:
        - myapp.example.com

resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 100m
    memory: 128Mi

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilizationPercentage: 80
  targetMemoryUtilizationPercentage: 80

nodeSelector: {}
tolerations: []
affinity: {}

config:
  redisUrl: "redis://redis:6379"

secrets:
  databaseUrl: ""
  apiKey: ""
```

### C# Helm Chart
```yaml
# charts/csharp-app/values.yaml
replicaCount: 3

image:
  repository: myregistry/csharp-app
  pullPolicy: IfNotPresent
  tag: ""

service:
  type: ClusterIP
  port: 80
  targetPort: 80

ingress:
  enabled: true
  className: "nginx"
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
  hosts:
    - host: myapp.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: csharp-app-tls
      hosts:
        - myapp.example.com

resources:
  limits:
    cpu: 1000m
    memory: 1Gi
  requests:
    cpu: 200m
    memory: 256Mi

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilizationPercentage: 80

config:
  aspnetcoreEnvironment: "Production"
  loggingLevel: "Information"

secrets:
  connectionString: ""
  jwtSecret: ""
```

## Infrastructure as Code

### Terraform AWS Infrastructure
```hcl
# main.tf
terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  backend "s3" {
    bucket = "my-terraform-state"
    key    = "infrastructure/terraform.tfstate"
    region = "us-west-2"
  }
}

provider "aws" {
  region = var.aws_region
}

# VPC
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = "${var.project_name}-vpc"
    Environment = var.environment
  }
}

# Subnets
resource "aws_subnet" "private" {
  count             = length(var.availability_zones)
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.${count.index + 1}.0/24"
  availability_zone = var.availability_zones[count.index]

  tags = {
    Name        = "${var.project_name}-private-${count.index + 1}"
    Environment = var.environment
  }
}

resource "aws_subnet" "public" {
  count                   = length(var.availability_zones)
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.${count.index + 10}.0/24"
  availability_zone       = var.availability_zones[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name        = "${var.project_name}-public-${count.index + 1}"
    Environment = var.environment
  }
}

# EKS Cluster
resource "aws_eks_cluster" "main" {
  name     = "${var.project_name}-cluster"
  role_arn = aws_iam_role.cluster.arn
  version  = var.kubernetes_version

  vpc_config {
    subnet_ids              = concat(aws_subnet.private[*].id, aws_subnet.public[*].id)
    endpoint_private_access = true
    endpoint_public_access  = true
    public_access_cidrs     = ["0.0.0.0/0"]
  }

  encryption_config {
    provider {
      key_arn = aws_kms_key.eks.arn
    }
    resources = ["secrets"]
  }

  enabled_cluster_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]

  depends_on = [
    aws_iam_role_policy_attachment.cluster_AmazonEKSClusterPolicy,
  ]

  tags = {
    Environment = var.environment
  }
}

# RDS Database
resource "aws_db_instance" "main" {
  identifier = "${var.project_name}-db"

  engine         = "postgres"
  engine_version = "15.4"
  instance_class = var.db_instance_class

  allocated_storage     = 20
  max_allocated_storage = 100
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name  = var.db_name
  username = var.db_username
  password = var.db_password

  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name   = aws_db_subnet_group.main.name

  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"

  skip_final_snapshot = false
  final_snapshot_identifier = "${var.project_name}-db-final-snapshot"

  tags = {
    Name        = "${var.project_name}-db"
    Environment = var.environment
  }
}
```

### Azure Resource Manager Template
```json
{
  "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
  "contentVersion": "1.0.0.0",
  "parameters": {
    "projectName": {
      "type": "string",
      "metadata": {
        "description": "Name of the project"
      }
    },
    "environment": {
      "type": "string",
      "allowedValues": ["dev", "staging", "prod"],
      "metadata": {
        "description": "Environment name"
      }
    },
    "kubernetesVersion": {
      "type": "string",
      "defaultValue": "1.28.3",
      "metadata": {
        "description": "Kubernetes version"
      }
    }
  },
  "variables": {
    "aksClusterName": "[concat(parameters('projectName'), '-aks')]",
    "resourceGroupName": "[concat(parameters('projectName'), '-', parameters('environment'))]"
  },
  "resources": [
    {
      "type": "Microsoft.ContainerService/managedClusters",
      "apiVersion": "2023-08-01",
      "name": "[variables('aksClusterName')]",
      "location": "[resourceGroup().location]",
      "identity": {
        "type": "SystemAssigned"
      },
      "properties": {
        "kubernetesVersion": "[parameters('kubernetesVersion')]",
        "dnsPrefix": "[concat(parameters('projectName'), '-dns')]",
        "agentPoolProfiles": [
          {
            "name": "nodepool1",
            "count": 3,
            "vmSize": "Standard_D2s_v3",
            "osType": "Linux",
            "mode": "System",
            "enableAutoScaling": true,
            "minCount": 1,
            "maxCount": 10
          }
        ],
        "networkProfile": {
          "networkPlugin": "azure",
          "serviceCidr": "10.0.0.0/16",
          "dnsServiceIP": "10.0.0.10"
        },
        "addonProfiles": {
          "azureKeyvaultSecretsProvider": {
            "enabled": true
          },
          "omsAgent": {
            "enabled": true,
            "config": {
              "logAnalyticsWorkspaceResourceID": "[resourceId('Microsoft.OperationalInsights/workspaces', concat(parameters('projectName'), '-logs'))]"
            }
          }
        }
      }
    }
  ]
}
```

## Monitoring and Observability

### Prometheus Configuration
```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093

scrape_configs:
  - job_name: 'kubernetes-apiservers'
    kubernetes_sd_configs:
    - role: endpoints
    scheme: https
    tls_config:
      ca_file: /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
    bearer_token_file: /var/run/secrets/kubernetes.io/serviceaccount/token
    relabel_configs:
    - source_labels: [__meta_kubernetes_namespace, __meta_kubernetes_service_name, __meta_kubernetes_endpoint_port_name]
      action: keep
      regex: default;kubernetes;https

  - job_name: 'python-app'
    kubernetes_sd_configs:
    - role: pod
    relabel_configs:
    - source_labels: [__meta_kubernetes_pod_label_app]
      action: keep
      regex: python-app
    - source_labels: [__address__, __meta_kubernetes_pod_annotation_prometheus_io_port]
      action: replace
      regex: ([^:]+)(?::\d+)?;(\d+)
      replacement: $1:$2
      target_label: __address__

  - job_name: 'csharp-app'
    kubernetes_sd_configs:
    - role: pod
    relabel_configs:
    - source_labels: [__meta_kubernetes_pod_label_app]
      action: keep
      regex: csharp-app
    - source_labels: [__address__, __meta_kubernetes_pod_annotation_prometheus_io_port]
      action: replace
      regex: ([^:]+)(?::\d+)?;(\d+)
      replacement: $1:$2
      target_label: __address__
```

### Application Metrics

#### Python Metrics with Prometheus
```python
# metrics.py
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import time
import functools

# Metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')
ACTIVE_CONNECTIONS = Gauge('active_connections', 'Active database connections')

def track_requests(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            REQUEST_COUNT.labels(method='GET', endpoint='/api/users', status='200').inc()
            return result
        except Exception as e:
            REQUEST_COUNT.labels(method='GET', endpoint='/api/users', status='500').inc()
            raise
        finally:
            REQUEST_DURATION.observe(time.time() - start_time)
    return wrapper

# Start metrics server
start_http_server(8080)
```

#### C# Metrics with Prometheus
```csharp
// Metrics.cs
using Prometheus;

public static class Metrics
{
    public static readonly Counter RequestCount = Prometheus.Metrics
        .CreateCounter("http_requests_total", "Total HTTP requests", 
                      new[] { "method", "endpoint", "status" });

    public static readonly Histogram RequestDuration = Prometheus.Metrics
        .CreateHistogram("http_request_duration_seconds", "HTTP request duration");

    public static readonly Gauge ActiveConnections = Prometheus.Metrics
        .CreateGauge("active_connections", "Active database connections");
}

// Startup.cs
public void Configure(IApplicationBuilder app, IWebHostEnvironment env)
{
    app.UseRouting();
    app.UseHttpMetrics(); // Add this for automatic HTTP metrics
    app.UseMetricServer(); // Expose /metrics endpoint
    
    app.UseEndpoints(endpoints =>
    {
        endpoints.MapControllers();
    });
}
```
