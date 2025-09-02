---
description: Security review with threat modeling and vulnerability assessment
argument-hint: [priority] [path]
allowed-tools: Bash(git diff:*), Bash(grep:*), Read(*.py), Read(*.js), Read(*.go)
---

# Switch to Security Review Mode

Activates heightened security analysis with threat modeling focus.

## Usage Examples
- `/security-review` - Review current changes with standard priority
- `/security-review high src/auth/` - High priority review of auth module
- `/security-review critical .` - Critical security audit of entire project

## Context Analysis
Recent changes: !`git diff --stat --name-only`

## Security Standards
Applying 0 security policies from @.egokit/policy-registry/charter.yaml:

## Behavior Changes
- Enhanced security vulnerability detection
- Threat modeling considerations for all code changes
- OWASP Top 10 validation
- Cryptographic implementation review
- Authentication and authorization analysis

## Implementation
```bash
export EGOKIT_MODE="security"
echo "🔒 Security review mode activated. All code will be analyzed for security implications."
```

## Context
This mode calibrates agent behavior for security-focused analysis, ensuring consistent application of security standards and threat awareness.