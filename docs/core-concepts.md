# EgoKit Core Concepts

This document defines the fundamental concepts and components that comprise the EgoKit agent behavior calibration system and AI agent alignment framework.

## Policy Charter

The **Policy Charter** is the central configuration file that defines organizational rules and requirements for AI coding agents. Stored as `.egokit/policy-registry/charter.yaml`, it contains enforceable policies organized by scope and category.

### Structure

```yaml
# .egokit/policy-registry/charter.yaml
version: 1.0.0
scopes:
  global:
    security:
      - id: SEC-001
        rule: "Never commit credentials or secrets"
        severity: critical
        detector: secret.regex.v1
        auto_fix: false
        example_violation: "api_key = 'sk-123456789abcdef'"
        example_fix: "api_key = os.environ['API_KEY']"
        tags: ["security", "credentials"]
```

### Policy Rules

Each policy rule consists of:

- **ID**: Unique identifier following the pattern `PREFIX-###` (e.g., SEC-001, QUAL-002)
- **Rule**: Human-readable description of the requirement or constraint
- **Severity**: Enforcement level (critical, warning, info)
- **Detector**: Module name that implements validation logic
- **Auto-fix**: Whether automatic remediation is available
- **Examples**: Violation and fix examples for educational purposes
- **Tags**: Categorization labels for rule organization

## Scope Hierarchy

EgoKit implements **hierarchical scopes** that enable agent behavior customization at different organizational levels while maintaining consistent alignment with established standards.

### Scope Types

**Global Scope**: Organization-wide policies that apply to all development teams and projects. These typically include security requirements, compliance standards, and fundamental code quality rules.

**Team Scope**: Team-specific policies that extend or override global rules for particular development groups. Backend teams might require database connection pooling, while frontend teams enforce accessibility standards.

**Project Scope**: Project-specific policies that address unique requirements for individual repositories. Authentication services might require JWT validation, while data processing pipelines enforce specific logging standards.

**User Scope**: Individual developer preferences that customize AI agent behavior without violating organizational policies. Users can adjust verbosity, communication style, or operational modes.

**Session Scope**: Temporary overrides for specific development tasks. Developers can switch AI agents to security review mode or documentation generation mode for focused activities.

### Precedence Resolution

When multiple scopes define rules with the same ID, EgoKit resolves conflicts using precedence ordering:

```
global < team < project < user < session
```

Later scopes override earlier ones, enabling hierarchical customization while maintaining consistent agent behavior alignment across the organization.

## Ego Configuration

**Ego Configuration** defines AI agent behavioral characteristics and operational preferences. Stored in `.egokit/policy-registry/ego/` files, these settings shape how AI agents communicate, structure responses, and approach development tasks.

### Behavioral Settings

```yaml
# .egokit/policy-registry/ego/global.yaml
ego:
  role: "Senior Software Engineer"
  tone:
    voice: "professional, educational, precise"
    verbosity: "balanced"
    formatting: ["code-with-comments", "bullet-lists-for-procedures"]
  
  defaults:
    code_style: "PEP-8 compliant with comprehensive type hints"
    error_handling: "Comprehensive with informative messages"
    testing: "Unit tests with meaningful assertions"
  
  reviewer_checklist:
    - "Code follows established patterns and style guides"
    - "Error handling covers expected failure cases"
    - "Documentation explains purpose and usage clearly"
  
  ask_when_unsure:
    - "Breaking changes to public interfaces"
    - "Security-sensitive code modifications"
```

### Operational Modes

Ego configuration supports **operational modes** that adjust AI agent behavior for specific tasks:

- **Implementer Mode**: Focused on clean implementation following established patterns
- **Reviewer Mode**: Detailed analysis with constructive feedback and thorough validation
- **Security Mode**: Heightened security awareness with threat modeling considerations

## Detectors

**Detectors** are validation modules that analyze code content for policy violations. They implement the core enforcement mechanism that enables EgoKit to identify non-compliant code and provide remediation guidance.

### Detector Interface

All detectors implement a standard interface that accepts content and file path parameters:

```python
# .egokit/policy-registry/detectors/example.v1.py
def run(text: str, path: str) -> List[Dict[str, Any]]:
    """Analyze content for policy violations."""
    violations = []
    
    # Detection logic here
    if violation_detected:
        violations.append({
            "rule": "EXAMPLE-001",
            "level": "warning",
            "msg": "Description of violation",
            "span": (start_pos, end_pos)
        })
    
    return violations
```

### Built-in Detectors

EgoKit includes several built-in detectors for common policy requirements:

- **secret.regex.v1**: Detects hardcoded API keys, passwords, and authentication tokens
- **docs.style.superlatives.v1**: Identifies promotional language in technical documentation
- **docs.style.no_emoji.v1**: Finds emoji usage in technical content
- **python.ast.typehints.v1**: Validates type hint presence in Python functions

### Custom Detectors

Organizations can extend EgoKit with custom detectors that address specialized policy requirements. Custom detectors follow the same interface and integrate automatically with the policy engine.

## Artifact Compiler

The **Artifact Compiler** transforms policy configurations into AI agent-specific formats. This component enables EgoKit to support heterogeneous AI toolchains while maintaining a single source of policy truth.

### Compilation Process

