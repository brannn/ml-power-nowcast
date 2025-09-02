# Team Scopes Example

This example demonstrates EgoKit's hierarchical scope system, showing how different teams can have customized policies while maintaining organizational standards.

## Overview

EgoKit supports multiple configuration scopes with clear precedence:

```
global < teams/backend < teams/frontend < projects/api < users/alice < session
```

Later scopes override earlier ones, allowing teams to customize while staying within organizational boundaries.

## Scope Hierarchy Demonstrated

### 1. Global Scope
Organization-wide standards that apply to everyone:
- Security fundamentals
- Documentation requirements
- Code quality baselines

### 2. Team Scopes
Team-specific customizations:
- **Backend Team**: API standards, database patterns, service architecture
- **Frontend Team**: UI/UX guidelines, accessibility, component patterns
- **Mobile Team**: Platform-specific rules, performance requirements
- **Data Team**: Data governance, privacy, ML practices

### 3. Project Scopes
Project-specific overrides:
- **API Project**: Stricter versioning, OpenAPI requirements
- **Admin Dashboard**: Enhanced security, audit logging
- **Public Website**: SEO requirements, performance budgets

### 4. User Scopes
Individual developer preferences:
- Personal coding style (within team standards)
- Preferred verbosity levels
- Custom tool configurations

## Directory Structure

```
.egokit/policy-registry/
├── charter.yaml                    # All scope definitions
├── ego/
│   ├── global.yaml                # Organization-wide ego config
│   ├── teams/
│   │   ├── backend.yaml          # Backend team overrides
│   │   ├── frontend.yaml         # Frontend team overrides
│   │   ├── mobile.yaml           # Mobile team overrides
│   │   └── data.yaml             # Data team overrides
│   ├── projects/
│   │   ├── api.yaml              # API project specific
│   │   ├── admin.yaml            # Admin dashboard specific
│   │   └── website.yaml          # Public website specific
│   └── users/
│       ├── alice.yaml            # Alice's preferences
│       └── bob.yaml              # Bob's preferences
└── schemas/                       # Validation schemas
```

## Usage Examples

### Apply Team Configuration

```bash
# Backend developer working on API
ego apply --scope global teams/backend projects/api

# Frontend developer on public website
ego apply --scope global teams/frontend projects/website

# Mobile developer with personal preferences
ego apply --scope global teams/mobile users/alice
```

### Validate with Scope Precedence

```bash
# Check which rules apply for backend team
ego doctor --scope global teams/backend

# See full resolution for specific developer
ego doctor --scope global teams/frontend users/bob
```

## Example: Backend Team Configuration

### Global Rules (Base)
```yaml
- id: GLOB-001
  rule: "Use descriptive variable names"
  severity: warning
```

### Backend Team Override
```yaml
- id: BACK-001
  rule: "Use dependency injection for all services"
  severity: critical
  
- id: BACK-002
  rule: "Document all API endpoints with OpenAPI"
  severity: critical
  
- id: GLOB-001  # Override global rule
  rule: "Use descriptive variable names following team conventions"
  severity: critical  # Elevated from warning
```

### Result for Backend Team
- GLOB-001 becomes critical (not warning)
- BACK-001 and BACK-002 are added
- Other global rules still apply

## Example: Frontend Team Configuration

### Additional Frontend Rules
```yaml
- id: FRONT-001
  rule: "Components must include accessibility attributes"
  severity: critical
  
- id: FRONT-002
  rule: "Use CSS-in-JS for component styling"
  severity: warning
  
- id: FRONT-003
  rule: "Implement responsive design breakpoints"
  severity: critical
```

### Frontend Ego Configuration
```yaml
ego:
  role: "Frontend Developer"
  tone:
    voice: "user-focused, accessible"
  defaults:
    component_pattern: "Functional components with hooks"
    styling: "CSS-in-JS with theme support"
    testing: "Component testing with user interactions"
```

## Scope Resolution Examples

### Scenario 1: Backend Developer on API Project

Command: `ego apply --scope global teams/backend projects/api`

Active Rules:
1. All global rules (base)
2. Backend team rules (override/extend global)
3. API project rules (override/extend backend)

### Scenario 2: New Developer Onboarding

Command: `ego apply --scope global teams/frontend`

Gets:
- Organization standards
- Team conventions
- No personal customizations yet

### Scenario 3: Cross-Team Collaboration

Frontend developer helping backend:
```bash
ego apply --scope global teams/backend --dry-run
```
Temporarily adopts backend team standards

## Benefits of Hierarchical Scopes

### For Organizations
- Consistent baseline standards
- Team autonomy within boundaries
- Gradual rollout of new policies
- Clear governance structure

### For Teams
- Customize for specific needs
- Share configurations easily
- Maintain team identity
- Evolve practices independently

### For Developers
- Personal preferences respected
- Context-aware configurations
- Smooth team transitions
- Clear expectations

## Managing Scope Conflicts

### Rule Precedence
When the same rule ID appears in multiple scopes:
- Later scope wins completely
- No merging of rule properties
- Clear override semantics

### Example Conflict Resolution
```yaml
# Global scope
- id: SEC-001
  severity: warning
  auto_fix: false

# Team scope (wins)
- id: SEC-001
  severity: critical
  auto_fix: true
```

Result: SEC-001 is critical with auto_fix enabled

## Best Practices

### 1. Start Conservative
Begin with strict global rules, relax in team scopes if needed

### 2. Document Overrides
Always explain why a team overrides a global rule

### 3. Regular Review
Audit scope configurations quarterly for drift

### 4. Promote Good Patterns
Move successful team rules to global scope

### 5. Limit User Scopes
User preferences should be minimal, mostly style

## Testing Scope Configurations

### Validate Each Scope Level
```bash
# Test global only
ego validate test-files/ --scope global

# Test with team scope
ego validate test-files/ --scope global teams/backend

# Test full stack
ego validate test-files/ --scope global teams/backend projects/api users/alice
```

### Preview Scope Resolution
```bash
# See what configuration would be applied
ego apply --dry-run --scope global teams/frontend projects/website
```

## Migration Strategy

### Rolling Out Team Scopes

1. **Phase 1**: Global scope only
   - Establish baseline standards
   - Get organizational buy-in

2. **Phase 2**: Team scopes
   - Let teams define their needs
   - Pilot with one team first

3. **Phase 3**: Project scopes
   - For special requirements
   - Temporary experiments

4. **Phase 4**: User scopes
   - Optional personal preferences
   - Monitor for anti-patterns

## Advanced Scenarios

### Temporary Scope Override
```bash
# Use different team's standards for code review
EGO_SCOPE="global teams/backend" ego validate

# Session-specific override
export EGO_SESSION_SCOPE="strict-review"
```

### Cross-Team Projects
```yaml
# projects/shared-lib.yaml
# Combines requirements from multiple teams
inherit_from:
  - teams/backend
  - teams/frontend
additional_rules:
  - id: SHARED-001
    rule: "Must work in both Node.js and browser"
```

### Scope Inheritance Chains
```yaml
# teams/backend-senior.yaml
inherit: teams/backend
overrides:
  - stricter_reviews: true
  - require_performance_tests: true
```

## Monitoring Scope Usage

Track which scopes are active:
- Include scope in commit messages
- Log scope in CI/CD pipelines
- Monitor rule violation patterns by scope
- Identify scope-specific pain points

## Next Steps

1. Design your organization's scope hierarchy
2. Start with global + one team scope
3. Document scope precedence clearly
4. Train teams on scope selection
5. Iterate based on feedback