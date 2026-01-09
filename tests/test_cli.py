"""End-to-end tests for PMP CLI commands."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Tuple

import pytest

from pmp import cli
from pmp.output import as_yaml


def _write_backend_config(tmp_path: Path, backend: str) -> Tuple[Path, Path]:
    config_path = tmp_path / "config.toml"
    storage = tmp_path / ("store.db" if backend == "sqlite" else "store")
    config_path.write_text(
        "\n".join(
            [
                f'backend = "{backend}"',
                "",
                f"[backends.{backend}]",
                f'path = "{storage}"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    return config_path, storage


@pytest.mark.parametrize("backend_name", ["file", "sqlite"])
def test_cli_crud_workflow(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    backend_name: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Exercise add/get/update/list/delete for both backends."""
    config_path, _ = _write_backend_config(tmp_path, backend_name)
    monkeypatch.setenv("PMP_CONFIG_FILE", str(config_path))

    assert (
        cli.main(
            [
                "add",
                "demo",
                "--content",
                "initial content",
                "--tag",
                "alpha,beta",
                "--model",
                "gpt-4",
            ]
        )
        == 0
    )
    capsys.readouterr()

    assert cli.main(["get", "demo", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["version"] == 1
    assert payload["metadata"]["tags"] == ["alpha", "beta"]
    assert payload["metadata"]["model"] == "gpt-4"

    assert (
        cli.main(["edit", "demo", "--content", "second revision", "--tag", "alpha"])
        == 0
    )
    capsys.readouterr()

    assert cli.main(["list", "--format", "json"]) == 0
    listing = json.loads(capsys.readouterr().out)
    assert listing[0]["name"] == "demo"
    assert listing[0]["latest_version"] == 2

    assert cli.main(["list", "--long"]) == 0
    table_output = capsys.readouterr().out
    assert "demo" in table_output
    assert "2" in table_output

    assert cli.main(["delete", "demo", "--version", "1"]) == 0
    capsys.readouterr()

    assert cli.main(["get", "demo", "--format", "json"]) == 0
    latest = json.loads(capsys.readouterr().out)
    assert latest["version"] == 2
    assert latest["content"] == "second revision"

    assert cli.main(["delete", "demo", "--force"]) == 0
    capsys.readouterr()

    assert cli.main(["list", "--format", "json"]) == 0
    remaining = json.loads(capsys.readouterr().out)
    assert remaining == []

@pytest.mark.parametrize("backend_name", ["file", "sqlite"])
def test_cli_error_flows(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    backend_name: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Ensure duplicate operations and missing resources surface clear errors."""
    config_path, _ = _write_backend_config(tmp_path, backend_name)
    monkeypatch.setenv("PMP_CONFIG_FILE", str(config_path))

    assert cli.main(["add", "demo", "--content", "body"]) == 0
    capsys.readouterr()

    with pytest.raises(SystemExit) as duplicate_exit:
        cli.main(["add", "demo", "--content", "second"])
    assert duplicate_exit.value.code == 1
    duplicate_err = capsys.readouterr().err
    assert "already exists" in duplicate_err

    with pytest.raises(SystemExit) as missing_version_exit:
        cli.main(["delete", "demo", "--version", "42"])
    assert missing_version_exit.value.code == 1
    version_err = capsys.readouterr().err
    assert "does not exist" in version_err or "not found" in version_err

    with pytest.raises(SystemExit) as missing_prompt_exit:
        cli.main(["get", "ghost"])
    assert missing_prompt_exit.value.code == 1
    missing_err = capsys.readouterr().err
    assert "does not exist" in missing_err


def test_config_all_possible_values(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test setting and getting all possible config values."""
    config_file = tmp_path / "config.toml"
    monkeypatch.setenv("PMP_CONFIG_FILE", str(config_file))

    # Test top-level backend values
    for backend in ["file", "sqlite"]:
        assert cli.main(["config", "set", "backend", backend]) == 0
        capsys.readouterr()
        assert cli.main(["config", "get", "backend"]) == 0
        assert capsys.readouterr().out.strip() == backend

    # Test backends.file.path
    file_path = str(tmp_path / "file_store")
    assert cli.main(["config", "set", "backends.file.path", file_path]) == 0
    capsys.readouterr()
    assert cli.main(["config", "get", "backends.file.path"]) == 0
    assert capsys.readouterr().out.strip() == file_path

    # Test backends.sqlite.path
    sqlite_path = str(tmp_path / "sqlite_store.db")
    assert cli.main(["config", "set", "backends.sqlite.path", sqlite_path]) == 0
    capsys.readouterr()
    assert cli.main(["config", "get", "backends.sqlite.path"]) == 0
    assert capsys.readouterr().out.strip() == sqlite_path

    # Test backends.sqlite.database (alternative to path)
    sqlite_db = str(tmp_path / "database.db")
    assert cli.main(["config", "set", "backends.sqlite.database", sqlite_db]) == 0
    capsys.readouterr()
    assert cli.main(["config", "get", "backends.sqlite.database"]) == 0
    assert capsys.readouterr().out.strip() == sqlite_db


def test_config_value_types(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test setting config values with different types (string, boolean, int, float)."""
    config_file = tmp_path / "config.toml"
    monkeypatch.setenv("PMP_CONFIG_FILE", str(config_file))

    # Test string values
    assert cli.main(["config", "set", "backend", "file"]) == 0
    capsys.readouterr()
    assert cli.main(["config", "get", "backend"]) == 0
    assert capsys.readouterr().out.strip() == "file"

    # Test boolean values
    assert cli.main(["config", "set", "test.bool_true", "true"]) == 0
    capsys.readouterr()
    assert cli.main(["config", "get", "test.bool_true"]) == 0
    assert capsys.readouterr().out.strip() == "True"

    assert cli.main(["config", "set", "test.bool_false", "false"]) == 0
    capsys.readouterr()
    assert cli.main(["config", "get", "test.bool_false"]) == 0
    assert capsys.readouterr().out.strip() == "False"

    # Test integer values
    assert cli.main(["config", "set", "test.int_value", "42"]) == 0
    capsys.readouterr()
    assert cli.main(["config", "get", "test.int_value"]) == 0
    assert capsys.readouterr().out.strip() == "42"

    assert cli.main(["config", "set", "test.negative_int", "-10"]) == 0
    capsys.readouterr()
    assert cli.main(["config", "get", "test.negative_int"]) == 0
    assert capsys.readouterr().out.strip() == "-10"

    # Test float values
    assert cli.main(["config", "set", "test.float_value", "3.14"]) == 0
    capsys.readouterr()
    assert cli.main(["config", "get", "test.float_value"]) == 0
    assert capsys.readouterr().out.strip() == "3.14"

    assert cli.main(["config", "set", "test.negative_float", "-2.5"]) == 0
    capsys.readouterr()
    assert cli.main(["config", "get", "test.negative_float"]) == 0
    assert capsys.readouterr().out.strip() == "-2.5"


def test_config_nested_paths(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test deeply nested config paths."""
    config_file = tmp_path / "config.toml"
    monkeypatch.setenv("PMP_CONFIG_FILE", str(config_file))

    # Test deeply nested paths
    assert cli.main(["config", "set", "level1.level2.level3.value", "nested"]) == 0
    capsys.readouterr()
    assert cli.main(["config", "get", "level1.level2.level3.value"]) == 0
    assert capsys.readouterr().out.strip() == "nested"

    # Test multiple nested values
    assert cli.main(["config", "set", "level1.level2.another", "value2"]) == 0
    capsys.readouterr()
    assert cli.main(["config", "get", "level1.level2.another"]) == 0
    assert capsys.readouterr().out.strip() == "value2"

    # Verify both values exist
    assert cli.main(["config", "list"]) == 0
    config_output = capsys.readouterr().out
    assert "nested" in config_output
    assert "value2" in config_output


def test_config_default_values(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test getting non-existent config values returns None or raises error."""
    config_file = tmp_path / "config.toml"
    monkeypatch.setenv("PMP_CONFIG_FILE", str(config_file))

    # Test getting non-existent key raises error
    with pytest.raises(SystemExit) as exit_info:
        cli.main(["config", "get", "nonexistent.key"])
    assert exit_info.value.code == 1
    error_output = capsys.readouterr().err
    assert "not set" in error_output or "does not exist" in error_output


def test_config_path_expansion(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test that paths with ~ are properly handled."""
    config_file = tmp_path / "config.toml"
    monkeypatch.setenv("PMP_CONFIG_FILE", str(config_file))

    # Test path with tilde
    tilde_path = "~/.pmp/test_store"
    assert cli.main(["config", "set", "backends.file.path", tilde_path]) == 0
    capsys.readouterr()
    assert cli.main(["config", "get", "backends.file.path"]) == 0
    # The value should be stored as-is (expansion happens at runtime)
    assert capsys.readouterr().out.strip() == tilde_path

    # Test relative path
    relative_path = "./relative_store"
    assert cli.main(["config", "set", "backends.sqlite.path", relative_path]) == 0
    capsys.readouterr()
    assert cli.main(["config", "get", "backends.sqlite.path"]) == 0
    assert capsys.readouterr().out.strip() == relative_path

    # Test absolute path
    absolute_path = str(tmp_path / "absolute_store")
    assert cli.main(["config", "set", "backends.file.path", absolute_path]) == 0
    capsys.readouterr()
    assert cli.main(["config", "get", "backends.file.path"]) == 0
    assert capsys.readouterr().out.strip() == absolute_path


def test_config_list_output(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test that config list shows all set values correctly."""
    config_file = tmp_path / "config.toml"
    monkeypatch.setenv("PMP_CONFIG_FILE", str(config_file))

    # Set various config values
    assert cli.main(["config", "set", "backend", "file"]) == 0
    capsys.readouterr()
    assert (
        cli.main(["config", "set", "backends.file.path", str(tmp_path / "store")]) == 0
    )
    capsys.readouterr()
    assert (
        cli.main(["config", "set", "backends.sqlite.path", str(tmp_path / "db.db")])
        == 0
    )
    capsys.readouterr()

    # List config and verify all values are present
    assert cli.main(["config", "list"]) == 0
    config_output = capsys.readouterr().out

    assert 'backend = "file"' in config_output
    assert "[backends.file]" in config_output
    assert "[backends.sqlite]" in config_output


@pytest.mark.parametrize("backend_name", ["file", "sqlite"])
def test_cli_template_rendering(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    backend_name: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test template rendering in CLI commands."""
    config_path, _ = _write_backend_config(tmp_path, backend_name)
    monkeypatch.setenv("PMP_CONFIG_FILE", str(config_path))

    assert (
        cli.main(
            ["add", "demo", "--content", "Hello, {{name}}! You are {{age}} years old."]
        )
        == 0
    )
    capsys.readouterr()

    assert cli.main(["get", "demo", "--vars", "name=John", "age=30"]) == 0
    content = capsys.readouterr().out
    assert content == "Hello, John! You are 30 years old.\n"
