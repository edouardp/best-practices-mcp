# Documentation and Maintenance Best Practices

## API Documentation

### Python API Documentation with FastAPI
```python
# main.py
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
import uvicorn

app = FastAPI(
    title="User Management API",
    description="A comprehensive API for managing users with advanced features",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {
            "name": "users",
            "description": "Operations with users. The **login** logic is also here.",
        },
        {
            "name": "admin",
            "description": "Administrative operations. Requires admin privileges.",
        },
    ]
)

# Pydantic models with comprehensive documentation
class UserCreate(BaseModel):
    """Model for creating a new user."""
    name: str = Field(..., min_length=1, max_length=100, description="Full name of the user")
    email: EmailStr = Field(..., description="Valid email address")
    age: Optional[int] = Field(None, ge=0, le=150, description="Age in years")
    
    class Config:
        schema_extra = {
            "example": {
                "name": "John Doe",
                "email": "john.doe@example.com",
                "age": 30
            }
        }

class UserResponse(BaseModel):
    """Model for user response data."""
    id: int = Field(..., description="Unique user identifier")
    name: str = Field(..., description="Full name of the user")
    email: str = Field(..., description="Email address")
    age: Optional[int] = Field(None, description="Age in years")
    created_at: str = Field(..., description="ISO timestamp of creation")
    
    class Config:
        schema_extra = {
            "example": {
                "id": 1,
                "name": "John Doe",
                "email": "john.doe@example.com",
                "age": 30,
                "created_at": "2023-01-01T00:00:00Z"
            }
        }

@app.post(
    "/users/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["users"],
    summary="Create a new user",
    description="Create a new user with the provided information. Email must be unique.",
    responses={
        201: {"description": "User created successfully"},
        400: {"description": "Invalid input data"},
        409: {"description": "Email already exists"},
        422: {"description": "Validation error"}
    }
)
async def create_user(
    user: UserCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new user with all the information:
    
    - **name**: Full name of the user (required)
    - **email**: Valid email address (required, must be unique)
    - **age**: Age in years (optional, must be between 0 and 150)
    
    Returns the created user with assigned ID and creation timestamp.
    """
    try:
        created_user = await user_service.create_user(user.dict())
        return UserResponse(**created_user)
    except EmailExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already exists"
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@app.get(
    "/users/{user_id}",
    response_model=UserResponse,
    tags=["users"],
    summary="Get user by ID",
    description="Retrieve a specific user by their unique identifier.",
    responses={
        200: {"description": "User found"},
        404: {"description": "User not found"},
        403: {"description": "Access denied"}
    }
)
async def get_user(
    user_id: int = Path(..., description="The ID of the user to retrieve", ge=1),
    current_user: dict = Depends(get_current_user)
):
    """
    Get a user by ID.
    
    - **user_id**: The unique identifier of the user (must be positive integer)
    
    Returns user information if found and accessible.
    """
    user = await user_service.get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return UserResponse(**user)
```

