# API Documentation

This document describes the SuperApp REST API version 2.4.1. All endpoints require authentication unless otherwise specified.

## Authentication

The API uses Bearer token authentication. Include your API token in the Authorization header:

```
Authorization: Bearer YOUR_API_TOKEN
```

Tokens expire after 24 hours. Request new tokens through the /auth/token endpoint.

## Endpoints

### POST /api/process

Processes input data through the configured pipeline.

**Request:**
```http
POST /api/process HTTP/1.1
Content-Type: application/json
Authorization: Bearer YOUR_API_TOKEN

{
  "data": [...],
  "options": {
    "validate": true,
    "format": "json"
  }
}
```

**Parameters:**
- `data` (array, required): Array of data objects to process
- `options.validate` (boolean, optional): Enable validation (default: true)
- `options.format` (string, optional): Output format - json, csv, xml (default: json)

**Response:**
```json
HTTP/1.1 200 OK
Content-Type: application/json

{
  "status": "success",
  "processed": 150,
  "results": [...],
  "processing_time": 1.234
}
```

**Status Codes:**
- `200 OK`: Processing completed successfully
- `400 Bad Request`: Invalid input data or parameters
- `401 Unauthorized`: Missing or invalid authentication token
- `422 Unprocessable Entity`: Validation failed
- `500 Internal Server Error`: Processing failed

**Error Response:**
```json
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "error": "ValidationError",
  "message": "Data validation failed at index 42",
  "details": {
    "field": "timestamp",
    "expected": "ISO 8601 format",
    "received": "invalid-date"
  }
}
```

### GET /api/status

Returns current system status and health metrics.

**Request:**
```http
GET /api/status HTTP/1.1
Authorization: Bearer YOUR_API_TOKEN
```

**Response:**
```json
HTTP/1.1 200 OK
Content-Type: application/json

{
  "status": "operational",
  "version": "2.4.1",
  "uptime": 864000,
  "metrics": {
    "requests_per_minute": 120,
    "average_response_time": 0.234,
    "error_rate": 0.001
  }
}
```

**Status Codes:**
- `200 OK`: System operational
- `503 Service Unavailable`: System experiencing issues

### PUT /api/config

Updates system configuration. Requires admin privileges.

**Request:**
```http
PUT /api/config HTTP/1.1
Content-Type: application/json
Authorization: Bearer YOUR_ADMIN_TOKEN

{
  "pipeline": {
    "steps": ["validate", "transform", "format"],
    "validation": {
      "strict": true
    }
  }
}
```

**Parameters:**
- `pipeline` (object, required): Pipeline configuration object
- `pipeline.steps` (array, required): Ordered list of processing steps
- `pipeline.validation` (object, optional): Validation settings

**Response:**
```json
HTTP/1.1 200 OK
Content-Type: application/json

{
  "status": "updated",
  "config": {...},
  "applied_at": "2025-08-31T10:30:00Z"
}
```

**Status Codes:**
- `200 OK`: Configuration updated successfully
- `400 Bad Request`: Invalid configuration format
- `401 Unauthorized`: Insufficient privileges
- `409 Conflict`: Configuration conflicts with running processes

## Rate Limiting

API requests are limited to 1000 requests per hour per token. Rate limit information is included in response headers:

```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 950
X-RateLimit-Reset: 1693564800
```

When rate limit is exceeded, the API returns:

```json
HTTP/1.1 429 Too Many Requests
Content-Type: application/json
Retry-After: 3600

{
  "error": "RateLimitExceeded",
  "message": "Rate limit of 1000 requests per hour exceeded",
  "retry_after": 3600
}
```

## Complete Example

Processing data with error handling:

```python
import requests
import json
from typing import Dict, List

API_BASE = "https://api.example.com"
API_TOKEN = "your_token_here"

def process_data(data: List[Dict]) -> Dict:
    """Process data through the API with proper error handling."""
    
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "data": data,
        "options": {
            "validate": True,
            "format": "json"
        }
    }
    
    try:
        response = requests.post(
            f"{API_BASE}/api/process",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        # Check for rate limiting
        if response.status_code == 429:
            retry_after = response.headers.get('Retry-After', 3600)
            raise Exception(f"Rate limited. Retry after {retry_after} seconds")
        
        # Check for other errors
        response.raise_for_status()
        
        return response.json()
        
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            error_data = e.response.json()
            print(f"Error details: {error_data}")
        raise

# Example usage
if __name__ == "__main__":
    sample_data = [
        {"id": 1, "value": 100},
        {"id": 2, "value": 200}
    ]
    
    result = process_data(sample_data)
    print(f"Processed {result['processed']} records in {result['processing_time']} seconds")
```