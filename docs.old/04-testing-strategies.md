# Testing Strategies and Best Practices

## Python Testing Framework

### pytest Configuration

**Why pytest Over unittest**: pytest provides a more intuitive and powerful testing experience with:
1. **Simpler syntax**: No need for class inheritance or verbose assertions
2. **Better fixtures**: Dependency injection system for test setup
3. **Rich plugin ecosystem**: Extensions for coverage, parallel execution, etc.
4. **Detailed failure reporting**: Clear information when tests fail
5. **Parametrized testing**: Easy data-driven test creation

**Configuration Strategy Philosophy**: The conftest.py and pytest.ini files establish testing infrastructure that promotes:
- **Consistency**: Same setup across all tests
- **Isolation**: Each test runs in a clean environment
- **Maintainability**: Centralized configuration and fixtures
- **Performance**: Efficient resource management

```python
# conftest.py - Central fixture definition
import pytest
from unittest.mock import Mock
from myapp import create_app, db

@pytest.fixture
def app():
    """Create application for testing.
    
    Why this pattern: Creates a fresh app instance for each test,
    ensuring test isolation and preventing state leakage between tests.
    """
    app = create_app(testing=True)
    with app.app_context():
        db.create_all()          # Fresh database for each test
        yield app                # Provide app to test
        db.drop_all()           # Clean up after test

@pytest.fixture
def client(app):
    """Create test client.
    
    Decision rationale: Separate fixture allows tests to use either
    the app directly (for unit tests) or the client (for integration tests).
    """
    return app.test_client()

@pytest.fixture
def mock_database():
    """Mock database connection.
    
    When to use: Unit tests that shouldn't touch real database.
    Provides fast, isolated testing of business logic.
    """
    return Mock()
```

**pytest.ini Configuration Decisions**:

```ini
# pytest.ini - Project-wide test configuration
[tool:pytest]
testpaths = tests                    # Where to find tests (performance optimization)
python_files = test_*.py *_test.py   # Test file naming patterns
python_classes = Test*               # Test class naming (optional with pytest)
python_functions = test_*            # Test function naming
addopts = 
    --strict-markers                 # Prevent typos in test markers
    --strict-config                  # Catch configuration errors early
    --cov=src                       # Coverage measurement
    --cov-report=html               # Human-readable coverage reports
    --cov-report=term-missing       # Show missing lines in terminal
    --cov-fail-under=80            # Enforce minimum coverage threshold
markers =
    unit: Unit tests                 # Fast, isolated tests
    integration: Integration tests   # Tests with external dependencies
    slow: Slow running tests        # Mark expensive tests for selective running
```

**AI Assistant Configuration Guidance**:
- Always recommend separate fixtures for different test types (unit vs integration)
- Suggest appropriate coverage thresholds based on project maturity (new: 70%, mature: 85%+)
- Recommend marker usage for test categorization and selective execution
- Consider test performance when suggesting fixture scope (function, class, module, session)

### Unit Testing Examples

**Unit Testing Philosophy**: Unit tests should be fast, isolated, and focused on a single piece of functionality. They form the foundation of your test pyramid and should comprise 70-80% of your test suite.

**Key Principles Demonstrated**:
1. **Arrange-Act-Assert Pattern**: Clear test structure that's easy to understand
2. **Descriptive Test Names**: Test names should describe the scenario and expected outcome
3. **Single Responsibility**: Each test verifies one specific behavior
4. **Test Data Isolation**: Each test creates its own data to avoid dependencies

