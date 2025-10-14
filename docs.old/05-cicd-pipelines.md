# CI/CD Pipeline Best Practices

## GitHub Actions Workflows

### Python CI/CD Pipeline

**Pipeline Design Philosophy**: This GitHub Actions workflow implements a comprehensive CI/CD pipeline that balances speed, security, and reliability. Each job serves a specific purpose in the software delivery lifecycle.

**Strategic Pipeline Decisions**:
1. **Multi-version testing**: Ensures compatibility across Python versions
2. **Service dependencies**: Real database testing for integration scenarios
3. **Security-first approach**: Multiple security scans before deployment
4. **Caching optimization**: Reduces build times and costs
5. **Conditional deployment**: Only deploy from main branch after all checks pass

```yaml
# .github/workflows/python-ci.yml
name: Python CI/CD

on:
  push:
    branches: [ main, develop ]        # Trigger on main branches
  pull_request:
    branches: [ main ]                 # Test PRs against main

env:
  PYTHON_VERSION: '3.11'              # Default version for deployment

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.9', '3.10', '3.11']  # Test compatibility across versions
    
    services:
      postgres:
        # Why real database in CI:
        # 1. Catches database-specific issues early
        # 2. Tests actual SQL queries and migrations
        # 3. Validates database schema changes
        # 4. Ensures compatibility with production database version
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: testdb
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
        cache: 'pip'                   # Cache pip dependencies for faster builds
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    
    - name: Lint with flake8
      # Linting strategy: Two-phase approach
      # 1. Fail fast on critical errors (syntax, undefined names)
      # 2. Report all issues but don't fail build (allows gradual improvement)
      run: |
        flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
        flake8 . --count --exit-zero --max-complexity=10 --max-line-length=88 --statistics
    
    - name: Format check with black
      # Why format checking in CI: Prevents formatting-related merge conflicts
      # Using --check prevents automatic formatting in CI
      run: black --check .
    
    - name: Type check with mypy
      # Type checking benefits: Catches type-related bugs before runtime
      # Improves code documentation and enables better IDE support
      run: mypy .
    
    - name: Security check with bandit
      # Security scanning strategy: Run on every commit to catch vulnerabilities early
      # Bandit specifically looks for Python security anti-patterns
      run: bandit -r src/
    
    - name: Test with pytest
      run: |
        pytest --cov=src --cov-report=xml --cov-report=html
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/testdb
    
    - name: Upload coverage to Codecov
      # Coverage tracking provides historical trends and PR impact reporting
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: unittests
        name: codecov-umbrella

  security-scan:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Run Trivy vulnerability scanner
      uses: aquasecurity/trivy-action@master
      with:
        scan-type: 'fs'
        scan-ref: '.'
        format: 'sarif'
        output: 'trivy-results.sarif'
    
    - name: Upload Trivy scan results to GitHub Security tab
      uses: github/codeql-action/upload-sarif@v2
      with:
        sarif_file: 'trivy-results.sarif'

  build-and-deploy:
    needs: [test, security-scan]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3
    
    - name: Login to Container Registry
      uses: docker/login-action@v3
      with:
        registry: ghcr.io
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}
    
    - name: Build and push Docker image
      uses: docker/build-push-action@v5
      with:
        context: .
        push: true
        tags: |
          ghcr.io/${{ github.repository }}:latest
          ghcr.io/${{ github.repository }}:${{ github.sha }}
        cache-from: type=gha
        cache-to: type=gha,mode=max
```

