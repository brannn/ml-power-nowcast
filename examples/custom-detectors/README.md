# Custom Detectors Example

This example demonstrates how to create custom detectors for EgoKit, allowing you to implement organization-specific validation logic beyond the built-in detectors.

## Overview

Custom detectors enable you to:
- Implement company-specific coding standards
- Integrate with external tools and services
- Create domain-specific validations
- Build complex multi-file analysis
- Add AI-powered code review

## Detector Structure

Each detector is a Python module that implements the detector protocol:

```python
from pathlib import Path
from typing import List
from egokit.detectors.base import DetectorBase
from egokit.models import DetectionResult, Severity

class CustomDetector(DetectorBase):
    """Your custom detector implementation."""
    
    def can_handle_file(self, file_path: Path) -> bool:
        """Determine if this detector should process the file."""
        return file_path.suffix in ['.py', '.js', '.ts']
    
    def detect_violations(self, content: str, file_path: Path) -> List[DetectionResult]:
        """Analyze content and return violations."""
        violations = []
        # Your detection logic here
        return violations
```

## Example Detectors Included

### 1. TODO Comment Detector
Finds TODO/FIXME comments that should be tracked as issues

### 2. Database Query Complexity Detector
Identifies potentially slow or complex database queries

### 3. API Rate Limit Detector
Ensures API endpoints have rate limiting configured

### 4. Import Organization Detector
Validates import statement organization and grouping

### 5. Secret Pattern Detector
Advanced secret detection using entropy analysis

### 6. Business Logic Detector
Domain-specific validations for business rules

### 7. Performance Pattern Detector
Identifies common performance anti-patterns

### 8. Dependency Security Detector
Checks dependencies against vulnerability databases

## Installation

### 1. Create Detector Directory

```bash
mkdir -p .egokit/policy-registry/detectors
```

### 2. Add Custom Detector

Create `.egokit/policy-registry/detectors/todo_comments.py`:

```python
from pathlib import Path
from typing import List
import re
from egokit.detectors.base import DetectorBase
from egokit.models import DetectionResult, Severity

class TodoCommentDetector(DetectorBase):
    """Detects TODO and FIXME comments in code."""
    
    def can_handle_file(self, file_path: Path) -> bool:
        """Handle common code files."""
        return file_path.suffix in [
            '.py', '.js', '.ts', '.java', '.go', 
            '.rs', '.cpp', '.c', '.cs', '.rb'
        ]
    
    def detect_violations(self, content: str, file_path: Path) -> List[DetectionResult]:
        """Find TODO/FIXME comments."""
        violations = []
        lines = content.split('\n')
        
        # Regex to find TODO, FIXME, HACK, XXX comments
        pattern = re.compile(
            r'(?:#|//|/\*)\s*(TODO|FIXME|HACK|XXX)\s*:?\s*(.+)',
            re.IGNORECASE
        )
        
        for line_num, line in enumerate(lines, 1):
            match = pattern.search(line)
            if match:
                comment_type = match.group(1).upper()
                comment_text = match.group(2).strip()
                
                # Determine severity based on type
                if comment_type in ['FIXME', 'XXX']:
                    severity = Severity.WARNING
                elif comment_type == 'HACK':
                    severity = Severity.CRITICAL
                else:  # TODO
                    severity = Severity.INFO
                
                violations.append(DetectionResult(
                    rule_id=f"TODO-{comment_type}",
                    severity=severity,
                    message=f"{comment_type} comment found: {comment_text}",
                    file_path=file_path,
                    line_number=line_num,
                    column_number=match.start() + 1,
                    suggestion=f"Create issue to track: {comment_text}"
                ))
        
        return violations
```

### 3. Register in Charter

```yaml
# charter.yaml
scopes:
  global:
    code_quality:
      - id: CUSTOM-001
        rule: "TODO comments must be tracked as issues"
        severity: warning
        detector: custom.todo_comments.v1
```

## Advanced Detector Examples