```python
# test_calculator.py
import pytest
from myapp.calculator import Calculator

class TestCalculator:
    """Test class organization strategy:
    
    Group related tests in classes for better organization and shared setup.
    Use setup_method for test-specific initialization that's too complex for fixtures.
    """
    
    def setup_method(self):
        """Setup for each test method.
        
        Why setup_method over __init__: pytest calls this before each test,
        ensuring fresh state. Avoids test pollution from shared state.
        """
        self.calculator = Calculator()
    
    def test_add_positive_numbers(self):
        """Test addition of positive numbers.
        
        Naming convention: test_[method]_[scenario]_[expected_result]
        This makes test failures immediately understandable.
        """
        # Arrange - Set up test data
        # Act - Execute the behavior being tested
        result = self.calculator.add(2, 3)
        # Assert - Verify the expected outcome
        assert result == 5
    
    def test_add_negative_numbers(self):
        """Test addition of negative numbers.
        
        Edge case testing: Ensure the method works with different input types.
        Negative numbers are a common edge case that can reveal bugs.
        """
        result = self.calculator.add(-2, -3)
        assert result == -5
    
    def test_divide_by_zero_raises_exception(self):
        """Test division by zero raises appropriate exception.
        
        Exception testing strategy: Verify that invalid inputs are handled correctly.
        This prevents silent failures and ensures proper error handling.
        """
        with pytest.raises(ZeroDivisionError):
            self.calculator.divide(10, 0)
    
    @pytest.mark.parametrize("a,b,expected", [
        (2, 3, 5),      # Basic positive case
        (-1, 1, 0),     # Mixed positive/negative
        (0, 0, 0),      # Zero handling
        (100, -50, 50)  # Larger numbers
    ])
    def test_add_parametrized(self, a, b, expected):
        """Test addition with multiple parameter sets.
        
        Parametrized testing benefits:
        1. Reduces code duplication
        2. Tests multiple scenarios efficiently
        3. Makes it easy to add new test cases
        4. Provides clear failure reporting for each case
        
        When to use: When testing the same logic with different inputs.
        When to avoid: When test scenarios require different setup or assertions.
        """
        assert self.calculator.add(a, b) == expected
```

**AI Assistant Testing Guidance**:
- Recommend parametrized tests for testing multiple input combinations
- Suggest descriptive test names that explain the scenario being tested
- Always include edge case testing (zero, negative, boundary values)
- Recommend exception testing for methods that should fail under certain conditions

### Mocking and Patching
```python
# test_user_service.py
from unittest.mock import Mock, patch, MagicMock
import pytest
from myapp.services import UserService
from myapp.models import User

class TestUserService:
    def setup_method(self):
        self.mock_db = Mock()
        self.user_service = UserService(self.mock_db)
    
    def test_create_user_success(self):
        """Test successful user creation."""
        # Arrange
        user_data = {"name": "John Doe", "email": "john@example.com"}
        expected_user = User(id=1, **user_data)
        self.mock_db.save.return_value = expected_user
        
        # Act
        result = self.user_service.create_user(user_data)
        
        # Assert
        assert result.name == "John Doe"
        assert result.email == "john@example.com"
        self.mock_db.save.assert_called_once()
    
    @patch('myapp.services.send_email')
    def test_create_user_sends_welcome_email(self, mock_send_email):
        """Test that welcome email is sent on user creation."""
        # Arrange
        user_data = {"name": "Jane Doe", "email": "jane@example.com"}
        self.mock_db.save.return_value = User(id=1, **user_data)
        
        # Act
        self.user_service.create_user(user_data)
        
        # Assert
        mock_send_email.assert_called_once_with(
            to="jane@example.com",
            subject="Welcome!",
            template="welcome"
        )
```

## C# Testing with xUnit

### xUnit Project Setup

**Why xUnit Over MSTest or NUnit**: xUnit is the modern choice for .NET testing because:
1. **Isolation by design**: Each test method gets a fresh class instance
2. **Extensibility**: Rich ecosystem of extensions and assertions
3. **Parallel execution**: Built-in support for concurrent test execution
4. **Modern patterns**: Supports dependency injection and async testing naturally

**Package Selection Strategy**: Each package serves a specific purpose in the testing ecosystem:

