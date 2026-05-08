"""
Smoke tests for python_magnetapi.

These tests are entirely offline (no server required).  They verify:
- package structure and imports
- version string is set
- public API signatures are intact
- exception hierarchy
- utility helpers with mocked HTTP
- setup_logging callable
"""

import inspect
import json
import logging
from unittest.mock import MagicMock
import requests

import pytest


# ---------------------------------------------------------------------------
# Package import & version
# ---------------------------------------------------------------------------

@pytest.mark.smoke
class TestPackageImport:
    def test_package_importable(self):
        import python_magnetapi  # noqa: F401

    def test_version_set(self):
        import python_magnetapi

        assert python_magnetapi.__version__ != ""

    def test_utils_importable(self):
        from python_magnetapi import utils  # noqa: F401

    def test_exceptions_importable(self):
        from python_magnetapi import exceptions  # noqa: F401

    def test_submodule_imports(self):
        from python_magnetapi import (  # noqa: F401
            attachment,
            geometry,
            magnet,
            material,
            part,
            record,
            site,
        )


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------

@pytest.mark.smoke
class TestExceptions:
    def test_base_exception(self):
        from python_magnetapi.exceptions import MagnetAPIException

        exc = MagnetAPIException("test error", status_code=404)
        assert "test error" in str(exc)
        assert exc.context["status_code"] == 404

    def test_authentication_error_is_base(self):
        from python_magnetapi.exceptions import AuthenticationError, MagnetAPIException

        assert issubclass(AuthenticationError, MagnetAPIException)

    def test_authorization_error_is_base(self):
        from python_magnetapi.exceptions import AuthorizationError, MagnetAPIException

        assert issubclass(AuthorizationError, MagnetAPIException)

    def test_server_error_is_base(self):
        from python_magnetapi.exceptions import ServerError, MagnetAPIException

        assert issubclass(ServerError, MagnetAPIException)

    def test_resource_conflict_error_is_base(self):
        from python_magnetapi.exceptions import ResourceConflictError, MagnetAPIException

        assert issubclass(ResourceConflictError, MagnetAPIException)


# ---------------------------------------------------------------------------
# setup_logging
# ---------------------------------------------------------------------------

@pytest.mark.smoke
class TestSetupLogging:
    def test_callable(self):
        from python_magnetapi.utils import setup_logging

        assert callable(setup_logging)

    def test_accepts_level_string(self):
        from python_magnetapi.utils import setup_logging

        # Should not raise
        setup_logging("WARNING")

    def test_accepts_log_file_param(self):
        from python_magnetapi.utils import setup_logging

        sig = inspect.signature(setup_logging)
        assert "log_file" in sig.parameters

    def test_invalid_level_falls_back_to_warning(self):
        from python_magnetapi.utils import setup_logging

        root = logging.getLogger()
        root.handlers.clear()
        setup_logging("NOTAVALIDLEVEL")
        # getattr with default returns WARNING for unknown names
        assert root.level == logging.WARNING


# ---------------------------------------------------------------------------
# get_list signature & offline behaviour
# ---------------------------------------------------------------------------

@pytest.mark.smoke
class TestGetListOffline:
    def _mock_session(self, items=None, status=200, last_page=1):
        items = items or [{"name": "obj1", "id": 1}]
        payload = {"items": items, "current_page": 1, "last_page": last_page}
        resp = MagicMock()
        resp.status_code = status
        resp.text = json.dumps(payload)
        resp.json.return_value = payload if status == 200 else {"detail": "error"}
        mock = MagicMock(spec=requests.Session)
        mock.get.return_value = resp
        return mock

    def test_signature_has_required_params(self):
        from python_magnetapi.utils import get_list

        sig = inspect.signature(get_list)
        assert "session" in sig.parameters
        assert "api_server" in sig.parameters
        assert "headers" in sig.parameters

    def test_signature_has_mtype_default(self):
        from python_magnetapi.utils import get_list

        sig = inspect.signature(get_list)
        assert sig.parameters["mtype"].default == "magnets"

    def test_returns_dict(self):
        from python_magnetapi.utils import get_list

        result = get_list(self._mock_session(), "http://test", headers={}, mtype="magnet")
        assert isinstance(result, dict)

    def test_returns_name_to_id_mapping(self):
        from python_magnetapi.utils import get_list

        items = [{"name": "alpha", "id": 42}]
        result = get_list(
            self._mock_session(items=items), "http://test", headers={}, mtype="magnet"
        )
        assert result == {"alpha": 42}

    def test_empty_on_http_error(self):
        from python_magnetapi.utils import get_list

        result = get_list(
            self._mock_session(status=404), "http://test", headers={}, mtype="magnet"
        )
        assert result == {}

    def test_filters_applied(self):
        from python_magnetapi.utils import get_list

        items = [
            {"name": "active_obj", "id": 1, "status": "active"},
            {"name": "inactive_obj", "id": 2, "status": "inactive"},
        ]
        result = get_list(
            self._mock_session(items=items),
            "http://test",
            headers={},
            mtype="magnet",
            filters={"status": "active"},
        )
        assert "active_obj" in result
        assert "inactive_obj" not in result

    def test_pagination_iterates_pages(self):
        from python_magnetapi.utils import get_list

        # page 1 returns current_page=1, last_page=2; page 2 returns current_page=2
        page1 = {"items": [{"name": "p1", "id": 1}], "current_page": 1, "last_page": 2}
        page2 = {"items": [{"name": "p2", "id": 2}], "current_page": 2, "last_page": 2}

        resp1 = MagicMock()
        resp1.status_code = 200
        resp1.text = json.dumps(page1)
        resp1.json.return_value = page1

        resp2 = MagicMock()
        resp2.status_code = 200
        resp2.text = json.dumps(page2)
        resp2.json.return_value = page2

        mock_session = MagicMock(spec=requests.Session)
        mock_session.get.side_effect = [resp1, resp2]

        result = get_list(mock_session, "http://test", headers={}, mtype="magnet")
        assert set(result.keys()) == {"p1", "p2"}


# ---------------------------------------------------------------------------
# get_fk_id helper
# ---------------------------------------------------------------------------

@pytest.mark.smoke
class TestGetFkId:
    def test_returns_id_when_present(self):
        from python_magnetapi.utils import get_fk_id

        obj = {"material_id": 7}
        assert get_fk_id(obj, "material") == 7

    def test_returns_none_when_absent(self):
        from python_magnetapi.utils import get_fk_id

        assert get_fk_id({}, "material") is None
