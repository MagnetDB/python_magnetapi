"""Tests for list command."""

import argparse
import pytest
from unittest.mock import Mock, patch

from python_magnetapi.cli.commands.list import ListCommand
from python_magnetapi.cli.context import CLIContext


def make_context():
    ctx = Mock(spec=CLIContext)
    ctx.session = Mock()
    ctx.web = "http://test:8000"
    ctx.headers = {"Authorization": "test-key"}
    ctx.debug = False
    return ctx


def test_list_command_execution():
    """Test list command executes correctly."""
    context = make_context()

    with patch("python_magnetapi.utils.get_list") as mock_get_list:
        mock_get_list.return_value = {"M10": 1, "M11": 2}

        cmd = ListCommand()
        args = Mock()
        args.mtype = "magnet"
        args.filters = None

        exit_code = cmd.execute(args, context)

        assert exit_code == 0
        mock_get_list.assert_called_once()


def test_list_command_parser_configuration():
    """Test list command parser configuration."""
    parser = argparse.ArgumentParser()
    cmd = ListCommand()
    cmd.configure_parser(parser)

    args = parser.parse_args(["--mtype", "part"])
    assert args.mtype == "part"


def test_list_command_default_mtype():
    """Test list command defaults to magnet."""
    parser = argparse.ArgumentParser()
    cmd = ListCommand()
    cmd.configure_parser(parser)

    args = parser.parse_args([])
    assert args.mtype == "magnet"


def test_list_command_with_filter():
    """Test list command parses filter arguments."""
    parser = argparse.ArgumentParser()
    cmd = ListCommand()
    cmd.configure_parser(parser)

    args = parser.parse_args(["--filter", "status=active"])
    assert args.filters == ["status=active"]


def test_list_command_name_and_help():
    """Test list command metadata."""
    cmd = ListCommand()
    assert cmd.name == "list"
    assert cmd.help
