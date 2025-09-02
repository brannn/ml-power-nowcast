# EgoKit

As AI agents become core to software development, organizational memory becomes critical infrastructure. Yet AI coding assistants forget user-defined standards even within the same session, producing inconsistent code that drifts from established patterns. Teams waste hours re-explaining the same requirements while each developer trains their AI differently, creating fragmented codebases where AI-generated code doesn't match team conventions.

EgoKit is a framework and set of tools to keep your AI coding agents consistently on-track with your standards, preventing quality drift and ensuring they remember your preferences across all projects. It provides agent behavior calibration for development teams working with AI assistants like Claude Code, AugmentCode, Cursor, and other coding agents.

## Overview

EgoKit acts as an agent behavior compass, pointing your AI coding assistants in the right direction for every task. Define your coding standards, architectural preferences, and quality requirements once, then EgoKit ensures all your AI agents consistently apply them across every interaction.

The system prevents agents from forgetting your established patterns while maintaining the flexibility that makes AI coding assistants valuable for development productivity.

## Installation

EgoKit requires Python 3.10 or later.

```bash
# Clone the repository
git clone https://github.com/brannn/egokit.git
cd egokit

# Install using the script (respects your current Python environment)
./install-egokit.sh

# Or manual install
pip install -e ".[dev]"
```

## Quick Start

### Step 1: Create Your Policy Registry

Initialize a policy registry (your source of truth for standards):

```bash
ego init --org "Acme Corp"
```

This creates the policy registry structure:
```
.egokit/policy-registry/  # Your organization's standards (SOURCE)
├── charter.yaml         # Policy rules and detectors
├── ego/                 # AI agent behavior configuration
│   ├── global.yaml     # Organization-wide settings
│   └── teams/          # Team-specific overrides
└── schemas/            # Validation schemas
```

### Step 2: Customize Your Policies

Edit the policy registry files to define your standards:

```yaml
# .egokit/policy-registry/charter.yaml - Define enforcement rules
version: 1.0.0
scopes:
  global:
    security:
      - id: SEC-001
        rule: "Never commit credentials or secrets"
        severity: critical
        detector: secret.regex.v1
```

```yaml
# .egokit/policy-registry/ego/global.yaml - Configure AI behavior
version: 1.0.0
ego:
  role: "Senior Software Engineer"
  tone:
    voice: "professional, precise, helpful"
```

### Step 3: Generate Artifacts for Your Projects

Apply policies to generate AI agent configuration files:

```bash
# Generate artifacts for Claude Code (default)
ego apply --repo /path/to/your/project

# Generate artifacts for specific agents
ego apply --repo /path/to/your/project --agent claude    # Claude Code
ego apply --repo /path/to/your/project --agent augment   # AugmentCode
ego apply --repo /path/to/your/project --agent cursor    # Cursor IDE
```

