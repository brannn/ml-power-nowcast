# Security-First Example

This example demonstrates how to configure EgoKit for security-conscious development teams, ensuring AI coding agents prioritize security in every interaction and never introduce vulnerabilities.

## Overview

This configuration enforces:
- Zero tolerance for hardcoded secrets or credentials
- Mandatory input validation and sanitization
- Secure coding patterns by default
- Threat modeling in design decisions
- OWASP Top 10 awareness
- Cryptographic best practices

## What's Included

### Policy Registry Configuration
- `charter.yaml` - Comprehensive security policies
- `ego/global.yaml` - Security-focused AI agent calibration
- `ego/teams/appsec.yaml` - Application security team overrides

### Test Files
- `test-files/vulnerable/` - Code with security issues
- `test-files/secure/` - Properly secured implementations

### Generated Artifacts
- `sample-project/` - Security-focused agent configurations

## Key Security Policies

### Critical Rules (Block Everything)
- **SEC-001**: Never commit credentials, secrets, or API keys
- **SEC-002**: Always validate and sanitize user input
- **SEC-003**: Use parameterized queries for database operations
- **SEC-004**: Implement proper authentication and authorization
- **SEC-005**: Use secure communication (HTTPS/TLS only)
- **SEC-006**: Apply principle of least privilege
- **SEC-007**: Validate and escape output to prevent XSS
- **SEC-008**: Use cryptographically secure random generators

### Warning Rules (Security Guidance)
- **SEC-009**: Implement rate limiting for APIs
- **SEC-010**: Add security headers to HTTP responses
- **SEC-011**: Log security events for monitoring
- **SEC-012**: Implement secure session management
- **SEC-013**: Use content security policies

## Usage

### Apply Security Configuration

```bash
cd your-project/
ego apply --registry examples/security-first/.egokit/policy-registry
```

### Run Security Validation

```bash
# Check all code for security issues
ego validate --all --registry examples/security-first/.egokit/policy-registry

# Focus on changed files in PR
ego validate --changed --format json
```

### Pre-commit Security Checks

```yaml
repos:
  - repo: local
    hooks:
      - id: ego-security
        name: Security Policy Validation
        entry: ego validate --changed
        language: system
        stages: [commit]
```

## Example Violations and Fixes

### Violation: Hardcoded Credentials
```python
# NEVER DO THIS
api_key = "sk-proj-abc123xyz789"
database_url = "postgresql://user:password@localhost/db"

def connect():
    return psycopg2.connect(database_url)
```

### Fixed: Environment Variables
```python
import os
from typing import Optional

def get_api_key() -> str:
    """Retrieve API key from environment variable."""
    api_key = os.environ.get('API_KEY')
    if not api_key:
        raise ValueError("API_KEY environment variable not set")
    return api_key

def get_database_url() -> str:
    """Construct database URL from environment variables."""
    db_host = os.environ.get('DB_HOST', 'localhost')
    db_port = os.environ.get('DB_PORT', '5432')
    db_name = os.environ.get('DB_NAME')
    db_user = os.environ.get('DB_USER')
    db_pass = os.environ.get('DB_PASSWORD')
    
    if not all([db_name, db_user, db_pass]):
        raise ValueError("Database configuration incomplete")
    
    return f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
```

### Violation: SQL Injection Vulnerability
```python
def get_user(user_id: str):
    query = f"SELECT * FROM users WHERE id = '{user_id}'"
    return db.execute(query)
```

### Fixed: Parameterized Query
```python
def get_user(user_id: str):
    """Safely retrieve user by ID using parameterized query."""
    query = "SELECT * FROM users WHERE id = %s"
    return db.execute(query, (user_id,))
```

### Violation: Weak Randomness
```python
import random

def generate_token():
    return ''.join(random.choices('abcdef0123456789', k=32))
```

### Fixed: Cryptographically Secure
```python
import secrets

def generate_token() -> str:
    """Generate cryptographically secure token."""
    return secrets.token_urlsafe(32)
```

## AI Agent Behavior

With this security configuration, AI agents will:

1. **Always check for secrets** before suggesting any code
2. **Default to secure patterns** even for simple examples
3. **Include security considerations** in design discussions
4. **Suggest threat mitigation** for new features
5. **Validate dependencies** for known vulnerabilities
6. **Implement defense in depth** automatically
7. **Document security implications** of changes

## Security Modes

### Available Modes

- **security-reviewer**: Deep security analysis mode
- **threat-modeler**: Focus on attack vectors and mitigations
- **compliance-checker**: Verify regulatory compliance
- **incident-responder**: Security incident handling mode

Activate with: `/mode-security-reviewer`

## Integration with Security Tools

This configuration integrates with:

- **Semgrep**: Custom rules for pattern matching
- **Bandit**: Python security linting
- **GitLeaks**: Secret detection in git history
- **OWASP Dependency Check**: Vulnerable dependency scanning
- **Trivy**: Container and IaC scanning

## Compliance Frameworks

Policies align with:
- OWASP Top 10
- CWE Top 25
- PCI DSS requirements
- SOC 2 Type II controls
- ISO 27001 standards
- NIST Cybersecurity Framework

## Security Training

The configuration includes educational components:

- Security best practices in comments
- Threat examples with mitigation strategies
- Links to security resources
- Common vulnerability patterns to avoid

## Monitoring and Alerting

Configure notifications for:
- Critical security violations in PRs
- New vulnerabilities in dependencies
- Suspicious code patterns
- Failed security validations

## Next Steps

1. Review and customize security policies for your threat model
2. Add industry-specific compliance requirements
3. Configure security tool integrations
4. Train team on security-first development
5. Monitor and refine based on findings