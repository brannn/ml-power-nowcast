# AI Modes Example

This example demonstrates how to configure different operational modes for AI coding agents, allowing them to switch contexts and behaviors based on the task at hand.

## Overview

AI modes allow you to define different "personalities" or behavioral configurations that agents can switch between. This enables optimal assistance for different types of work without constantly re-prompting.

## Available Modes in This Example

### Implementer Mode
Fast, practical coding with minimal explanation
- **Focus**: Getting working code quickly
- **Verbosity**: Concise
- **Style**: Direct implementation

### Reviewer Mode
Thorough code analysis with detailed feedback
- **Focus**: Finding issues and improvements
- **Verbosity**: Comprehensive
- **Style**: Analytical and constructive

### 🔒 Security Mode
Security-first mindset for threat analysis
- **Focus**: Vulnerabilities and attack vectors
- **Verbosity**: Detailed for risks
- **Style**: Paranoid and thorough

### Educator Mode
Teaching and explaining concepts clearly
- **Focus**: Understanding and learning
- **Verbosity**: Explanatory with examples
- **Style**: Patient and comprehensive

### Architect Mode
System design and high-level planning
- **Focus**: Architecture and patterns
- **Verbosity**: Strategic
- **Style**: Abstract thinking

### Debugger Mode
Systematic problem-solving and diagnostics
- **Focus**: Finding root causes
- **Verbosity**: Step-by-step
- **Style**: Methodical investigation

### 📝 Documenter Mode
Creating clear, comprehensive documentation
- **Focus**: Clarity and completeness
- **Verbosity**: Detailed
- **Style**: Structured and organized

### Optimizer Mode
Performance improvements and efficiency
- **Focus**: Speed and resource usage
- **Verbosity**: Metrics-driven
- **Style**: Analytical

## Usage

### Switching Modes

Using custom slash commands (automatically discovered by Claude Code):
```
/mode-implementer     # Quick coding mode
/mode-reviewer        # Code review mode
/mode-security        # Security analysis
/mode-educator        # Teaching mode
/mode-architect       # System design
/mode-debugger        # Troubleshooting
/mode-documenter      # Documentation
/mode-optimizer       # Performance tuning
```

These commands are available in the slash command menu when you type `/` in Claude Code.

### Mode Configuration

Each mode is defined in the ego configuration:
```yaml
modes:
  implementer:
    verbosity: "concise"
    focus: "working code quickly"
    guidelines:
      - "Minimal explanation"
      - "Focus on functionality"
      - "Quick iterations"
```

## Mode Behaviors

### Implementer Mode Example

**Request**: "Add user authentication"

**Response Style**:
```python
# Quick JWT auth implementation
from fastapi import Depends, HTTPException
from jose import jwt

def verify_token(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload["sub"]
    except:
        raise HTTPException(401)

@app.post("/login")
def login(username: str, password: str):
    if verify_password(username, password):
        return {"token": create_token(username)}
    raise HTTPException(401)
```

### Reviewer Mode Example

**Request**: "Review this authentication code"

**Response Style**:
```
## Security Analysis

**Critical Issues:**
1. No rate limiting on login endpoint - vulnerable to brute force
2. Generic exception handling masks specific JWT errors
3. Missing token expiration validation

**Code Quality:**
- Function names are clear ✓
- Type hints needed for return values
- Missing docstrings

**Suggestions:**
1. Implement rate limiting: `@rate_limit(max_calls=5, period=60)`
2. Add specific JWT exception handling
3. Include token expiration: `exp = datetime.utcnow() + timedelta(hours=1)`
4. Add comprehensive logging for security events

**Risk Level**: High - Authentication without rate limiting
```

### Educator Mode Example

**Request**: "Explain JWT authentication"

