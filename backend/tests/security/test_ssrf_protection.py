"""SSRF and scan target validation tests."""

import pytest

from app.services.target_validation import TargetValidationError, TargetValidator


@pytest.fixture
def validator():
    return TargetValidator()


def test_blocks_localhost(validator: TargetValidator):
    with pytest.raises(TargetValidationError) as exc:
        validator.validate("127.0.0.1", "ip")
    assert exc.value.code in ("BLOCKED_LOCALHOST", "BLOCKED_PRIVATE_IP")


def test_blocks_private_ip(validator: TargetValidator):
    with pytest.raises(TargetValidationError) as exc:
        validator.validate("192.168.1.1", "ip")
    assert exc.value.code == "BLOCKED_PRIVATE_IP"


def test_blocks_metadata_endpoint(validator: TargetValidator):
    with pytest.raises(TargetValidationError):
        validator.validate("http://169.254.169.254/latest/meta-data/", "url")


def test_blocks_internal_cidr(validator: TargetValidator):
    with pytest.raises(TargetValidationError):
        validator.validate("10.0.0.0/8", "cidr")


def test_allows_public_domain(validator: TargetValidator):
    result = validator.validate("https://example.com", "url")
    assert "example.com" in result


def test_blocks_shell_metacharacters(validator: TargetValidator):
    from app.scanners.base import BaseScannerAdapter

    class TestAdapter(BaseScannerAdapter):
        scanner_type = "test"

        async def scan(self, target, options=None):
            pass

    adapter = TestAdapter()
    with pytest.raises(ValueError):
        adapter.sanitize_target("example.com; rm -rf /")
