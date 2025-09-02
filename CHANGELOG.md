# Changelog

All notable changes to EgoKit will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2025-01-09

### Added
- Fresh repository with clean commit history
- Complete project reinitialization

### Changed
- Repository restructured with single initial commit
- All previous development consolidated into clean state

## Previous Development

The project was developed iteratively with the following major milestones consolidated into v0.3.0:

### Added
- Multi-agent support with `--agent` CLI parameter for claude, augment, and cursor
- Cursor IDE integration with `.cursorrules` and MDC format (`.cursor/rules/*.mdc`)
- AugmentCode artifact generation with standardized method naming
- Comprehensive slash commands documentation in `docs/claude-slash-commands.md`
- Non-opinionated installation script `install-egokit.sh`
- Multi-agent test suite with 13 comprehensive tests
- `VERSIONING.md` documenting semantic versioning strategy
- `CHANGELOG.md` for tracking version history

### Changed
- Updated `refresh-policies` command to handle dependency installation automatically
- Improved documentation to follow strict standards (no emojis, no superlatives)
- Updated `.gitignore` to exclude `.egokit/` and `reference/` directories
- Migrated from deprecated Pydantic methods (`parse_obj` -> `model_validate`, `dict` -> `model_dump`)

### Removed
- Deprecated `sync` command (functionality moved to `apply`)
- Promotional language from documentation
- Emojis from all documentation files

### Fixed
- YAML serialization issues in test fixtures
- All test failures related to sync command removal
- Pydantic deprecation warnings throughout codebase

## [0.1.0] - 2024-01-08

### Added
- Initial release of EgoKit
- Policy registry system with hierarchical scopes
- Claude Code artifact generation (CLAUDE.md, .claude/ directory)
- CLI commands: init, apply, validate, doctor, export-system-prompt
- Policy charter and ego configuration schemas
- Comprehensive test suite
- Documentation and getting started guide

[0.2.0]: https://github.com/brannn/egokit/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/brannn/egokit/releases/tag/v0.1.0