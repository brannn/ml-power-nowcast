# Getting Started with EgoKit

This guide walks through setting up EgoKit to maintain consistent AI agent behavior across your development team. The system enforces your organization's coding standards and prevents quality drift through policy-driven configuration.

## Prerequisites

- Python 3.10 or later
- Git repository for your project
- AI coding agent (Claude Code, AugmentCode, Cursor, or similar)

## Installation

Clone and install EgoKit:

```bash
git clone https://github.com/brannn/egokit.git
cd egokit

# Quick install (uses your current Python environment)
./install-egokit.sh

# Or manual install
pip install -e ".[dev]"
```

Note: EgoKit respects your Python environment choices. Use whatever virtual environment, conda environment, or system Python configuration your team prefers.

Verify installation:

```bash
ego --help
```

## Understanding the EgoKit Workflow

EgoKit follows a clear separation between source configuration (what you write) and generated artifacts (what AI agents read):

```
WRITE (You) → COMPILE (EgoKit) → READ (AI Agents)

.egokit/policy-registry/  ego apply  CLAUDE.md
  charter.yaml    ───────────→    .claude/*
  ego/global.yaml                  .augment/*
                                   .cursor/*
                                   EGO.md
```

## Setting Up Your First Policy Registry

Initialize a new policy registry in your organization's central repository:

```bash
mkdir my-org-policies
cd my-org-policies
ego init --org "Acme Corporation"
```

This creates your source configuration structure:

```
.egokit/policy-registry/  # Your organization's standards (SOURCE)
├── charter.yaml         # Policy rules and detectors
├── ego/                 # AI agent behavior configuration
│   ├── global.yaml     # Organization-wide settings
│   └── teams/          # Team-specific overrides (optional)
└── schemas/            # Validation schemas
```

These files are:
- Your source of truth - Version controlled centrally
- Manually edited - You customize these for your standards
- Shared across teams - One registry for your organization

## Generating Artifacts for Your Project

Navigate to your development project and generate AI agent configuration files:

```bash
cd /path/to/your/project

# Generate for Claude Code (default)
ego apply --registry /path/to/my-org-policies/.egokit/policy-registry

# Generate for specific AI agents
ego apply --registry /path/to/my-org-policies/.egokit/policy-registry --agent claude
ego apply --registry /path/to/my-org-policies/.egokit/policy-registry --agent augment
ego apply --registry /path/to/my-org-policies/.egokit/policy-registry --agent cursor
```

This generates artifacts in your project:

```
your-project/             # Your development project
├── CLAUDE.md            # Claude Code configuration (--agent claude)
├── .claude/             # Claude Code specific files
│   ├── settings.json   # Permissions and behavior settings
│   ├── commands/       # Custom slash commands
│   └── system-prompt-fragments/  # System prompt additions
├── .augment/            # AugmentCode specific files (--agent augment)
│   └── rules/          # Policy and style rules
├── .cursorrules         # Cursor IDE legacy config (--agent cursor)
├── .cursor/             # Cursor IDE modern format
│   └── rules/          # MDC rule files with YAML frontmatter
└── EGO.md              # Quick reference for humans (all agents)
```

These files are:
- Generated output - Created by `ego apply`
- Tool-specific formats - Optimized for each AI tool
- Regenerated as needed - Run `ego apply` after policy updates

### Key Concept

- You maintain the policy registry (source)
- EgoKit compiles your policies into tool-specific formats
- AI agents consume the generated artifacts

## Multi-Agent Support

The `--agent` parameter allows you to generate artifacts for specific AI tools without cluttering your repository with unnecessary files. This is particularly useful when different team members use different AI assistants.

```bash
# Generate only Claude Code artifacts
ego apply --repo . --agent claude

# Generate only AugmentCode artifacts
ego apply --repo . --agent augment

# Generate only Cursor IDE artifacts
ego apply --repo . --agent cursor
```

Valid agent identifiers:
- `claude` - Claude Code by Anthropic
- `augment` - AugmentCode
- `cursor` - Cursor IDE

If no `--agent` is specified, the default is `claude`.

## Validating Code Against Policies

Run policy validation on your codebase:

```bash
# Validate changed files since last commit
ego validate --changed

# Validate specific files
ego validate src/main.py README.md

# Get detailed validation report
ego validate --all --format json
```

Critical violations prevent commits and CI builds. Warning violations provide guidance but do not block development.

