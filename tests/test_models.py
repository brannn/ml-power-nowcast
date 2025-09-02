"""Tests for EgoKit data models."""

import pytest
from pydantic import ValidationError

from egokit.models import (
    EgoCharter,
    EgoConfig,
    PolicyCharter,
    PolicyRule,
    Severity,
    ToneConfig,
)


class TestPolicyRule:
    """Test PolicyRule validation."""
    
    def test_valid_rule(self) -> None:
        """Test creating a valid policy rule."""
        rule = PolicyRule(
            id="SEC-001",
            rule="Never commit secrets",
            severity=Severity.CRITICAL,
            detector="secret.regex.v1",
        )
        assert rule.id == "SEC-001"
        assert rule.severity == Severity.CRITICAL
    
    def test_invalid_rule_id(self) -> None:
        """Test invalid rule ID format."""
        with pytest.raises(ValidationError, match="Rule ID must follow format"):
            PolicyRule(
                id="invalid-id",
                rule="Test rule",
                severity=Severity.WARNING,
                detector="test.v1",
            )
    
    def test_invalid_detector_name(self) -> None:
        """Test invalid detector name format."""
        with pytest.raises(ValidationError, match="Detector must follow format"):
            PolicyRule(
                id="TEST-001",
                rule="Test rule",
                severity=Severity.WARNING,
                detector="invalid_detector_name",
            )


class TestPolicyCharter:
    """Test PolicyCharter validation."""
    
    def test_valid_charter(self) -> None:
        """Test creating a valid policy charter."""
        charter = PolicyCharter(
            version="1.0.0",
            scopes={
                "global": {
                    "security": [
                        {
                            "id": "SEC-001",
                            "rule": "Never commit secrets",
                            "severity": "critical",
                            "detector": "secret.regex.v1",
                        }
                    ]
                }
            },
        )
        assert charter.version == "1.0.0"
    
    def test_invalid_version(self) -> None:
        """Test invalid version format."""
        with pytest.raises(ValidationError, match="Version must follow semantic versioning"):
            PolicyCharter(
                version="invalid-version",
                scopes={},
            )


class TestEgoConfig:
    """Test EgoConfig validation."""
    
    def test_valid_ego_config(self) -> None:
        """Test creating a valid ego configuration."""
        config = EgoConfig(
            role="Senior Engineer",
            tone=ToneConfig(
                voice="professional",
                verbosity="balanced",
            ),
        )
        assert config.role == "Senior Engineer"
        assert config.tone.voice == "professional"


class TestEgoCharter:
    """Test EgoCharter validation."""
    
    def test_valid_ego_charter(self) -> None:
        """Test creating a valid ego charter."""
        charter = EgoCharter(
            version="1.0.0",
            ego=EgoConfig(
                role="Engineer",
                tone=ToneConfig(voice="professional", verbosity="balanced"),
            ),
        )
        assert charter.version == "1.0.0"
        assert charter.ego.role == "Engineer"