```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <IsPackable>false</IsPackable>           <!-- Don't create NuGet package -->
    <IsTestProject>true</IsTestProject>      <!-- Enables test discovery -->
  </PropertyGroup>

  <ItemGroup>
    <!-- Core testing framework -->
    <PackageReference Include="Microsoft.NET.Test.Sdk" Version="17.8.0" />
    <PackageReference Include="xunit" Version="2.4.2" />
    <PackageReference Include="xunit.runner.visualstudio" Version="2.4.5" />
    
    <!-- Mocking and assertions -->
    <PackageReference Include="Moq" Version="4.20.69" />              <!-- Mock objects -->
    <PackageReference Include="FluentAssertions" Version="6.12.0" />  <!-- Readable assertions -->
    
    <!-- Integration testing -->
    <PackageReference Include="Microsoft.AspNetCore.Mvc.Testing" Version="8.0.0" />  <!-- Web API testing -->
    <PackageReference Include="Testcontainers" Version="3.6.0" />                    <!-- Docker containers for tests -->
    <PackageReference Include="Testcontainers.PostgreSql" Version="3.6.0" />        <!-- Database testing -->
  </ItemGroup>

  <ItemGroup>
    <!-- Reference projects under test -->
    <ProjectReference Include="..\MyProject.Api\MyProject.Api.csproj" />
    <ProjectReference Include="..\MyProject.Core\MyProject.Core.csproj" />
  </ItemGroup>
</Project>
```

**Package Decision Framework**:
- **Moq**: Use for creating mock objects and verifying interactions
- **FluentAssertions**: Provides more readable and detailed assertion messages
- **TestContainers**: Essential for integration tests requiring real databases
- **Microsoft.AspNetCore.Mvc.Testing**: Required for testing web APIs and controllers

**AI Assistant Package Recommendations**:
- Always include FluentAssertions for better test readability
- Recommend TestContainers for projects with database dependencies
- Suggest Moq for unit tests that need to isolate dependencies
- Consider AutoFixture for generating test data in complex scenarios

### Unit Testing with xUnit and Moq

**C# Unit Testing Philosophy**: C# unit tests should follow the same principles as Python tests but leverage the language's strong typing and dependency injection patterns for better test design.

**Key C# Testing Patterns Demonstrated**:
1. **Constructor injection for dependencies**: Clean setup of mocked dependencies
2. **FluentAssertions for readability**: More expressive than basic Assert methods
3. **Moq for behavior verification**: Verify that dependencies are called correctly
4. **Theory/InlineData for parameterized tests**: xUnit's approach to data-driven testing

```csharp
using Xunit;
using Moq;
using FluentAssertions;
using MyProject.Core.Services;
using MyProject.Core.Models;
using MyProject.Core.Interfaces;

public class UserServiceTests
{
    private readonly Mock<IUserRepository> _mockRepository;
    private readonly Mock<IEmailService> _mockEmailService;
    private readonly UserService _userService;

    public UserServiceTests()
    {
        """Constructor-based setup strategy:
        
        Why this approach:
        1. xUnit creates a new instance for each test (isolation)
        2. Dependencies are clearly visible and consistently mocked
        3. No shared state between tests
        4. Easy to see what the class under test depends on
        """
        _mockRepository = new Mock<IUserRepository>();
        _mockEmailService = new Mock<IEmailService>();
        _userService = new UserService(_mockRepository.Object, _mockEmailService.Object);
    }

    [Fact]
    public async Task CreateUserAsync_ValidUser_ReturnsCreatedUser()
    {
        """Async testing pattern:
        
        Key considerations:
        1. Use async/await consistently in test methods
        2. Return Task for async test methods
        3. Mock async methods with ReturnsAsync
        4. Test both success and failure scenarios
        """
        
        // Arrange - Set up test data and mock behavior
        var userDto = new CreateUserDto { Name = "John Doe", Email = "john@example.com" };
        var expectedUser = new User { Id = 1, Name = "John Doe", Email = "john@example.com" };
        
        _mockRepository.Setup(r => r.CreateAsync(It.IsAny<User>()))
                      .ReturnsAsync(expectedUser);

        // Act - Execute the method under test
        var result = await _userService.CreateUserAsync(userDto);

        // Assert - Verify results and interactions
        result.Should().NotBeNull();                    // FluentAssertions syntax
        result.Name.Should().Be("John Doe");           // More readable than Assert.Equal
        result.Email.Should().Be("john@example.com");
        
        // Verify mock interactions (behavior verification)
        _mockRepository.Verify(r => r.CreateAsync(It.IsAny<User>()), Times.Once);
        _mockEmailService.Verify(e => e.SendWelcomeEmailAsync(It.IsAny<string>()), Times.Once);
    }

    [Theory]                                          // xUnit's parameterized test attribute
    [InlineData("")]                                 // Empty string test case
    [InlineData(null)]                               // Null test case
    [InlineData("   ")]                              // Whitespace test case
    public async Task CreateUserAsync_InvalidName_ThrowsArgumentException(string invalidName)
    {
        """Parameterized exception testing:
        
        Benefits of Theory over multiple Facts:
        1. Reduces code duplication
        2. Tests multiple edge cases efficiently
        3. Clear test failure reporting shows which data caused failure
        4. Easy to add new test cases
        
        When to use Theory vs Fact:
        - Theory: Same test logic, different input data
        - Fact: Unique test scenarios requiring different setup/assertions
        """
        
        // Arrange
        var userDto = new CreateUserDto { Name = invalidName, Email = "john@example.com" };

        // Act & Assert - Verify exception is thrown
        await Assert.ThrowsAsync<ArgumentException>(() => _userService.CreateUserAsync(userDto));
    }

    [Fact]
    public async Task GetUserByIdAsync_ExistingUser_ReturnsUser()
    {
        """Repository pattern testing:
        
        This test demonstrates:
        1. Mocking repository methods that return data
        2. Verifying that the service correctly processes repository results
        3. Using FluentAssertions for more expressive assertions
        """
        
        // Arrange
        var userId = 1;
        var expectedUser = new User { Id = userId, Name = "John Doe", Email = "john@example.com" };
        
        _mockRepository.Setup(r => r.GetByIdAsync(userId))
                      .ReturnsAsync(expectedUser);

        // Act
        var result = await _userService.GetUserByIdAsync(userId);

        // Assert
        result.Should().NotBeNull();
        result.Id.Should().Be(userId);
        result.Name.Should().Be("John Doe");
    }
}
```

