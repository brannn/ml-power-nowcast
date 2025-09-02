# Documentation Standards Example

This example demonstrates how to use EgoKit to enforce professional technical documentation standards across your organization, ensuring AI coding agents maintain consistent, high-quality documentation without marketing language or excessive embellishments.

## Overview

Based on real-world documentation standards, this configuration ensures:
- No superlatives or promotional language in technical docs
- Professional tone without emojis or decorative symbols
- Preference for prose over excessive bullet points
- Complete and functional code examples
- Accurate technical specifications

## What's Included

### Policy Registry Configuration
- `charter.yaml` - Documentation-focused policy rules with detectors
- `ego/global.yaml` - AI agent calibration for technical writing
- `ego/teams/docs.yaml` - Documentation team specific overrides

### Sample Violations & Fixes
- `test-files/violations/` - Examples that violate standards
- `test-files/fixed/` - Corrected versions showing proper style

### Generated Artifacts
- `sample-project/` - Shows what EgoKit generates for your project

## Key Policies Enforced

### Critical Rules (Block Commits)
- **DOCS-001**: No superlatives or marketing language
- **DOCS-002**: No emoji in technical documentation
- **DOCS-003**: Code examples must include context and imports

### Warning Rules (Guidance)
- **DOCS-004**: Prefer prose over excessive bullet points
- **DOCS-005**: Include error handling documentation
- **DOCS-006**: Maintain consistent section structure

## Usage

### 1. Apply to Your Project

```bash
cd your-project/
ego apply --registry examples/documentation-standards/.egokit/policy-registry
```

### 2. Validate Documentation

```bash
# Check specific documentation files
ego validate README.md docs/api.md --registry examples/documentation-standards/.egokit/policy-registry

# Check all markdown files
ego validate --all --registry examples/documentation-standards/.egokit/policy-registry
```

### 3. Pre-commit Integration

Add to `.pre-commit-config.yaml`:
```yaml
repos:
  - repo: local
    hooks:
      - id: ego-docs
        name: Documentation Standards Check
        entry: ego validate
        language: system
        files: \.(md|rst|txt)$
        pass_filenames: true
```

## Example Violations

### Violation: Marketing Language
```markdown
## Our Amazing Features

This incredible, cutting-edge system provides world-class performance that will revolutionize your workflow!
```

### Fixed: Professional Technical Writing
```markdown
## System Features

This system provides automated workflow processing with measured performance improvements of 40% in standard benchmarks.
```

### Violation: Incomplete Code Example
```python
# Just use our function!
result = process_data(input)
```

### Fixed: Complete, Contextual Example
```python
from dataprocessor import process_data
import pandas as pd

# Load input data from CSV
input_data = pd.read_csv('data/metrics.csv')

# Process data with default configuration
result = process_data(input_data, validate=True, format='json')

# Result contains processed metrics as dictionary
print(f"Processed {len(result)} records")
```

## AI Agent Behavior

When these policies are active, AI coding agents will:

1. **Write professionally** - No marketing fluff or hyperbole
2. **Provide complete examples** - All code samples are runnable
3. **Structure content logically** - Clear progression from overview to details
4. **Document errors properly** - Include troubleshooting steps
5. **Maintain consistency** - Follow established patterns across all docs

## Customization

### Adjusting Severity Levels

Edit `charter.yaml` to change rule enforcement:
```yaml
- id: DOCS-001
  rule: "No superlatives or marketing language"
  severity: warning  # Changed from critical
```

### Adding Custom Rules

Extend the charter with organization-specific requirements:
```yaml
- id: DOCS-CUSTOM-001
  rule: "Include performance benchmarks for all optimization claims"
  severity: critical
  detector: docs.benchmarks.v1
```

### Team-Specific Overrides

Create team configurations in `ego/teams/`:
```yaml
# ego/teams/marketing.yaml
ego:
  tone:
    voice: "engaging, accessible"  # More relaxed for marketing team
```

## Benefits

Using this documentation standards configuration:

- **Consistency** - All documentation follows the same professional standards
- **Quality** - AI agents produce technical content, not marketing copy
- **Efficiency** - Catch documentation issues before review
- **Learning** - AI agents learn and maintain your documentation style
- **Automation** - Reduce manual documentation review burden

## Testing the Configuration

### Run Validation Tests
```bash
cd examples/documentation-standards

# Test against violations (should fail)
ego validate test-files/violations/ --registry .egokit/policy-registry/

# Test against fixed versions (should pass)
ego validate test-files/fixed/ --registry .egokit/policy-registry/
```

### Preview Generated Artifacts
```bash
ego apply --dry-run --registry .egokit/policy-registry/
```

## Integration with AI Agents

The generated artifacts teach AI coding agents to:

### Claude Code
- Custom `/docs-review` command for documentation validation
- System prompt emphasizing technical writing standards
- Settings preventing emoji and superlative usage
- CLAUDE.md configuration enforcing documentation policies

### AugmentCode
- Documentation-specific rules in `.augment/rules/`
- Style guide enforcement
- Example patterns for proper documentation

## Next Steps

1. Copy this example to your organization's policy repository
2. Customize rules based on your documentation standards
3. Add custom detectors for organization-specific requirements
4. Roll out to development teams incrementally
5. Monitor and refine based on false positive rates

## Additional Resources

- [EgoKit Documentation](../../docs/)
- [Writing Custom Detectors](../custom-detectors/)
- [Team Scopes Example](../team-scopes/)