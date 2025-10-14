# Security Best Practices

## Static Application Security Testing (SAST)

### SonarQube Integration

**Why SonarQube is Critical**: SonarQube provides comprehensive static analysis that catches security vulnerabilities, code smells, and maintainability issues before they reach production. It's particularly valuable because it:
1. **Catches OWASP Top 10 vulnerabilities** automatically
2. **Provides security hotspots** for manual review
3. **Tracks technical debt** over time
4. **Integrates with CI/CD** for automated quality gates

**Decision Framework for SonarQube**:
- **Team Size**: Essential for teams > 3 developers
- **Compliance Requirements**: Mandatory for regulated industries
- **Code Quality Goals**: Use when aiming for production-grade quality
- **Budget Considerations**: Community edition vs. commercial features

#### SonarQube Setup for Python

**Configuration Strategy**: The sonar-project.properties file defines what gets analyzed and how. Each setting serves a specific purpose in the security analysis pipeline.

```bash
# Install sonar-scanner
npm install -g sonarqube-scanner

# Create sonar-project.properties
sonar.projectKey=my-python-project        # Unique identifier in SonarQube
sonar.projectName=My Python Project       # Human-readable name
sonar.projectVersion=1.0                  # Version tracking for trend analysis
sonar.sources=src                         # Source code location (exclude tests)
sonar.tests=tests                         # Test code location (different rules apply)
sonar.python.coverage.reportPaths=coverage.xml  # Coverage integration
sonar.python.xunit.reportPath=test-results.xml  # Test results integration
```

**AI Assistant Considerations**:
- Always exclude test directories from main source analysis
- Recommend coverage integration for comprehensive quality metrics
- Suggest appropriate project keys that follow organizational naming conventions
- Consider existing SonarQube instance configuration when providing setup advice

#### SonarQube Setup for C#

**Why NuGet Package Over CLI**: The SonarAnalyzer.CSharp NuGet package provides real-time analysis in the IDE and integrates seamlessly with the build process. This approach ensures consistent analysis across development and CI environments.

**Package Configuration Strategy**:
- **PrivateAssets="all"**: Prevents the analyzer from being included in published packages
- **IncludeAssets="analyzers"**: Only includes the analyzer functionality
- **Version Management**: Keep analyzer versions consistent across projects

```xml
<!-- Install SonarAnalyzer.CSharp -->
<PackageReference Include="SonarAnalyzer.CSharp" Version="9.12.0.78982">
  <PrivateAssets>all</PrivateAssets>        <!-- Don't include in package output -->
  <IncludeAssets>analyzers</IncludeAssets>  <!-- Only include analyzer functionality -->
</PackageReference>
```

**SonarScanner Integration**: The three-step process (begin, build, end) ensures comprehensive analysis including test coverage and code duplication detection.

```bash
# Begin analysis (sets up analysis context)
dotnet sonarscanner begin /k:"my-csharp-project" /d:sonar.host.url="http://localhost:9000"

# Build project (analyzers run during compilation)
dotnet build

# Run tests with coverage (provides quality metrics)
dotnet test --collect:"XPlat Code Coverage"

# End analysis (uploads results to SonarQube)
dotnet sonarscanner end
```

**AI Assistant Decision Points**:
- Recommend the NuGet package approach for better IDE integration
- Suggest consistent analyzer versions across solution projects
- Always include test coverage collection for comprehensive analysis
- Consider SonarCloud for teams without on-premise SonarQube infrastructure

### Bandit for Python Security

**Why Bandit is Essential for Python**: Bandit specializes in finding common security issues in Python code that general linters miss. It understands Python-specific security anti-patterns like:
- **SQL injection vulnerabilities** in string formatting
- **Hardcoded passwords** and secrets
- **Insecure random number generation**
- **Shell injection** through subprocess calls
- **Insecure cryptographic practices**

**Strategic Implementation**:
- **CI/CD Integration**: Run Bandit in every build to catch issues early
- **Baseline Establishment**: Use initial scan to set security baseline
- **Progressive Improvement**: Address high-severity issues first
- **False Positive Management**: Use configuration to handle legitimate exceptions

```bash
# Install bandit
pip install bandit

# Run security scan (basic usage)
bandit -r src/

# Generate report (for CI/CD integration)
bandit -r src/ -f json -o bandit-report.json

# Configuration in .bandit (fine-tuning for your project)
[bandit]
exclude_dirs = tests,venv        # Exclude test code and dependencies
skips = B101,B601               # Skip specific checks (document reasoning)
```

**Configuration Decision Framework**:
- **exclude_dirs**: Always exclude test directories and virtual environments
- **skips**: Only skip checks after careful consideration and documentation
- **severity levels**: Focus on HIGH and MEDIUM severity issues first
- **baseline files**: Use for legacy codebases to track improvement

