"""Tests for PolicyRegistry core functionality."""

import tempfile
from pathlib import Path
from typing import Dict, Any

import pytest
import yaml

from egokit.exceptions import RegistryError, ScopeError
from egokit.models import PolicyCharter, EgoConfig, Severity
from egokit.registry import PolicyRegistry


class TestPolicyRegistry:
    """Test PolicyRegistry core functionality."""
    
    @pytest.fixture
    def temp_registry(self) -> Path:
        """Create a temporary policy registry for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / ".egokit" / "policy-registry"
            registry_path.mkdir(parents=True)
            
            # Create charter.yaml
            charter_data = {
                "version": "1.0.0",
                "scopes": {
                    "global": {
                        "security": [
                            {
                                "id": "SEC-001",
                                "rule": "Never commit secrets to version control",
                                "severity": "critical",
                                "detector": "secret.regex.v1",
                                "auto_fix": False,
                                "tags": ["security", "credentials"]
                            }
                        ],
                        "code_quality": [
                            {
                                "id": "QUAL-001", 
                                "rule": "Use type hints for all functions",
                                "severity": "warning",
                                "detector": "python.ast.typehints.v1",
                                "auto_fix": True,
                                "tags": ["python", "typing"]
                            }
                        ]
                    },
                    "teams/backend": {
                        "security": [
                            {
                                "id": "BACK-001",
                                "rule": "Validate all database inputs",
                                "severity": "critical", 
                                "detector": "sql.injection.v1",
                                "auto_fix": False,
                                "tags": ["security", "database"]
                            }
                        ]
                    }
                },
                "metadata": {
                    "description": "Test policy charter",
                    "maintainer": "Test Team"
                }
            }
            
            with open(registry_path / "charter.yaml", "w") as f:
                yaml.dump(charter_data, f)
            
            # Create ego configurations
            ego_dir = registry_path / "ego"
            ego_dir.mkdir()
            
            # Global ego config
            global_ego = {
                "version": "1.0.0",
                "ego": {
                    "role": "Senior Software Engineer",
                    "tone": {
                        "voice": "professional, precise",
                        "verbosity": "balanced",
                        "formatting": ["code-with-comments", "bullet-lists"]
                    },
                    "defaults": {
                        "structure": "overview → implementation → validation",
                        "testing": "unit tests with assertions"
                    },
                    "reviewer_checklist": [
                        "Code follows established patterns",
                        "Security best practices followed"
                    ],
                    "ask_when_unsure": [
                        "Breaking API changes",
                        "Security modifications"
                    ],
                    "modes": {
                        "implementer": {
                            "verbosity": "balanced",
                            "focus": "clean implementation"
                        },
                        "security": {
                            "verbosity": "detailed", 
                            "focus": "security implications"
                        }
                    }
                }
            }
            
            with open(ego_dir / "global.yaml", "w") as f:
                yaml.dump(global_ego, f)
            
            # Team-specific ego config
            teams_ego = {
                "version": "1.0.0", 
                "ego": {
                    "role": "Backend Engineer",
                    "tone": {
                        "voice": "technical, direct",
                        "verbosity": "detailed"
                    },
                    "defaults": {
                        "structure": "security → implementation → performance"
                    }
                }
            }
            
            teams_dir = ego_dir / "teams"
            teams_dir.mkdir(exist_ok=True)
            with open(teams_dir / "backend.yaml", "w") as f:
                yaml.dump(teams_ego, f)
            
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
    
    def test_load_charter_success(self, temp_registry: Path) -> None:
        """Test successful charter loading."""
        registry = PolicyRegistry(temp_registry)
        charter = registry.load_charter(validate=False)
        
        assert isinstance(charter, PolicyCharter)
        assert charter.version == "1.0.0"
        assert "global" in charter.scopes
        assert "teams/backend" in charter.scopes
    
    def test_load_charter_missing_file(self) -> None:
        """Test charter loading with missing file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry = PolicyRegistry(Path(temp_dir))
            
            with pytest.raises(RegistryError, match="Charter file not found"):
                registry.load_charter()
    
    def test_load_ego_config_global(self, temp_registry: Path) -> None:
        """Test loading global ego configuration."""
        registry = PolicyRegistry(temp_registry)
        ego_config = registry.load_ego_config("global", validate=False)
        
        assert isinstance(ego_config, EgoConfig)
        assert ego_config.role == "Senior Software Engineer"
        assert ego_config.tone.voice == "professional, precise"
        assert "implementer" in ego_config.modes
        assert "security" in ego_config.modes
    
    def test_load_ego_config_team_specific(self, temp_registry: Path) -> None:
        """Test loading team-specific ego configuration."""
        registry = PolicyRegistry(temp_registry)
        ego_config = registry.load_ego_config("teams/backend", validate=False)
        
        assert ego_config.role == "Backend Engineer"
        assert ego_config.tone.voice == "technical, direct"
        assert ego_config.tone.verbosity == "detailed"
    
    def test_load_ego_config_missing_file(self, temp_registry: Path) -> None:
        """Test ego config loading with missing file."""
        registry = PolicyRegistry(temp_registry)
        
        with pytest.raises(RegistryError, match="Ego config not found"):
            registry.load_ego_config("nonexistent")
    
    def test_merge_scope_rules_hierarchical(self, temp_registry: Path) -> None:
        """Test merging rules across hierarchical scopes."""
        registry = PolicyRegistry(temp_registry)
        charter = registry.load_charter(validate=False)
        
        # Test global only
        global_rules = registry.merge_scope_rules(charter, ["global"])
        assert len(global_rules) == 2  # SEC-001 and QUAL-001
        rule_ids = {rule.id for rule in global_rules}
        assert "SEC-001" in rule_ids
        assert "QUAL-001" in rule_ids
        
        # Test with team override
        merged_rules = registry.merge_scope_rules(charter, ["global", "teams/backend"])
        assert len(merged_rules) == 3  # SEC-001, QUAL-001, BACK-001
        rule_ids = {rule.id for rule in merged_rules}
        assert "SEC-001" in rule_ids
        assert "QUAL-001" in rule_ids
        assert "BACK-001" in rule_ids
    
    def test_merge_scope_rules_invalid_scope(self, temp_registry: Path) -> None:
        """Test merging rules with invalid scope."""
        registry = PolicyRegistry(temp_registry)
        charter = registry.load_charter(validate=False)
        
        with pytest.raises(ScopeError, match="Scope 'invalid' not found"):
            registry.merge_scope_rules(charter, ["global", "invalid"])
    
    def test_merge_ego_configs_hierarchical(self, temp_registry: Path) -> None:
        """Test merging ego configurations with precedence."""
        registry = PolicyRegistry(temp_registry)
        
        # Global only
        global_ego = registry.merge_ego_configs(["global"])
        assert global_ego.role == "Senior Software Engineer"
        assert global_ego.tone.verbosity == "balanced"
        
        # With team override - team should take precedence
        merged_ego = registry.merge_ego_configs(["global", "teams/backend"])
        assert merged_ego.role == "Backend Engineer"  # Overridden by team
        assert merged_ego.tone.verbosity == "detailed"  # Overridden by team
        
        # But should still have global defaults where team doesn't override
        assert len(merged_ego.reviewer_checklist) == 2  # From global
        assert len(merged_ego.ask_when_unsure) == 2  # From global
    
    def test_discover_ego_scopes(self, temp_registry: Path) -> None:
        """Test discovering all available ego scopes."""
        registry = PolicyRegistry(temp_registry)
        scopes = registry.discover_ego_scopes()
        
        assert "global" in scopes
        assert "teams/backend" in scopes
        assert len(scopes) == 2
        
    def test_rule_severity_enforcement(self, temp_registry: Path) -> None:
        """Test that rule severity levels are properly handled."""
        registry = PolicyRegistry(temp_registry)
        charter = registry.load_charter(validate=False)
        rules = registry.merge_scope_rules(charter, ["global", "teams/backend"])
        
        critical_rules = [r for r in rules if r.severity == Severity.CRITICAL]
        warning_rules = [r for r in rules if r.severity == Severity.WARNING]
        
        assert len(critical_rules) == 2  # SEC-001, BACK-001
        assert len(warning_rules) == 1   # QUAL-001
        
        # Check specific rule properties
        sec_rule = next(r for r in rules if r.id == "SEC-001")
        assert sec_rule.severity == Severity.CRITICAL
        assert sec_rule.auto_fix is False
        assert "security" in sec_rule.tags
        assert "credentials" in sec_rule.tags