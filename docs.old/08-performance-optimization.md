# Performance Optimization Best Practices

## Database Optimization

### Python Database Performance

#### SQLAlchemy Optimization
```python
# database.py
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool
import logging

# Optimized database configuration
DATABASE_CONFIG = {
    'pool_size': 20,
    'max_overflow': 30,
    'pool_pre_ping': True,
    'pool_recycle': 3600,
    'echo': False,  # Set to True for debugging
}

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    **DATABASE_CONFIG
)

# Session configuration
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Query optimization examples
class UserRepository:
    def __init__(self, db_session):
        self.db = db_session
    
    def get_users_with_orders(self, limit=100):
        """Optimized query with eager loading."""
        return (
            self.db.query(User)
            .options(
                joinedload(User.orders),  # Eager load orders
                selectinload(User.profile)  # Select in load for one-to-one
            )
            .limit(limit)
            .all()
        )
    
    def get_users_by_status_bulk(self, statuses):
        """Bulk query with IN clause."""
        return (
            self.db.query(User)
            .filter(User.status.in_(statuses))
            .options(defer(User.large_text_field))  # Defer large fields
            .all()
        )
    
    def update_users_bulk(self, user_updates):
        """Bulk update operation."""
        self.db.bulk_update_mappings(User, user_updates)
        self.db.commit()
    
    def get_user_statistics(self):
        """Optimized aggregation query."""
        return (
            self.db.query(
                func.count(User.id).label('total_users'),
                func.avg(User.age).label('avg_age'),
                func.count(case([(User.status == 'active', 1)])).label('active_users')
            )
            .first()
        )

# Connection pooling monitoring
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Set database-specific optimizations."""
    if 'postgresql' in str(engine.url):
        cursor = dbapi_connection.cursor()
        cursor.execute("SET statement_timeout = '30s'")
        cursor.execute("SET lock_timeout = '10s'")
        cursor.close()

# Query performance monitoring
@event.listens_for(engine, "before_cursor_execute")
def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    context._query_start_time = time.time()

@event.listens_for(engine, "after_cursor_execute")
def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total = time.time() - context._query_start_time
    if total > 0.5:  # Log slow queries
        logging.warning(f"Slow query: {total:.2f}s - {statement[:100]}...")
```

#### Redis Caching Strategy
```python
# cache.py
import redis
import json
import pickle
from functools import wraps
from typing import Any, Optional
import hashlib

class CacheManager:
    def __init__(self, redis_url: str):
        self.redis_client = redis.from_url(
            redis_url,
            decode_responses=False,  # Handle binary data
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
            health_check_interval=30
        )
    
    def cache_result(self, ttl: int = 3600, key_prefix: str = ""):
        """Decorator for caching function results."""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Generate cache key
                cache_key = self._generate_cache_key(func.__name__, args, kwargs, key_prefix)
                
                # Try to get from cache
                cached_result = self.get(cache_key)
                if cached_result is not None:
                    return cached_result
                
                # Execute function and cache result
                result = func(*args, **kwargs)
                self.set(cache_key, result, ttl)
                return result
            return wrapper
        return decorator
    
    def _generate_cache_key(self, func_name: str, args: tuple, kwargs: dict, prefix: str) -> str:
        """Generate a consistent cache key."""
        key_data = {
            'function': func_name,
            'args': args,
            'kwargs': sorted(kwargs.items())
        }
        key_string = json.dumps(key_data, sort_keys=True, default=str)
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        return f"{prefix}:{func_name}:{key_hash}"
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            data = self.redis_client.get(key)
            if data:
                return pickle.loads(data)
        except Exception as e:
            logging.error(f"Cache get error: {e}")
        return None
    
    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set value in cache."""
        try:
            data = pickle.dumps(value)
            return self.redis_client.setex(key, ttl, data)
        except Exception as e:
            logging.error(f"Cache set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        try:
            return bool(self.redis_client.delete(key))
        except Exception as e:
            logging.error(f"Cache delete error: {e}")
            return False
    
    def invalidate_pattern(self, pattern: str):
        """Invalidate all keys matching pattern."""
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
        except Exception as e:
            logging.error(f"Cache invalidate error: {e}")

# Usage example
cache = CacheManager(REDIS_URL)

class UserService:
    @cache.cache_result(ttl=1800, key_prefix="user")
    def get_user_profile(self, user_id: int):
        """Get user profile with caching."""
        return self.repository.get_user_with_profile(user_id)
    
    @cache.cache_result(ttl=300, key_prefix="stats")
    def get_user_statistics(self):
        """Get user statistics with short-term caching."""
        return self.repository.get_user_statistics()
    
    def update_user(self, user_id: int, user_data: dict):
        """Update user and invalidate related cache."""
        user = self.repository.update_user(user_id, user_data)
        
        # Invalidate related cache entries
        cache.delete(f"user:get_user_profile:*{user_id}*")
        cache.invalidate_pattern("stats:*")
        
        return user
```