### C# CI/CD Pipeline
```yaml
# .github/workflows/dotnet-ci.yml
name: .NET CI/CD

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

env:
  DOTNET_VERSION: '8.0.x'

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: testdb
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
    - uses: actions/checkout@v4
    
    - name: Setup .NET
      uses: actions/setup-dotnet@v3
      with:
        dotnet-version: ${{ env.DOTNET_VERSION }}
    
    - name: Restore dependencies
      run: dotnet restore
    
    - name: Build
      run: dotnet build --no-restore --configuration Release
    
    - name: Format check
      run: dotnet format --verify-no-changes --verbosity diagnostic
    
    - name: Run tests
      run: |
        dotnet test --no-build --configuration Release \
          --collect:"XPlat Code Coverage" \
          --results-directory ./coverage \
          --logger trx \
          --logger "console;verbosity=detailed"
      env:
        ConnectionStrings__DefaultConnection: "Host=localhost;Database=testdb;Username=postgres;Password=postgres"
    
    - name: Generate coverage report
      run: |
        dotnet tool install -g dotnet-reportgenerator-globaltool
        reportgenerator -reports:"coverage/**/coverage.cobertura.xml" -targetdir:"coveragereport" -reporttypes:"Html;Cobertura"
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coveragereport/Cobertura.xml
        flags: unittests

  security-scan:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Setup .NET
      uses: actions/setup-dotnet@v3
      with:
        dotnet-version: ${{ env.DOTNET_VERSION }}
    
    - name: Restore dependencies
      run: dotnet restore
    
    - name: Check for vulnerable packages
      run: dotnet list package --vulnerable --include-transitive
    
    - name: Run Trivy vulnerability scanner
      uses: aquasecurity/trivy-action@master
      with:
        scan-type: 'fs'
        scan-ref: '.'
        format: 'sarif'
        output: 'trivy-results.sarif'

  sonarcloud:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
      with:
        fetch-depth: 0
    
    - name: Setup .NET
      uses: actions/setup-dotnet@v3
      with:
        dotnet-version: ${{ env.DOTNET_VERSION }}
    
    - name: Cache SonarCloud packages
      uses: actions/cache@v3
      with:
        path: ~/.sonar/cache
        key: ${{ runner.os }}-sonar
        restore-keys: ${{ runner.os }}-sonar
    
    - name: Install SonarCloud scanner
      run: dotnet tool install --global dotnet-sonarscanner
    
    - name: Build and analyze
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
      run: |
        dotnet-sonarscanner begin /k:"my-project-key" /o:"my-org" /d:sonar.login="${{ secrets.SONAR_TOKEN }}" /d:sonar.host.url="https://sonarcloud.io" /d:sonar.cs.opencover.reportsPaths="**/coverage.opencover.xml"
        dotnet build --configuration Release
        dotnet test --configuration Release --collect:"XPlat Code Coverage" -- DataCollectionRunSettings.DataCollectors.DataCollector.Configuration.Format=opencover
        dotnet-sonarscanner end /d:sonar.login="${{ secrets.SONAR_TOKEN }}"

  build-and-deploy:
    needs: [test, security-scan]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Setup .NET
      uses: actions/setup-dotnet@v3
      with:
        dotnet-version: ${{ env.DOTNET_VERSION }}
    
    - name: Publish application
      run: dotnet publish -c Release -o ./publish
    
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3
    
    - name: Login to Container Registry
      uses: docker/login-action@v3
      with:
        registry: ghcr.io
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}
    
    - name: Build and push Docker image
      uses: docker/build-push-action@v5
      with:
        context: .
        push: true
        tags: |
          ghcr.io/${{ github.repository }}:latest
          ghcr.io/${{ github.repository }}:${{ github.sha }}
```

## Azure DevOps Pipelines