1. **Policy Resolution**: Merge policies from applicable scopes according to precedence rules
2. **Agent Detection**: Identify AI agents used in the target repository 
3. **Format Translation**: Convert policies into agent-specific configuration formats
4. **Artifact Generation**: Write configuration files to appropriate locations

### Supported Agents

**Claude Code**: Generates comprehensive integration with 10+ artifacts:
- `CLAUDE.md` - Enhanced agent behavior calibration with policy rules and ego configuration
- `.claude/settings.json` - Policy-derived permissions, behavior settings, and automation configuration
- `.claude/commands/` - Custom slash commands for policy validation and mode switching
- `.claude/system-prompt-fragments/` - System prompt fragments for enhanced policy reinforcement

**AugmentCode**: Creates `.augment/rules/` directory with separate policy and behavioral rule files formatted according to AugmentCode's YAML frontmatter specification.

**Generic Output**: Produces `EGO.md` quick reference cards that developers can use with any AI agent as behavioral guidance.

### Extensibility

New AI agent support can be added by implementing compilation methods that transform EgoKit policies into the target agent's expected configuration format.

## Command Line Interface

The **CLI** provides operational commands for managing policy registries, generating artifacts, and validating code compliance.

### Core Commands

**ego init**: Initialize new policy registry with starter templates and organizational configuration. Creates complete directory structure with example policies and schemas.

**ego apply**: Apply organizational policies to development repositories by generating AI agent configuration artifacts. Supports dry-run mode for preview operations.

**ego validate**: Analyze code files against active policies and report violations. Supports changed file detection, specific file validation, and JSON output for CI integration.

**ego doctor**: Inspect effective policy configuration and ego settings. Displays scope resolution results and current behavioral configuration for debugging and verification.

**ego export-system-prompt**: Export system prompt fragments for Claude Code `--append-system-prompt` integration. Generates policy-aware context that can be appended to Claude Code headless mode operations.

**ego claude-headless**: Execute Claude Code in headless mode with automatic EgoKit policy context injection. Integrates with `--append-system-prompt` for policy-aware automated workflows.

**ego watch**: Monitor policy registry for changes and automatically sync Claude Code configurations across all projects in the workspace. Enables real-time policy updates without manual intervention.

### Configuration Sources

The CLI automatically discovers policy registries through multiple mechanisms:

1. **--registry** flag for explicit specification
2. **EGOKIT_REGISTRY** environment variable
3. **Local .egokit/policy-registry/ directory** in current working directory
4. **Git repository scanning** for .egokit/policy-registry/ directories in parent paths

## Policy Registry Structure

The **Policy Registry** organizes all EgoKit configuration in a standardized directory structure:

```
.egokit/policy-registry/
├── charter.yaml              # Main policy rules
├── ego/
│   ├── global.yaml          # Global ego configuration
│   ├── team/
│   │   └── backend.yaml     # Team-specific settings
│   └── project/
│       └── auth_service.yaml # Project-specific settings
├── schemas/
│   ├── charter.schema.json  # Charter validation schema
│   └── ego.schema.json      # Ego configuration schema
└── detectors/               # Custom detector modules
    └── custom_detector.v1.py
```

### Version Management

Policy registries support semantic versioning to track configuration evolution and ensure compatibility between EgoKit versions and policy definitions.

## Validation Framework

The **Validation Framework** coordinates policy enforcement through detector execution and violation reporting. This system provides the runtime policy evaluation that enables EgoKit to enforce organizational standards.

### Validation Process

1. **File Analysis**: Identify files requiring policy validation based on file types and modification status
2. **Detector Selection**: Load applicable detectors based on policy configuration and file characteristics
3. **Violation Detection**: Execute detectors against file content and collect violation reports
4. **Severity Assessment**: Categorize violations by severity level and determine enforcement actions
5. **Result Aggregation**: Compile validation results with file locations, rule IDs, and remediation guidance

### Integration Points

**Pre-commit Hooks**: Block commits containing critical policy violations before they reach the repository

**CI/CD Pipelines**: Validate pull requests and prevent policy violations from merging into main branches

**Development Environment**: Provide immediate feedback during development activities through editor integration and command-line validation

## Security Model

EgoKit implements defense-in-depth security through multiple validation layers and comprehensive policy enforcement mechanisms.

### Threat Prevention

**Credential Exposure**: Detectors identify hardcoded secrets, API keys, and authentication tokens before they reach version control systems

**Insecure Practices**: Policies enforce secure coding standards such as HTTPS usage, input validation, and proper error handling

**Compliance Violations**: Automated validation ensures code meets regulatory requirements and organizational security standards

### Audit Trail

All policy validations generate audit records that organizations can use for compliance reporting and security analysis. Violation patterns inform policy refinement and security training initiatives.

## Configuration Management

EgoKit policies are designed for collaborative management through standard development workflow practices.

### Version Control Integration

Policy registries integrate with Git workflows, enabling policy changes to follow the same review processes as code changes. Organizations can track policy evolution, revert problematic configurations, and coordinate policy updates across development teams.

### Collaborative Development

Multiple stakeholders can contribute to policy definition through pull request workflows. Security teams define security policies, architecture teams establish code quality standards, and documentation teams configure content requirements.

### Environment Consistency

Policy compilation ensures consistent AI agent behavior across development, staging, and production environments. The same policy source generates appropriate configurations for different deployment contexts.