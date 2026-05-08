"""Tests for the analysis subpackage registry (no heavy deps required)."""

import pytest
from python_magnetapi.analysis import get, names, register, _REGISTRY


BUILTIN_ANALYSES = ["inductances", "flow_params", "hoop_stress", "hoop_stress_parallel"]

EXPECTED_MTYPES = {
    "inductances": ["magnet", "site"],
    "flow_params": ["magnet"],
    "hoop_stress": ["part"],
    "hoop_stress_parallel": ["part"],
}


def test_builtin_names_present():
    registered = names()
    for name in BUILTIN_ANALYSES:
        assert name in registered


def test_unknown_name_returns_none():
    assert get("nonexistent_analysis") is None


def test_builtin_mtypes_metadata():
    # Read mtypes directly from _REGISTRY — no module import, no heavy deps.
    for name, expected in EXPECTED_MTYPES.items():
        assert name in _REGISTRY, f"{name} not in registry"
        assert _REGISTRY[name]["mtypes"] == expected


def test_builtin_function_name_metadata():
    # Each built-in should declare "compute" as its entry point.
    for name in BUILTIN_ANALYSES:
        assert _REGISTRY[name]["function"] == "compute"


@pytest.mark.parametrize("name", BUILTIN_ANALYSES)
def test_builtin_has_compute(name):
    """Verify the compute callable loads; skip if optional deps are absent."""
    pytest.importorskip(
        _REGISTRY[name]["module"].lstrip("."),
        reason=f"optional deps for {name!r} not installed",
    )
    entry = get(name)
    assert callable(entry["compute"])


def test_register_custom():
    import types
    import sys

    dummy = types.ModuleType("dummy_mod")
    dummy.run = lambda: "ok"
    sys.modules["dummy_mod"] = dummy

    try:
        register("custom_test", module="dummy_mod", function="run", mtypes=["site"], help="test")
        assert "custom_test" in names()
        entry = get("custom_test")
        assert entry["compute"]() == "ok"
        assert entry["mtypes"] == ["site"]
    finally:
        del sys.modules["dummy_mod"]
        _REGISTRY.pop("custom_test", None)
