import pytest

from planner_to_unit4.entrypoints.archive_file import validate_config


def _base_config() -> dict[str, object]:
    return {
        "archive_root_path": "Files/FPA_Ingestion_Test/archive",
    }


def test_validate_config_applies_defaults() -> None:
    validated = validate_config(_base_config())

    assert validated["archive_root_path"] == "Files/FPA_Ingestion_Test/archive"
    assert validated["archive_retention_days"] is None
    assert validated["archive_write_mode"] == "copy"


def test_validate_config_rejects_missing_required_keys() -> None:
    config = _base_config()
    config.pop("archive_root_path")

    with pytest.raises(ValueError, match=r"missing keys=\['archive_root_path'\]"):
        validate_config(config)


def test_validate_config_rejects_unknown_keys() -> None:
    config = _base_config()
    config["extra"] = "value"

    with pytest.raises(ValueError, match=r"unknown keys=\['extra'\]"):
        validate_config(config)


def test_validate_config_rejects_invalid_types() -> None:
    config = _base_config()
    config["archive_root_path"] = 123
    config["archive_retention_days"] = "7"
    config["archive_write_mode"] = 1

    with pytest.raises(ValueError) as excinfo:
        validate_config(config)

    message = str(excinfo.value)
    assert "invalid types={" in message
    assert "archive_root_path': 'int'" in message
    assert "archive_retention_days': 'str'" in message
    assert "archive_write_mode': 'int'" in message


def test_validate_config_rejects_invalid_ranges() -> None:
    config = _base_config()
    config["archive_retention_days"] = 0

    with pytest.raises(ValueError) as excinfo:
        validate_config(config)

    message = str(excinfo.value)
    assert "invalid ranges={" in message
    assert "archive_retention_days': 0" in message


def test_validate_config_rejects_invalid_values() -> None:
    config = _base_config()
    config["archive_write_mode"] = "rename"

    with pytest.raises(ValueError) as excinfo:
        validate_config(config)

    message = str(excinfo.value)
    assert "invalid values={" in message
    assert "archive_write_mode': 'rename'" in message


def test_validate_config_accepts_move_write_mode() -> None:
    config = _base_config()
    config["archive_write_mode"] = "move"

    validated = validate_config(config)

    assert validated["archive_write_mode"] == "move"
