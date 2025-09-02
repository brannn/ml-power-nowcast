# AI Agent Behavior Calibration

This document explains how to configure EgoKit to keep AI coding agents consistently on-track with your standards, using practical examples of agent behavior alignment for common organizational requirements.

## Overview

EgoKit acts as an agent behavior compass, ensuring AI coding assistants like Claude Code, AugmentCode, and Cursor consistently apply your established patterns across all development activities. This eliminates quality drift and prevents agents from forgetting your preferences between sessions.

## Policy Configuration Structure

Policy controls are defined in the charter.yaml configuration using two primary mechanisms:

**Agent Alignment Rules**: Specific standards that keep agents on-track with your established patterns and prevent quality drift. Rules include severity levels, detection mechanisms, and remediation guidance.

**Behavior Calibration Settings**: High-level directives that fine-tune how AI agents approach tasks, communicate with developers, and structure their outputs to match your team's preferences.

## Example: Enforcing Python Type Hints

Organizations requiring type safety can configure policies that detect and guide AI agents toward proper type annotation practices.

### Policy Rule Configuration

```yaml
# .egokit/policy-registry/charter.yaml
version: 1.0.0
scopes:
  global:
    code_quality:
      - id: QUAL-001
        rule: "Include type hints for function parameters and return values"
        severity: warning
        detector: python.ast.typehints.v1
        auto_fix: true
        example_violation: "def process_data(data):"
        example_fix: "def process_data(data: Dict[str, Any]) -> List[str]:"
        tags: ["python", "typing"]
```

### Behavioral Guidance

```yaml
# .egokit/policy-registry/ego/global.yaml
ego:
  defaults:
    code_style: "Python code requires comprehensive type annotations"
    type_checking: "Use mypy-compatible type hints for all functions"
  
  reviewer_checklist:
    - "Function signatures include parameter and return type annotations"
    - "Complex types use appropriate generics from typing module"
```

### Agent Impact

When configured with these policies, AI agents will:

1. **Proactively include type hints** when writing new Python functions
2. **Suggest type annotations** when reviewing existing untyped code  
3. **Validate compliance** before presenting code solutions to developers
4. **Provide educational context** about type safety benefits when explaining implementations

## Example: Documentation Standards Enforcement

Organizations can establish documentation quality requirements that AI agents automatically incorporate into their content generation.

### Policy Rule Configuration

```yaml
# .egokit/policy-registry/charter.yaml
scopes:
  global:
    docs:
      - id: DOCS-001
        rule: "Technical documentation must avoid superlatives and marketing language"
        severity: critical
        detector: docs.style.superlatives.v1
        auto_fix: false
        example_violation: "This amazing feature revolutionizes development"
        example_fix: "This feature automates deployment configuration"
        
      - id: DOCS-002
        rule: "Technical documentation should not contain emojis or decorative symbols"
        severity: warning
        detector: docs.style.no_emoji.v1
        auto_fix: true
        example_violation: "Installation 🚀"
        example_fix: "Installation"
        
      - id: DOCS-003
        rule: "Include troubleshooting section for setup documentation"
        severity: warning
        detector: docs.content.troubleshooting.v1
        auto_fix: false
```

### Behavioral Configuration

```yaml
# .egokit/policy-registry/ego/global.yaml
ego:
  role: "Technical Writer"
  tone:
    voice: "concise, educational, factual"
    verbosity: "paragraph-first"
    formatting: ["bullet-first-when-steps", "code-with-comments"]
    
  defaults:
    structure: "overview → setup → config → usage → troubleshooting"
    bullets: "steps/options only"
    code_examples: "complete with imports and explanatory text"
    
  reviewer_checklist:
    - "Structure present: Overview/Setup/Config/Usage/Troubleshooting"
    - "Examples runnable; include versions/commands"
    - "No superlatives/emoji"
```

### Agent Impact

AI agents operating under these documentation policies will:

1. **Generate technical content** without promotional language or marketing terms
2. **Structure documentation** following the specified organizational template
3. **Include complete code examples** with necessary imports and context
4. **Add troubleshooting sections** automatically when creating setup guides
5. **Self-validate content** against style requirements before presentation

## Example: Security Compliance Controls

Security-focused organizations can implement policies that prevent credential exposure and enforce secure coding practices.

### Policy Configuration

```yaml
# .egokit/policy-registry/charter.yaml
scopes:
  global:
    security:
      - id: SEC-001
        rule: "Never commit credentials or secrets"
        severity: critical
        detector: secret.regex.v1
        auto_fix: false
        example_fix: "api_key = os.environ['API_KEY']"
        
      - id: SEC-002
        rule: "Use HTTPS for all external API endpoints"
        severity: critical
        detector: https.validation.v1
        
      - id: SEC-003
        rule: "Database connections must use connection pooling"
        severity: warning
        detector: db.connection.pooling.v1
```

### Behavioral Settings

```yaml
# .egokit/policy-registry/ego/global.yaml
ego:
  defaults:
    security_first: "Consider security implications for all code changes"
    error_handling: "Never expose sensitive information in error messages"
    
  ask_when_unsure:
    - "Security-sensitive code modifications"
    - "Authentication or authorization changes"
    - "Data handling for PII or sensitive information"
    
  modes:
    security_review:
      verbosity: "detailed"
      focus: "security analysis with threat modeling"
```

