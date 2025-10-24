# Database Best Practices

> Defaults: **MySQL 8.0+**, **UTF8MB4**, **UTC timestamps**, **parameterized queries**, **connection pooling**, **read replicas**, **backup automation**.

---

## 1. Schema Design

### Use appropriate data types; avoid TEXT for short strings

**Why:** Proper data types improve performance, storage efficiency, and data integrity. VARCHAR with appropriate length limits prevents runaway data and improves indexing performance.

```sql
-- ❌ Bad - Inefficient data types
CREATE TABLE orders (
    id TEXT,
    status TEXT,
    amount TEXT,
    created_at TEXT
);

-- ✅ Good - Appropriate data types
CREATE TABLE orders (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    status ENUM('pending', 'processing', 'completed', 'cancelled'),
    amount DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Normalize to 3NF; denormalize only for OLAP/reporting

**Why:** Third Normal Form eliminates data redundancy and update anomalies, ensuring data consistency. Slight relaxation for pragmatic reasons is acceptable in OLTP systems, but denormalization should be reserved for OLAP/reporting systems where read performance is prioritized over write consistency.

```sql
-- ✅ Good - Normalized (3NF)
CREATE TABLE customers (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL
);

CREATE TABLE orders (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    customer_id BIGINT NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

-- ❌ Bad for OLTP - Denormalized (causes update anomalies)
CREATE TABLE orders_denormalized (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    customer_name VARCHAR(255),  -- Duplicated data
    customer_email VARCHAR(255), -- Update anomaly risk
    amount DECIMAL(10,2) NOT NULL
);

-- ✅ Acceptable for OLAP - Denormalized for reporting performance
CREATE TABLE order_summary_report (
    customer_name VARCHAR(255),
    customer_email VARCHAR(255),
    total_orders INT,
    total_amount DECIMAL(12,2),
    last_order_date DATE
);
```

### Primary keys: BIGINT AUTO_INCREMENT; avoid UUIDs for high-volume tables

**Why:** Auto-incrementing integers provide better performance for primary keys due to sequential inserts and smaller index size. UUIDs can cause page splits and fragmentation in high-volume scenarios.

**Note:** If you need UUIDs for external APIs, add a separate `external_id` (or more descriptive name) column. Use the BIGINT primary key for all internal JOINs and the UUID only for external interfaces.

```sql
CREATE TABLE orders (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,  -- Internal joins
    external_id CHAR(36) UNIQUE NOT NULL,  -- External API
    customer_id BIGINT NOT NULL,           -- References customers.id
    amount DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_external_id (external_id)
);
```

---

## 2. Constraints

### Always define foreign key constraints for referential integrity

**Why:** Foreign key constraints prevent orphaned records and maintain data consistency. They catch referential integrity violations at the database level, preventing data corruption that application-level checks might miss.

```sql
-- ✅ Good - Foreign key constraints enforce referential integrity
CREATE TABLE customers (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL
);

CREATE TABLE orders (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    customer_id BIGINT NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE RESTRICT
);

-- ❌ Bad - No foreign key constraint allows orphaned records
CREATE TABLE orders_bad (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    customer_id BIGINT NOT NULL,  -- No constraint - orphans possible
    amount DECIMAL(10,2) NOT NULL
);
```

### Use CHECK constraints to enforce data formatting and business rules

**Why:** CHECK constraints enforce data validity at the database level, preventing invalid data from being inserted regardless of the application layer. This provides a safety net against bugs and ensures data integrity across all access paths.

```sql
-- ✅ Good - CHECK constraints enforce data rules
CREATE TABLE users (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    age INT,
    status ENUM('active', 'inactive', 'suspended') DEFAULT 'active',
    phone VARCHAR(20),
    CHECK (email REGEXP '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'),
    CHECK (age IS NULL OR (age >= 0 AND age <= 150)),
    CHECK (phone IS NULL OR phone REGEXP '^\\+?[1-9]\\d{1,14}$')
);

CREATE TABLE products (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    price DECIMAL(10,2) NOT NULL,
    discount_percent DECIMAL(5,2) DEFAULT 0,
    CHECK (price > 0),
    CHECK (discount_percent >= 0 AND discount_percent <= 100)
);

-- ❌ Bad - No constraints allow invalid data
CREATE TABLE users_bad (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255),  -- No format validation
    age INT,             -- No range validation
    phone VARCHAR(20)    -- No format validation
);
```

---

## 3. Indexing

### Index foreign keys, WHERE clauses, ORDER BY columns

**Why:** Proper indexing dramatically improves query performance. Foreign keys need indexes for efficient JOINs, WHERE clauses for filtering, and ORDER BY columns for sorting.

```sql
-- Index foreign keys
CREATE INDEX idx_orders_customer_id ON orders(customer_id);