### C# API Documentation with Swagger
```csharp
// Program.cs
using Microsoft.OpenApi.Models;
using System.Reflection;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen(c =>
{
    c.SwaggerDoc("v1", new OpenApiInfo
    {
        Title = "User Management API",
        Version = "v1",
        Description = "A comprehensive API for managing users with advanced features",
        Contact = new OpenApiContact
        {
            Name = "API Support",
            Email = "support@example.com",
            Url = new Uri("https://example.com/support")
        },
        License = new OpenApiLicense
        {
            Name = "MIT License",
            Url = new Uri("https://opensource.org/licenses/MIT")
        }
    });
    
    // Include XML comments
    var xmlFile = $"{Assembly.GetExecutingAssembly().GetName().Name}.xml";
    var xmlPath = Path.Combine(AppContext.BaseDirectory, xmlFile);
    c.IncludeXmlComments(xmlPath);
    
    // Add JWT authentication
    c.AddSecurityDefinition("Bearer", new OpenApiSecurityScheme
    {
        Description = "JWT Authorization header using the Bearer scheme",
        Name = "Authorization",
        In = ParameterLocation.Header,
        Type = SecuritySchemeType.ApiKey,
        Scheme = "Bearer"
    });
    
    c.AddSecurityRequirement(new OpenApiSecurityRequirement
    {
        {
            new OpenApiSecurityScheme
            {
                Reference = new OpenApiReference
                {
                    Type = ReferenceType.SecurityScheme,
                    Id = "Bearer"
                }
            },
            Array.Empty<string>()
        }
    });
});

var app = builder.Build();

if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI(c =>
    {
        c.SwaggerEndpoint("/swagger/v1/swagger.json", "User Management API V1");
        c.RoutePrefix = string.Empty; // Serve Swagger UI at root
    });
}

// Controllers with comprehensive documentation
/// <summary>
/// Controller for managing users
/// </summary>
[ApiController]
[Route("api/[controller]")]
[Produces("application/json")]
public class UsersController : ControllerBase
{
    private readonly IUserService _userService;
    private readonly ILogger<UsersController> _logger;
    
    /// <summary>
    /// Initializes a new instance of the UsersController
    /// </summary>
    /// <param name="userService">User service dependency</param>
    /// <param name="logger">Logger dependency</param>
    public UsersController(IUserService userService, ILogger<UsersController> logger)
    {
        _userService = userService;
        _logger = logger;
    }
    
    /// <summary>
    /// Creates a new user
    /// </summary>
    /// <param name="userDto">User creation data</param>
    /// <returns>The created user</returns>
    /// <response code="201">User created successfully</response>
    /// <response code="400">Invalid input data</response>
    /// <response code="409">Email already exists</response>
    [HttpPost]
    [ProducesResponseType(typeof(UserResponseDto), StatusCodes.Status201Created)]
    [ProducesResponseType(typeof(ValidationProblemDetails), StatusCodes.Status400BadRequest)]
    [ProducesResponseType(typeof(ProblemDetails), StatusCodes.Status409Conflict)]
    public async Task<ActionResult<UserResponseDto>> CreateUser([FromBody] CreateUserDto userDto)
    {
        try
        {
            var user = await _userService.CreateUserAsync(userDto);
            return CreatedAtAction(nameof(GetUser), new { id = user.Id }, user);
        }
        catch (EmailExistsException)
        {
            return Conflict(new ProblemDetails
            {
                Title = "Email already exists",
                Detail = "A user with this email address already exists",
                Status = StatusCodes.Status409Conflict
            });
        }
    }
    
    /// <summary>
    /// Gets a user by ID
    /// </summary>
    /// <param name="id">The user ID</param>
    /// <returns>The user if found</returns>
    /// <response code="200">User found</response>
    /// <response code="404">User not found</response>
    [HttpGet("{id:int}")]
    [ProducesResponseType(typeof(UserResponseDto), StatusCodes.Status200OK)]
    [ProducesResponseType(typeof(ProblemDetails), StatusCodes.Status404NotFound)]
    public async Task<ActionResult<UserResponseDto>> GetUser(
        /// <summary>The unique identifier of the user</summary>
        [FromRoute] int id)
    {
        var user = await _userService.GetUserByIdAsync(id);
        if (user == null)
        {
            return NotFound(new ProblemDetails
            {
                Title = "User not found",
                Detail = $"No user found with ID {id}",
                Status = StatusCodes.Status404NotFound
            });
        }
        
        return Ok(user);
    }
}

// Data Transfer Objects with documentation
/// <summary>
/// Data transfer object for creating a user
/// </summary>
public class CreateUserDto
{
    /// <summary>
    /// Full name of the user
    /// </summary>
    /// <example>John Doe</example>
    [Required]
    [StringLength(100, MinimumLength = 1)]
    public string Name { get; set; }
    
    /// <summary>
    /// Valid email address (must be unique)
    /// </summary>
    /// <example>john.doe@example.com</example>
    [Required]
    [EmailAddress]
    public string Email { get; set; }
    
    /// <summary>
    /// Age in years (optional)
    /// </summary>
    /// <example>30</example>
    [Range(0, 150)]
    public int? Age { get; set; }
}
```

## Code Documentation

