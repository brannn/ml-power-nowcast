# Sample Project Directory

This directory represents a typical development project where you would run:

```bash
ego apply --registry ../.egokit/policy-registry
```

## What Gets Generated

When you run `ego apply` in your actual project, EgoKit will generate:

```
your-project/
├── CLAUDE.md            # Primary configuration (all AI agents)
├── .claude/
│   ├── settings.json   # Claude Code specific settings
│   ├── commands/       # Custom slash commands
│   │   ├── docs-review.md
│   │   └── checkpoint.md
│   └── system-prompt-fragments/
│       └── egokit-policies.txt
├── .augment/
│   └── rules/
│       ├── policy-rules.md
│       └── coding-style.md
└── EGO.md              # Human-readable summary
```

## How It Works

1. **Source Configuration** (in `.egokit/policy-registry/`):
   - You define documentation standards in `charter.yaml`
   - You configure AI behavior in `ego/global.yaml`

2. **Generation Process**:
   - EgoKit reads your policy registry
   - Compiles rules and ego settings
   - Generates tool-specific artifacts

3. **AI Agent Behavior**:
   - Agents read `CLAUDE.md` for primary configuration
   - Use tool-specific files for enhanced features
   - Follow the compiled rules and guidelines

## Example Effect

With the documentation-standards configuration:

**Before EgoKit:**
```markdown
## 🚀 Amazing Features!
This incredible tool is world-class! 
```

**After EgoKit:**
```markdown
## System Features
This tool provides automated processing with measured performance improvements.
```

## Testing the Configuration

1. Navigate to your actual project
2. Run `ego apply --registry path/to/examples/documentation-standards/.egokit/policy-registry`
3. Open the project in Claude Code or Cursor
4. Ask the AI to write documentation
5. Observe how it follows the standards

## Note

This directory is intentionally empty - it represents where YOUR project files would be. The actual generated artifacts should not be committed to the EgoKit repository, as they are specific to each project that uses EgoKit.