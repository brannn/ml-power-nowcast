# EgoKit Examples

This directory contains practical examples demonstrating how to use EgoKit to keep AI coding agents consistently on-track with your standards.

## Available Examples

### 📝 [documentation-standards](./documentation-standards/)
Complete policy framework for enforcing technical documentation standards. Shows how to:
- Prevent marketing language and superlatives in technical docs
- Enforce consistent API documentation patterns
- Require examples in documentation
- Maintain professional technical tone
- Validate README structure and completeness

### 🔒 [security-first](./security-first/)
Security-focused configuration for teams handling sensitive data. Demonstrates:
- Critical security policies that block commits
- Secret detection and prevention
- OWASP compliance rules
- Security review modes for AI agents
- Threat modeling integration

### 👥 [team-scopes](./team-scopes/)
Hierarchical team configuration showing scope precedence. Includes:
- Global organizational standards
- Team-specific overrides (backend, frontend, mobile)
- Project-level customizations
- User preference layers
- Scope resolution examples

### [ai-modes](./ai-modes/)
Different operational modes for AI agents. Features:
- Implementer mode for coding
- Reviewer mode for code reviews
- Security mode for threat analysis
- Documentation mode for writing
- Custom mode definitions

### [custom-detectors](./custom-detectors/)
Extending EgoKit with organization-specific detectors. Shows:
- Creating custom detector modules
- Python AST-based analysis
- Regex pattern matching
- Integration with external tools
- Custom validation logic

## Getting Started

Each example includes:
- `README.md` - Detailed explanation and use cases
- `.egokit/policy-registry/` - Complete policy configuration
- `sample-project/` - Example project showing generated artifacts
- `test-files/` - Files demonstrating violations and fixes

## Using an Example

1. Copy the example's .egokit/policy-registry to your organization:
```bash
cp -r examples/documentation-standards/.egokit/policy-registry ~/my-org-policies
```

2. Customize the policies for your needs:
```bash
cd ~/my-org-policies
# Edit charter.yaml and ego configurations
```

3. Apply to your projects:
```bash
cd ~/my-project
ego apply --registry ~/my-org-policies
```

## Testing Examples

Each example includes test files showing both violations and proper implementations:

```bash
# Run validation against example violations
cd examples/documentation-standards
ego validate test-files/violations/ --registry .egokit/policy-registry/

# See how fixes resolve issues
ego validate test-files/fixed/ --registry .egokit/policy-registry/
```

## Contributing Examples

To contribute a new example:
1. Create a directory with a descriptive name
2. Include a complete .egokit/policy-registry configuration
3. Add sample files showing violations and fixes
4. Document the use case and benefits
5. Test that all commands work as expected

## Example Categories

Examples are organized by primary use case:

- **Standards Enforcement**: documentation-standards, code-style
- **Security & Compliance**: security-first, compliance-sox
- **Team Organization**: team-scopes, multi-project
- **AI Behavior**: ai-modes, tone-calibration
- **Extensions**: custom-detectors, external-tools