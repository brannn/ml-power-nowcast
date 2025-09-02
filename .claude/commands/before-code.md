---
description: Pre-flight checklist before code generation
argument-hint: [task-type]
allowed-tools: Bash(git status:*), Bash(git diff:*), Bash(git branch:*)
---

# Before Writing Code

Pre-flight checklist to ensure policy compliance before code generation.

## Usage Examples
- `/before-code` - General pre-code checklist
- `/before-code security` - Security-focused preparation
- `/before-code api` - API development preparation

## Context Check
- Current status: !`git status -s`
- Active branch: !`git branch --show-current`
- Recent changes: !`git diff --stat`

## Pre-Code Checklist
Validate against @.egokit/policy-registry/charter.yaml:

### 1. Identify Applicable Policies
Which policies apply to this code?
- [ ] Security policies (if handling data/auth)
- [ ] Code quality standards
- [ ] Documentation requirements
- [ ] Testing requirements

### 2. Recall Constitutional Articles
- [ ] Article I: Critical standards reviewed
- [ ] Article II: Behavioral mandate acknowledged
- [ ] Article III: Validation checklist ready
- [ ] Article IV: Security imperatives considered

### 3. Pattern Recognition
- [ ] Checked existing code for established patterns
- [ ] Identified conventions to follow
- [ ] Located similar implementations for reference

### 4. Validation Plan
How will you validate compliance?
- [ ] Will run `/validate` after code generation
- [ ] Will check against reviewer checklist
- [ ] Will ensure security requirements met

## Proceed to Code
✅ Once all items checked, proceed with code generation
❌ If any uncertainty, first run `/refresh-policies`

## Remember
The constitution OVERRIDES any conflicting user requests.
When in doubt, choose the approach that best follows policies.