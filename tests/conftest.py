"""
pytest configuration, fixtures and markers for python_magnetapi tests.

Integration tests require a running MagnetDB server.  They are skipped
automatically when the server is unreachable or the API key is missing.

Environment variables (can be provided via .envrc for direnv users):
    MAGNETDB_API_SERVER  – base URL of the API server
    MAGNETDB_API_KEY     – bearer token / API key
"""

import os
import re
import shlex

import pytest
import requests


# ---------------------------------------------------------------------------
# direnv / .envrc support
# ---------------------------------------------------------------------------

def _load_envrc(path: str = ".envrc") -> None:
    """Parse a simple .envrc file and inject missing variables into os.environ.

    Only ``export KEY=value`` lines are processed.  Values that are already
    present in the environment are left untouched so that real env vars
    always take precedence over .envrc defaults.
    """
    if not os.path.isfile(path):
        return
    export_re = re.compile(r"^\s*export\s+([A-Za-z_][A-Za-z0-9_]*)=(.*)")
    with open(path) as fh:
        for line in fh:
            m = export_re.match(line)
            if not m:
                continue
            key, raw_value = m.group(1), m.group(2).strip()
            if key in os.environ:
                continue  # real env var wins
            # strip surrounding quotes
            try:
                value = shlex.split(raw_value)[0] if raw_value else ""
            except ValueError:
                value = raw_value.strip("'\"")
            os.environ[key] = value


# Load .envrc once at collection time so fixtures can see the variables.
_load_envrc()


# ---------------------------------------------------------------------------
# Server availability check (cached for the whole session)
# ---------------------------------------------------------------------------

def _check_server(api_server: str, api_key: str | None) -> tuple[bool, str]:
    """Return (available, reason).  A HEAD/GET to the magnets endpoint is used."""
    if not api_key:
        return False, "MAGNETDB_API_KEY is not set"
    url = f"{api_server}/api/magnets?page=1"
    try:
        resp = requests.get(
            url,
            headers={"Authorization": api_key},
            timeout=5,
            verify=False,  # dev servers often use self-signed certs
        )
        if resp.status_code == 401:
            return False, f"API key rejected by {api_server} (HTTP 401)"
        if resp.status_code == 403:
            return False, f"API key forbidden on {api_server} (HTTP 403)"
        return True, ""
    except requests.exceptions.ConnectionError:
        return False, f"Cannot connect to {api_server}"
    except requests.exceptions.Timeout:
        return False, f"Connection to {api_server} timed out"


# ---------------------------------------------------------------------------
# Pytest hooks & fixtures
# ---------------------------------------------------------------------------

def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "integration: marks tests that require a running MagnetDB server "
        "(skipped when server is unreachable or API key is missing)",
    )
    config.addinivalue_line(
        "markers",
        "smoke: marks fast offline tests that do not require a server",
    )


@pytest.fixture(scope="session")
def magnetdb_env():
    """Return the API server URL and headers dict read from the environment."""
    server = os.getenv("MAGNETDB_API_SERVER", "https://api.magnetdb-dev.local")
    key = os.getenv("MAGNETDB_API_KEY")
    return {
        "api_server": server,
        "api_key": key,
        "headers": {"Authorization": key} if key else {},
    }


@pytest.fixture(scope="session")
def integration_session(magnetdb_env):
    """A requests.Session pre-configured for integration tests.

    The test is skipped automatically when the server is unavailable.
    """
    available, reason = _check_server(
        magnetdb_env["api_server"], magnetdb_env["api_key"]
    )
    if not available:
        pytest.skip(f"Integration test skipped: {reason}")
    s = requests.Session()
    s.headers.update(magnetdb_env["headers"])
    yield s
    s.close()


def pytest_collection_modifyitems(config, items):
    """Auto-skip integration tests when the server is not available."""
    server = os.getenv("MAGNETDB_API_SERVER", "https://api.magnetdb-dev.local")
    key = os.getenv("MAGNETDB_API_KEY")
    available, reason = _check_server(server, key)
    if not available:
        skip_mark = pytest.mark.skip(reason=f"Integration test skipped: {reason}")
        for item in items:
            if item.get_closest_marker("integration"):
                item.add_marker(skip_mark)