### C# Database Performance

#### Entity Framework Optimization
```csharp
// DatabaseContext.cs
public class ApplicationDbContext : DbContext
{
    public ApplicationDbContext(DbContextOptions<ApplicationDbContext> options) : base(options)
    {
    }
    
    protected override void OnConfiguring(DbContextOptionsBuilder optionsBuilder)
    {
        if (!optionsBuilder.IsConfigured)
        {
            optionsBuilder
                .EnableSensitiveDataLogging(false)
                .EnableServiceProviderCaching()
                .EnableDetailedErrors(false)
                .ConfigureWarnings(warnings => 
                    warnings.Ignore(CoreEventId.RowLimitingOperationWithoutOrderByWarning));
        }
    }
    
    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        // Configure indexes for performance
        modelBuilder.Entity<User>()
            .HasIndex(u => u.Email)
            .IsUnique();
            
        modelBuilder.Entity<User>()
            .HasIndex(u => new { u.Status, u.CreatedAt });
            
        modelBuilder.Entity<Order>()
            .HasIndex(o => new { o.UserId, o.Status, o.CreatedAt });
    }
}

// Optimized repository
public class UserRepository
{
    private readonly ApplicationDbContext _context;
    
    public UserRepository(ApplicationDbContext context)
    {
        _context = context;
    }
    
    public async Task<List<User>> GetUsersWithOrdersAsync(int limit = 100)
    {
        return await _context.Users
            .Include(u => u.Orders)
            .ThenInclude(o => o.OrderItems)
            .AsSplitQuery() // Use split queries for multiple includes
            .Take(limit)
            .AsNoTracking() // Read-only queries
            .ToListAsync();
    }
    
    public async Task<List<User>> GetUsersByStatusAsync(List<string> statuses)
    {
        return await _context.Users
            .Where(u => statuses.Contains(u.Status))
            .Select(u => new User // Project only needed fields
            {
                Id = u.Id,
                Name = u.Name,
                Email = u.Email,
                Status = u.Status
            })
            .AsNoTracking()
            .ToListAsync();
    }
    
    public async Task BulkUpdateUsersAsync(List<UserUpdateDto> updates)
    {
        var userIds = updates.Select(u => u.Id).ToList();
        var users = await _context.Users
            .Where(u => userIds.Contains(u.Id))
            .ToListAsync();
        
        foreach (var user in users)
        {
            var update = updates.First(u => u.Id == user.Id);
            user.Name = update.Name;
            user.Status = update.Status;
            user.UpdatedAt = DateTime.UtcNow;
        }
        
        await _context.SaveChangesAsync();
    }
    
    public async Task<UserStatistics> GetUserStatisticsAsync()
    {
        return await _context.Users
            .GroupBy(u => 1)
            .Select(g => new UserStatistics
            {
                TotalUsers = g.Count(),
                ActiveUsers = g.Count(u => u.Status == "Active"),
                AverageAge = g.Average(u => u.Age)
            })
            .FirstAsync();
    }
}
```

