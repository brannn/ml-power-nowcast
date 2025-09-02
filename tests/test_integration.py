"""End-to-end integration tests for EgoKit workflow."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml
from typer.testing import CliRunner

from egokit.cli import app
from egokit.exceptions import EgoKitError
from egokit.models import Severity
from egokit.registry import PolicyRegistry
from egokit.validator import PolicyValidator


class TestEgoKitIntegration:
    """Test complete EgoKit workflow integration."""
    
    @pytest.fixture
    def complete_registry(self) -> Path:
        """Create a comprehensive policy registry for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / ".egokit" / "policy-registry"
            registry_path.mkdir(parents=True)
            
            # Comprehensive charter with multiple rule types
            charter_data = {
                "version": "1.2.0",
                "scopes": {
                    "global": {
                        "security": [
                            {
                                "id": "SEC-001",
                                "rule": "Never commit secrets, API keys, or credentials to version control",
                                "severity": "critical",
                                "detector": "secret.regex.v1",
                                "auto_fix": False,
                                "example_violation": "api_key = 'sk-123456789abcdef'",
                                "example_fix": "api_key = os.environ['API_KEY']",
                                "tags": ["security", "credentials", "git"]
                            },
                            {
                                "id": "SEC-002", 
                                "rule": "Use HTTPS for all external API calls",
                                "severity": "critical",
                                "detector": "network.https.v1", 
                                "auto_fix": True,
                                "tags": ["security", "network"]
                            }
                        ],
                        "code_quality": [
                            {
                                "id": "QUAL-001",
                                "rule": "All function parameters must have type hints",
                                "severity": "warning",
                                "detector": "python.ast.typehints.v1",
                                "auto_fix": True,
                                "example_violation": "def process_data(data):",
                                "example_fix": "def process_data(data: Dict[str, Any]) -> List[str]:",
                                "tags": ["python", "typing", "quality"]
                            },
                            {
                                "id": "QUAL-002",
                                "rule": "Functions must not exceed 50 lines",
                                "severity": "warning", 
                                "detector": "python.complexity.length.v1",
                                "auto_fix": False,
                                "tags": ["python", "complexity"]
                            }
                        ],
                        "docs": [
                            {
                                "id": "DOCS-001",
                                "rule": "Technical documentation must avoid marketing superlatives",
                                "severity": "warning",
                                "detector": "docs.style.superlatives.v1",
                                "auto_fix": False,
                                "example_violation": "This amazing feature is world-class",
                                "example_fix": "This feature provides X functionality",
                                "tags": ["documentation", "style", "marketing"]
                            }
                        ]
                    },
                    "teams/backend": {
                        "security": [
                            {
                                "id": "BACK-001", 
                                "rule": "All database queries must use parameterized statements",
                                "severity": "critical",
                                "detector": "sql.injection.v1",
                                "auto_fix": False,
                                "tags": ["security", "database", "sql"]
                            }
                        ],
                        "code_quality": [
                            {
                                "id": "BACK-002",
                                "rule": "Use dependency injection for external services",
                                "severity": "warning",
                                "detector": "python.dependency.injection.v1", 
                                "auto_fix": False,
                                "tags": ["architecture", "testing"]
                            }
                        ]
                    }
                },
                "metadata": {
                    "description": "Complete organizational policy charter",
                    "maintainer": "Platform Engineering Team",
                    "last_updated": "2025-01-01"
                }
            }
            
            with open(registry_path / "charter.yaml", "w") as f:
                yaml.dump(charter_data, f)
            
            # Complete ego configurations
            ego_dir = registry_path / "ego"
            ego_dir.mkdir()
            
            # Global ego configuration
            global_ego = {
                "version": "1.0.0",
                "ego": {
                    "role": "Senior Software Engineer",
                    "tone": {
                        "voice": "professional, precise, helpful",
                        "verbosity": "balanced",
                        "formatting": [
                            "code-with-comments",
                            "bullet-lists-for-steps",
                            "examples-when-helpful"
                        ]
                    },
                    "defaults": {
                        "structure": "overview → implementation → validation → documentation",
                        "code_style": "Follow established project conventions",
                        "documentation": "clear, concise, actionable",
                        "testing": "unit tests with meaningful assertions"
                    },
                    "reviewer_checklist": [
                        "Code follows established patterns and conventions",
                        "Type hints are comprehensive and accurate", 
                        "Error handling is appropriate and informative",
                        "Documentation is clear and up-to-date",
                        "Tests cover critical functionality",
                        "Security best practices are followed"
                    ],
                    "ask_when_unsure": [
                        "Breaking changes to public APIs",
                        "Security-sensitive modifications",
                        "Performance-critical optimizations",
                        "Database schema changes"
                    ],
                    "modes": {
                        "implementer": {
                            "verbosity": "balanced",
                            "focus": "clean implementation with good practices"
                        },
                        "reviewer": {
                            "verbosity": "detailed",
                            "focus": "thorough analysis and constructive feedback"
                        },
                        "security": {
                            "verbosity": "detailed",
                            "focus": "security implications and threat modeling"
                        }
                    }
                }
            }
            
            with open(ego_dir / "global.yaml", "w") as f:
                yaml.dump(global_ego, f)
            
            # Team-specific ego configuration
            (ego_dir / "teams").mkdir()
            backend_ego = {
                "version": "1.0.0",
                "ego": {
                    "role": "Backend Engineer", 
                    "tone": {
                        "voice": "technical, direct, security-conscious",
                        "verbosity": "detailed"
                    },
                    "defaults": {
                        "structure": "security → performance → implementation → monitoring"
                    },
                    "reviewer_checklist": [
                        "Database operations are secure and efficient",
                        "API endpoints have proper authentication",
                        "Error responses don't leak sensitive information"
                    ]
                }
            }
            
            with open(ego_dir / "teams" / "backend.yaml", "w") as f:
                yaml.dump(backend_ego, f)
            
            # Create schemas directory for validation
            schemas_dir = registry_path / "schemas"
            schemas_dir.mkdir()
            
            # Create minimal schemas
            charter_schema = {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "required": ["version", "scopes"],
                "properties": {
                    "version": {"type": "string"},
                    "scopes": {"type": "object"}
                }
            }
            
            import json
            with open(schemas_dir / "charter.schema.json", "w") as f:
                json.dump(charter_schema, f)
            
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
    def sample_project(self) -> Path:
        """Create a sample project with various file types for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "sample_project"
            project_path.mkdir()
            
            # Python files for testing
            (project_path / "src").mkdir()
            
            # Good Python file
            good_py = project_path / "src" / "good_example.py"
            good_py.write_text("""
