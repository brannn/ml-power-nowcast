# Versioning Strategy

This document defines the semantic versioning strategy for EgoKit, establishing clear guidelines for version numbering, release management, and compatibility guarantees.

## Semantic Versioning

EgoKit follows Semantic Versioning 2.0.0 specification with version numbers structured as MAJOR.MINOR.PATCH:

- **MAJOR**: Incremented for incompatible API changes that require user intervention
- **MINOR**: Incremented for backward-compatible functionality additions
- **PATCH**: Incremented for backward-compatible bug fixes and minor improvements

## Version Progression

### Major Version (1.0.0, 2.0.0, etc.)

Major versions indicate breaking changes that require users to modify their existing configurations, commands, or integrations. Examples include:

- Removal or renaming of CLI commands
- Changes to policy charter schema that invalidate existing configurations
- Modifications to artifact output structure that break AI agent compatibility
- Alterations to the registry structure or discovery mechanism
- Breaking changes to the Python API for programmatic usage

### Minor Version (0.1.0, 0.2.0, etc.)

Minor versions introduce new functionality while maintaining backward compatibility. Examples include:

- Addition of new AI agent support (Claude, Cursor, AugmentCode)
- New CLI commands that don't affect existing workflows
- Additional policy rule types or detectors
- New configuration options with sensible defaults
- Performance improvements that don't alter behavior
- Extended artifact generation capabilities

### Patch Version (0.1.1, 0.1.2, etc.)

Patch versions address bugs, security issues, and minor improvements without adding functionality. Examples include:

- Bug fixes in policy validation logic
- Security patches for dependency vulnerabilities
- Documentation corrections and clarifications
- Performance optimizations without behavioral changes
- Minor output formatting improvements

## Pre-release Versions

Pre-release versions use the format MAJOR.MINOR.PATCH-PRERELEASE where PRERELEASE follows the pattern:

- **alpha.N**: Early development versions with unstable APIs
- **beta.N**: Feature-complete versions undergoing testing
- **rc.N**: Release candidates ready for final validation

Example progression: 0.2.0-alpha.1 → 0.2.0-alpha.2 → 0.2.0-beta.1 → 0.2.0-rc.1 → 0.2.0

## Version Management

### Source of Truth

The version number is maintained in `pyproject.toml` under the `[project]` section. This single source of truth ensures consistency across package distribution, documentation, and git tags.

### Git Tags

Each release receives a git tag with the format `v{VERSION}` where VERSION matches the pyproject.toml version. Tags are annotated with release notes summarizing changes.

Tag creation process:
```bash
# Update version in pyproject.toml
git add pyproject.toml
git commit -m "Bump version to X.Y.Z"

# Create annotated tag
git tag -a vX.Y.Z -m "Release version X.Y.Z

Summary of changes:
- Feature: Description
- Fix: Description
- Breaking: Description (if applicable)"

# Push tag to remote
git push origin vX.Y.Z
```

### Version Synchronization Requirements

**CRITICAL**: Git tags and pyproject.toml versions must always be synchronized. Failure to maintain this synchronization results in incorrect package versions and deployment issues.

**Required Process**:
1. **Update pyproject.toml first**: Change the version number in the `[project]` section
2. **Commit the version bump**: Create a dedicated commit for the version change
3. **Tag the version commit**: Apply the git tag to the commit containing the updated pyproject.toml
4. **Verify synchronization**: Ensure the git tag points to a commit where pyproject.toml matches the tag version

**Common Mistake - DO NOT DO**:
```bash
# ❌ WRONG: Tagging before updating pyproject.toml
git tag -a v1.2.3 -m "Release 1.2.3"    # pyproject.toml still says 1.2.2
git push origin v1.2.3                  # Package builds as 1.2.2, not 1.2.3
```

**Correct Process**:
```bash
# ✅ CORRECT: Update pyproject.toml first, then tag
sed -i 's/version = "1.2.2"/version = "1.2.3"/' pyproject.toml
git add pyproject.toml
git commit -m "Bump version to 1.2.3"
git tag -a v1.2.3 -m "Release version 1.2.3"
git push && git push origin v1.2.3
```

**Fixing Version Mismatch**:
If a tag was created before updating pyproject.toml:
```bash
# Delete incorrect tag
git tag -d v1.2.3
git push origin :refs/tags/v1.2.3

# Update pyproject.toml and commit
sed -i 's/version = "1.2.2"/version = "1.2.3"/' pyproject.toml  
git add pyproject.toml
git commit -m "Bump version to 1.2.3"

# Recreate tag on correct commit
git tag -a v1.2.3 -m "Release version 1.2.3"
git push origin v1.2.3
```

### Release Branch Strategy

Releases follow a simplified git flow:

- **main**: Current development branch containing the latest changes
- **release/X.Y**: Release branches for minor version series maintenance
- **hotfix/X.Y.Z**: Emergency patches to released versions

Major and minor releases originate from main. Patch releases may originate from release branches when maintaining previous minor versions.

## Compatibility Guarantees

### Within Major Versions

Users can upgrade between minor and patch versions within the same major version without modifying their configurations or workflows. Policy charters, ego configurations, and generated artifacts remain compatible.

### Across Major Versions

Major version upgrades may require:

- Migration of policy charters to new schemas
- Updates to CLI command invocations
- Regeneration of AI agent artifacts
- Modifications to custom detectors or extensions

Migration guides accompany major releases, detailing required changes and providing automated migration tools when feasible.

## Deprecation Policy

Features marked for removal follow a deprecation cycle:

1. **Deprecation Notice**: Feature marked as deprecated in minor release with warnings
2. **Grace Period**: Feature remains functional for at least one minor version
3. **Removal**: Feature removed in next major version

Deprecation warnings include migration instructions and alternative approaches.

## Version Discovery

Users can determine the installed version through multiple methods:

```bash
# CLI version command
ego --version

# Python package query
python -c "import egokit; print(egokit.__version__)"

# Package manager query
pip show egokit
```

## Release Cadence

EgoKit does not follow a fixed release schedule. Releases occur when:

- Critical security vulnerabilities require immediate patches
- Significant features reach maturity and stability
- Accumulated improvements warrant a new version
- Breaking changes necessitate a major version increment

Patch releases may occur frequently to address bugs. Minor releases typically occur monthly when new features are ready. Major releases are rare and carefully planned with extensive notice.

## Changelog Management

Each release includes a CHANGELOG.md entry following Keep a Changelog format with sections:

- **Added**: New features and capabilities
- **Changed**: Modifications to existing functionality
- **Deprecated**: Features marked for future removal
- **Removed**: Deleted features or capabilities
- **Fixed**: Bug fixes and corrections
- **Security**: Vulnerability patches and security improvements

## Version Support

Active support focuses on the latest minor version of the current major release. Previous minor versions receive security patches only. Previous major versions receive critical security patches for six months after the next major release.

Support matrix example:
- v1.2.x (Latest): Full support with features and fixes
- v1.1.x: Security patches only
- v1.0.x: Security patches only
- v0.x.x: End of life, no support

## Implementation Notes

Version checks in code should use tuple comparison for flexibility:

```python
from packaging import version

if version.parse(egokit.__version__) >= version.parse("1.2.0"):
    # Use new feature
else:
    # Fall back to legacy approach
```

Generated artifacts include version metadata to ensure compatibility between EgoKit and AI agents. Version mismatches trigger warnings but don't prevent operation unless breaking changes exist.