"""
Test suite for multi-agent support in EgoKit.

This module tests the --agent CLI parameter functionality and ensures
that agent-specific artifacts are generated correctly for Claude Code,
AugmentCode, and Cursor IDE.
"""

import json
import tempfile
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, patch, MagicMock

import pytest
import yaml
from typer.testing import CliRunner

from egokit.cli import app
from egokit.compiler import ArtifactCompiler
from egokit.models import (
    PolicyCharter,
    ScopeRules,
    PolicyRule,
    Severity,
    EgoCharter,
    EgoConfig,
    ToneConfig,
    CompilationContext,
)


@pytest.fixture
def sample_charter() -> PolicyCharter:
    """Create a sample charter for testing."""
    return PolicyCharter(
        version="1.0.0",
        scopes={
            "global": ScopeRules(
                security=[
                    PolicyRule(
                        id="SEC-001",
                        rule="Never commit credentials or secrets",
                        severity=Severity.CRITICAL,
                        detector="secret.regex.v1",
                    )
                ],
                code_quality=[
                    PolicyRule(
                        id="QUAL-001",
                        rule="Use type hints for all function parameters",
                        severity=Severity.WARNING,
                        detector="python.typehints.v1",
                    )
                ],
                documentation=[
                    PolicyRule(
                        id="DOC-001",
                        rule="All functions must have docstrings",
                        severity=Severity.INFO,
                        detector="python.docstring.v1",
                    )
                ],
            )
        },
    )


@pytest.fixture
def sample_ego_config() -> EgoCharter:
    """Create a sample ego configuration for testing."""
    return EgoCharter(
        version="1.0.0",
        ego=EgoConfig(
            role="Senior Software Engineer",
            tone=ToneConfig(
                voice="professional, precise, helpful",
                verbosity="concise",
            ),
        ),
    )