-- Index commonly filtered columns
CREATE INDEX idx_orders_status_created ON orders(status, created_at);

-- Composite indexes for multi-column queries
CREATE INDEX idx_orders_customer_status ON orders(customer_id, status);
```

---

## 4. Performance

### Use LIMIT with ORDER BY; avoid SELECT *

**Why:** LIMIT prevents accidentally returning massive result sets. ORDER BY with LIMIT uses indexes efficiently. SELECT * transfers unnecessary data and breaks when schema changes.

```sql
-- ❌ Bad - No limits, SELECT *
SELECT * FROM orders WHERE status = 'pending';

-- ✅ Good - Limited, specific columns
SELECT id, customer_id, amount, created_at 
FROM orders 
WHERE status = 'pending' 
ORDER BY created_at DESC 
LIMIT 100;
```

---

## 5. Transactions

### Always use transactions for multi-statement operations

**Why:** Transactions ensure data consistency by making multiple operations atomic. Without transactions, partial failures can leave your database in an inconsistent state.

```csharp
// ❌ Bad - No transaction, partial failure possible
await connection.ExecuteAsync("INSERT INTO orders (customer_id, amount) VALUES (@CustomerId, @Amount)", order);
await connection.ExecuteAsync("UPDATE customers SET total_spent = total_spent + @Amount WHERE id = @CustomerId", order);

// ✅ Good - Transaction ensures atomicity
using var transaction = await connection.BeginTransactionAsync();
try
{
    await connection.ExecuteAsync(
        "INSERT INTO orders (customer_id, amount) VALUES (@CustomerId, @Amount)", 
        order, transaction);
    
    await connection.ExecuteAsync(
        "UPDATE customers SET total_spent = total_spent + @Amount WHERE id = @CustomerId", 
        order, transaction);
    
    await transaction.CommitAsync();
}
catch
{
    await transaction.RollbackAsync();
    throw;
}
```

---

## 6. Security

### Parameterized queries only; never string concatenation

**Why:** Parameterized queries prevent SQL injection attacks by separating SQL code from data. String concatenation creates vulnerabilities that can lead to data breaches.

```csharp
// ❌ Bad - SQL injection vulnerability
var sql = $"SELECT * FROM orders WHERE customer_id = '{customerId}'";

// ✅ Good - Parameterized query
var sql = "SELECT * FROM orders WHERE customer_id = @CustomerId";
var orders = await connection.QueryAsync<Order>(sql, new { CustomerId = customerId });
```

---

## 7. Migrations

### Version controlled; forward-only; test rollbacks

**Why:** Database schema changes must be versioned and reproducible. Forward-only migrations prevent conflicts. Testing rollbacks ensures you can recover from failed deployments.

```sql
-- Migration: 001_create_orders_table.sql
CREATE TABLE orders (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    customer_id BIGINT NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    status ENUM('pending', 'processing', 'completed', 'cancelled') DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_customer_id (customer_id),
    INDEX idx_status_created (status, created_at)
);
```