#### Memory Caching with IMemoryCache
```csharp
// CacheService.cs
public interface ICacheService
{
    Task<T> GetOrSetAsync<T>(string key, Func<Task<T>> getItem, TimeSpan? expiry = null);
    Task RemoveAsync(string key);
    Task RemoveByPatternAsync(string pattern);
}

public class CacheService : ICacheService
{
    private readonly IMemoryCache _memoryCache;
    private readonly IDistributedCache _distributedCache;
    private readonly ILogger<CacheService> _logger;
    private readonly ConcurrentDictionary<string, SemaphoreSlim> _semaphores = new();
    
    public CacheService(
        IMemoryCache memoryCache,
        IDistributedCache distributedCache,
        ILogger<CacheService> logger)
    {
        _memoryCache = memoryCache;
        _distributedCache = distributedCache;
        _logger = logger;
    }
    
    public async Task<T> GetOrSetAsync<T>(string key, Func<Task<T>> getItem, TimeSpan? expiry = null)
    {
        // Try memory cache first (L1)
        if (_memoryCache.TryGetValue(key, out T cachedValue))
        {
            return cachedValue;
        }
        
        // Use semaphore to prevent cache stampede
        var semaphore = _semaphores.GetOrAdd(key, _ => new SemaphoreSlim(1, 1));
        
        await semaphore.WaitAsync();
        try
        {
            // Double-check memory cache
            if (_memoryCache.TryGetValue(key, out cachedValue))
            {
                return cachedValue;
            }
            
            // Try distributed cache (L2)
            var distributedValue = await GetFromDistributedCacheAsync<T>(key);
            if (distributedValue != null)
            {
                // Store in memory cache
                var memoryExpiry = expiry ?? TimeSpan.FromMinutes(5);
                _memoryCache.Set(key, distributedValue, memoryExpiry);
                return distributedValue;
            }
            
            // Get from source
            var value = await getItem();
            
            // Store in both caches
            var cacheExpiry = expiry ?? TimeSpan.FromMinutes(30);
            _memoryCache.Set(key, value, TimeSpan.FromMinutes(5));
            await SetDistributedCacheAsync(key, value, cacheExpiry);
            
            return value;
        }
        finally
        {
            semaphore.Release();
        }
    }
    
    private async Task<T> GetFromDistributedCacheAsync<T>(string key)
    {
        try
        {
            var cachedData = await _distributedCache.GetStringAsync(key);
            if (cachedData != null)
            {
                return JsonSerializer.Deserialize<T>(cachedData);
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error getting from distributed cache: {Key}", key);
        }
        
        return default(T);
    }
    
    private async Task SetDistributedCacheAsync<T>(string key, T value, TimeSpan expiry)
    {
        try
        {
            var serializedData = JsonSerializer.Serialize(value);
            var options = new DistributedCacheEntryOptions
            {
                AbsoluteExpirationRelativeToNow = expiry
            };
            
            await _distributedCache.SetStringAsync(key, serializedData, options);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error setting distributed cache: {Key}", key);
        }
    }
    
    public async Task RemoveAsync(string key)
    {
        _memoryCache.Remove(key);
        await _distributedCache.RemoveAsync(key);
    }
    
    public async Task RemoveByPatternAsync(string pattern)
    {
        // Implementation depends on cache provider
        // For Redis, you could use SCAN with pattern matching
    }
}

// Usage in service
public class UserService
{
    private readonly ICacheService _cache;
    private readonly IUserRepository _repository;
    
    public UserService(ICacheService cache, IUserRepository repository)
    {
        _cache = cache;
        _repository = repository;
    }
    
    public async Task<User> GetUserAsync(int userId)
    {
        var cacheKey = $"user:{userId}";
        return await _cache.GetOrSetAsync(
            cacheKey,
            () => _repository.GetByIdAsync(userId),
            TimeSpan.FromMinutes(30)
        );
    }
    
    public async Task<UserStatistics> GetUserStatisticsAsync()
    {
        var cacheKey = "user:statistics";
        return await _cache.GetOrSetAsync(
            cacheKey,
            () => _repository.GetUserStatisticsAsync(),
            TimeSpan.FromMinutes(5)
        );
    }
}
```

## Application Performance

### Python Performance Optimization

