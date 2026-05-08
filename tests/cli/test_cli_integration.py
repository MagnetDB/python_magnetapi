"""Integration tests for CLI."""

import os
import pytest
from unittest.mock import patch, Mock

from python_magnetapi.cli import main


def test_cli_missing_api_key():
    """Test CLI raises AuthenticationError without API key."""
    from python_magnetapi.exceptions import AuthenticationError

    env = {k: v for k, v in os.environ.items() if k != "MAGNETDB_API_KEY"}
    with patch.dict(os.environ, env, clear=True):
        with pytest.raises(AuthenticationError):
            main(["list"])


def test_cli_no_command_returns_nonzero():
    """Test CLI returns non-zero exit code when no command given."""
    with patch.dict(os.environ, {"MAGNETDB_API_KEY": "test-key"}):
        exit_code = main([])
        assert exit_code != 0


def test_list_command_runs():
    """Test list command runs end-to-end with mocked HTTP."""
    with patch.dict(os.environ, {"MAGNETDB_API_KEY": "test-key"}):
        with patch("requests.Session") as mock_session_cls:
            mock_session = Mock()
            mock_session_cls.return_value.__enter__ = Mock(return_value=mock_session)
            mock_session_cls.return_value.__exit__ = Mock(return_value=False)

            with patch("python_magnetapi.utils.get_list") as mock_get_list:
                mock_get_list.return_value = {"M10": 1}

                exit_code = main(["--server", "localhost", "list", "--mtype", "magnet"])
                assert exit_code == 0
                mock_get_list.assert_called_once()


def test_process_command_runs():
    """Test process command returns 0 (not implemented stub)."""
    with patch.dict(os.environ, {"MAGNETDB_API_KEY": "test-key"}):
        with patch("requests.Session") as mock_session_cls:
            mock_session = Mock()
            mock_session.__enter__ = Mock(return_value=mock_session)
            mock_session.__exit__ = Mock(return_value=False)
            mock_session_cls.return_value = mock_session

            exit_code = main(["--server", "localhost", "process"])
            assert exit_code == 0


def test_view_command_not_found():
    """Test view command raises ResourceNotFoundError when object missing."""
    from python_magnetapi.exceptions import ResourceNotFoundError

    with patch.dict(os.environ, {"MAGNETDB_API_KEY": "test-key"}):
        with patch("requests.Session") as mock_session_cls:
            mock_session = Mock()
            mock_session.__enter__ = Mock(return_value=mock_session)
            mock_session.__exit__ = Mock(return_value=False)
            mock_session_cls.return_value = mock_session

            with patch("python_magnetapi.utils.get_list") as mock_get_list:
                mock_get_list.return_value = {}

                with pytest.raises(ResourceNotFoundError):
                    main(["--server", "localhost", "view", "--name", "nonexistent"])