**Response Style**:
```
## Understanding JWT Authentication

JSON Web Tokens (JWT) provide stateless authentication. Let me break this down:

### What is a JWT?
A JWT consists of three parts separated by dots: header.payload.signature

1. **Header**: Contains token type and signing algorithm
2. **Payload**: Contains claims (user data)
3. **Signature**: Ensures token hasn't been tampered with

### How it Works:
1. User provides credentials
2. Server validates and creates signed JWT
3. Client includes JWT in subsequent requests
4. Server validates signature and extracts user info

### Example Implementation:
[Detailed code example with comments explaining each step...]

### Security Considerations:
- Never store sensitive data in payload (it's base64, not encrypted)
- Always validate expiration
- Use strong secret keys
- Implement refresh tokens for long sessions

Would you like me to explain any specific part in more detail?
```

## Mode Combinations

Modes can be combined for specific scenarios:

### Security + Reviewer Mode
Deep security-focused code review

### Architect + Documenter Mode
System design with comprehensive documentation

### Debugger + Educator Mode
Troubleshooting while explaining the process

## Custom Mode Creation

Define your own modes in `ego/global.yaml`:

```yaml
modes:
  custom_mode:
    verbosity: "your_preference"
    focus: "specific_focus_area"
    guidelines:
      - "Custom guideline 1"
      - "Custom guideline 2"
    tools_preference:
      - "Preferred tools"
    output_format:
      - "Preferred format"
```

## Mode Context Persistence

Modes maintain context within a session:

1. **Mode Memory**: Remembers the active mode
2. **Style Consistency**: Maintains tone throughout
3. **Focus Retention**: Keeps attention on mode's focus area
4. **Guideline Adherence**: Follows mode-specific rules

## Best Practices

### When to Use Each Mode

- **Implementer**: Rapid prototyping, hackathons
- **Reviewer**: PRs, code quality checks
- **Security**: Handling sensitive data, auth systems
- **Educator**: Onboarding, learning new concepts
- **Architect**: New projects, refactoring
- **Debugger**: Production issues, bug fixes
- **Documenter**: API docs, README files
- **Optimizer**: Performance issues, scaling

### Mode Switching Strategy

1. Start with **Architect** for new features
2. Switch to **Implementer** for coding
3. Use **Reviewer** before committing
4. Apply **Security** for sensitive changes
5. Finish with **Documenter** for documentation

## Team-Specific Modes

Teams can define their own modes:

### Frontend Team Modes
- `designer`: Focus on UI/UX implementation
- `a11y-expert`: Accessibility specialist
- `performance`: Frontend optimization

### Backend Team Modes
- `api-designer`: REST/GraphQL API design
- `database-expert`: Query optimization
- `devops`: Deployment and infrastructure

### Data Team Modes
- `analyst`: Data exploration and insights
- `ml-engineer`: Machine learning pipelines
- `privacy-officer`: GDPR/CCPA compliance

## Mode Metrics

Track mode effectiveness:

```yaml
metrics:
  implementer:
    avg_time_to_solution: "5 min"
    code_quality_score: "B+"
    explanation_clarity: "C"
  
  reviewer:
    issues_caught: "85%"
    false_positives: "10%"
    feedback_quality: "A"
```

## Troubleshooting

### Mode Not Switching
- Check if command is properly configured
- Verify ego configuration has mode defined
- Ensure no syntax errors in YAML

### Inconsistent Behavior
- Mode may need more specific guidelines
- Check for conflicting global settings
- Review mode precedence rules

### Mode Too Verbose/Concise
- Adjust `verbosity` setting
- Add specific output format guidelines
- Provide examples of desired output

## Advanced Mode Features

### Conditional Modes
```yaml
modes:
  production_debugger:
    when: "environment == 'production'"
    verbosity: "minimal"  # Don't leak info
    focus: "quick resolution"
```

### Mode Inheritance
```yaml
modes:
  senior_implementer:
    inherit_from: "implementer"
    additional_guidelines:
      - "Consider scalability"
      - "Document decisions"
```

### Mode Scheduling
```yaml
modes:
  morning_focus:
    active_hours: "09:00-12:00"
    verbosity: "minimal"
    focus: "deep work"
```

## Next Steps

1. Try each mode with a sample task
2. Customize modes for your workflow
3. Create team-specific mode sets
4. Document mode best practices
5. Share effective modes with team