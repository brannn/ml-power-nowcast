"""Tests for CLI commands and integration."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml
from typer.testing import CliRunner

from egokit.cli import app, _discover_registry


class TestCLI:
    """Test CLI commands."""
    
    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create CLI test runner."""
        return CliRunner()
    
    @pytest.fixture  
    def temp_registry(self) -> Path:
        """Create a minimal temporary policy registry."""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / ".egokit" / "policy-registry"
            registry_path.mkdir(parents=True)
            
            # Create minimal charter
            charter_data = {
                "version": "1.0.0",
                "scopes": {
                    "global": {
                        "security": [
                            {
                                "id": "SEC-001",
                                "rule": "Never commit secrets",
                                "severity": "critical",
                                "detector": "secret.regex.v1",
                                "tags": ["security"]
                            }
                        ]
                    }
                },
                "metadata": {"description": "Test"}
            }
            
            with open(registry_path / "charter.yaml", "w") as f:
                yaml.dump(charter_data, f)
            
            # Create minimal ego config
            ego_dir = registry_path / "ego"
            ego_dir.mkdir()
            
            ego_data = {
                "version": "1.0.0",
                "ego": {
                    "role": "Engineer",
                    "tone": {
                        "voice": "professional",
                        "verbosity": "balanced"
                    },
                    "defaults": {"structure": "clean"},
                    "modes": {
                        "implementer": {
                            "verbosity": "balanced",
                            "focus": "implementation"
                        }
                    }
                }
            }
            
            with open(ego_dir / "global.yaml", "w") as f:
                yaml.dump(ego_data, f)
            
            # Create schemas directory (required for validation)
            schemas_dir = registry_path / "schemas"
            schemas_dir.mkdir()
            
            # Create minimal charter schema
            charter_schema = {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "required": ["version", "scopes"],
                "properties": {
                    "version": {"type": "string"},
                    "scopes": {"type": "object"}
                }
            }
            
            with open(schemas_dir / "charter.schema.json", "w") as f:
                json.dump(charter_schema, f)
            
            # Create minimal ego schema
            ego_schema = {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "properties": {
                    "version": {"type": "string"},
                    "ego": {"type": "object"}
                }
            }
            
            with open(schemas_dir / "ego.schema.json", "w") as f:
                json.dump(ego_schema, f)
            
            yield registry_path
    
    @pytest.fixture
    def temp_repo(self) -> Path:
        """Create a temporary target repository."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir) / "test_repo" 
            repo_path.mkdir()
            yield repo_path
    
    def test_init_command_creates_registry(self, runner: CliRunner) -> None:
        """Test that init command creates a complete policy registry."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = runner.invoke(app, [
                "init", 
                "--path", temp_dir,
                "--org", "Test Organization"
            ])
            
            assert result.exit_code == 0
            assert "Policy registry initialized" in result.stdout
            
            registry_path = Path(temp_dir) / ".egokit" / "policy-registry"
            assert registry_path.exists()
            assert (registry_path / "charter.yaml").exists()
            assert (registry_path / "ego" / "global.yaml").exists()
            assert (registry_path / "schemas").exists()
            
            # Check charter content
            with open(registry_path / "charter.yaml") as f:
                charter = yaml.safe_load(f)
            assert "Test Organization" in charter["metadata"]["description"]
    
    def test_apply_command_generates_artifacts(
        self, 
        runner: CliRunner,
        temp_registry: Path,
        temp_repo: Path
    ) -> None:
        """Test that apply command generates comprehensive Claude artifacts."""
        result = runner.invoke(app, [
            "apply",
            "--repo", str(temp_repo),
            "--registry", str(temp_registry)
        ])
        
        assert result.exit_code == 0
        # The apply command defaults to claude agent
        assert "Claude artifacts synced" in result.stdout or "✓" in result.stdout
        
        # Check artifacts were created
        assert (temp_repo / "CLAUDE.md").exists()
        assert (temp_repo / ".claude" / "settings.json").exists()
        assert (temp_repo / ".claude" / "commands").exists()
        assert (temp_repo / ".claude" / "system-prompt-fragments" / "egokit-policies.txt").exists()
        assert (temp_repo / "EGO.md").exists()
        
        # Check CLAUDE.md content
        claude_md = (temp_repo / "CLAUDE.md").read_text()
        assert "Agent Behavior Calibration" in claude_md
        assert "SEC-001" in claude_md
        assert "Never commit secrets" in claude_md
        
        # Check settings.json structure
        settings = json.loads((temp_repo / ".claude" / "settings.json").read_text())
        assert "permissions" in settings
        assert "behavior" in settings
        assert "automation" in settings
    
    def test_apply_command_dry_run(
        self,
        runner: CliRunner, 
        temp_registry: Path,
        temp_repo: Path
    ) -> None:
        """Test apply command dry run mode."""
        result = runner.invoke(app, [
            "apply",
            "--repo", str(temp_repo),
            "--registry", str(temp_registry),
            "--dry-run"
        ])
        
        assert result.exit_code == 0
        assert "Dry run - showing generated content" in result.stdout
        assert "CLAUDE.md:" in result.stdout
        assert ".claude/settings.json:" in result.stdout
        
        # Files should not be created in dry run
        assert not (temp_repo / "CLAUDE.md").exists()
        assert not (temp_repo / ".claude").exists()
    
    def test_export_system_prompt_command(
        self,
        runner: CliRunner,
        temp_registry: Path
    ) -> None:
        """Test export-system-prompt command.""" 
        with patch("egokit.cli._discover_registry", return_value=temp_registry):
            result = runner.invoke(app, [
                "export-system-prompt"
            ])
            
            assert result.exit_code == 0
            # Check for key components of the system prompt
            assert "INVIOLABLE ORGANIZATIONAL CONSTITUTION" in result.stdout or "CRITICAL" in result.stdout
            assert "Never commit secrets" in result.stdout
            assert "Engineer" in result.stdout
    
    def test_export_system_prompt_to_file(
        self,
        runner: CliRunner,
        temp_registry: Path
    ) -> None:
        """Test export-system-prompt command with file output."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "system-prompt.txt"
            
            result = runner.invoke(app, [
                "export-system-prompt", 
                "--registry", str(temp_registry),
                "--output", str(output_file)
            ])
            
            assert result.exit_code == 0
            assert "System prompt fragment exported" in result.stdout
            assert output_file.exists()
            
            content = output_file.read_text()
            assert "INVIOLABLE ORGANIZATIONAL CONSTITUTION" in content or "CRITICAL" in content
            assert "Never commit secrets" in content
    
    @patch("subprocess.run")
    def test_claude_headless_command(
        self,
        mock_subprocess: Mock,
        runner: CliRunner,
        temp_registry: Path
    ) -> None:
        """Test claude-headless command integration."""
        # Mock successful subprocess execution
        mock_result = Mock()
        mock_result.stdout = "Claude Code output"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result
        
        with patch("egokit.cli._discover_registry", return_value=temp_registry):
            result = runner.invoke(app, [
                "claude-headless",
                "Test prompt for Claude Code"
            ])
            
            assert result.exit_code == 0
            assert "Claude Code output" in result.stdout
            
            # Check subprocess was called with correct arguments
            mock_subprocess.assert_called_once()
            call_args = mock_subprocess.call_args[0][0]
            assert "claude-code" in call_args
            assert "-p" in call_args
            assert "--append-system-prompt" in call_args
            assert "Test prompt for Claude Code" in call_args
    
    def test_doctor_command(
        self,
        runner: CliRunner,
        temp_registry: Path
    ) -> None:
        """Test doctor command provides configuration overview."""
        result = runner.invoke(app, [
            "doctor",
            "--registry", str(temp_registry)
        ])
        
        assert result.exit_code == 0
        assert "EgoKit Policy Doctor" in result.stdout
        assert "Policy Version" in result.stdout
        assert "1.0.0" in result.stdout
        assert "Active Rules" in result.stdout
        assert "SEC-001" in result.stdout
    
    def test_discover_registry_finds_local(self) -> None:
        """Test registry discovery in directory hierarchy."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create nested directory structure
            project_dir = temp_path / "projects" / "my-project"
            project_dir.mkdir(parents=True)
            
            # Create registry at higher level
            registry_dir = temp_path / ".egokit" / "policy-registry"
            registry_dir.mkdir(parents=True)
            
            # Change to project directory and test discovery
            original_cwd = Path.cwd()
            try:
                import os
                os.chdir(project_dir)
                discovered = _discover_registry()
                # Use resolve() to handle symlinks
                assert discovered.resolve() == registry_dir.resolve()
            finally:
                os.chdir(original_cwd)
    
    def test_discover_registry_not_found(self) -> None:
        """Test registry discovery when no registry exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            project_dir = temp_path / "project" 
            project_dir.mkdir()
            
            original_cwd = Path.cwd()
            try:
                import os
                os.chdir(project_dir)
                discovered = _discover_registry()
                assert discovered is None
            finally:
                os.chdir(original_cwd)
    
    def test_apply_command_with_scope_precedence(
        self,
        runner: CliRunner,
        temp_registry: Path,
        temp_repo: Path
    ) -> None:
        """Test apply command with custom scope precedence."""
        result = runner.invoke(app, [
            "apply",
            "--repo", str(temp_repo),
            "--registry", str(temp_registry),
            "--scope", "global",
            "--scope", "teams/backend"  # This won't exist but should handle gracefully
        ])
        
        # Should still work with global scope even if team scope doesn't exist
        assert result.exit_code == 0 or "not found" in result.stdout.lower()
    
    def test_cli_error_handling(self, runner: CliRunner) -> None:
        """Test CLI error handling for missing registry."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = runner.invoke(app, [
                "apply",
                "--repo", temp_dir,
                "--registry", "/nonexistent/registry"
            ])
            
            assert result.exit_code == 1
            assert "Policy registry not found" in result.stdout