### Python Docstring Standards
```python
# user_service.py
from typing import List, Optional, Dict, Any
from datetime import datetime

class UserService:
    """
    Service class for managing user operations.
    
    This service provides comprehensive user management functionality including
    creation, retrieval, updating, and deletion of user records. It handles
    business logic validation and coordinates with the data access layer.
    
    Attributes:
        repository (UserRepository): Data access layer for user operations
        email_service (EmailService): Service for sending user-related emails
        cache_service (CacheService): Caching service for performance optimization
    
    Example:
        >>> user_service = UserService(repository, email_service, cache_service)
        >>> user = user_service.create_user({"name": "John", "email": "john@example.com"})
        >>> print(user.id)
        1
    """
    
    def __init__(self, repository: 'UserRepository', email_service: 'EmailService', 
                 cache_service: 'CacheService'):
        """
        Initialize the UserService with required dependencies.
        
        Args:
            repository: Data access layer for user operations
            email_service: Service for sending emails
            cache_service: Service for caching operations
        """
        self.repository = repository
        self.email_service = email_service
        self.cache_service = cache_service
    
    def create_user(self, user_data: Dict[str, Any]) -> 'User':
        """
        Create a new user with the provided data.
        
        This method validates the user data, checks for email uniqueness,
        creates the user record, sends a welcome email, and returns the
        created user object.
        
        Args:
            user_data: Dictionary containing user information with keys:
                - name (str): Full name of the user (required)
                - email (str): Valid email address (required, must be unique)
                - age (int, optional): Age in years (0-150)
                - preferences (dict, optional): User preferences
        
        Returns:
            User: The created user object with assigned ID and timestamps
        
        Raises:
            ValidationError: If the provided data is invalid
            EmailExistsError: If the email address is already in use
            DatabaseError: If there's an error saving to the database
            EmailServiceError: If welcome email fails to send (non-blocking)
        
        Example:
            >>> user_data = {
            ...     "name": "Jane Smith",
            ...     "email": "jane@example.com",
            ...     "age": 25
            ... }
            >>> user = service.create_user(user_data)
            >>> print(f"Created user {user.name} with ID {user.id}")
            Created user Jane Smith with ID 2
        
        Note:
            The welcome email is sent asynchronously. If it fails, the user
            creation will still succeed, but an error will be logged.
        """
        # Validate input data
        self._validate_user_data(user_data)
        
        # Check email uniqueness
        if self.repository.email_exists(user_data['email']):
            raise EmailExistsError(f"Email {user_data['email']} already exists")
        
        try:
            # Create user
            user = self.repository.create_user(user_data)
            
            # Send welcome email (non-blocking)
            try:
                self.email_service.send_welcome_email(user.email, user.name)
            except EmailServiceError as e:
                # Log error but don't fail user creation
                logger.error(f"Failed to send welcome email to {user.email}: {e}")
            
            # Invalidate related cache
            self.cache_service.invalidate_pattern("user_stats:*")
            
            return user
            
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            raise DatabaseError("Failed to create user") from e
    
    def get_user_by_id(self, user_id: int) -> Optional['User']:
        """
        Retrieve a user by their unique identifier.
        
        This method first checks the cache for the user data. If not found,
        it queries the database and caches the result for future requests.
        
        Args:
            user_id: The unique identifier of the user (must be positive)
        
        Returns:
            User object if found, None otherwise
        
        Raises:
            ValueError: If user_id is not a positive integer
            DatabaseError: If there's an error querying the database
        
        Example:
            >>> user = service.get_user_by_id(1)
            >>> if user:
            ...     print(f"Found user: {user.name}")
            ... else:
            ...     print("User not found")
            Found user: Jane Smith
        """
        if not isinstance(user_id, int) or user_id <= 0:
            raise ValueError("user_id must be a positive integer")
        
        # Try cache first
        cache_key = f"user:{user_id}"
        cached_user = self.cache_service.get(cache_key)
        if cached_user:
            return cached_user
        
        try:
            user = self.repository.get_by_id(user_id)
            if user:
                # Cache for 30 minutes
                self.cache_service.set(cache_key, user, ttl=1800)
            return user
        except Exception as e:
            logger.error(f"Failed to get user {user_id}: {e}")
            raise DatabaseError(f"Failed to retrieve user {user_id}") from e
    
    def _validate_user_data(self, user_data: Dict[str, Any]) -> None:
        """
        Validate user data before processing.
        
        This is a private method that performs comprehensive validation
        of user input data according to business rules.
        
        Args:
            user_data: Dictionary containing user data to validate
        
        Raises:
            ValidationError: If any validation rule is violated
        
        Note:
            This method is for internal use only and should not be called
            directly by external code.
        """
        required_fields = ['name', 'email']
        for field in required_fields:
            if field not in user_data or not user_data[field]:
                raise ValidationError(f"Field '{field}' is required")
        
        # Validate email format
        if not self._is_valid_email(user_data['email']):
            raise ValidationError("Invalid email format")
        
        # Validate age if provided
        if 'age' in user_data and user_data['age'] is not None:
            age = user_data['age']
            if not isinstance(age, int) or age < 0 or age > 150:
                raise ValidationError("Age must be between 0 and 150")
```