### Database Query Complexity Detector

```python
class DatabaseQueryDetector(DetectorBase):
    """Detects complex or potentially slow database queries."""
    
    def detect_violations(self, content: str, file_path: Path) -> List[DetectionResult]:
        violations = []
        
        # Check for N+1 query patterns
        if self._has_n_plus_one_pattern(content):
            violations.append(DetectionResult(
                rule_id="DB-N+1",
                severity=Severity.WARNING,
                message="Potential N+1 query pattern detected",
                suggestion="Use eager loading or batch queries"
            ))
        
        # Check for missing indexes
        if self._has_unindexed_query(content):
            violations.append(DetectionResult(
                rule_id="DB-INDEX",
                severity=Severity.WARNING,
                message="Query on potentially unindexed field",
                suggestion="Ensure database indexes exist for queried fields"
            ))
        
        # Check for SELECT *
        if "SELECT *" in content or "select *" in content:
            violations.append(DetectionResult(
                rule_id="DB-SELECT-STAR",
                severity=Severity.INFO,
                message="Avoid SELECT *, specify needed columns",
                suggestion="List specific columns needed"
            ))
        
        return violations
```

### API Rate Limit Detector

```python
class RateLimitDetector(DetectorBase):
    """Ensures API endpoints have rate limiting."""
    
    def detect_violations(self, content: str, file_path: Path) -> List[DetectionResult]:
        violations = []
        
        # For Python FastAPI
        if "@app.post" in content or "@app.get" in content:
            if "@rate_limit" not in content:
                violations.append(DetectionResult(
                    rule_id="API-RATE-LIMIT",
                    severity=Severity.WARNING,
                    message="API endpoint missing rate limiting",
                    suggestion="Add @rate_limit decorator"
                ))
        
        # For Express.js
        if "router.post" in content or "router.get" in content:
            if "rateLimit" not in content:
                violations.append(DetectionResult(
                    rule_id="API-RATE-LIMIT",
                    severity=Severity.WARNING,
                    message="API endpoint missing rate limiting",
                    suggestion="Add rate limiting middleware"
                ))
        
        return violations
```

### Secret Entropy Detector

```python
import math
import re

class EntropySecretDetector(DetectorBase):
    """Detects high-entropy strings that might be secrets."""
    
    def calculate_entropy(self, string: str) -> float:
        """Calculate Shannon entropy of a string."""
        if not string:
            return 0.0
        
        prob = {}
        for char in string:
            prob[char] = prob.get(char, 0) + 1
        
        entropy = 0.0
        for count in prob.values():
            p = count / len(string)
            if p > 0:
                entropy -= p * math.log2(p)
        
        return entropy
    
    def detect_violations(self, content: str, file_path: Path) -> List[DetectionResult]:
        violations = []
        
        # Find potential secret patterns
        patterns = [
            (r'["\']([A-Za-z0-9+/]{40,})["\']', "Possible base64 secret"),
            (r'["\']([a-f0-9]{32,})["\']', "Possible hex secret"),
            (r'api[_-]?key\s*=\s*["\']([^"\']+)["\']', "API key detected"),
            (r'token\s*=\s*["\']([^"\']+)["\']', "Token detected"),
        ]
        
        for pattern, description in patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                secret_candidate = match.group(1)
                entropy = self.calculate_entropy(secret_candidate)
                
                # High entropy indicates possible secret
                if entropy > 4.5:
                    violations.append(DetectionResult(
                        rule_id="SECRET-ENTROPY",
                        severity=Severity.CRITICAL,
                        message=f"{description} with high entropy ({entropy:.2f})",
                        file_path=file_path,
                        line_number=content[:match.start()].count('\n') + 1,
                        suggestion="Move to environment variable or secret manager"
                    ))
        
        return violations
```

### Business Logic Detector