This generates artifacts in your project (GENERATED OUTPUT):

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
└── EGO.md               # Quick reference for humans (all agents)
```

### Understanding the Structure

**Source Configuration (What You Write):**
- `.egokit/policy-registry/` - Your centralized source of truth
  - `charter.yaml` - Defines rules, severity, and detectors
  - `ego/global.yaml` - Configures AI agent behavior
  - `ego/teams/*.yaml` - Team-specific overrides
- Version controlled and shared across organization
- Modified manually by your team

**Generated Artifacts (What EgoKit Creates):**
- `CLAUDE.md` - Primary agent configuration file
  - Combines charter rules + ego configuration
  - Read by Claude Code, Cursor, and other AI agents
  - Contains behavioral guidelines and policy rules
- `.claude/` - Claude Code specific enhancements
- `.augment/` - AugmentCode specific format
- `EGO.md` - Human-readable summary (optional)

**Key Concept:** You maintain the policy registry, EgoKit generates the artifacts that AI agents consume.

## Configuration

### Policy Rules

Policy rules define enforceable standards with four severity levels:

- `critical` - Blocks commits and CI builds
- `warning` - Provides feedback but does not block
- `info` - Informational guidance only

Each rule specifies a detector module that implements the validation logic. EgoKit includes built-in detectors for common requirements like secret detection and documentation standards.

### Scope Hierarchy

EgoKit supports hierarchical configuration with precedence ordering:

```
global < team < project < user < session
```

Later scopes override earlier ones when rule IDs match. This enables organization-wide standards with team-specific customizations and individual developer preferences.

### Agent Behavior Calibration

The ego layer fine-tunes agent responses to match your organizational standards. Configure communication style, verbosity preferences, and operational modes to ensure consistent agent behavior that aligns with your team's working style across all interactions.

### Claude Code Integration

EgoKit generates custom slash commands that integrate directly with Claude Code, providing powerful workflow controls:

```bash
# Policy enforcement commands
/validate              # Run comprehensive policy validation
/security-review       # Switch to heightened security analysis mode
/compliance-check      # Assess overall standards adherence

# Behavioral calibration commands  
/refresh-policies      # Reload latest configurations to prevent drift
/checkpoint           # Validate policy recall and compliance status
/before-code          # Pre-flight checklist before code generation

# Mode switching (based on your ego configuration)
/mode-implementer     # Focus on clean, efficient implementation
/mode-reviewer        # Critical analysis and improvement suggestions  
/mode-security        # Security-first evaluation and threat modeling
```

These commands maintain consistent agent behavior throughout development sessions. The `/refresh-policies` command prevents drift by reloading your organizational standards every 10-15 interactions. The `/before-code` checklist ensures compliance before any code generation, while mode switching adapts the agent's focus to match your current development context.

### Memory Persistence Mechanisms

EgoKit employs multiple reinforcement strategies to ensure AI agents maintain policy awareness throughout their sessions. The system injects organizational policies through system prompt fragments that establish constitutional constraints, making policies take precedence over conflicting requests. Custom slash commands provide interactive checkpoints for memory validation and policy refresh at regular intervals. Redundant policy documents placed strategically across the project directory create multiple touchpoints for policy reinforcement.

These mechanisms work together to prevent drift: the `/checkpoint` command validates policy recall every 10 interactions, `/periodic-refresh` reloads configurations every 30 minutes, and `/before-code` ensures compliance before any code generation. The system prompt fragments frame policies as inviolable principles that guide all agent responses, while CLAUDE.md serves as the primary configuration file and .claude/settings.json enforces behavioral boundaries.

## Usage

### Generate Artifacts

```bash
# Apply policy artifacts to current directory
ego apply

# Apply to specific repository
ego apply --repo /path/to/project

# Apply for specific AI agent
ego apply --agent claude    # Claude Code artifacts
ego apply --agent augment   # AugmentCode artifacts
ego apply --agent cursor    # Cursor IDE artifacts

# Preview without writing files
ego apply --dry-run --agent cursor
```

### Validate Code

```bash
# Validate changed files
ego validate --changed

# Validate specific files
ego validate src/main.py docs/api.md

# Validate all files in repository
ego validate --all

# Output JSON for CI integration
ego validate --changed --format json
```

### Inspect Configuration

```bash
# Show effective policy configuration
ego doctor

# Display current ego settings
ego doctor --scope global team/backend
```

## Integration

### Pre-commit Hooks

Add validation to your pre-commit configuration:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: ego-validate
        name: EgoKit Policy Validation
        entry: ego validate --changed --format json
        language: system
        pass_filenames: false
        always_run: true
```

### CI/CD Integration

Include policy validation in your GitHub Actions workflow:

```yaml
# .github/workflows/policy.yml
name: Policy Validation
on: [pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      
      - uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      
      - name: Install EgoKit
        run: pip install egokit
      
      - name: Validate Policy Compliance
        run: ego validate --changed --format json
```

## Architecture

EgoKit consists of four core components:

1. **Policy Registry** - YAML-based configuration with JSON Schema validation
2. **Scope Merger** - Hierarchical rule resolution with conflict handling
3. **Artifact Compiler** - Generates agent-specific configuration files
4. **Detector Framework** - Pluggable validation modules for policy enforcement

The system operates entirely through file-based configuration, enabling version control integration and collaborative policy management.

## Extending EgoKit

### Custom Detectors

Create custom detectors by implementing the detector protocol:

```python
from pathlib import Path
from typing import List
from egokit.detectors.base import DetectorBase
from egokit.models import DetectionResult, Severity

class CustomDetector(DetectorBase):
    def can_handle_file(self, file_path: Path) -> bool:
        return file_path.suffix == '.py'
    
    def detect_violations(self, content: str, file_path: Path) -> List[DetectionResult]:
        violations = []
        # Implementation here
        return violations
```

### Adding Agent Support

EgoKit generates artifacts for specific AI coding tools. To add support for a new agent, extend the `ArtifactCompiler` class with a new compilation method that formats policies and ego configuration according to the target agent's expected input format.

## Troubleshooting

### Common Issues

**Schema validation errors**: Verify your YAML syntax matches the provided JSON schemas in `.egokit/policy-registry/schemas/`. Use a YAML validator to check for syntax errors before running EgoKit commands.

**Detector loading failures**: Ensure detector modules exist in the expected location and implement the required interface. Check the detector name format follows the `name.version.v1` convention.

**Scope resolution errors**: Verify scope names in your precedence list match the scope keys defined in your charter configuration. Scope names are case-sensitive.

**Permission errors during apply**: Ensure write permissions for the target repository directory. EgoKit creates directories and files as needed during artifact injection.

### Troubleshooting Commands

Preview changes and inspect configuration:

```bash
ego apply --dry-run  # Preview generated artifacts without writing files
ego doctor          # Show effective policy configuration and scope resolution
```

### Getting Help

For additional support or to report issues, consult the project documentation or file an issue in the project repository.