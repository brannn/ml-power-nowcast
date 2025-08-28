# Documentation Standards

This document establishes the writing standards and conventions for all documentation in the ML Power Nowcast project.

## Core Principles

Documentation serves to inform and educate users about the project's functionality, architecture, and usage. All written content should prioritize clarity, accuracy, and practical utility over promotional language or stylistic flourishes.

## Writing Style

### Tone and Voice

Use a concise and educational tone throughout all documentation. Focus on delivering factual explanations that help users understand concepts, procedures, and technical details. Avoid subjective language, marketing terminology, or promotional content.

### Language Guidelines

Avoid superlatives and self-promotional language. Terms such as "amazing," "incredible," "world-class," "cutting-edge," or similar promotional adjectives should not appear in technical documentation. Instead, use precise, descriptive language that accurately conveys functionality and capabilities.

Do not use emoji icons or decorative symbols in documentation. Technical documentation should maintain a professional appearance focused on content rather than visual embellishment.

### Structure and Format

Prefer prose and narrative explanations over excessive bullet points. While lists serve specific purposes for enumerating steps or options, most explanatory content should flow as coherent paragraphs that guide readers through concepts logically.

When bullet points are necessary, use them sparingly and only for:
- Sequential steps in procedures
- Lists of specific options or parameters
- Brief feature enumerations where prose would be unnecessarily verbose

### Technical Accuracy

All technical information must be accurate and verifiable. Include specific version numbers, exact command syntax, and precise configuration details. When describing system requirements or dependencies, provide complete information that enables users to replicate the described environment.

### Code Examples

Code examples should be complete and functional. Include necessary imports, configuration settings, and context that allows users to understand and execute the examples successfully. Provide explanatory text before and after code blocks to establish context and explain outcomes.

### Error Handling

Document common error conditions and their resolutions. Include actual error messages when possible, along with step-by-step troubleshooting procedures. This information helps users resolve issues independently.

## Content Organization

### Logical Flow

Organize information in a logical progression from general concepts to specific implementation details. Begin with overview information, proceed through setup and configuration, and conclude with advanced usage scenarios.

### Cross-References

Use clear cross-references to related sections or external resources. Avoid vague references like "as mentioned above" in favor of specific section titles or explicit links.

### Maintenance

Keep documentation current with code changes. When modifying functionality, update corresponding documentation in the same commit or pull request. Outdated documentation creates confusion and reduces user confidence in the project.

## File-Specific Guidelines

### README Files

README files should provide a clear project overview, installation instructions, and basic usage examples. Focus on getting users started quickly while providing enough context to understand the project's purpose and scope.

### API Documentation

API documentation requires complete parameter descriptions, return value specifications, and working examples for each endpoint or function. Include information about authentication, rate limiting, and error responses.

### Configuration Documentation

Configuration documentation must specify all available options, their data types, default values, and effects on system behavior. Provide examples of common configuration scenarios.

### Troubleshooting Guides

Troubleshooting documentation should address real problems encountered by users. Include diagnostic steps, common causes, and verified solutions. Organize troubleshooting information by symptom or error type for easy navigation.

## Review Process

All documentation changes should undergo review for technical accuracy, clarity, and adherence to these standards. Reviewers should verify that examples work as described and that instructions produce the expected results.

Documentation quality directly impacts user experience and project adoption. Maintaining high standards for written content reflects the same attention to detail applied to code quality and system design.