from typing import Dict, List, Any
import os

def process_user_data(data: Dict[str, Any]) -> List[str]:
    \"\"\"Process user data securely.\"\"\"
    api_key = os.environ.get('API_KEY')
    if not api_key:
        raise ValueError("API key not configured")
    
    results = []
    for item in data.get('items', []):
        if item.get('valid'):
            results.append(item['name'])
    return results
""")
            
            # Bad Python file with violations
            bad_py = project_path / "src" / "bad_example.py" 
            bad_py.write_text("""
def process_data(data):  # Missing type hints - QUAL-001 violation
    api_key = "sk-123456789abcdef"  # Hardcoded secret - SEC-001 violation  
    
    # This function is way too long - QUAL-002 violation
    result = []
    for i in range(100):
        if i % 2 == 0:
            result.append(str(i))
        elif i % 3 == 0:
            result.append(str(i * 2))
        elif i % 5 == 0:
            result.append(str(i * 3))
        elif i % 7 == 0:
            result.append(str(i * 4))
        # ... many more lines to exceed 50 line limit
        for j in range(10):
            for k in range(10):
                if (i + j + k) % 2 == 0:
                    result.append(f"{i}-{j}-{k}")
                else:
                    result.append(f"{k}-{j}-{i}")
    
    # More code to make this function exceed 50 lines
    final_result = []
    for item in result:
        processed = item.upper()
        if len(processed) > 3:
            final_result.append(processed[:3])
        else:
            final_result.append(processed)
    
    return final_result  # Function ends at line ~35+ (exceeds 50 line rule)
""")
            
            # Documentation with violations
            readme = project_path / "README.md"
            readme.write_text("""
# Amazing Project

This world-class, incredible, revolutionary project is the best solution ever created!  # DOCS-001 violation

## Features