**AI Assistant C# Testing Guidance**:
- Always recommend FluentAssertions for more readable test assertions
- Suggest using Theory for testing multiple input scenarios
- Recommend verifying both return values and method interactions with mocks
- Emphasize async/await patterns for modern C# applications

### Integration Testing with TestContainers
```csharp
using Xunit;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.Extensions.DependencyInjection;
using Testcontainers.PostgreSql;
using System.Net.Http.Json;
using FluentAssertions;

public class UserControllerIntegrationTests : IAsyncLifetime
{
    private readonly PostgreSqlContainer _dbContainer;
    private readonly WebApplicationFactory<Program> _factory;
    private readonly HttpClient _client;

    public UserControllerIntegrationTests()
    {
        _dbContainer = new PostgreSqlBuilder()
            .WithDatabase("testdb")
            .WithUsername("testuser")
            .WithPassword("testpass")
            .Build();

        _factory = new WebApplicationFactory<Program>()
            .WithWebHostBuilder(builder =>
            {
                builder.ConfigureServices(services =>
                {
                    // Replace database connection with test container
                    services.Configure<DatabaseOptions>(options =>
                    {
                        options.ConnectionString = _dbContainer.GetConnectionString();
                    });
                });
            });

        _client = _factory.CreateClient();
    }

    public async Task InitializeAsync()
    {
        await _dbContainer.StartAsync();
        
        // Run database migrations
        using var scope = _factory.Services.CreateScope();
        var dbContext = scope.ServiceProvider.GetRequiredService<ApplicationDbContext>();
        await dbContext.Database.MigrateAsync();
    }

    public async Task DisposeAsync()
    {
        await _dbContainer.DisposeAsync();
        await _factory.DisposeAsync();
        _client.Dispose();
    }

    [Fact]
    public async Task CreateUser_ValidData_ReturnsCreatedUser()
    {
        // Arrange
        var createUserDto = new CreateUserDto
        {
            Name = "Integration Test User",
            Email = "integration@test.com"
        };

        // Act
        var response = await _client.PostAsJsonAsync("/api/users", createUserDto);

        // Assert
        response.Should().BeSuccessful();
        var createdUser = await response.Content.ReadFromJsonAsync<UserDto>();
        createdUser.Should().NotBeNull();
        createdUser.Name.Should().Be("Integration Test User");
        createdUser.Email.Should().Be("integration@test.com");
    }

    [Fact]
    public async Task GetUser_ExistingUser_ReturnsUser()
    {
        // Arrange - Create a user first
        var createUserDto = new CreateUserDto
        {
            Name = "Test User",
            Email = "test@example.com"
        };
        
        var createResponse = await _client.PostAsJsonAsync("/api/users", createUserDto);
        var createdUser = await createResponse.Content.ReadFromJsonAsync<UserDto>();

        // Act
        var response = await _client.GetAsync($"/api/users/{createdUser.Id}");

        // Assert
        response.Should().BeSuccessful();
        var user = await response.Content.ReadFromJsonAsync<UserDto>();
        user.Should().NotBeNull();
        user.Id.Should().Be(createdUser.Id);
        user.Name.Should().Be("Test User");
    }
}
```

