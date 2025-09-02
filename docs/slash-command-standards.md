# Slash Command Standards

This document defines the standardized frontmatter and patterns for EgoKit-generated Claude Code slash commands, ensuring consistent user experience and proper tool constraints.

## Frontmatter Schema

All EgoKit slash commands include YAML frontmatter with these standardized keys:

### Required Fields

**description**: Brief, clear explanation of what the command does
- Format: Single line, imperative voice
- Example: `"Validate code against organizational policy standards"`

**argument-hint**: Autocomplete guidance for command arguments
- Format: Bracketed optional args, space-separated positional args
- Example: `"[--all] [file/path]"` or `"[priority] [path]"`

### Security Fields

**allowed-tools**: Constrained tool access to prevent accidental privilege escalation
- Format: Tool names with permission patterns
- Example: `"Bash(git status:*), Read(*.py), Read(*.md)"`
- Purpose: Gates dangerous operations like unrestricted shell access

### Performance Fields

**model**: Optimization hint for Claude Code model selection
- Values: `fast` (quick checks), `detailed` (comprehensive analysis) 
- Purpose: Use efficient models for simple tasks, powerful models for complex analysis

## Command Structure

### Frontmatter Block
```yaml
---
description: Command purpose in imperative voice
argument-hint: [optional] [positional]
allowed-tools: Tool(pattern:*), Tool(pattern:*)
model: fast|detailed
---
```

### Content Sections

**Usage Examples**: Multiple concrete examples showing argument patterns
```markdown
## Usage Examples
- `/command` - Basic usage
- `/command arg1 path/` - With arguments
- `/command --flag value` - With flags
```

**Context Analysis**: Live system state using command substitution
```markdown
## Context Check
- Current status: !`git status -s`
- Recent changes: !`git diff --stat`
```

**Policy Integration**: Reference to organizational standards
```markdown
## Policy Standards
Enforcing standards from @.egokit/policy-registry/charter.yaml:
```

## Command Patterns

### Bash Command Substitution

Use `!` prefix for live command execution within allowed-tools constraints:

```markdown
Current branch: !`git branch --show-current`
Recent commits: !`git log --oneline -5`
File changes: !`git diff --name-only`
```

Commands are gated by allowed-tools frontmatter to prevent privilege escalation.

### File Reference Pattern  

Use `@` prefix for file content inclusion:

```markdown
Policy rules: @.egokit/policy-registry/charter.yaml
Security standards: @docs/security-guidelines.md
```

Files are read directly into the prompt context for policy enforcement.

### Argument Variable Substitution

Use `$1`, `$2`, etc. for positional arguments and `$VARIABLE` for named parameters:

```markdown
Review code at $2 with priority $1 using our security checklist.
Validate files matching pattern $PATTERN in directory $1.
```

## Tool Constraints

### Bash Tool Patterns

Restrict bash access to specific command patterns:

```yaml
# Safe git operations only
allowed-tools: Bash(git status:*), Bash(git diff:*), Bash(git log:*)

# EgoKit commands only  
allowed-tools: Bash(ego validate:*), Bash(ego apply:*)

# Specific file patterns
allowed-tools: Bash(grep:*), Read(*.py), Read(*.md)
```

### File Access Patterns

Control file access through glob patterns:

```yaml
# Source code files only
allowed-tools: Read(src/*.py), Read(tests/*.py)

# Configuration files only  
allowed-tools: Read(.egokit/*), Read(*.yaml), Read(*.json)

# Documentation files only
allowed-tools: Read(docs/*.md), Read(*.md)
```

## Model Selection Guidelines

### Fast Model Usage
Use `model: fast` for:
- Simple validation checks
- Policy lookups
- Status queries
- Quick compliance checks

### Detailed Model Usage  
Use `model: detailed` for:
- Security threat modeling
- Comprehensive code analysis
- Complex compliance audits
- Architectural reviews

## Standard Command Categories

### Policy Enforcement Commands
```yaml
description: Validate code against organizational policy standards
argument-hint: [--all] [file/path]
allowed-tools: Bash(ego validate:*), Read(*.py), Read(*.md)
model: fast
```

### Security Analysis Commands
```yaml  
description: Security review with threat modeling and vulnerability assessment
argument-hint: [priority] [path]
allowed-tools: Bash(git diff:*), Read(*.py), Read(*.js), Read(*.go)
model: detailed
```

### Behavioral Calibration Commands
```yaml
description: Reload latest organizational policies to prevent drift
argument-hint: [scope]
allowed-tools: Bash(ego apply:*), Read(@.egokit/policy-registry/*)
model: fast
```

### Preparation Commands
```yaml
description: Pre-flight checklist before code generation  
argument-hint: [task-type]
allowed-tools: Bash(git status:*), Bash(git diff:*), Bash(git branch:*)
model: fast
```

## Implementation Notes

### Argument Processing
Commands should handle both positional and named arguments gracefully:
- Check for argument presence before substitution
- Provide helpful error messages for missing required arguments
- Use sensible defaults for optional parameters

### Error Handling
Include error recovery patterns:
- Validate tool permissions before execution
- Provide fallback behavior when tools are unavailable
- Guide users to alternative approaches when constraints block operations

### Security Considerations  
Always apply principle of least privilege:
- Grant minimal necessary tool access
- Use specific file patterns instead of wildcards when possible
- Validate user input before command substitution
- Document security implications of each allowed-tool pattern

## Migration from Legacy Commands

Existing commands without frontmatter should be upgraded to include:
1. Complete YAML frontmatter block
2. Argument hint for autocomplete
3. Tool constraints for security
4. Model optimization hints
5. Updated usage examples with arguments
6. Context analysis with command substitution
7. Policy file references with @ pattern

This ensures consistent user experience and proper security boundaries across all EgoKit-generated slash commands.