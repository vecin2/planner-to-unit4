import pytest

from planner_to_unit4.entrypoints.submit_budget_variance_config import validate_config


def _base_config() -> dict[str, object]:
    return {
        "source_table_name": "source.table",
        "version": "ADJ",
        "batch": "WKD",
        "endpoint": "https://example.test/service.svc",
        "username": "user",
        "client": "bi",
        "password": "secret",
        "segment_monitoring_table": "planner_to_unit4.segment_monitoring",
    }


def test_validate_config_applies_defaults() -> None:
    validated = validate_config(_base_config())

    assert validated["max_segment_size"] == 12000
    assert validated["timeout"] == 90
    assert validated["max_records"] is None


def test_validate_config_rejects_missing_required_keys() -> None:
    config = _base_config()
    config.pop("endpoint")

    with pytest.raises(ValueError, match=r"missing keys=\['endpoint'\]"):
        validate_config(config)


def test_validate_config_rejects_unknown_keys() -> None:
    config = _base_config()
    config["extra"] = "value"

    with pytest.raises(ValueError, match=r"unknown keys=\['extra'\]"):
        validate_config(config)


def test_validate_config_rejects_invalid_types() -> None:
    config = _base_config()
    config["endpoint"] = 123
    config["max_records"] = "10"
    config["max_segment_size"] = True

    with pytest.raises(ValueError) as excinfo:
        validate_config(config)

    message = str(excinfo.value)
    assert "invalid types={" in message
    assert "endpoint': 'int'" in message
    assert "max_records': 'str'" in message
    assert "max_segment_size': 'bool'" in message


def test_validate_config_rejects_invalid_ranges() -> None:
    config = _base_config()
    config["max_segment_size"] = 0
    config["timeout"] = -1
    config["max_records"] = 0

    with pytest.raises(ValueError) as excinfo:
        validate_config(config)

    message = str(excinfo.value)
    assert "invalid ranges={" in message
    assert "max_segment_size': 0" in message
    assert "timeout': -1" in message
    assert "max_records': 0" in message