```python
class BusinessLogicDetector(DetectorBase):
    """Validates business-specific rules."""
    
    def detect_violations(self, content: str, file_path: Path) -> List[DetectionResult]:
        violations = []
        
        # Example: Ensure price calculations include tax
        if "calculate_price" in content:
            if "tax" not in content.lower():
                violations.append(DetectionResult(
                    rule_id="BIZ-TAX",
                    severity=Severity.CRITICAL,
                    message="Price calculation missing tax computation",
                    suggestion="Include tax calculation in pricing logic"
                ))
        
        # Example: Validate currency handling
        if "amount" in content and "currency" not in content:
            violations.append(DetectionResult(
                rule_id="BIZ-CURRENCY",
                severity=Severity.WARNING,
                message="Monetary amount without currency specification",
                suggestion="Always specify currency with monetary amounts"
            ))
        
        # Example: Ensure audit logging for sensitive operations
        if any(op in content for op in ["delete_user", "transfer_funds", "change_permissions"]):
            if "audit_log" not in content:
                violations.append(DetectionResult(
                    rule_id="BIZ-AUDIT",
                    severity=Severity.CRITICAL,
                    message="Sensitive operation missing audit logging",
                    suggestion="Add audit logging for compliance"
                ))
        
        return violations
```

## External Tool Integration

### Integrating with Semgrep

```python
import subprocess
import json

class SemgrepDetector(DetectorBase):
    """Runs Semgrep rules as a detector."""
    
    def detect_violations(self, content: str, file_path: Path) -> List[DetectionResult]:
        violations = []
        
        # Run Semgrep on the file
        try:
            result = subprocess.run(
                ["semgrep", "--json", "--config=auto", str(file_path)],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                for finding in data.get("results", []):
                    violations.append(DetectionResult(
                        rule_id=finding["check_id"],
                        severity=self._map_severity(finding["severity"]),
                        message=finding["message"],
                        file_path=file_path,
                        line_number=finding["start"]["line"],
                        suggestion=finding.get("fix", "Review and fix manually")
                    ))
        except Exception as e:
            # Handle gracefully if Semgrep not installed
            pass
        
        return violations
    
    def _map_severity(self, semgrep_severity: str) -> Severity:
        mapping = {
            "ERROR": Severity.CRITICAL,
            "WARNING": Severity.WARNING,
            "INFO": Severity.INFO
        }
        return mapping.get(semgrep_severity, Severity.INFO)
```

## Multi-File Analysis

### Cross-Reference Detector

```python
class CrossReferenceDetector(DetectorBase):
    """Detects broken references across files."""
    
    def __init__(self):
        self.symbol_map = {}  # Track defined symbols
        self.reference_map = {}  # Track symbol references
    
    def analyze_project(self, project_path: Path) -> List[DetectionResult]:
        """Analyze entire project for cross-references."""
        violations = []
        
        # First pass: collect all defined symbols
        for py_file in project_path.rglob("*.py"):
            self._collect_symbols(py_file)
        
        # Second pass: check all references
        for py_file in project_path.rglob("*.py"):
            violations.extend(self._check_references(py_file))
        
        return violations
    
    def _collect_symbols(self, file_path: Path):
        """Collect function and class definitions."""
        # Parse AST and collect definitions
        pass
    
    def _check_references(self, file_path: Path) -> List[DetectionResult]:
        """Check if all imports and references are valid."""
        # Parse imports and validate against symbol_map
        pass
```

## Testing Custom Detectors

### Unit Test Example

```python
import pytest
from pathlib import Path
from policy_registry.detectors.todo_comments import TodoCommentDetector

def test_todo_detector():
    detector = TodoCommentDetector()
    
    content = """
    def process():
        # TODO: Add error handling
        data = fetch_data()
        # FIXME: This is broken
        return data
    """
    
    violations = detector.detect_violations(content, Path("test.py"))
    
    assert len(violations) == 2
    assert violations[0].rule_id == "TODO-TODO"
    assert violations[0].severity == Severity.INFO
    assert violations[1].rule_id == "TODO-FIXME"
    assert violations[1].severity == Severity.WARNING
```