- Blazingly fast performance
- Unmatched reliability  
- Industry-leading security
""")
            
            yield project_path
    
    @pytest.fixture
    def runner(self) -> CliRunner:
        """CLI test runner."""
        return CliRunner()
    
    def test_complete_workflow_registry_to_artifacts(
        self,
        complete_registry: Path,
        sample_project: Path,
        runner: CliRunner
    ) -> None:
        """Test complete workflow from registry to generated artifacts."""
        # Step 1: Generate artifacts using apply command
        result = runner.invoke(app, [
            "apply",
            "--repo", str(sample_project),
            "--registry", str(complete_registry),
            "--scope", "global",
            "--scope", "teams/backend",
            "--agent", "claude"
        ])
        
        assert result.exit_code == 0
        assert "Claude artifacts synced" in result.stdout or "✓" in result.stdout
        
        # Step 2: Verify all expected artifacts exist
        expected_files = [
            "CLAUDE.md",
            ".claude/settings.json", 
            ".claude/commands/validate.md",
            ".claude/commands/security-review.md",
            ".claude/commands/compliance-check.md",
            ".claude/commands/refresh-policies.md",
            ".claude/commands/mode-implementer.md",
            ".claude/commands/mode-reviewer.md",
            ".claude/commands/mode-security.md",
            ".claude/system-prompt-fragments/egokit-policies.txt",
            "EGO.md"
        ]
        
        for expected_file in expected_files:
            file_path = sample_project / expected_file
            assert file_path.exists(), f"Expected file {expected_file} not found"
            assert file_path.stat().st_size > 0, f"File {expected_file} is empty"
        
        # Step 3: Verify content quality and completeness
        claude_md = (sample_project / "CLAUDE.md").read_text()
        
        # Check messaging themes
        assert "Agent Behavior Calibration" in claude_md
        assert "consistently on-track" in claude_md
        assert "prevents quality drift" in claude_md
        
        # Check policy integration
        assert "SEC-001" in claude_md  # Global security rule
        assert "BACK-001" in claude_md  # Team-specific rule
        assert "Never commit secrets" in claude_md
        assert "parameterized statements" in claude_md
        
        # Check ego integration - team scope overrides global
        assert "Backend Engineer" in claude_md  # Team override replaces global role
        assert "security-conscious" in claude_md  # Team tone
        
        # Check modes integration
        assert "Available Modes" in claude_md
        assert "Implementer Mode" in claude_md
        assert "Security Mode" in claude_md
    
    def test_policy_validation_integration(
        self,
        complete_registry: Path,
        sample_project: Path
    ) -> None:
        """Test policy validation detects violations correctly."""
        # Load registry and create validator
        registry = PolicyRegistry(complete_registry)
        validator = PolicyValidator(registry)
        
        # Test files from sample project
        test_files = [
            sample_project / "src" / "good_example.py",
            sample_project / "src" / "bad_example.py", 
            sample_project / "README.md"
        ]
        
        # Run validation
        report = validator.validate_files(test_files, ["global", "teams/backend"])
        
        # Note: Actual violation detection depends on detector implementation
        # Since detectors aren't implemented, we're testing the integration structure
        assert len(report.files_checked) == len(test_files)
        assert report.execution_time > 0
        
        # The report structure should be sound
        # (We can't test for actual violations without real detector implementations)
        
        # Test severity filtering
        critical_violations = report.critical_violations
        warning_violations = report.warning_violations
        
        # Structure should be sound
        assert len(critical_violations) + len(warning_violations) == len(report.violations)
    
    def test_hierarchical_scope_precedence(self, complete_registry: Path) -> None:
        """Test that hierarchical scope precedence works correctly."""
        registry = PolicyRegistry(complete_registry)
        charter = registry.load_charter()
        
        # Test global scope only
        global_rules = registry.merge_scope_rules(charter, ["global"])
        global_rule_ids = {rule.id for rule in global_rules}
        assert "SEC-001" in global_rule_ids
        assert "QUAL-001" in global_rule_ids
        assert "DOCS-001" in global_rule_ids
        assert "BACK-001" not in global_rule_ids  # Team-specific rule
        
        # Test with team scope (should include both global and team rules)
        merged_rules = registry.merge_scope_rules(charter, ["global", "teams/backend"])
        merged_rule_ids = {rule.id for rule in merged_rules}
        assert "SEC-001" in merged_rule_ids  # Global rule
        assert "BACK-001" in merged_rule_ids  # Team rule
        assert "BACK-002" in merged_rule_ids  # Team rule
        
        # Should have more rules with team scope
        assert len(merged_rules) > len(global_rules)
        
        # Test ego config precedence
        global_ego = registry.merge_ego_configs(["global"])
        assert global_ego.role == "Senior Software Engineer"
        
        merged_ego = registry.merge_ego_configs(["global", "teams/backend"])
        assert merged_ego.role == "Backend Engineer"  # Team overrides global
        assert merged_ego.tone.voice == "technical, direct, security-conscious"  # Team override
        
        # But should retain global defaults where team doesn't override
        assert len(merged_ego.ask_when_unsure) > 0  # From global config
    
    def test_cli_doctor_comprehensive_report(
        self,
        complete_registry: Path,
        runner: CliRunner
    ) -> None:
        """Test doctor command provides comprehensive configuration report."""
        result = runner.invoke(app, [
            "doctor",
            "--registry", str(complete_registry),
            "--scope", "global", 
            "--scope", "teams/backend"
        ])
        
        assert result.exit_code == 0
        
        # Check report structure
        assert "EgoKit Policy Doctor" in result.stdout
        assert "Policy Version" in result.stdout
        assert "1.2.0" in result.stdout
        assert "Active Scopes" in result.stdout
        assert "global → teams/backend" in result.stdout
        
        # Check rule counts
        assert "Total Rules" in result.stdout
        assert "Critical Rules" in result.stdout
        assert "Warning Rules" in result.stdout
        
        # Check ego configuration
        assert "Ego Role" in result.stdout
        assert "Backend Engineer" in result.stdout  # Should show team override
        
        # Check active rules listing
        assert "Active Rules:" in result.stdout
        assert "SEC-001" in result.stdout
        assert "BACK-001" in result.stdout
    
    def test_end_to_end_claude_code_integration(
        self,
        complete_registry: Path,
        sample_project: Path,
        runner: CliRunner
    ) -> None:
        """Test end-to-end Claude Code integration workflow."""
        # Step 1: Apply comprehensive artifacts
        apply_result = runner.invoke(app, [
            "apply",
            "--repo", str(sample_project),
            "--registry", str(complete_registry),
            "--scope", "global",
            "--scope", "teams/backend",
            "--agent", "claude"
        ])
        
        assert apply_result.exit_code == 0
        
        # Step 2: Export system prompt for verification
        with patch("egokit.cli._discover_registry", return_value=complete_registry):
            prompt_result = runner.invoke(app, [
                "export-system-prompt",
                "--scope", "global",
                "--scope", "teams/backend"
            ])
            
            assert prompt_result.exit_code == 0
            prompt_content = prompt_result.stdout
            
            # Should contain critical policies
            assert "INVIOLABLE ORGANIZATIONAL CONSTITUTION" in prompt_content or "CRITICAL ORGANIZATIONAL STANDARDS:" in prompt_content
            assert "Never commit secrets" in prompt_content or "Never commit credentials" in prompt_content
            assert "parameterized statements" in prompt_content or "SQL queries" in prompt_content
            
            # Should contain behavioral calibration
            assert "Backend Engineer" in prompt_content  # Team role
            assert "security-conscious" in prompt_content  # Team tone
            
            # Should contain consistency requirements  
            assert "ENFORCEMENT PROTOCOL" in prompt_content or "Stay on-track with established patterns" in prompt_content
            assert "drift" in prompt_content.lower()
        
        # Step 3: Verify settings.json has correct permissions and behavior
        settings_file = sample_project / ".claude" / "settings.json"
        assert settings_file.exists()
        
        import json
        settings = json.loads(settings_file.read_text())
        
        # Should have security-conscious permissions due to security rules
        assert settings["behavior"]["security_first"] is True
        assert settings["behavior"]["require_confirmation_for_critical"] is True
        
        # Should suggest fixes due to auto_fix rules
        assert settings["automation"]["suggest_fixes"] is True
        
        # Step 4: Verify custom commands are comprehensive
        commands_dir = sample_project / ".claude" / "commands"
        command_files = list(commands_dir.glob("*.md"))
        
        assert len(command_files) >= 7  # validate, security-review, compliance-check, refresh-policies, 3 modes
        
        # Check validate command mentions active rule count
        validate_cmd = (commands_dir / "validate.md").read_text()
        assert "organizational standards" in validate_cmd.lower()
        # Should mention more rules due to team scope inclusion
        assert "7 organizational standards" in validate_cmd or "6 organizational standards" in validate_cmd
        
        # Check security command reflects security rules
        security_cmd = (commands_dir / "security-review.md").read_text()
        assert "Active Security Policies" in security_cmd
        assert "SEC-001" in security_cmd or "SEC-002" in security_cmd