**AI Assistant Guidance**:
- Always recommend Bandit for Python projects handling sensitive data
- Suggest appropriate exclusions based on project structure
- Warn about the security implications of skipping specific checks
- Recommend regular Bandit updates to catch new vulnerability patterns

### Security Code Analysis for C#
```xml
<PropertyGroup>
  <EnableNETAnalyzers>true</EnableNETAnalyzers>
  <AnalysisLevel>latest</AnalysisLevel>
  <WarningsAsErrors />
</PropertyGroup>

<PackageReference Include="Microsoft.CodeAnalysis.BannedApiAnalyzers" Version="3.3.4" PrivateAssets="all" />
<PackageReference Include="Microsoft.VisualStudio.Threading.Analyzers" Version="17.7.30" PrivateAssets="all" />
```

## Container Security with Trivy

### Trivy Installation and Usage

**Why Trivy is the Gold Standard**: Trivy provides comprehensive vulnerability scanning for containers, filesystems, and dependencies. It's particularly valuable because it:
1. **Scans multiple layers**: OS packages, language dependencies, and configuration files
2. **Provides actionable results**: Shows which vulnerabilities are actually exploitable
3. **Integrates everywhere**: Works with CI/CD, registries, and Kubernetes
4. **Stays current**: Database updates automatically with latest CVE information

**Scanning Strategy Decision Matrix**:
- **Filesystem scanning**: Use during development for early detection
- **Image scanning**: Essential for container-based deployments
- **Registry integration**: Scan images before deployment
- **Kubernetes integration**: Runtime scanning for deployed workloads

```bash
# Install trivy (choose method based on environment)
curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin

# Scan filesystem (development phase)
trivy fs .

# Scan container image (pre-deployment)
trivy image python:3.11-slim

# Generate report (CI/CD integration)
trivy fs --format json --output trivy-report.json .
```

**AI Assistant Decision Framework**:
- Recommend filesystem scanning for development environments
- Suggest image scanning for all containerized applications
- Always include Trivy in CI/CD pipelines for container-based projects
- Consider severity filtering based on organizational risk tolerance

### Dockerfile Security Best Practices

**Security-First Container Design Philosophy**: Every Dockerfile decision impacts security. The multi-stage approach and security configurations shown here address the most common container security vulnerabilities identified by OWASP and NIST.

**Critical Security Principles**:
1. **Minimal attack surface**: Use slim base images and remove unnecessary components
2. **Non-root execution**: Run applications as unprivileged users
3. **Immutable containers**: Use read-only filesystems where possible
4. **Least privilege**: Grant only necessary permissions and capabilities

#### Python Dockerfile Security Analysis

```dockerfile
# Python Dockerfile
FROM python:3.11-slim as base          # Slim images reduce attack surface

# Create non-root user (CRITICAL SECURITY PRACTICE)
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR /app

# Copy requirements first for better caching (and security scanning)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt  # --no-cache-dir reduces image size

# Copy application code
COPY --chown=appuser:appuser . .       # Set ownership during copy

# Switch to non-root user (PREVENTS PRIVILEGE ESCALATION)
USER appuser

# Expose port (documentation only, doesn't open ports)
EXPOSE 8000

CMD ["python", "app.py"]
```

**Security Decision Points**:
- **Base Image Choice**: `python:3.11-slim` balances functionality with security (fewer packages = smaller attack surface)
- **User Creation**: Non-root execution prevents container breakout attacks
- **File Ownership**: `--chown` ensures proper permissions without additional RUN commands
- **Package Installation**: `--no-cache-dir` reduces image size and potential cache poisoning

#### C# Dockerfile Security Analysis

```dockerfile
# C# Dockerfile
FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS base  # Official Microsoft images (trusted source)
WORKDIR /app
EXPOSE 80
EXPOSE 443

# Create non-root user (SECURITY REQUIREMENT)
RUN adduser --disabled-password --gecos '' appuser

FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build    # Separate build stage (security isolation)
WORKDIR /src
COPY ["MyProject.Api/MyProject.Api.csproj", "MyProject.Api/"]
RUN dotnet restore "MyProject.Api/MyProject.Api.csproj"  # Restore in separate layer

COPY . .
WORKDIR "/src/MyProject.Api"
RUN dotnet build "MyProject.Api.csproj" -c Release -o /app/build

FROM build AS publish
RUN dotnet publish "MyProject.Api.csproj" -c Release -o /app/publish

FROM base AS final                     # Multi-stage build (removes build tools from final image)
WORKDIR /app
COPY --from=publish /app/publish .     # Only copy published artifacts
USER appuser                           # Run as non-root user
ENTRYPOINT ["dotnet", "MyProject.Api.dll"]
```

**Multi-Stage Security Benefits**:
- **Build Tool Isolation**: SDK and build tools don't exist in final image
- **Reduced Attack Surface**: Final image contains only runtime dependencies
- **Smaller Image Size**: Fewer components to scan and secure
- **Clear Separation**: Build-time vs. runtime security considerations

