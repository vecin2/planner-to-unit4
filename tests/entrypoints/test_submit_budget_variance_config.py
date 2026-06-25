import pytest

from planner_to_unit4.entrypoints.submit_budget_variance import validate_config
from planner_to_unit4.entrypoints.submit_budget_variance import _format_submitter_config_log


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
    assert validated["segment_monitor_retention_days"] is None
    assert validated["timeout"] == 90
    assert validated["report_max_sample_rows"] == 10
    assert validated["artifact_save_mode"] == "on_failure"
    assert validated["soap_retry_retries"] == 0


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
    config["max_segment_size"] = True
    config["segment_monitor_retention_days"] = "7"
    config["report_max_sample_rows"] = False
    config["artifact_save_mode"] = 1
    config["soap_retry_retries"] = True

    with pytest.raises(ValueError) as excinfo:
        validate_config(config)

    message = str(excinfo.value)
    assert "invalid types={" in message
    assert "endpoint': 'int'" in message
    assert "max_segment_size': 'bool'" in message
    assert "segment_monitor_retention_days': 'str'" in message
    assert "report_max_sample_rows': 'bool'" in message
    assert "artifact_save_mode': 'int'" in message
    assert "soap_retry_retries': 'bool'" in message


def test_validate_config_rejects_invalid_ranges() -> None:
    config = _base_config()
    config["max_segment_size"] = 0
    config["segment_monitor_retention_days"] = 0
    config["timeout"] = -1
    config["report_max_sample_rows"] = 0
    config["soap_retry_retries"] = -1

    with pytest.raises(ValueError) as excinfo:
        validate_config(config)

    message = str(excinfo.value)
    assert "invalid ranges={" in message
    assert "max_segment_size': 0" in message
    assert "segment_monitor_retention_days': 0" in message
    assert "timeout': -1" in message
    assert "report_max_sample_rows': 0" in message
    assert "soap_retry_retries': -1" in message


def test_validate_config_rejects_invalid_values() -> None:
    config = _base_config()
    config["artifact_save_mode"] = "sometimes"

    with pytest.raises(ValueError) as excinfo:
        validate_config(config)

    message = str(excinfo.value)
    assert "invalid values={" in message
    assert "artifact_save_mode': 'sometimes'" in message


def test_format_submitter_config_log_redacts_password() -> None:
    validated = validate_config(_base_config())

    message = _format_submitter_config_log(
        validated=validated,
        artifact_fs_enabled=True,
        rows_filter_enabled=False,
    )

    assert "password='***'" in message
    assert "password='secret'" not in message
    assert "artifact_fs_enabled=True" in message
    assert "rows_filter_enabled=False" in message
