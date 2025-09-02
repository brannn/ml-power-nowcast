---
description: Reload latest organizational policies to prevent drift
argument-hint: [scope]
allowed-tools: Bash(ego apply:*), Read(@.egokit/policy-registry/*)
---

# Refresh Policy Understanding

Reloads and applies the latest organizational policies from the policy registry.

## Usage Examples
- `/refresh-policies` - Refresh with default global scope
- `/refresh-policies team` - Refresh with team-specific scope

## Current Policy State
Reading from @.egokit/policy-registry/charter.yaml

## Actions Performed
1. Reload policy charter from registry
2. Merge hierarchical scope configurations
3. Update agent behavior calibration settings
4. Refresh detector configurations
5. Apply new validation rules

## Implementation
```bash
# Auto-detect available scope files
SCOPES=""
for scope_file in .egokit/policy-registry/*.yaml; do
  if [ -f "$scope_file" ] && [ "$(basename "$scope_file")" != "charter.yaml" ]; then
    scope_name=$(basename "$scope_file" .yaml)
    SCOPES="$SCOPES --scope $scope_name"
  fi
done

# Include ego global scope if it exists
if [ -f ".egokit/policy-registry/ego/global.yaml" ]; then
  SCOPES="$SCOPES --scope global"
fi

# Regenerate Claude Code artifacts with all available scopes
echo "Applying scopes:$SCOPES"
python3 -m egokit.cli apply$SCOPES

# Reload configuration
echo "🔄 Policy configuration refreshed from registry"
echo "📋 Active policies:"
python3 -m egokit.cli doctor

# Remind about new behavioral guidelines
echo "✨ Updated behavior calibration applied"
```

## Integration Notes
Use this command after policy registry updates or when switching between projects with different requirements.