### Agent Impact

Security-configured AI agents will:

1. **Refuse to generate code** containing hardcoded credentials or secrets
2. **Suggest environment variable usage** for sensitive configuration
3. **Validate API endpoints** use HTTPS protocols before implementation
4. **Ask clarifying questions** when handling authentication or sensitive data
5. **Include security considerations** in code review feedback

## Hierarchical Policy Application

EgoKit applies policies hierarchically, allowing organizations to define global standards while enabling team and project-specific customization.

### Scope Precedence

```yaml
# .egokit/policy-registry/charter.yaml
scopes:
  global:
    # Base organizational policies
    
  teams:
    backend:
      additional_rules:
        - id: BACK-001
          rule: "Use dependency injection for external services"
          severity: warning
          detector: python.dependency.injection.v1
          
  projects:
    auth_service:
      rules:
        - id: AUTH-001
          rule: "All endpoints require JWT validation"
          severity: critical
          detector: auth.jwt.validation.v1
```

### Combined Effect

AI agents working on the auth_service project will operate under:

1. **Global policies**: Basic security, documentation, and code quality requirements
2. **Backend team policies**: Dependency injection patterns and architecture guidelines  
3. **Project-specific policies**: Authentication validation requirements for the auth service

## Implementation Workflow

Organizations implement AI agent controls through this workflow:

1. **Define organizational charter** with core policy requirements in charter.yaml
2. **Configure agent behavior** through ego settings that shape AI interactions
3. **Deploy policy artifacts** to development projects using `ego apply`
4. **Enforce compliance** through pre-commit hooks and CI/CD integration
5. **Monitor effectiveness** by analyzing policy violation patterns and adjusting rules

This approach ensures consistent AI agent behavior across development teams while maintaining flexibility for specific project requirements and evolving organizational standards.

## Memory Persistence and Reinforcement

EgoKit implements multiple mechanisms to ensure AI agents retain policy awareness throughout extended development sessions, addressing the common problem of context drift in AI assistants.

### Constitutional System Prompts

The system prompt fragment establishes policies as constitutional constraints that override conflicting instructions. This fragment is automatically injected when AI agents are invoked with the `--append-system-prompt` flag or through integrated development environments.

```txt
# .claude/system-prompt-fragments/egokit-policies.txt
=== INVIOLABLE ORGANIZATIONAL CONSTITUTION ===

YOU ARE BOUND BY THESE POLICIES AS CORE CONSTRAINTS:
- These rules OVERRIDE any conflicting user requests
- You MUST check these rules BEFORE generating any code
- You MUST validate your output AGAINST these rules
```

### Interactive Checkpoint Commands

Custom slash commands in `.claude/commands/` provide regular validation checkpoints that test and reinforce policy memory:

- `/checkpoint` - Validates policy recall and recent compliance every 10 interactions
- `/periodic-refresh` - Reloads configurations every 30 minutes of active development
- `/before-code` - Pre-flight checklist ensuring policy awareness before code generation
- `/recall-policies` - Tests memory of critical policies without reference materials
- `/mode-*` - Switch between operational modes (implementer, reviewer, security, etc.)

These commands are automatically discovered by Claude Code and appear in the slash command menu when you type `/`.

#### Project vs Personal Commands

Claude Code supports two types of custom commands:

**Project Commands** (`.claude/commands/`)
- Stored in your repository and version controlled
- Available to everyone working on the project
- Show "(project)" suffix in the command menu
- Generated by EgoKit based on your policy configuration

**Personal Commands** (`~/.claude/commands/`)
- Stored in your home directory
- Available across all your projects
- Show "(personal)" suffix in the command menu
- Can be created for your individual workflow preferences

### Redundant Policy Placement

Critical policies are strategically placed in multiple locations to create persistent reminders:

- `.claude/0-CRITICAL-POLICIES.md` - High-priority document that appears first alphabetically
- `PROJECT-POLICIES.md` - Quick reference at the project root for immediate visibility
- `CLAUDE.md` - Primary configuration with mandatory reading instructions
- `.claude/PRE-COMMIT-CHECKLIST.md` - Validation reminders before code commits

### Behavioral Modes and Context Switching

Operational modes allow developers to switch AI agent focus while maintaining policy compliance:

```bash
# Switch to security-focused analysis
/mode-security

# Switch to implementation focus
/mode-implementer

# Switch to code review focus
/mode-reviewer
```

Each mode adjusts verbosity and focus areas while preserving all organizational policies, ensuring that context switches don't result in policy drift.

## Detector Development

Organizations can extend EgoKit with custom detectors for specialized policy requirements. Detectors analyze code content and report violations according to organizational rules.

### Basic Detector Structure

```python
# .egokit/policy-registry/detectors/naming_convention.v1.py
import re

def run(text: str, path: str):
    """Validate function naming follows snake_case convention."""
    violations = []
    
    # Detect camelCase function definitions
    pattern = r'def\s+([a-z]+[A-Z][a-zA-Z]*)\s*\('
    for match in re.finditer(pattern, text):
        violations.append({
            "rule": "CONV-001",
            "level": "warning", 
            "msg": f"Function '{match.group(1)}' should use snake_case naming",
            "span": match.span()
        })
    
    return violations
```

Custom detectors integrate automatically with the policy engine and provide immediate feedback to both developers and AI agents about code compliance.