@pytest.fixture
def temp_workspace(sample_charter: PolicyCharter, sample_ego_config: EgoCharter) -> Path:
    """Create a temporary workspace with policy registry."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        
        # Create policy registry structure
        registry_dir = workspace / ".egokit" / "policy-registry"
        registry_dir.mkdir(parents=True)
        
        # Write charter (convert to dict with mode='json' to serialize enums properly)
        charter_path = registry_dir / "charter.yaml"
        # Use mode='json' to convert all enums to their string values
        charter_dict = sample_charter.model_dump(mode='json')
        charter_path.write_text(yaml.dump(charter_dict))
        
        # Write ego config (convert to dict with mode='json' for proper serialization)
        ego_dir = registry_dir / "ego"
        ego_dir.mkdir()
        ego_config_path = ego_dir / "global.yaml"
        ego_config_path.write_text(yaml.dump(sample_ego_config.model_dump(mode='json')))
        
        # Create minimal schema files (required by PolicyRegistry)
        schemas_dir = registry_dir / "schemas"
        schemas_dir.mkdir()
        
        # Minimal charter schema
        charter_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "version": {"type": "string"},
                "scopes": {"type": "object"}
            },
            "required": ["version", "scopes"]
        }
        (schemas_dir / "charter.schema.json").write_text(json.dumps(charter_schema))
        
        # Minimal ego schema
        ego_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "version": {"type": "string"},
                "ego": {"type": "object"}
            },
            "required": ["version", "ego"]
        }
        (schemas_dir / "ego.schema.json").write_text(json.dumps(ego_schema))
        
        yield workspace


class TestMultiAgentCLI:
    """Test the multi-agent CLI functionality."""
    
    def test_claude_agent_selection(self, temp_workspace: Path) -> None:
        """Test that --agent claude generates Claude-specific artifacts."""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            project_dir = Path.cwd()
            
            # Run apply with claude agent
            result = runner.invoke(
                app,
                [
                    "apply",
                    "--registry", str(temp_workspace / ".egokit" / "policy-registry"),
                    "--repo", str(project_dir),
                    "--agent", "claude",
                    "--dry-run",
                ],
            )
            
            if result.exit_code != 0:
                print(f"CLI failed with output: {result.output}")
            assert result.exit_code == 0
            assert "Claude Code" in result.output or "claude" in result.output.lower()
            assert "CLAUDE.md" in result.output
            assert ".augment" not in result.output
            assert ".cursor" not in result.output
    
    def test_augment_agent_selection(self, temp_workspace: Path) -> None:
        """Test that --agent augment generates AugmentCode-specific artifacts."""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            project_dir = Path.cwd()
            
            # Run apply with augment agent
            result = runner.invoke(
                app,
                [
                    "apply",
                    "--registry", str(temp_workspace / ".egokit" / "policy-registry"),
                    "--repo", str(project_dir),
                    "--agent", "augment",
                    "--dry-run",
                ],
            )
            
            assert result.exit_code == 0
            assert "AugmentCode" in result.output
            assert ".augment/rules" in result.output
            assert ".claude" not in result.output
            assert ".cursor" not in result.output
    
    def test_cursor_agent_selection(self, temp_workspace: Path) -> None:
        """Test that --agent cursor generates Cursor-specific artifacts."""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            project_dir = Path.cwd()
            
            # Run apply with cursor agent
            result = runner.invoke(
                app,
                [
                    "apply",
                    "--registry", str(temp_workspace / ".egokit" / "policy-registry"),
                    "--repo", str(project_dir),
                    "--agent", "cursor",
                    "--dry-run",
                ],
            )
            
            assert result.exit_code == 0
            assert "Cursor" in result.output
            assert ".cursorrules" in result.output or ".cursor/rules" in result.output
            assert ".claude" not in result.output
            assert ".augment" not in result.output
    
    def test_invalid_agent_selection(self, temp_workspace: Path) -> None:
        """Test that invalid agent names are rejected."""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            project_dir = Path.cwd()
            
            # Run apply with invalid agent
            result = runner.invoke(
                app,
                [
                    "apply",
                    "--registry", str(temp_workspace / ".egokit" / "policy-registry"),
                    "--repo", str(project_dir),
                    "--agent", "invalid_agent",
                    "--dry-run",
                ],
            )
            
            assert result.exit_code != 0
            assert "Invalid agent" in result.output or "must be one of" in result.output
    
    def test_default_agent_is_claude(self, temp_workspace: Path) -> None:
        """Test that the default agent is Claude when not specified."""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            project_dir = Path.cwd()
            
            # Run apply without agent parameter
            result = runner.invoke(
                app,
                [
                    "apply",
                    "--registry", str(temp_workspace / ".egokit" / "policy-registry"),
                    "--repo", str(project_dir),
                    "--dry-run",
                ],
            )
            
            assert result.exit_code == 0
            assert "Claude Code" in result.output or "CLAUDE.md" in result.output


class TestArtifactCompiler:
    """Test the ArtifactCompiler for agent-specific compilation."""
    
    def test_compile_claude_artifacts(
        self, sample_charter: PolicyCharter, sample_ego_config: EgoCharter
    ) -> None:
        """Test Claude artifact compilation."""
        context = CompilationContext(
            target_repo=Path("/tmp/test"),
            policy_charter=sample_charter,
            ego_config=sample_ego_config.ego,
        )
        compiler = ArtifactCompiler(context)
        artifacts = compiler.compile_claude_artifacts()
        
        # Check CLAUDE.md is generated
        assert "CLAUDE.md" in artifacts
        assert "MANDATORY CONFIGURATION" in artifacts["CLAUDE.md"]
        assert "Agent Behavior Calibration" in artifacts["CLAUDE.md"]
        
        # Check .claude/settings.json
        assert ".claude/settings.json" in artifacts
        settings = json.loads(artifacts[".claude/settings.json"])
        assert "permissions" in settings
        # Note: scopedPermissions may not be in the base configuration
    
    def test_compile_augment_artifacts(
        self, sample_charter: PolicyCharter, sample_ego_config: EgoCharter
    ) -> None:
        """Test AugmentCode artifact compilation."""
        context = CompilationContext(
            target_repo=Path("/tmp/test"),
            policy_charter=sample_charter,
            ego_config=sample_ego_config.ego,
        )
        compiler = ArtifactCompiler(context)
        
        # Test the standardized AugmentCode compilation method
        artifacts = compiler.compile_augment_artifacts()
        
        # Check that artifacts are generated
        assert ".augment/rules/policy-rules.md" in artifacts
        assert ".augment/rules/coding-style.md" in artifacts
        assert ".augment/rules/guidelines.md" in artifacts
        
        # Check policy rules content
        policy_content = artifacts[".augment/rules/policy-rules.md"]
        assert len(policy_content) > 0
        assert "Never commit credentials or secrets" in policy_content  # Our SEC-001 rule text
        assert "Use type hints for all function parameters" in policy_content  # Our QUAL-001 rule text
        
        # Check coding style content
        ego_content = artifacts[".augment/rules/coding-style.md"]
        assert len(ego_content) > 0
        assert "senior software engineer" in ego_content.lower()  # Our test role
    
    def test_compile_cursor_artifacts(
        self, sample_charter: PolicyCharter, sample_ego_config: EgoCharter
    ) -> None:
        """Test Cursor artifact compilation."""
        context = CompilationContext(
            target_repo=Path("/tmp/test"),
            policy_charter=sample_charter,
            ego_config=sample_ego_config.ego,
        )
        compiler = ArtifactCompiler(context)
        artifacts = compiler.compile_cursor_artifacts()
        
        # Check .cursorrules is generated
        assert ".cursorrules" in artifacts
        rules_content = artifacts[".cursorrules"]
        # Basic content check
        assert len(rules_content) > 0
        
        # Check MDC rules are generated
        mdc_rules = [k for k in artifacts if ".cursor/rules" in k and k.endswith(".mdc")]
        assert len(mdc_rules) > 0
        
        # Verify MDC format with frontmatter
        for mdc_path in mdc_rules:
            content = artifacts[mdc_path]
            assert content.startswith("---")
            assert "title:" in content
            assert "priority:" in content
            assert "---" in content[3:]  # Second frontmatter delimiter
    
    def test_cursor_mdc_frontmatter_format(
        self, sample_charter: PolicyCharter, sample_ego_config: EgoCharter
    ) -> None:
        """Test that Cursor MDC files have correct frontmatter format."""
        context = CompilationContext(
            target_repo=Path("/tmp/test"),
            policy_charter=sample_charter,
            ego_config=sample_ego_config.ego,
        )
        compiler = ArtifactCompiler(context)
        artifacts = compiler.compile_cursor_artifacts()
        
        # Find an MDC file
        mdc_files = [k for k in artifacts if k.endswith(".mdc")]
        assert len(mdc_files) > 0
        
        for mdc_file in mdc_files:
            content = artifacts[mdc_file]
            lines = content.split("\n")
            
            # Check frontmatter delimiters
            assert lines[0] == "---"
            
            # Find end of frontmatter
            end_idx = -1
            for i, line in enumerate(lines[1:], 1):
                if line == "---":
                    end_idx = i
                    break
            
            assert end_idx > 0, "Frontmatter must be properly closed"
            
            # Parse frontmatter
            frontmatter_lines = lines[1:end_idx]
            frontmatter_text = "\n".join(frontmatter_lines)
            frontmatter = yaml.safe_load(frontmatter_text)
            
            # Verify required fields
            assert "title" in frontmatter
            assert "priority" in frontmatter
            # Priority can be string ("high") or int
            assert "priority" in frontmatter
    
    def test_agent_specific_ego_card(
        self, sample_charter: PolicyCharter, sample_ego_config: EgoCharter
    ) -> None:
        """Test that EGO.md is generated for all agents."""
        context = CompilationContext(
            target_repo=Path("/tmp/test"),
            policy_charter=sample_charter,
            ego_config=sample_ego_config.ego,
        )
        compiler = ArtifactCompiler(context)
        
        # Test Claude
        claude_artifacts = compiler.compile_claude_artifacts()
        ego_card = compiler.compile_ego_card()
        assert ego_card is not None
        assert "Ego Configuration" in ego_card or "Role:" in ego_card
        
        # Test Augment (using the standardized method)
        augment_artifacts = compiler.compile_augment_artifacts()
        assert augment_artifacts is not None
        assert len(augment_artifacts) > 0
        
        # Test Cursor
        cursor_artifacts = compiler.compile_cursor_artifacts()
        assert cursor_artifacts is not None


class TestAgentIntegration:
    """Integration tests for multi-agent support."""
    
    def test_end_to_end_claude_workflow(self, temp_workspace: Path) -> None:
        """Test complete Claude workflow from CLI to artifact generation."""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            project_dir = Path.cwd()
            
            # Apply policies for Claude
            result = runner.invoke(
                app,
                [
                    "apply",
                    "--registry", str(temp_workspace / ".egokit" / "policy-registry"),
                    "--repo", str(project_dir),
                    "--agent", "claude",
                ],
            )
            
            assert result.exit_code == 0
            
            # Verify files were created
            assert (project_dir / "CLAUDE.md").exists()
            assert (project_dir / ".claude" / "settings.json").exists()
            assert (project_dir / "EGO.md").exists()
            
            # Verify no other agent artifacts
            assert not (project_dir / ".augment").exists()
            assert not (project_dir / ".cursorrules").exists()
            assert not (project_dir / ".cursor").exists()
    
    def test_end_to_end_cursor_workflow(self, temp_workspace: Path) -> None:
        """Test complete Cursor workflow from CLI to artifact generation."""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            project_dir = Path.cwd()
            
            # Apply policies for Cursor
            result = runner.invoke(
                app,
                [
                    "apply",
                    "--registry", str(temp_workspace / ".egokit" / "policy-registry"),
                    "--repo", str(project_dir),
                    "--agent", "cursor",
                ],
            )
            
            assert result.exit_code == 0
            
            # Verify files were created
            assert (project_dir / ".cursorrules").exists()
            assert (project_dir / ".cursor" / "rules").exists()
            assert (project_dir / "EGO.md").exists()
            
            # Verify MDC files
            mdc_files = list((project_dir / ".cursor" / "rules").glob("*.mdc"))
            assert len(mdc_files) > 0
            
            # Verify no other agent artifacts
            assert not (project_dir / "CLAUDE.md").exists()
            assert not (project_dir / ".claude").exists()
            assert not (project_dir / ".augment").exists()
    
    def test_agent_switching(self, temp_workspace: Path) -> None:
        """Test switching between different agents in the same project."""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            project_dir = Path.cwd()
            
            # First apply Claude
            result = runner.invoke(
                app,
                [
                    "apply",
                    "--registry", str(temp_workspace / ".egokit" / "policy-registry"),
                    "--repo", str(project_dir),
                    "--agent", "claude",
                ],
            )
            assert result.exit_code == 0
            assert (project_dir / "CLAUDE.md").exists()
            
            # Then apply Cursor (should not remove Claude artifacts)
            result = runner.invoke(
                app,
                [
                    "apply",
                    "--registry", str(temp_workspace / ".egokit" / "policy-registry"),
                    "--repo", str(project_dir),
                    "--agent", "cursor",
                ],
            )
            assert result.exit_code == 0
            assert (project_dir / ".cursorrules").exists()
            
            # Verify both agent artifacts coexist
            assert (project_dir / "CLAUDE.md").exists()
            assert (project_dir / ".cursorrules").exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])