## Setting Up Enforcement

### Pre-commit Integration

Add EgoKit validation to your pre-commit configuration:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: ego-policy
        name: EgoKit Policy Validation
        entry: ego validate --changed
        language: system
        pass_filenames: false
```

Install the pre-commit hook:

```bash
pre-commit install
```

### CI/CD Integration

Add policy validation to your continuous integration workflow:

```yaml
# .github/workflows/policy.yml
name: Policy Validation
on:
  pull_request:
    branches: [main, develop]

jobs:
  policy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      
      - uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      
      - name: Install EgoKit
        run: |
          git clone https://github.com/brannn/egokit.git
          cd egokit
          pip install -e .
      
      - name: Validate Policy Compliance
        run: ego validate --changed --format json
```

## Team Customization

Organizations can define team-specific policies by adding scope sections to the charter:

```yaml
# .egokit/policy-registry/charter.yaml
version: 1.0.0
scopes:
  global:
    # Global rules here
  
  teams:
    backend:
      code_quality:
        - id: BACK-001
          rule: "Use dependency injection for external services"
          severity: warning
          detector: python.dependency.injection.v1
    
    frontend:
      code_quality:
        - id: FRONT-001
          rule: "Components must include accessibility attributes"
          severity: critical
          detector: react.a11y.v1
```

Generate team-specific artifacts:

```bash
ego apply --scope global teams/backend --agent claude
```

## Inspecting Configuration

Use the doctor command to understand effective policy configuration:

```bash
ego doctor --scope global teams/backend projects/api
```

This shows which rules are active, their precedence resolution, and current ego settings.

## Maintaining Policy Awareness

After applying policies to your project, AI agents have access to multiple reinforcement mechanisms that maintain policy compliance throughout development sessions.

### Using Checkpoint Commands (Claude Code)

Claude Code users can leverage custom slash commands to maintain policy awareness:

```bash
# Run memory checkpoint every 10 interactions
/checkpoint

# Perform periodic refresh every 30 minutes
/periodic-refresh

# Test policy recall without looking at files
/recall-policies
```

### Pre-Code Validation (Claude Code)

Before generating code, ensure policy compliance:

```bash
# Run pre-flight checklist
/before-code

# This command verifies:
# - Applicable policies are identified
# - Constitutional articles are recalled
# - Validation plan is in place
```

### Switching Operational Modes (Claude Code)

Adjust AI agent focus while maintaining policy compliance:

```bash
# Security analysis mode
/mode-security

# Implementation mode
/mode-implementer

# Code review mode
/mode-reviewer
```

Note: Slash commands are specific to Claude Code. Other AI agents consume policy configuration through their respective artifact formats.

## Advanced Configuration

### Session Overrides

Temporarily modify agent behavior for specific tasks:

```bash
# Switch to security-focused mode for security review
ego ego set security

# Return to default mode
ego ego set implementer
```

### Custom Detectors

Extend EgoKit with organization-specific detectors by implementing the detector protocol and placing modules in your policy registry's detector directory.

## Troubleshooting

### Schema Validation Errors

Validate your YAML configuration against the provided schemas:

```bash
# Check charter format
jsonschema -i .egokit/policy-registry/charter.yaml .egokit/policy-registry/schemas/charter.schema.json

# Check ego format  
jsonschema -i .egokit/policy-registry/ego/global.yaml .egokit/policy-registry/schemas/ego.schema.json
```

### Detector Loading Issues

Verify detector modules exist and follow naming conventions. Detector names must follow the format `category.implementation.v1` and contain either a `Detector` class or `run` function.

### Permission Issues

Ensure write permissions for target directories when running `ego apply`. EgoKit creates the required directories if they do not exist.

### Git Integration Problems

For `--changed` file detection, ensure you are in a Git repository with committed changes. EgoKit uses `git diff --name-only` to identify modified files.

### Slash Command Dependencies

If Claude Code slash commands encounter missing dependencies, they will automatically attempt to install required packages. The `/refresh-policies` command handles virtual environment detection and dependency installation transparently.

## Next Steps

Once EgoKit is operational in your workflow:

1. Monitor policy violation metrics to identify noisy rules
2. Tune detector sensitivity based on false positive rates
3. Expand scope-specific configurations as teams define specialized requirements
4. Integrate with code review processes for policy compliance feedback

EgoKit provides the foundation for consistent, policy-driven AI-assisted development across your organization.