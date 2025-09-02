"""Tests for ArtifactCompiler Claude Code integration."""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from egokit.compiler import ArtifactCompiler, ArtifactInjector
from egokit.models import (
    CompilationContext,
    EgoConfig,
    ModeConfig, 
    PolicyCharter,
    PolicyRule,
    Severity,
    ToneConfig,
)


class TestArtifactCompiler:
    """Test ArtifactCompiler Claude Code integration features."""
    
    @pytest.fixture
    def sample_context(self) -> CompilationContext:
        """Create a sample compilation context for testing."""
        # Create sample policy rules
        charter = PolicyCharter(
            version="1.0.0",
            scopes={
                "global": {
                    "security": [
                        {
                            "id": "SEC-001",
                            "rule": "Never commit credentials or API keys",
                            "severity": "critical",
                            "detector": "secret.regex.v1",
                            "auto_fix": False,
                            "example_violation": "api_key = 'sk-123456'",
                            "example_fix": "api_key = os.environ['API_KEY']",
                            "tags": ["security", "credentials"]
                        }
                    ],
                    "code_quality": [
                        {
                            "id": "QUAL-001",
                            "rule": "Use comprehensive type hints",
                            "severity": "warning", 
                            "detector": "python.ast.typehints.v1",
                            "auto_fix": True,
                            "tags": ["python", "typing"]
                        }
                    ],
                    "docs": [
                        {
                            "id": "DOCS-001",
                            "rule": "Avoid marketing superlatives in documentation",
                            "severity": "warning",
                            "detector": "docs.style.superlatives.v1",
                            "auto_fix": False,
                            "tags": ["documentation", "style"]
                        }
                    ]
                }
            },
            metadata={"description": "Test charter"}
        )
        
        # Create sample ego config
        ego_config = EgoConfig(
            role="Senior Software Engineer",
            tone=ToneConfig(
                voice="professional, precise, helpful",
                verbosity="balanced",
                formatting=["code-with-comments", "bullet-lists-for-steps"]
            ),
            defaults={
                "structure": "overview → implementation → validation",
                "code_style": "Follow project conventions",
                "testing": "unit tests with meaningful assertions"
            },
            reviewer_checklist=[
                "Code follows established patterns",
                "Type hints are comprehensive",
                "Security best practices followed"
            ],
            ask_when_unsure=[
                "Breaking API changes",
                "Security-sensitive modifications"
            ],
            modes={
                "implementer": ModeConfig(
                    verbosity="balanced",
                    focus="clean implementation"
                ),
                "security": ModeConfig(
                    verbosity="detailed",
                    focus="security implications and threat modeling"
                )
            }
        )
        
        return CompilationContext(
            target_repo=Path("/test/repo"),
            policy_charter=charter,
            ego_config=ego_config,
            active_scope="global",
            generation_timestamp=datetime(2025, 1, 1, 12, 0, 0)
        )
    
    def test_compile_claude_artifacts_completeness(self, sample_context: CompilationContext) -> None:
        """Test that comprehensive Claude artifacts are generated."""
        compiler = ArtifactCompiler(sample_context)
        artifacts = compiler.compile_claude_artifacts()
        
        # Check all expected artifacts are present
        expected_artifacts = {
            "CLAUDE.md",
            "PROJECT-POLICIES.md",
            ".claude/0-CRITICAL-POLICIES.md",
            ".claude/PRE-COMMIT-CHECKLIST.md",
            ".claude/settings.json", 
            ".claude/commands/validate.md",
            ".claude/commands/security-review.md",
            ".claude/commands/compliance-check.md",
            ".claude/commands/refresh-policies.md",
            ".claude/commands/mode-implementer.md",
            ".claude/commands/mode-security.md",
            ".claude/commands/checkpoint.md",
            ".claude/commands/periodic-refresh.md",
            ".claude/commands/before-code.md",
            ".claude/commands/recall-policies.md",
            ".claude/system-prompt-fragments/egokit-policies.txt"
        }
        
        assert set(artifacts.keys()) == expected_artifacts
        
        # Check that all artifacts have content
        for artifact_path, content in artifacts.items():
            assert content.strip(), f"Artifact {artifact_path} is empty"
    
    def test_compile_claude_md_content(self, sample_context: CompilationContext) -> None:
        """Test CLAUDE.md content structure and messaging."""
        compiler = ArtifactCompiler(sample_context)
        artifacts = compiler.compile_claude_artifacts()
        claude_md = artifacts["CLAUDE.md"]
        
        # Check for agent behavior calibration messaging
        assert "Agent Behavior Calibration" in claude_md
        assert "prevents quality drift" in claude_md
        assert "consistently on-track" in claude_md
        
        # Check for policy sections
        assert "Critical Standards - Never Violate" in claude_md
        assert "Quality Guidelines - Follow Consistently" in claude_md
        assert "SEC-001" in claude_md
        assert "QUAL-001" in claude_md
        
        # Check for ego configuration
        assert "Senior Software Engineer" in claude_md
        assert "professional, precise, helpful" in claude_md
        assert "balanced" in claude_md
        
        # Check for modes
        assert "Available Modes" in claude_md
        assert "Implementer Mode" in claude_md
        assert "Security Mode" in claude_md
    
    def test_compile_claude_settings_structure(self, sample_context: CompilationContext) -> None:
        """Test .claude/settings.json structure and policy derivation."""
        compiler = ArtifactCompiler(sample_context)
        artifacts = compiler.compile_claude_artifacts()
        settings_json = artifacts[".claude/settings.json"]
        
        settings = json.loads(settings_json)
        
        # Check main sections exist
        assert "permissions" in settings
        assert "behavior" in settings
        assert "automation" in settings
        
        # Check permissions structure
        permissions = settings["permissions"]
        assert "allow" in permissions
        assert "deny" in permissions  
        assert "ask" in permissions
        
        # Check behavior configuration
        behavior = settings["behavior"]
        assert "security_first" in behavior
        assert "require_confirmation_for_critical" in behavior
        assert "documentation_standards" in behavior
        
        # Security rules should trigger security_first behavior
        assert behavior["security_first"] is True
        assert behavior["require_confirmation_for_critical"] is True
        
        # Documentation standards should be extracted from doc rules
        doc_standards = behavior["documentation_standards"]
        assert "no_superlatives" in doc_standards
        assert doc_standards["no_superlatives"] is True
    
    def test_compile_system_prompt_fragment(self, sample_context: CompilationContext) -> None:
        """Test system prompt fragment generation."""
        compiler = ArtifactCompiler(sample_context)
        artifacts = compiler.compile_claude_artifacts()
        fragment = artifacts[".claude/system-prompt-fragments/egokit-policies.txt"]
        
        # Check critical policies are included
        assert "INVIOLABLE ORGANIZATIONAL CONSTITUTION" in fragment or "CRITICAL" in fragment
        assert "Never commit credentials" in fragment or "SEC-001" in fragment
        
        # Check behavioral guidelines
        assert "Senior Software Engineer" in fragment
        assert "professional, precise, helpful" in fragment
        assert "balanced" in fragment
        
        # Check security section
        assert "SECURITY IMPERATIVES" in fragment or "SECURITY REQUIREMENTS:" in fragment
        assert "security implications" in fragment
        assert "Never suggest hardcoded credentials" in fragment or "NEVER suggest hardcoded credentials" in fragment
        
        # Check consistency reminders
        assert "ENFORCEMENT PROTOCOL" in fragment or "CONSISTENCY REQUIREMENTS:" in fragment
        assert "Code follows established patterns" in fragment or "Stay on-track with established patterns" in fragment
        assert "drift" in fragment.lower()
    
    def test_compile_custom_commands_generation(self, sample_context: CompilationContext) -> None:
        """Test custom slash commands are properly generated."""
        compiler = ArtifactCompiler(sample_context)
        artifacts = compiler.compile_claude_artifacts()
        
        # Test validate command
        validate_cmd = artifacts[".claude/commands/validate.md"]
        assert "Validate Code Against Organizational Standards" in validate_cmd
        assert "EgoKit policy validation" in validate_cmd
        assert "ego validate --changed" in validate_cmd
        assert "Enforcing 3 organizational standards" in validate_cmd  # SEC-001, QUAL-001, DOCS-001
        
        # Test security review command
        security_cmd = artifacts[".claude/commands/security-review.md"]
        assert "Switch to Security Review Mode" in security_cmd
        assert "heightened security analysis" in security_cmd
        assert "OWASP Top 10" in security_cmd
        assert 'EGOKIT_MODE="security"' in security_cmd
        
        # Test mode commands
        implementer_mode = artifacts[".claude/commands/mode-implementer.md"]
        assert "Switch to Implementer Mode" in implementer_mode
        assert "clean implementation" in implementer_mode
        assert 'EGOKIT_MODE="implementer"' in implementer_mode
        
        security_mode = artifacts[".claude/commands/mode-security.md"]
        assert "Switch to Security Mode" in security_mode
        assert "security implications and threat modeling" in security_mode
    
    def test_policy_rule_extraction_and_filtering(self, sample_context: CompilationContext) -> None:
        """Test that policy rules are properly extracted and filtered by severity."""
        compiler = ArtifactCompiler(sample_context)
        rules = compiler._extract_rules_from_charter()
        
        assert len(rules) == 3
        
        # Test rule extraction accuracy
        rule_ids = {rule.id for rule in rules}
        assert "SEC-001" in rule_ids
        assert "QUAL-001" in rule_ids  
        assert "DOCS-001" in rule_ids
        
        # Test severity filtering
        critical_rules = [r for r in rules if r.severity == Severity.CRITICAL]
        warning_rules = [r for r in rules if r.severity == Severity.WARNING]
        
        assert len(critical_rules) == 1  # SEC-001
        assert len(warning_rules) == 2   # QUAL-001, DOCS-001
        
        # Test tag-based filtering for security
        security_rules = [r for r in rules if "security" in (r.tags or [])]
        assert len(security_rules) == 1
        assert security_rules[0].id == "SEC-001"