**AI Assistant Security Guidance**:
- Always recommend non-root users in container suggestions
- Suggest multi-stage builds for compiled languages
- Recommend official base images from trusted sources
- Warn about security implications of running containers as root

## Dependency Security

### Python Dependency Scanning
```bash
# Install safety
pip install safety

# Check for known vulnerabilities
safety check

# Generate report
safety check --json --output safety-report.json

# Check requirements file
safety check -r requirements.txt
```

### pip-audit for Python
```bash
# Install pip-audit
pip install pip-audit

# Audit installed packages
pip-audit

# Audit requirements file
pip-audit -r requirements.txt

# Generate report
pip-audit --format=json --output=audit-report.json
```

### .NET Dependency Scanning
```bash
# Check for vulnerable packages
dotnet list package --vulnerable

# Check for outdated packages
dotnet list package --outdated

# Update packages
dotnet add package PackageName --version LatestVersion
```

## Secrets Management

### Environment Variables Best Practices
```python
# Python - using python-dotenv
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
API_KEY = os.getenv('API_KEY')

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")
```

```csharp
// C# - using IConfiguration
public class DatabaseService
{
    private readonly string _connectionString;
    
    public DatabaseService(IConfiguration configuration)
    {
        _connectionString = configuration.GetConnectionString("DefaultConnection") 
            ?? throw new InvalidOperationException("Connection string not found");
    }
}
```

### Git Secrets Prevention
```bash
# Install git-secrets
git secrets --install

# Add patterns to prevent commits
git secrets --register-aws
git secrets --add 'password\s*=\s*.+'
git secrets --add 'api[_-]?key\s*=\s*.+'

# Scan repository
git secrets --scan
```

### Pre-commit Hooks for Security
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
  
  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.5
    hooks:
      - id: bandit
        args: ['-c', '.bandit']
```

## Input Validation and Sanitization

### Python Input Validation
```python
from typing import Optional
import re
from email_validator import validate_email, EmailNotValidError

def validate_user_input(email: str, age: Optional[int] = None) -> dict:
    """Validate user input with proper sanitization."""
    errors = []
    
    # Email validation
    try:
        valid_email = validate_email(email)
        email = valid_email.email
    except EmailNotValidError:
        errors.append("Invalid email format")
    
    # Age validation
    if age is not None:
        if not isinstance(age, int) or age < 0 or age > 150:
            errors.append("Age must be between 0 and 150")
    
    return {"email": email, "age": age, "errors": errors}
```

### C# Input Validation
```csharp
using System.ComponentModel.DataAnnotations;

public class UserDto
{
    [Required]
    [EmailAddress]
    [StringLength(100)]
    public string Email { get; set; }
    
    [Range(0, 150)]
    public int? Age { get; set; }
    
    [RegularExpression(@"^[a-zA-Z\s]+$")]
    [StringLength(50)]
    public string Name { get; set; }
}

public class UserController : ControllerBase
{
    [HttpPost]
    public IActionResult CreateUser([FromBody] UserDto user)
    {
        if (!ModelState.IsValid)
        {
            return BadRequest(ModelState);
        }
        
        // Process valid input
        return Ok();
    }
}
```

## Authentication and Authorization

### JWT Security Best Practices
```python
# Python JWT implementation
import jwt
from datetime import datetime, timedelta
from typing import Optional

class JWTManager:
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
    
    def create_token(self, user_id: str, expires_in: int = 3600) -> str:
        payload = {
            "user_id": user_id,
            "exp": datetime.utcnow() + timedelta(seconds=expires_in),
            "iat": datetime.utcnow()
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> Optional[dict]:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
```

```csharp
// C# JWT implementation
public class JwtService
{
    private readonly string _secretKey;
    private readonly string _issuer;
    
    public JwtService(IConfiguration configuration)
    {
        _secretKey = configuration["Jwt:SecretKey"];
        _issuer = configuration["Jwt:Issuer"];
    }
    
    public string GenerateToken(string userId, int expiresInMinutes = 60)
    {
        var key = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(_secretKey));
        var credentials = new SigningCredentials(key, SecurityAlgorithms.HmacSha256);
        
        var claims = new[]
        {
            new Claim(ClaimTypes.NameIdentifier, userId),
            new Claim(JwtRegisteredClaimNames.Jti, Guid.NewGuid().ToString()),
            new Claim(JwtRegisteredClaimNames.Iat, DateTimeOffset.UtcNow.ToUnixTimeSeconds().ToString())
        };
        
        var token = new JwtSecurityToken(
            issuer: _issuer,
            audience: _issuer,
            claims: claims,
            expires: DateTime.UtcNow.AddMinutes(expiresInMinutes),
            signingCredentials: credentials
        );
        
        return new JwtSecurityTokenHandler().WriteToken(token);
    }
}
```
