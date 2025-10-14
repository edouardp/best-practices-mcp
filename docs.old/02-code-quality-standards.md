# Code Quality and Standards Best Practices

## Python Code Quality

### Code Formatting with Black
```bash
# Install black
pip install black

# Format code
black .

# Check formatting
black --check .

# Configuration in pyproject.toml
[tool.black]
line-length = 88
target-version = ['py311']
include = '\.pyi?$'
```

### Linting with Flake8
```bash
# Install flake8
pip install flake8

# Run linting
flake8 .

# Configuration in .flake8
[flake8]
max-line-length = 88
extend-ignore = E203, W503
exclude = .git,__pycache__,venv
```

### Type Checking with mypy
```bash
# Install mypy
pip install mypy

# Run type checking
mypy .

# Configuration in mypy.ini
[mypy]
python_version = 3.11
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True
```

### Import Sorting with isort
```bash
# Install isort
pip install isort

# Sort imports
isort .

# Configuration in pyproject.toml
[tool.isort]
profile = "black"
multi_line_output = 3
```

## C# Code Quality

### Code Formatting with dotnet format
```bash
# Format code
dotnet format

# Verify formatting
dotnet format --verify-no-changes

# Format specific project
dotnet format MyProject.sln
```

### EditorConfig for C#
```ini
[*.cs]
# Indentation preferences
csharp_indent_case_contents = true
csharp_indent_switch_labels = true

# New line preferences
csharp_new_line_before_open_brace = all
csharp_new_line_before_else = true
csharp_new_line_before_catch = true

# Space preferences
csharp_space_after_cast = false
csharp_space_after_keywords_in_control_flow_statements = true

# Organize usings
dotnet_sort_system_directives_first = true
dotnet_separate_import_directive_groups = false
```

### Roslyn Analyzers
```xml
<PackageReference Include="Microsoft.CodeAnalysis.Analyzers" Version="3.3.4" PrivateAssets="all" />
<PackageReference Include="Microsoft.CodeAnalysis.NetAnalyzers" Version="8.0.0" PrivateAssets="all" />
<PackageReference Include="StyleCop.Analyzers" Version="1.1.118" PrivateAssets="all" />
```

## Code Review Guidelines

### Python Code Review Checklist
- [ ] Code follows PEP 8 standards
- [ ] Type hints are present and accurate
- [ ] Docstrings follow Google or NumPy style
- [ ] No hardcoded values or secrets
- [ ] Error handling is appropriate
- [ ] Tests cover new functionality
- [ ] Performance considerations addressed

### C# Code Review Checklist
- [ ] Follows C# coding conventions
- [ ] XML documentation comments present
- [ ] Proper exception handling
- [ ] SOLID principles applied
- [ ] Async/await used correctly
- [ ] Memory management considered
- [ ] Security best practices followed

## Documentation Standards

### Python Docstring Examples
```python
def calculate_discount(price: float, discount_rate: float) -> float:
    """Calculate discounted price.
    
    Args:
        price: Original price of the item
        discount_rate: Discount rate as decimal (0.1 for 10%)
        
    Returns:
        Discounted price
        
    Raises:
        ValueError: If price is negative or discount_rate is invalid
    """
    if price < 0:
        raise ValueError("Price cannot be negative")
    if not 0 <= discount_rate <= 1:
        raise ValueError("Discount rate must be between 0 and 1")
    
    return price * (1 - discount_rate)
```

### C# XML Documentation
```csharp
/// <summary>
/// Calculates the discounted price for an item
/// </summary>
/// <param name="price">The original price of the item</param>
/// <param name="discountRate">The discount rate as a decimal (0.1 for 10%)</param>
/// <returns>The discounted price</returns>
/// <exception cref="ArgumentException">Thrown when price is negative or discount rate is invalid</exception>
public decimal CalculateDiscount(decimal price, decimal discountRate)
{
    if (price < 0)
        throw new ArgumentException("Price cannot be negative", nameof(price));
    if (discountRate < 0 || discountRate > 1)
        throw new ArgumentException("Discount rate must be between 0 and 1", nameof(discountRate));
    
    return price * (1 - discountRate);
}
```

## Complexity Management

### Cyclomatic Complexity Guidelines
- Functions should have complexity ≤ 10
- Classes should have complexity ≤ 50
- Use tools like radon (Python) or Visual Studio metrics (C#)

### Python Complexity Checking
```bash
# Install radon
pip install radon

# Check cyclomatic complexity
radon cc . -a

# Check maintainability index
radon mi .
```

### C# Complexity Analysis
```xml
<!-- In .csproj file -->
<PropertyGroup>
  <CodeAnalysisRuleSet>ruleset.ruleset</CodeAnalysisRuleSet>
  <WarningsAsErrors />
  <TreatWarningsAsErrors>true</TreatWarningsAsErrors>
</PropertyGroup>
```