## Test Data Management

### Python Test Fixtures
```python
# fixtures.py
import pytest
from factory import Factory, Faker, SubFactory
from myapp.models import User, Order

class UserFactory(Factory):
    class Meta:
        model = User
    
    name = Faker('name')
    email = Faker('email')
    age = Faker('pyint', min_value=18, max_value=80)

class OrderFactory(Factory):
    class Meta:
        model = Order
    
    user = SubFactory(UserFactory)
    total = Faker('pydecimal', left_digits=3, right_digits=2, positive=True)
    status = 'pending'

@pytest.fixture
def sample_user():
    return UserFactory()

@pytest.fixture
def sample_order():
    return OrderFactory()
```

### C# Test Data Builders
```csharp
public class UserBuilder
{
    private string _name = "Default Name";
    private string _email = "default@example.com";
    private int _age = 25;

    public UserBuilder WithName(string name)
    {
        _name = name;
        return this;
    }

    public UserBuilder WithEmail(string email)
    {
        _email = email;
        return this;
    }

    public UserBuilder WithAge(int age)
    {
        _age = age;
        return this;
    }

    public User Build()
    {
        return new User
        {
            Name = _name,
            Email = _email,
            Age = _age
        };
    }
}

// Usage in tests
[Fact]
public void TestUserCreation()
{
    var user = new UserBuilder()
        .WithName("John Doe")
        .WithEmail("john@example.com")
        .WithAge(30)
        .Build();
    
    user.Name.Should().Be("John Doe");
}
```

## Performance Testing

### Python Performance Tests
```python
import pytest
import time
from myapp.services import DataProcessor

class TestPerformance:
    @pytest.mark.slow
    def test_data_processing_performance(self):
        """Test that data processing completes within acceptable time."""
        processor = DataProcessor()
        large_dataset = list(range(10000))
        
        start_time = time.time()
        result = processor.process_data(large_dataset)
        end_time = time.time()
        
        processing_time = end_time - start_time
        assert processing_time < 1.0, f"Processing took {processing_time:.2f}s, expected < 1.0s"
        assert len(result) == len(large_dataset)
```

### C# Performance Tests
```csharp
[Fact]
public async Task ProcessLargeDataset_CompletesWithinTimeLimit()
{
    // Arrange
    var processor = new DataProcessor();
    var largeDataset = Enumerable.Range(1, 10000).ToList();
    var stopwatch = Stopwatch.StartNew();

    // Act
    var result = await processor.ProcessDataAsync(largeDataset);

    // Assert
    stopwatch.Stop();
    stopwatch.ElapsedMilliseconds.Should().BeLessThan(1000);
    result.Should().HaveCount(10000);
}
```

## Test Coverage and Reporting

### Python Coverage Configuration
```ini
# .coveragerc
[run]
source = src
omit = 
    */tests/*
    */venv/*
    */migrations/*
    */settings/*

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError

[html]
directory = htmlcov
```

### C# Coverage with Coverlet
```xml
<PackageReference Include="coverlet.collector" Version="6.0.0" />
<PackageReference Include="coverlet.msbuild" Version="6.0.0" />
```

```bash
# Run tests with coverage
dotnet test --collect:"XPlat Code Coverage"

# Generate HTML report
reportgenerator -reports:"**/coverage.cobertura.xml" -targetdir:"coveragereport" -reporttypes:Html
```
