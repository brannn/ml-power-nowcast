---
description: Validate code against organizational policy standards
argument-hint: [--all] [file/path]
allowed-tools: Bash(ego validate:*), Read(*.py), Read(*.md)
---

# Validate Code Against Organizational Standards

This command runs EgoKit policy validation to ensure code stays on-track with established patterns.

## Usage Examples
- `/validate` - Validate changed files only
- `/validate --all` - Validate entire codebase
- `/validate src/models.py` - Validate specific file
- `/validate src/` - Validate directory

## Context Check
Current status: !`git status -s`

## Active Policy Rules
Enforcing 63 organizational standards from @.egokit/policy-registry/charter.yaml:

### Critical Standards (Will Block Commits)

- **DOCS-001**: Technical documentation must avoid superlatives and self-promotional language
- **DOCS-002**: Do not use emoji icons or decorative symbols in technical documentation
- **DOCS-004**: Code examples must be complete and functional with necessary imports and context
- **DOCS-005**: Include specific version numbers and exact command syntax in instructions
- **DOCS-006**: Document error conditions with actual error messages and resolution steps
- ... and 38 more critical standards

## Implementation
```bash
# Run EgoKit validation
python3 -m egokit.cli validate --changed --format json

# Parse results and provide summary
if [ $? -eq 0 ]; then
    echo "✅ All policy checks passed"
else
    echo "❌ Policy violations detected. Run 'python3 -m egokit.cli validate --changed' for details."
fi
```

## Context
This command integrates with the organizational policy framework to prevent quality drift and ensure consistent agent behavior across all development activities.