#### Async/Await Patterns
```python
# async_service.py
import asyncio
import aiohttp
import asyncpg
from typing import List, Dict, Any
import time

class AsyncUserService:
    def __init__(self, db_pool: asyncpg.Pool, http_session: aiohttp.ClientSession):
        self.db_pool = db_pool
        self.http_session = http_session
    
    async def get_user_with_external_data(self, user_id: int) -> Dict[str, Any]:
        """Fetch user data and external API data concurrently."""
        
        # Run database and API calls concurrently
        user_task = self.get_user_from_db(user_id)
        profile_task = self.get_external_profile(user_id)
        preferences_task = self.get_user_preferences(user_id)
        
        # Wait for all tasks to complete
        user, external_profile, preferences = await asyncio.gather(
            user_task,
            profile_task,
            preferences_task,
            return_exceptions=True
        )
        
        # Handle exceptions
        if isinstance(external_profile, Exception):
            external_profile = None
        
        return {
            'user': user,
            'external_profile': external_profile,
            'preferences': preferences
        }
    
    async def get_user_from_db(self, user_id: int) -> Dict[str, Any]:
        """Get user from database."""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, name, email, created_at FROM users WHERE id = $1",
                user_id
            )
            return dict(row) if row else None
    
    async def get_external_profile(self, user_id: int) -> Dict[str, Any]:
        """Get profile from external API with timeout."""
        try:
            timeout = aiohttp.ClientTimeout(total=5)
            async with self.http_session.get(
                f"https://api.external.com/users/{user_id}",
                timeout=timeout
            ) as response:
                if response.status == 200:
                    return await response.json()
                return None
        except asyncio.TimeoutError:
            return None
    
    async def get_user_preferences(self, user_id: int) -> Dict[str, Any]:
        """Get user preferences from database."""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT key, value FROM user_preferences WHERE user_id = $1",
                user_id
            )
            return {row['key']: row['value'] for row in rows}
    
    async def bulk_process_users(self, user_ids: List[int]) -> List[Dict[str, Any]]:
        """Process multiple users concurrently with rate limiting."""
        
        # Create semaphore to limit concurrent operations
        semaphore = asyncio.Semaphore(10)
        
        async def process_user_with_limit(user_id: int):
            async with semaphore:
                return await self.get_user_with_external_data(user_id)
        
        # Process all users concurrently
        tasks = [process_user_with_limit(user_id) for user_id in user_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions
        return [result for result in results if not isinstance(result, Exception)]

# Connection pooling setup
async def create_db_pool():
    """Create optimized database connection pool."""
    return await asyncpg.create_pool(
        DATABASE_URL,
        min_size=5,
        max_size=20,
        command_timeout=30,
        server_settings={
            'application_name': 'myapp',
            'tcp_keepalives_idle': '600',
            'tcp_keepalives_interval': '30',
            'tcp_keepalives_count': '3',
        }
    )

async def create_http_session():
    """Create optimized HTTP session."""
    connector = aiohttp.TCPConnector(
        limit=100,
        limit_per_host=30,
        ttl_dns_cache=300,
        use_dns_cache=True,
        keepalive_timeout=30,
        enable_cleanup_closed=True
    )
    
    timeout = aiohttp.ClientTimeout(total=30, connect=5)
    
    return aiohttp.ClientSession(
        connector=connector,
        timeout=timeout,
        headers={'User-Agent': 'MyApp/1.0'}
    )
```

