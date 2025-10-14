# Development Environment Setup Best Practices

## Python Environment Management

### Virtual Environments with venv

**Why This Matters**: Virtual environments are fundamental to Python development because they isolate project dependencies, preventing version conflicts between projects. Without virtual environments, installing packages globally can lead to dependency hell where different projects require incompatible versions of the same package.

**Decision Making**: Choose venv for simplicity and built-in availability, pyenv for Python version management, or Poetry for advanced dependency management with lock files.

```bash
# Create virtual environment
python -m venv myproject-env

# Activate (Linux/macOS)
source myproject-env/bin/activate

# Activate (Windows)
myproject-env\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Deactivate
deactivate
```

**AI Assistant Considerations**: 
- Always check if a virtual environment is active before suggesting package installations
- Recommend creating project-specific environments rather than using global Python
- Consider the target OS when providing activation commands
- Suggest using descriptive environment names that include project context

### Advanced Environment Management with pyenv

**Why pyenv**: Different projects often require different Python versions. System Python versions can become outdated or incompatible. pyenv allows seamless switching between Python versions per project without affecting the system installation.

**Decision Criteria**: Use pyenv when:
- Working with multiple projects requiring different Python versions
- Need to test compatibility across Python versions
- System Python is outdated or managed by the OS package manager
- Working in a team where Python version consistency is critical

```bash
# Install specific Python version
pyenv install 3.11.5

# Set global Python version
pyenv global 3.11.5

# Set local project version
pyenv local 3.11.5
```

**AI Assistant Guidance**: 
- Check project requirements before suggesting Python versions
- Recommend LTS versions for production projects
- Consider team consistency when suggesting version choices
- Always verify pyenv is installed before suggesting pyenv commands

### Poetry for Dependency Management

**Why Poetry Over pip**: Poetry solves several critical problems in Python dependency management:
1. **Lock files**: Ensures reproducible builds across environments
2. **Dependency resolution**: Automatically resolves version conflicts
3. **Virtual environment management**: Handles venv creation automatically
4. **Build system**: Standardized packaging and publishing
5. **Semantic versioning**: Better version constraint handling

**When to Choose Poetry**:
- New projects where you control the toolchain
- Projects requiring strict dependency reproducibility
- Libraries that will be published to PyPI
- Teams that need consistent dependency management

**When to Avoid Poetry**:
- Legacy projects with existing pip workflows
- Environments where Poetry installation is restricted
- Simple scripts with minimal dependencies

```bash
# Initialize new project
poetry init

# Add dependencies
poetry add requests pytest

# Add development dependencies
poetry add --group dev black flake8 mypy

# Install dependencies
poetry install

# Activate shell
poetry shell
```

**AI Assistant Decision Framework**:
- For new projects: Recommend Poetry unless constraints exist
- For existing projects: Assess migration effort vs. benefits
- Consider team familiarity and CI/CD pipeline compatibility
- Always check if pyproject.toml exists before suggesting Poetry commands

## C# Development Environment

### .NET SDK Management

**Why SDK Version Management Matters**: Different projects may target different .NET versions for compatibility, performance, or feature requirements. Global.json ensures team consistency and prevents "works on my machine" issues.

**Decision Considerations**:
- **LTS vs Current**: LTS for production stability, Current for latest features
- **Backward compatibility**: Newer SDKs can target older frameworks
- **Team alignment**: Use global.json to enforce team-wide consistency
- **CI/CD compatibility**: Ensure build agents support the chosen version

```bash
# List installed SDKs
dotnet --list-sdks

# Create global.json for version pinning
echo '{"sdk": {"version": "8.0.100"}}' > global.json

# Create new solution
dotnet new sln -n MyProject

# Create projects
dotnet new webapi -n MyProject.Api
dotnet new classlib -n MyProject.Core
dotnet new xunit -n MyProject.Tests
```

**AI Assistant Guidance**:
- Always check existing global.json before suggesting SDK versions
- Recommend LTS versions for new production projects
- Consider project type when suggesting templates (webapi, classlib, console)
- Verify SDK availability before suggesting specific versions

### Project Structure Best Practices

**Why This Structure**: This follows .NET solution conventions and promotes:
1. **Separation of concerns**: Clear boundaries between API, business logic, and data access
2. **Testability**: Separate test projects for each component
3. **Maintainability**: Logical organization that scales with project growth
4. **Team collaboration**: Familiar structure for .NET developers

**Decision Framework for Project Organization**:
- **Small projects**: May combine Core and Infrastructure
- **Microservices**: Each service gets its own solution
- **Shared libraries**: Consider separate solutions for reusable components
- **Integration tests**: May warrant separate project from unit tests

```
MyProject/
├── src/                          # Source code (separates from tests/docs)
│   ├── MyProject.Api/           # Web API layer (controllers, middleware)
│   ├── MyProject.Core/          # Business logic (domain models, services)
│   └── MyProject.Infrastructure/ # Data access, external services
├── tests/                       # All test projects
│   ├── MyProject.Api.Tests/     # API integration tests
│   ├── MyProject.Core.Tests/    # Unit tests for business logic
│   └── MyProject.Integration.Tests/ # End-to-end tests
├── docs/                        # Documentation
├── scripts/                     # Build/deployment scripts
└── MyProject.sln               # Solution file
```

**AI Assistant Considerations**:
- Suggest appropriate project types based on described functionality
- Recommend consistent naming conventions across the solution
- Consider project dependencies when suggesting structure modifications
- Always maintain the src/tests separation for clarity

## IDE Configuration

### VS Code Settings