### README Documentation Template
```markdown
# Project Name

Brief description of what this project does and who it's for.

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Testing](#testing)
- [Deployment](#deployment)
- [Contributing](#contributing)
- [License](#license)

## Features

- ✅ User management with CRUD operations
- ✅ JWT-based authentication
- ✅ Role-based access control
- ✅ Email notifications
- ✅ Comprehensive logging
- ✅ Performance monitoring
- ✅ Docker support
- ✅ Kubernetes deployment

## Prerequisites

- Python 3.11+ or .NET 8.0+
- PostgreSQL 15+
- Redis 7+
- Docker (optional)

## Installation

### Python Setup

```bash
# Clone the repository
git clone https://github.com/username/project-name.git
cd project-name

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt
```

### C# Setup

```bash
# Clone the repository
git clone https://github.com/username/project-name.git
cd project-name

# Restore dependencies
dotnet restore

# Build the project
dotnet build
```

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# Redis
REDIS_URL=redis://localhost:6379

# JWT
JWT_SECRET=your-secret-key
JWT_EXPIRY_HOURS=24

# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Logging
LOG_LEVEL=INFO
```

### Database Setup

```bash
# Run migrations (Python)
alembic upgrade head

# Run migrations (C#)
dotnet ef database update
```

## Usage

### Running the Application

#### Python (FastAPI)
```bash
# Development
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Production
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

#### C# (ASP.NET Core)
```bash
# Development
dotnet run

# Production
dotnet run --configuration Release
```

### API Examples

#### Create a User
```bash
curl -X POST "http://localhost:8000/users/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "name": "John Doe",
    "email": "john@example.com",
    "age": 30
  }'
```

#### Get a User
```bash
curl -X GET "http://localhost:8000/users/1" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## API Documentation

- **Swagger UI**: http://localhost:8000/docs (Python) or http://localhost:5000/swagger (C#)
- **ReDoc**: http://localhost:8000/redoc (Python only)

## Testing

### Running Tests

#### Python
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_user_service.py

# Run with markers
pytest -m "not slow"
```

#### C#
```bash
# Run all tests
dotnet test

# Run with coverage
dotnet test --collect:"XPlat Code Coverage"

# Run specific test project
dotnet test tests/MyProject.Tests/
```

### Test Categories

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test component interactions
- **End-to-End Tests**: Test complete user workflows

## Deployment

### Docker

```bash
# Build image
docker build -t myapp:latest .

# Run container
docker run -p 8000:8000 --env-file .env myapp:latest
```

### Kubernetes

```bash
# Apply manifests
kubectl apply -f k8s/

# Check deployment status
kubectl get pods -l app=myapp
```

### CI/CD

This project uses GitHub Actions for continuous integration and deployment. See `.github/workflows/` for pipeline configurations.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow the coding standards defined in `.editorconfig`
- Write tests for new features
- Update documentation for API changes
- Run linting and formatting before committing

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- 📧 Email: support@example.com
- 💬 Slack: #project-support
- 📖 Wiki: [Project Wiki](https://github.com/username/project-name/wiki)
- 🐛 Issues: [GitHub Issues](https://github.com/username/project-name/issues)
```