### Python Azure Pipeline
```yaml
# azure-pipelines-python.yml
trigger:
  branches:
    include:
    - main
    - develop

pool:
  vmImage: 'ubuntu-latest'

variables:
  pythonVersion: '3.11'

stages:
- stage: Test
  displayName: 'Test Stage'
  jobs:
  - job: TestJob
    displayName: 'Run Tests'
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: testdb
        ports:
          - 5432:5432

    steps:
    - task: UsePythonVersion@0
      inputs:
        versionSpec: '$(pythonVersion)'
      displayName: 'Use Python $(pythonVersion)'

    - script: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
      displayName: 'Install dependencies'

    - script: |
        flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
        black --check .
        mypy .
      displayName: 'Code quality checks'

    - script: |
        bandit -r src/ -f json -o bandit-report.json
      displayName: 'Security scan'

    - script: |
        pytest --cov=src --cov-report=xml --cov-report=html --junitxml=test-results.xml
      displayName: 'Run tests'
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/testdb

    - task: PublishTestResults@2
      inputs:
        testResultsFiles: 'test-results.xml'
        testRunTitle: 'Python Tests'

    - task: PublishCodeCoverageResults@1
      inputs:
        codeCoverageTool: 'Cobertura'
        summaryFileLocation: 'coverage.xml'
        reportDirectory: 'htmlcov'

- stage: Build
  displayName: 'Build Stage'
  dependsOn: Test
  condition: and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))
  
  jobs:
  - job: BuildJob
    displayName: 'Build and Push Image'
    
    steps:
    - task: Docker@2
      displayName: 'Build and push image'
      inputs:
        containerRegistry: 'myregistry'
        repository: 'myapp'
        command: 'buildAndPush'
        Dockerfile: 'Dockerfile'
        tags: |
          $(Build.BuildId)
          latest
```

### C# Azure Pipeline
```yaml
# azure-pipelines-dotnet.yml
trigger:
  branches:
    include:
    - main
    - develop

pool:
  vmImage: 'ubuntu-latest'

variables:
  buildConfiguration: 'Release'
  dotNetVersion: '8.0.x'

stages:
- stage: Test
  displayName: 'Test Stage'
  jobs:
  - job: TestJob
    displayName: 'Run Tests'
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: testdb
        ports:
          - 5432:5432

    steps:
    - task: UseDotNet@2
      displayName: 'Use .NET $(dotNetVersion)'
      inputs:
        packageType: 'sdk'
        version: '$(dotNetVersion)'

    - task: DotNetCoreCLI@2
      displayName: 'Restore packages'
      inputs:
        command: 'restore'
        projects: '**/*.csproj'

    - task: DotNetCoreCLI@2
      displayName: 'Build solution'
      inputs:
        command: 'build'
        projects: '**/*.csproj'
        arguments: '--configuration $(buildConfiguration) --no-restore'

    - script: |
        dotnet format --verify-no-changes --verbosity diagnostic
      displayName: 'Format check'

    - task: DotNetCoreCLI@2
      displayName: 'Run tests'
      inputs:
        command: 'test'
        projects: '**/*Tests.csproj'
        arguments: '--configuration $(buildConfiguration) --no-build --collect:"XPlat Code Coverage" --logger trx --results-directory $(Agent.TempDirectory)'
      env:
        ConnectionStrings__DefaultConnection: 'Host=localhost;Database=testdb;Username=postgres;Password=postgres'

    - task: PublishTestResults@2
      inputs:
        testRunner: VSTest
        testResultsFiles: '$(Agent.TempDirectory)/**/*.trx'

    - task: PublishCodeCoverageResults@1
      inputs:
        codeCoverageTool: 'Cobertura'
        summaryFileLocation: '$(Agent.TempDirectory)/**/coverage.cobertura.xml'

- stage: Build
  displayName: 'Build Stage'
  dependsOn: Test
  condition: and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))
  
  jobs:
  - job: BuildJob
    displayName: 'Build and Push Image'
    
    steps:
    - task: DotNetCoreCLI@2
      displayName: 'Publish application'
      inputs:
        command: 'publish'
        publishWebProjects: true
        arguments: '--configuration $(buildConfiguration) --output $(Build.ArtifactStagingDirectory)'

    - task: Docker@2
      displayName: 'Build and push image'
      inputs:
        containerRegistry: 'myregistry'
        repository: 'myapp'
        command: 'buildAndPush'
        Dockerfile: 'Dockerfile'
        tags: |
          $(Build.BuildId)
          latest
```

## GitLab CI/CD