### Integration Test

```python
def test_detector_with_ego_validate():
    """Test detector works with ego validate command."""
    # Create test file with violations
    test_file = Path("test_todo.py")
    test_file.write_text("# TODO: Fix this later")
    
    # Run ego validate
    result = subprocess.run(
        ["ego", "validate", str(test_file)],
        capture_output=True
    )
    
    assert "TODO-TODO" in result.stdout.decode()
```

## Performance Considerations

### Async Detectors

For I/O-bound operations:

```python
import asyncio

class AsyncDetector(DetectorBase):
    """Async detector for external API calls."""
    
    async def detect_violations_async(self, content: str, file_path: Path):
        """Async violation detection."""
        async with aiohttp.ClientSession() as session:
            # Make async API calls
            pass
    
    def detect_violations(self, content: str, file_path: Path):
        """Wrapper to run async detector."""
        return asyncio.run(self.detect_violations_async(content, file_path))
```

### Caching Results

```python
from functools import lru_cache

class CachedDetector(DetectorBase):
    """Detector with result caching."""
    
    @lru_cache(maxsize=100)
    def detect_violations(self, content: str, file_path: Path):
        """Cached violation detection."""
        # Expensive detection logic
        pass
```

## Deployment

### Package Structure

```
.egokit/policy-registry/
├── detectors/
│   ├── __init__.py
│   ├── todo_comments.py
│   ├── database_queries.py
│   ├── api_security.py
│   └── business_logic.py
├── tests/
│   ├── test_todo_detector.py
│   └── test_database_detector.py
└── requirements.txt
```

### Requirements

```txt
# requirements.txt for custom detectors
egokit>=0.1.0
ast
regex
aiohttp  # for async detectors
semgrep  # for semgrep integration
bandit   # for security analysis
```

## Best Practices

### 1. Clear Rule IDs
Use prefixed rule IDs to avoid conflicts:
- `CUSTOM-TODO-001`
- `CUSTOM-DB-001`
- `CUSTOM-API-001`

### 2. Meaningful Messages
Provide actionable feedback:
```python
DetectionResult(
    message="Database query missing index on 'user_id' field",
    suggestion="Add index: CREATE INDEX idx_user_id ON orders(user_id)"
)
```

### 3. Performance
- Cache expensive operations
- Use early returns
- Limit regex complexity
- Consider file size limits

### 4. Error Handling
```python
def detect_violations(self, content: str, file_path: Path):
    try:
        # Detection logic
    except Exception as e:
        # Log but don't crash
        logger.warning(f"Detector failed: {e}")
        return []
```

### 5. Documentation
Document what your detector checks:
```python
class CustomDetector(DetectorBase):
    """
    Detects X in Y files.
    
    Checks for:
    - Condition A
    - Pattern B
    - Issue C
    
    Configuration:
    - threshold: Minimum score to trigger
    - strict: Enable strict mode
    """
```

## Sharing Detectors

### Publishing to PyPI

```python
# setup.py
setup(
    name="egokit-custom-detectors",
    packages=["custom_detectors"],
    entry_points={
        "egokit.detectors": [
            "todo=custom_detectors.todo:TodoDetector",
            "database=custom_detectors.db:DatabaseDetector",
        ]
    }
)
```

### Community Registry

Share detectors with the community:
1. Create GitHub repository
2. Add to EgoKit detector registry
3. Document usage and examples
4. Accept contributions

## Troubleshooting

### Detector Not Loading
- Check module naming matches charter reference
- Verify Python path includes detector directory
- Check for import errors in detector module

### False Positives
- Refine detection patterns
- Add context awareness
- Implement allowlist/ignorelist

### Performance Issues
- Profile detector execution
- Add caching where appropriate
- Consider async for I/O operations

## Next Steps

1. Start with simple pattern matching
2. Add context-aware analysis
3. Integrate external tools
4. Build domain-specific validators
5. Share with your team