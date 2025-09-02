# Claude Code Slash Commands Guide

EgoKit generates custom slash commands that integrate with Claude Code to maintain policy compliance and behavioral consistency throughout development sessions. These commands provide structured workflows for policy enforcement, mode switching, and periodic calibration checks.

## Command Overview

Claude Code slash commands are markdown files placed in the `.claude/commands/` directory of your repository. When you type `/` followed by the command name in Claude Code, the agent reads and executes the instructions contained in that command file. EgoKit generates these commands based on your organization's policy charter and ego configuration.

## Core Policy Commands

### /validate

Runs comprehensive policy validation against your codebase. This command executes the EgoKit validation engine to check all changed files against your organization's policy rules. The validation covers security standards, code quality requirements, and documentation guidelines as defined in your policy charter.

The command runs EgoKit validation to check only modified files, making it efficient for iterative development. (Internally uses `python3 -m egokit.cli validate --changed`, but users should run `ego validate --changed` directly.) After validation, it provides a detailed report of any policy violations found, including severity levels and suggested fixes.

### /compliance-check

Performs a broader compliance assessment across the entire codebase. Unlike validate which focuses on changed files, compliance-check examines the overall adherence to organizational standards. This includes checking for patterns that might indicate technical debt accumulation or systematic policy drift.

### /security-review

Switches Claude Code into heightened security analysis mode. When activated, the agent prioritizes security considerations in all responses, performs threat modeling for proposed changes, and validates against security best practices including OWASP guidelines. This mode is particularly useful when working on authentication, authorization, data handling, or any security-sensitive components.

## Behavioral Calibration Commands

### /refresh-policies

Re-reads and internalizes the latest policy configurations from CLAUDE.md and related files. This command prevents behavioral drift during long sessions by explicitly reloading the organizational constitution and standards. The agent performs a three-step refresh: re-reading core documents, validating recent compliance, and resetting behavioral calibration to match current configurations.

Use this command every 10-15 interactions or after completing major features to ensure consistent policy adherence throughout the session.

### /checkpoint

Creates a mental checkpoint of current policy awareness and compliance status. The agent reviews the last several interactions to verify that all responses have followed established patterns and policies. This lightweight check helps maintain consistency without the full overhead of refresh-policies.

### /periodic-refresh

A scheduled reminder command that prompts for policy refresh at regular intervals. This command establishes a maintenance routine during extended development sessions, ensuring that the agent's responses remain aligned with organizational standards even as context accumulates.

## Mode Switching Commands

Mode switching commands are generated dynamically based on your ego configuration. The available modes depend on what you've defined in your `.egokit/policy-registry/ego/global.yaml` file under the `modes:` section.

### Default Available Modes

The standard ego configuration includes these modes:

#### /mode-implementer

Switches to implementation-focused mode where the agent prioritizes clean, efficient code generation following established patterns. In this mode, responses emphasize practical implementation details, code organization, and adherence to project conventions. The verbosity adjusts to match the mode's configuration, typically providing balanced explanations focused on the code itself.

#### /mode-reviewer

Activates code review mode where the agent adopts a critical analysis perspective. Responses focus on identifying potential issues, suggesting improvements, and ensuring compliance with all quality standards. The agent examines code for security vulnerabilities, performance concerns, architectural consistency, and adherence to team conventions.

#### /mode-security

Engages specialized security analysis mode with heightened attention to vulnerability detection and threat modeling. The agent evaluates all code through a security lens, considering attack vectors, input validation, authentication flows, and data protection. This mode is essential when implementing security-critical features or reviewing sensitive code paths.

### Custom Modes

You can define additional modes in your ego configuration. Each mode you define will automatically generate a corresponding `/mode-{name}` slash command. See the `examples/ai-modes/` directory for examples of extended mode configurations including architect, debugger, educator, mentor, optimizer, prototyper, and documenter modes.

## Pre-Flight Commands

### /before-code

Executes a pre-code generation checklist to ensure all applicable policies are considered before writing new code. The agent identifies relevant policies for the task at hand, recalls constitutional articles that apply, recognizes existing patterns to follow, and establishes a validation plan for the generated code.

This systematic approach prevents policy violations before they occur, reducing the need for corrections and ensuring first-attempt compliance with organizational standards.

### /recall-policies

Performs an explicit policy recall without full refresh, useful when you need quick confirmation of specific standards or rules. The agent summarizes critical policies, current operational mode, and any special considerations active in the current context. This lightweight command helps maintain awareness without interrupting workflow.

## Integration with EgoKit

These slash commands work in conjunction with other EgoKit-generated artifacts. The CLAUDE.md file provides the persistent policy configuration that these commands reference and enforce. The settings.json file configures behavioral defaults that influence how commands execute. The system prompt fragments ensure that policy awareness persists even when commands are not explicitly invoked.

Commands automatically adapt to your organization's specific policies. When you run `ego apply` to generate Claude Code artifacts, the command files are customized with your actual policy IDs, rules, severity levels, and behavioral preferences. This ensures that slash commands enforce your specific standards rather than generic guidelines.

## Usage Patterns

Effective use of slash commands follows natural development workflows. Begin sessions with `/refresh-policies` to establish baseline compliance. Before implementing new features, run `/before-code` to activate relevant policies. After generating code, use `/validate` to check compliance. Switch modes as your focus changes between implementation, review, and security analysis. Periodically run `/checkpoint` or `/periodic-refresh` during long sessions to maintain consistency.

The commands are designed to be unobtrusive yet effective. They integrate naturally into development conversations without disrupting creative flow while ensuring that organizational standards are consistently maintained. The agent internalizes these commands as part of its operational protocol, often following their guidance even when not explicitly invoked.

## Customization

While EgoKit generates standard commands based on your policies, you can extend the command set by adding custom markdown files to the `.claude/commands/` directory. Custom commands should follow the same format: a descriptive title, usage instruction, detailed execution steps, and clear outcomes. Ensure custom commands align with and reinforce your organizational policies rather than contradicting them.

Commands can reference specific policy IDs from your charter, invoke external tools through bash execution, or establish multi-step workflows for complex compliance scenarios. The flexibility of the command system allows adaptation to unique organizational requirements while maintaining the consistency benefits of standardized policy enforcement.