class TestArtifactInjector:
    """Test ArtifactInjector functionality."""
    
    @pytest.fixture
    def temp_repo(self) -> Path:
        """Create a temporary repository for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir) / "test_repo"
            repo_path.mkdir()
            yield repo_path
    
    def test_inject_claude_artifacts_complete(self, temp_repo: Path) -> None:
        """Test complete Claude artifacts injection."""
        artifacts = {
            "CLAUDE.md": "# Test CLAUDE.md content",
            ".claude/settings.json": '{"test": "config"}',
            ".claude/commands/validate.md": "# Validate command",
            ".claude/system-prompt-fragments/egokit-policies.txt": "Test policies"
        }
        
        injector = ArtifactInjector(temp_repo)
        injector.inject_claude_artifacts(artifacts)
        
        # Check all files were created
        assert (temp_repo / "CLAUDE.md").exists()
        assert (temp_repo / ".claude" / "settings.json").exists()
        assert (temp_repo / ".claude" / "commands" / "validate.md").exists()
        assert (temp_repo / ".claude" / "system-prompt-fragments" / "egokit-policies.txt").exists()
        
        # Check content
        assert (temp_repo / "CLAUDE.md").read_text() == "# Test CLAUDE.md content"
        assert (temp_repo / ".claude" / "settings.json").read_text() == '{"test": "config"}'
    
    def test_inject_claude_artifacts_creates_directories(self, temp_repo: Path) -> None:
        """Test that nested directories are created automatically."""
        artifacts = {
            ".claude/deep/nested/path/test.md": "Deep nested content"
        }
        
        injector = ArtifactInjector(temp_repo)
        injector.inject_claude_artifacts(artifacts)
        
        nested_file = temp_repo / ".claude" / "deep" / "nested" / "path" / "test.md"
        assert nested_file.exists()
        assert nested_file.read_text() == "Deep nested content"
    
    def test_inject_claude_artifacts_overwrites_existing(self, temp_repo: Path) -> None:
        """Test that existing artifacts are properly overwritten."""
        # Create existing file
        claude_md = temp_repo / "CLAUDE.md"
        claude_md.write_text("Old content")
        
        artifacts = {
            "CLAUDE.md": "New content"
        }
        
        injector = ArtifactInjector(temp_repo)
        injector.inject_claude_artifacts(artifacts)
        
        assert claude_md.read_text() == "New content"