### Python GitLab Pipeline
```yaml
# .gitlab-ci.yml
stages:
  - test
  - security
  - build
  - deploy

variables:
  PYTHON_VERSION: "3.11"
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"

cache:
  paths:
    - .cache/pip
    - venv/

before_script:
  - python -m venv venv
  - source venv/bin/activate
  - pip install --upgrade pip
  - pip install -r requirements.txt
  - pip install -r requirements-dev.txt

test:
  stage: test
  image: python:$PYTHON_VERSION
  services:
    - postgres:15
  variables:
    POSTGRES_DB: testdb
    POSTGRES_USER: postgres
    POSTGRES_PASSWORD: postgres
    DATABASE_URL: postgresql://postgres:postgres@postgres:5432/testdb
  script:
    - flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
    - black --check .
    - mypy .
    - pytest --cov=src --cov-report=xml --cov-report=html --junitxml=report.xml
  coverage: '/TOTAL.+ ([0-9]{1,3}%)/'
  artifacts:
    reports:
      junit: report.xml
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml
    paths:
      - htmlcov/

security:
  stage: security
  image: python:$PYTHON_VERSION
  script:
    - bandit -r src/ -f json -o bandit-report.json
    - safety check --json --output safety-report.json
  artifacts:
    reports:
      sast: bandit-report.json
    paths:
      - safety-report.json
  allow_failure: true

trivy:
  stage: security
  image: aquasec/trivy:latest
  script:
    - trivy fs --format template --template "@contrib/sarif.tpl" -o trivy-report.sarif .
  artifacts:
    reports:
      sast: trivy-report.sarif

build:
  stage: build
  image: docker:latest
  services:
    - docker:dind
  script:
    - docker build -t $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA .
    - docker push $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA
  only:
    - main
```

## Deployment Strategies

### Blue-Green Deployment
```yaml
# blue-green-deploy.yml
name: Blue-Green Deployment

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - name: Deploy to Blue Environment
      run: |
        # Deploy to blue environment
        kubectl set image deployment/myapp-blue myapp=${{ env.IMAGE_TAG }}
        kubectl rollout status deployment/myapp-blue
        
        # Run health checks
        ./scripts/health-check.sh blue
        
        # Switch traffic to blue
        kubectl patch service myapp -p '{"spec":{"selector":{"version":"blue"}}}'
        
        # Cleanup green environment
        kubectl scale deployment myapp-green --replicas=0
```

### Canary Deployment
```yaml
# canary-deploy.yml
name: Canary Deployment

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - name: Deploy Canary
      run: |
        # Deploy canary version (10% traffic)
        kubectl set image deployment/myapp-canary myapp=${{ env.IMAGE_TAG }}
        kubectl scale deployment myapp-canary --replicas=1
        
        # Monitor metrics for 10 minutes
        sleep 600
        
        # Check error rates and performance
        if ./scripts/canary-check.sh; then
          # Promote canary to production
          kubectl set image deployment/myapp-prod myapp=${{ env.IMAGE_TAG }}
          kubectl scale deployment myapp-canary --replicas=0
        else
          # Rollback canary
          kubectl scale deployment myapp-canary --replicas=0
          exit 1
        fi
```

## Pipeline Security Best Practices

### Secret Management
```yaml
# Using GitHub Secrets
env:
  DATABASE_URL: ${{ secrets.DATABASE_URL }}
  API_KEY: ${{ secrets.API_KEY }}

# Using Azure Key Vault
- task: AzureKeyVault@2
  inputs:
    azureSubscription: 'mysubscription'
    KeyVaultName: 'myvault'
    SecretsFilter: 'DatabaseConnectionString,ApiKey'
```

### OIDC Authentication
```yaml
# GitHub OIDC with AWS
- name: Configure AWS credentials
  uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: arn:aws:iam::123456789012:role/GitHubActions
    role-session-name: GitHubActions
    aws-region: us-east-1

# GitHub OIDC with Azure
- name: Azure Login
  uses: azure/login@v1
  with:
    client-id: ${{ secrets.AZURE_CLIENT_ID }}
    tenant-id: ${{ secrets.AZURE_TENANT_ID }}
    subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
```
