"""End-to-end tests for PMP CLI commands."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Tuple

import pytest

from pmp import cli


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
def test_cli_crud_workflow(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, backend_name: str, capsys: pytest.CaptureFixture[str]) -> None:
    """Exercise add/get/update/list/delete for both backends."""
    config_path, _ = _write_backend_config(tmp_path, backend_name)
    monkeypatch.setenv("PMP_CONFIG_FILE", str(config_path))

    assert cli.main(
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
    ) == 0
    capsys.readouterr()

    assert cli.main(["get", "demo", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["version"] == 1
    assert payload["metadata"]["tags"] == ["alpha", "beta"]
    assert payload["metadata"]["model"] == "gpt-4"

    assert cli.main(["update", "demo", "--content", "second revision", "--tag", "alpha"]) == 0
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


def test_config_commands_and_profiles(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Verify config set/get/list and profile management flow."""
    config_file = tmp_path / "config.toml"
    monkeypatch.setenv("PMP_CONFIG_FILE", str(config_file))

    assert cli.main(["config", "set", "backend", "file"]) == 0
    capsys.readouterr()

    assert cli.main(["config", "get", "backend"]) == 0
    assert capsys.readouterr().out.strip() == "file"

    sqlite_db = tmp_path / "remote.db"
    assert cli.main(
        [
            "config",
            "profile",
            "add",
            "remote",
            "--backend",
            "sqlite",
            "--path",
            str(sqlite_db),
        ]
    ) == 0
    capsys.readouterr()

    assert cli.main(["config", "profile", "use", "remote"]) == 0
    capsys.readouterr()

    assert cli.main(["config", "list"]) == 0
    config_text = capsys.readouterr().out
    assert "[profiles.remote]" in config_text
    assert 'backend = "sqlite"' in config_text
    assert str(sqlite_db) in config_text


@pytest.mark.parametrize("backend_name", ["file", "sqlite"])
def test_cli_error_flows(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, backend_name: str, capsys: pytest.CaptureFixture[str]
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