**Why These Settings Matter**: Consistent IDE configuration across team members prevents formatting conflicts, enables early error detection, and improves code quality through automated tooling.

**Configuration Philosophy**:
- **Automation over manual work**: Let tools handle formatting and basic checks
- **Early feedback**: Catch issues in the editor before commit
- **Team consistency**: Shared settings prevent style conflicts
- **Language-specific optimization**: Tailored settings for Python and C#

```json
{
  "python.defaultInterpreterPath": "./venv/bin/python",  // Project-specific Python
  "python.linting.enabled": true,                       // Enable linting
  "python.linting.pylintEnabled": true,                 // Use pylint for comprehensive checks
  "python.formatting.provider": "black",                // Consistent formatting
  "omnisharp.enableRoslynAnalyzers": true,             // C# code analysis
  "dotnet.completion.showCompletionItemsFromUnimportedNamespaces": true  // Better IntelliSense
}
```

**Decision Criteria for IDE Settings**:
- **Team vs Individual**: Use workspace settings for team consistency
- **Tool Selection**: Choose tools that integrate well with your CI/CD pipeline
- **Performance**: Balance features with editor responsiveness
- **Extension Management**: Standardize essential extensions across the team

**AI Assistant Guidance**:
- Always suggest workspace settings for team projects
- Recommend extensions that complement the suggested settings
- Consider the developer's OS when suggesting paths and configurations
- Verify tool availability before suggesting specific integrations

### EditorConfig

**Why EditorConfig is Essential**: EditorConfig ensures consistent formatting across different editors, operating systems, and team members. It's particularly crucial in mixed-language projects and diverse development environments.

**Key Benefits**:
1. **Cross-editor consistency**: Works with VS Code, Visual Studio, IntelliJ, etc.
2. **Automatic application**: No manual configuration needed
3. **Language-specific rules**: Different settings for different file types
4. **Version control friendly**: Prevents formatting-related merge conflicts

**Decision Framework**:
- **Line endings**: LF for cross-platform compatibility, CRLF only if Windows-specific
- **Indentation**: Spaces for consistency, tabs only if team prefers them
- **Charset**: UTF-8 for international character support
- **Final newline**: Required for POSIX compliance and better diffs

```ini
root = true

[*]                              # Apply to all files
charset = utf-8                  # Unicode support
end_of_line = lf                # Unix line endings (cross-platform)
insert_final_newline = true     # POSIX compliance
trim_trailing_whitespace = true # Clean diffs

[*.{py,cs}]                     # Python and C# files
indent_style = space            # Spaces over tabs for consistency
indent_size = 4                 # Standard for both languages

[*.{json,yml,yaml}]             # Configuration files
indent_size = 2                 # Smaller indentation for readability
```

**AI Assistant Considerations**:
- Always include EditorConfig in new project setups
- Respect existing EditorConfig settings when suggesting changes
- Consider file types when recommending indentation rules
- Explain the reasoning behind line ending choices for cross-platform projects

## Git Configuration

### .gitignore Templates

**Why Comprehensive .gitignore Matters**: A well-crafted .gitignore prevents sensitive data leaks, reduces repository size, and eliminates noise from generated files. It's your first line of defense against accidental commits of secrets or build artifacts.

**Strategic Considerations**:
- **Security**: Never commit secrets, API keys, or credentials
- **Performance**: Exclude large binary files and build outputs
- **Collaboration**: Ignore IDE-specific files that vary by developer
- **Maintenance**: Keep patterns up-to-date with toolchain changes

```gitignore
# Python
__pycache__/                    # Compiled Python files
*.py[cod]                       # Python bytecode variants
*$py.class                      # Jython compiled classes
.env                           # Environment variables (CRITICAL for security)
venv/                          # Virtual environment
.pytest_cache/                 # Test cache files

# C#
bin/                           # Compiled binaries
obj/                           # Build intermediate files
*.user                         # User-specific project settings
*.suo                          # Visual Studio user options
.vs/                           # Visual Studio cache
```

**AI Assistant Decision Framework**:
- Always include .env and credential files in .gitignore suggestions
- Consider the specific tools and frameworks being used
- Recommend language-specific templates from gitignore.io
- Warn about potential security risks when files might contain secrets

### Git Hooks Setup

**Why Git Hooks are Game-Changers**: Git hooks automate quality checks before code reaches the repository, preventing broken builds and maintaining code standards. They're your automated quality gate that runs consistently for every developer.

**Hook Strategy**:
- **Pre-commit**: Fast checks that prevent obviously broken commits
- **Pre-push**: More comprehensive checks before sharing code
- **Fail fast**: Quick feedback loop for developers
- **Consistent enforcement**: Same checks for all team members

**Implementation Considerations**:
- **Performance**: Keep pre-commit hooks fast (< 30 seconds)
- **Reliability**: Hooks should be deterministic and not flaky
- **Bypass mechanism**: Allow override for emergency situations
- **Tool availability**: Ensure all required tools are documented

```bash
# Pre-commit hook for Python
#!/bin/sh
# Fast formatting and linting checks
black --check .                 # Formatting verification (fast)
flake8 .                       # Linting (catches obvious issues)
pytest tests/unit/             # Only fast unit tests

# Pre-commit hook for C#
#!/bin/sh
# Code quality checks before commit
dotnet format --verify-no-changes  # Formatting verification
dotnet test --filter Category=Unit # Fast unit tests only
```

**AI Assistant Guidance**:
- Suggest appropriate hook types based on project needs
- Recommend fast checks for pre-commit, comprehensive for pre-push
- Always include instructions for hook installation and bypass
- Consider CI/CD pipeline alignment when suggesting hook content