#### Memory and CPU Optimization
```python
# optimization.py
import sys
from functools import lru_cache, wraps
from typing import Generator, List, Any
import gc
import psutil
import cProfile
import pstats
from memory_profiler import profile

class PerformanceOptimizer:
    @staticmethod
    def memory_efficient_batch_processor(items: List[Any], batch_size: int = 1000) -> Generator:
        """Process large datasets in memory-efficient batches."""
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            yield batch
            
            # Force garbage collection after each batch
            gc.collect()
    
    @staticmethod
    @lru_cache(maxsize=1000)
    def expensive_calculation(value: int) -> int:
        """Cache expensive calculations."""
        # Simulate expensive operation
        result = sum(i * i for i in range(value))
        return result
    
    @staticmethod
    def profile_function(func):
        """Decorator to profile function performance."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            profiler = cProfile.Profile()
            profiler.enable()
            
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                profiler.disable()
                stats = pstats.Stats(profiler)
                stats.sort_stats('cumulative')
                stats.print_stats(10)  # Print top 10 functions
        
        return wrapper
    
    @staticmethod
    def monitor_memory_usage(func):
        """Decorator to monitor memory usage."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            process = psutil.Process()
            memory_before = process.memory_info().rss / 1024 / 1024  # MB
            
            result = func(*args, **kwargs)
            
            memory_after = process.memory_info().rss / 1024 / 1024  # MB
            memory_diff = memory_after - memory_before
            
            print(f"Memory usage: {memory_before:.2f}MB -> {memory_after:.2f}MB (diff: {memory_diff:.2f}MB)")
            
            return result
        
        return wrapper

# Usage examples
class OptimizedDataProcessor:
    def __init__(self):
        self.optimizer = PerformanceOptimizer()
    
    @PerformanceOptimizer.monitor_memory_usage
    def process_large_dataset(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process large dataset efficiently."""
        results = []
        
        for batch in self.optimizer.memory_efficient_batch_processor(data, batch_size=500):
            batch_results = []
            
            for item in batch:
                # Process item
                processed_item = self.process_item(item)
                batch_results.append(processed_item)
            
            results.extend(batch_results)
            
            # Clear batch from memory
            del batch_results
        
        return results
    
    def process_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Process individual item."""
        # Use cached expensive calculation
        calculated_value = self.optimizer.expensive_calculation(item.get('value', 0))
        
        return {
            'id': item['id'],
            'processed_value': calculated_value,
            'timestamp': item.get('timestamp')
        }
```

### C# Performance Optimization

#### Async/Await Best Practices
```csharp
// AsyncService.cs
public class AsyncUserService
{
    private readonly HttpClient _httpClient;
    private readonly IUserRepository _repository;
    private readonly SemaphoreSlim _semaphore;
    
    public AsyncUserService(HttpClient httpClient, IUserRepository repository)
    {
        _httpClient = httpClient;
        _repository = repository;
        _semaphore = new SemaphoreSlim(10, 10); // Limit concurrent operations
    }
    
    public async Task<UserWithExternalData> GetUserWithExternalDataAsync(int userId)
    {
        // Run multiple async operations concurrently
        var userTask = _repository.GetByIdAsync(userId);
        var externalProfileTask = GetExternalProfileAsync(userId);
        var preferencesTask = _repository.GetUserPreferencesAsync(userId);
        
        // Wait for all tasks to complete
        await Task.WhenAll(userTask, externalProfileTask, preferencesTask);
        
        return new UserWithExternalData
        {
            User = await userTask,
            ExternalProfile = await externalProfileTask,
            Preferences = await preferencesTask
        };
    }
    
    private async Task<ExternalProfile> GetExternalProfileAsync(int userId)
    {
        try
        {
            using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(5));
            var response = await _httpClient.GetAsync($"users/{userId}", cts.Token);
            
            if (response.IsSuccessStatusCode)
            {
                var json = await response.Content.ReadAsStringAsync();
                return JsonSerializer.Deserialize<ExternalProfile>(json);
            }
        }
        catch (OperationCanceledException)
        {
            // Handle timeout
        }
        catch (HttpRequestException)
        {
            // Handle HTTP errors
        }
        
        return null;
    }
    
    public async Task<List<UserWithExternalData>> BulkProcessUsersAsync(List<int> userIds)
    {
        var tasks = userIds.Select(async userId =>
        {
            await _semaphore.WaitAsync();
            try
            {
                return await GetUserWithExternalDataAsync(userId);
            }
            finally
            {
                _semaphore.Release();
            }
        });
        
        var results = await Task.WhenAll(tasks);
        return results.Where(r => r != null).ToList();
    }
    
    public async Task<List<T>> ProcessInBatchesAsync<T>(
        IEnumerable<T> items,
        Func<T, Task<T>> processor,
        int batchSize = 10)
    {
        var results = new List<T>();
        var batches = items.Chunk(batchSize);
        
        foreach (var batch in batches)
        {
            var batchTasks = batch.Select(processor);
            var batchResults = await Task.WhenAll(batchTasks);
            results.AddRange(batchResults);
            
            // Optional: Add delay between batches to prevent overwhelming external services
            await Task.Delay(100);
        }
        
        return results;
    }
}
```

