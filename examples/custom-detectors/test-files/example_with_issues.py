"""Example file demonstrating various detector violations."""

import os
from typing import List, Dict, Any

# TODO: Add error handling for this function
def process_user_data(user_id: str) -> Dict:
    """Process user data from database."""
    
    # FIXME: This is broken in production
    connection_string = "postgresql://admin:password123@localhost/prod"  # CUSTOM-DB-002 violation
    
    # HACK: Temporary workaround for performance
    query = f"SELECT * FROM users WHERE id = '{user_id}'"  # Multiple violations:
    # - CUSTOM-DB-001: SELECT *
    # - CUSTOM-DB-002: SQL injection risk
    # - CUSTOM-DB-003: No LIMIT clause
    
    result = db.execute(query)
    
    # N+1 query problem
    for order in user.orders:  # CUSTOM-DB-004 violation
        items = db.query(f"SELECT * FROM items WHERE order_id = {order.id}")
        order.items = items
    
    return result


# API endpoint without security
@app.post("/api/users")  # Multiple violations:
def create_user(data: dict):  # CUSTOM-API-001: No authentication
    # CUSTOM-API-003: No input validation
    
    # Multiple database operations without transaction
    db.execute("INSERT INTO users VALUES (...)")  # CUSTOM-DB-005 violation
    db.execute("INSERT INTO profiles VALUES (...)")
    db.execute("UPDATE stats SET user_count = user_count + 1")
    
    # Returning stack trace in error
    try:
        process_payment(data['payment'])
    except Exception as e:
        import traceback
        return {"error": traceback.format_exc()}  # CUSTOM-API-004 violation
    
    return {"status": "created"}


# CORS with wildcard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # CUSTOM-API-005 violation
    allow_methods=["*"],
    allow_headers=["*"],
)


def calculate_price(amount: float) -> float:  # CUSTOM-BIZ-002: No currency
    """Calculate final price."""
    # CUSTOM-BIZ-001: Missing tax calculation
    discount = amount * 0.1
    return amount - discount


def delete_user(user_id: str):  # CUSTOM-BIZ-003: No audit logging
    """Delete user account."""
    # CUSTOM-BIZ-004: No data retention policy handling
    db.execute(f"DELETE FROM users WHERE id = {user_id}")
    # XXX: Should we also delete related data?


# Performance issues
async def fetch_data():  # CUSTOM-PERF-001: Sync I/O in async
    with open('data.txt', 'r') as f:  # Should use aiofiles
        return f.read()


def expensive_calculation(n: int) -> int:  # CUSTOM-PERF-002: Should cache
    """Compute fibonacci recursively."""
    if n <= 1:
        return n
    return expensive_calculation(n-1) + expensive_calculation(n-2)


# Missing API versioning - CUSTOM-API-006
@app.get("/users")  # Should be /api/v1/users
def get_users():
    pass