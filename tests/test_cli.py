"""Tests for the CLI interface."""

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from falgit.cli import main
from falgit.models.types import Commit, Status


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "Git-like version control" in result.output


def test_cli_init_success():
    runner = CliRunner()
    with patch("falgit.cli._connect") as mock_connect:
        mock_db = MagicMock()
        mock_connect.return_value = mock_db
        with patch("falgit.cli.FalgitRepo.init") as mock_init:
            mock_repo = MagicMock()
            mock_repo.status.return_value = Status()
            mock_repo.log.return_value = [
                Commit("abc123", "Initial", 0, None, True, "main")
            ]
            mock_init.return_value = mock_repo

            result = runner.invoke(main, ["init", "test_graph"])
            assert result.exit_code == 0
            assert "Initialized" in result.output


def test_cli_status_clean():
    runner = CliRunner()
    with patch("falgit.cli._connect") as mock_connect:
        mock_db = MagicMock()
        mock_connect.return_value = mock_db
        with patch("falgit.cli.FalgitRepo") as MockRepo:
            mock_repo = MagicMock()
            mock_repo.status.return_value = Status()
            MockRepo.return_value = mock_repo

            result = runner.invoke(main, ["status", "test_graph"])
            assert result.exit_code == 0
            assert "Nothing changed" in result.output


def test_cli_status_with_changes():
    runner = CliRunner()
    with patch("falgit.cli._connect") as mock_connect:
        mock_db = MagicMock()
        mock_connect.return_value = mock_db
        with patch("falgit.cli.FalgitRepo") as MockRepo:
            mock_repo = MagicMock()
            mock_repo.status.return_value = Status(
                added_nodes=["key1", "key2"],
                deleted_edges=["key3"],
            )
            MockRepo.return_value = mock_repo

            result = runner.invoke(main, ["status", "test_graph"])
            assert result.exit_code == 0
            assert "3 total" in result.output