#### Memory Management and Object Pooling
```csharp
// ObjectPooling.cs
public class PooledStringBuilder : IDisposable
{
    private static readonly ObjectPool<StringBuilder> Pool = 
        new DefaultObjectPool<StringBuilder>(new StringBuilderPooledObjectPolicy());
    
    private readonly StringBuilder _stringBuilder;
    private bool _disposed;
    
    private PooledStringBuilder(StringBuilder stringBuilder)
    {
        _stringBuilder = stringBuilder;
    }
    
    public static PooledStringBuilder Get()
    {
        return new PooledStringBuilder(Pool.Get());
    }
    
    public StringBuilder StringBuilder => _stringBuilder;
    
    public void Dispose()
    {
        if (!_disposed)
        {
            Pool.Return(_stringBuilder);
            _disposed = true;
        }
    }
}

public class StringBuilderPooledObjectPolicy : PooledObjectPolicy<StringBuilder>
{
    public override StringBuilder Create()
    {
        return new StringBuilder();
    }
    
    public override bool Return(StringBuilder obj)
    {
        if (obj.Capacity > 1024)
        {
            // Don't return very large StringBuilders to pool
            return false;
        }
        
        obj.Clear();
        return true;
    }
}

// High-performance data processing
public class HighPerformanceProcessor
{
    private readonly ArrayPool<byte> _arrayPool;
    private readonly ObjectPool<List<string>> _listPool;
    
    public HighPerformanceProcessor()
    {
        _arrayPool = ArrayPool<byte>.Shared;
        _listPool = new DefaultObjectPool<List<string>>(new ListPooledObjectPolicy<string>());
    }
    
    public async Task<string> ProcessLargeDataAsync(Stream dataStream)
    {
        // Rent buffer from array pool
        var buffer = _arrayPool.Rent(4096);
        var results = _listPool.Get();
        
        try
        {
            using var pooledStringBuilder = PooledStringBuilder.Get();
            var sb = pooledStringBuilder.StringBuilder;
            
            int bytesRead;
            while ((bytesRead = await dataStream.ReadAsync(buffer, 0, buffer.Length)) > 0)
            {
                // Process buffer data
                var text = Encoding.UTF8.GetString(buffer, 0, bytesRead);
                sb.Append(text);
                
                // Process in chunks to avoid large string allocations
                if (sb.Length > 1000)
                {
                    results.Add(sb.ToString());
                    sb.Clear();
                }
            }
            
            if (sb.Length > 0)
            {
                results.Add(sb.ToString());
            }
            
            return string.Join("", results);
        }
        finally
        {
            // Return rented objects to pools
            _arrayPool.Return(buffer);
            _listPool.Return(results);
        }
    }
    
    public void ProcessWithSpan(ReadOnlySpan<char> input)
    {
        // Use Span<T> for high-performance, allocation-free operations
        foreach (var line in input.EnumerateLines())
        {
            if (line.IsEmpty) continue;
            
            // Process line without allocating strings
            var trimmed = line.Trim();
            if (trimmed.StartsWith("ERROR"))
            {
                // Handle error line
                ProcessErrorLine(trimmed);
            }
        }
    }
    
    private void ProcessErrorLine(ReadOnlySpan<char> errorLine)
    {
        // High-performance string processing without allocations
        var parts = errorLine.Split(' ');
        // Process parts...
    }
}

public class ListPooledObjectPolicy<T> : PooledObjectPolicy<List<T>>
{
    public override List<T> Create()
    {
        return new List<T>();
    }
    
    public override bool Return(List<T> obj)
    {
        if (obj.Count > 1000)
        {
            // Don't return very large lists to pool
            return false;
        }
        
        obj.Clear();
        return true;
    }
}
```
