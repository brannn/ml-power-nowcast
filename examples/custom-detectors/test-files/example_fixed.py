"""Example file with all detector issues fixed."""

import os
from typing import List, Dict, Any, Optional
from decimal import Decimal
from functools import lru_cache
import asyncio
import aiofiles
from fastapi import Depends, HTTPException
from sqlalchemy.orm import selectinload

# TODO (JIRA-1234): Add comprehensive error handling for edge cases
def process_user_data(user_id: str) -> Dict:
    """Process user data from database securely."""
    
    # Get connection string from environment
    connection_string = os.environ.get('DATABASE_URL')
    if not connection_string:
        raise ValueError("Database URL not configured")
    
    # Use parameterized query with specific columns
    query = """
        SELECT id, name, email, created_at, status 
        FROM users 
        WHERE id = %s 
        LIMIT 1
    """
    
    result = db.execute(query, (user_id,))
    
    # Avoid N+1 with eager loading
    user = db.query(User).options(
        selectinload(User.orders).selectinload(Order.items)
    ).filter_by(id=user_id).first()
    
    return result.to_dict()


# API endpoint with proper security
@app.post("/api/v1/users")
@require_auth  # Authentication
@rate_limit(calls=100, period=60)  # Rate limiting
async def create_user(
    data: UserCreateSchema,  # Input validation via Pydantic
    current_user: User = Depends(get_current_user)
):
    """Create a new user with proper validation and security."""
    
    # Use transaction for multiple operations
    async with db.transaction():
        user = await db.execute("INSERT INTO users VALUES (...) RETURNING *", data.dict())
        profile = await db.execute("INSERT INTO profiles VALUES (...)", {"user_id": user.id})
        await db.execute("UPDATE stats SET user_count = user_count + 1")
    
    # Proper error handling without stack trace disclosure
    try:
        await process_payment(data.payment)
    except PaymentError as e:
        # Log full error internally
        logger.error(f"Payment failed for user {user.id}: {e}", exc_info=True)
        # Return generic error to client
        raise HTTPException(status_code=400, detail="Payment processing failed")
    
    # Audit log for sensitive operation
    await audit_log.record(
        action="user_created",
        user_id=current_user.id,
        target_id=user.id,
        ip_address=request.client.host
    )
    
    return {"status": "created", "user_id": user.id}


# CORS with specific origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://app.example.com",
        "https://admin.example.com"
    ],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


class Money:
    """Represent monetary values with currency."""
    def __init__(self, amount: Decimal, currency: str):
        self.amount = amount
        self.currency = currency


def calculate_price(amount: Money, tax_rate: Decimal = Decimal("0.08")) -> Money:
    """Calculate final price including tax."""
    # Apply discount
    discount = amount.amount * Decimal("0.1")
    subtotal = amount.amount - discount
    
    # Calculate tax
    tax = subtotal * tax_rate
    total = subtotal + tax
    
    return Money(total, amount.currency)


async def delete_user(user_id: str, deleted_by: str):
    """Delete user account following data retention policies."""
    
    # Audit log before deletion
    await audit_log.record(
        action="user_deletion_initiated",
        user_id=deleted_by,
        target_id=user_id,
        metadata={"reason": "user_request"}
    )
    
    async with db.transaction():
        # Handle data retention requirements
        # Archive user data for compliance (GDPR requires 3 years)
        await db.execute(
            "INSERT INTO archived_users SELECT * FROM users WHERE id = %s",
            (user_id,)
        )
        
        # Anonymize rather than delete for data integrity
        await db.execute(
            """UPDATE users 
               SET email = %s, name = 'Deleted User', 
                   deleted_at = NOW() 
               WHERE id = %s""",
            (f"deleted_{user_id}@example.com", user_id)
        )
    
    # Final audit entry
    await audit_log.record(
        action="user_deletion_completed",
        user_id=deleted_by,
        target_id=user_id
    )


# Async I/O for async functions
async def fetch_data():
    """Fetch data using async I/O."""
    async with aiofiles.open('data.txt', 'r') as f:
        return await f.read()


# Cache expensive calculations
@lru_cache(maxsize=128)
def expensive_calculation(n: int) -> int:
    """Compute fibonacci with memoization."""
    if n <= 1:
        return n
    return expensive_calculation(n-1) + expensive_calculation(n-2)


# Proper API versioning
@app.get("/api/v1/users")
@require_auth
@rate_limit(calls=1000, period=60)
async def get_users(
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(get_current_user)
):
    """Get users with pagination and proper versioning."""
    users = await db.fetch(
        "SELECT id, name, email FROM users LIMIT %s OFFSET %s",
        (limit, offset)
    )
    return {"users": users, "version": "1.0"}