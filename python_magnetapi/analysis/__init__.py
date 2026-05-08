"""
Registry-based analysis subpackage.

Built-in analyses (inductances, flow_params, hoop_stress, hoop_stress_parallel)
are registered below.  Third-party packages can extend the registry by:

  1. Calling ``register()`` directly after importing this package.
  2. Declaring an entry point in their pyproject.toml::

       [project.entry-points."python_magnetapi.analysis"]
       my_analysis = "my_package.my_module"

     The entry point value must be an importable module path; the module must
     expose a ``compute`` function (or override ``function`` in the register call).

Heavy optional dependencies (magnettools, python_magnetcooling, …) are imported
lazily — only when ``get(name)`` is actually called.
"""

from __future__ import annotations

import importlib
from typing import Any

_REGISTRY: dict[str, dict[str, Any]] = {}


def register(
    name: str,
    *,
    module: str,
    function: str = "compute",
    mtypes: list[str],
    help: str = "",
) -> None:
    """Register an analysis by name.

    Parameters
    ----------
    name:
        Registry key used to look up this analysis (e.g. ``"hoop_stress"``).
    module:
        Importable module path, relative to this package (e.g. ``".hoop_stress"``)
        or absolute (``"mypkg.mymodule"``).
    function:
        Name of the callable inside *module* to use as the compute entry point.
    mtypes:
        Object types this analysis supports (e.g. ``["part"]``).  An empty list
        means "unrestricted"; the caller is responsible for validation.
    help:
        One-line description shown in CLI listings.
    """
    _REGISTRY[name] = {
        "module": module,
        "function": function,
        "mtypes": mtypes,
        "help": help,
    }


def get(name: str) -> dict[str, Any] | None:
    """Lazy-load and return the analysis entry, or *None* if unknown.

    Returns a dict with keys ``compute`` (callable), ``mtypes`` (list[str]),
    and ``help`` (str).  The module is imported on the first call.
    """
    entry = _REGISTRY.get(name)
    if entry is None:
        return None
    mod = importlib.import_module(entry["module"], package=__package__)
    return {
        "compute": getattr(mod, entry["function"]),
        "mtypes": entry["mtypes"],
        "help": entry["help"],
    }


def names() -> list[str]:
    """Return the names of all registered analyses."""
    return list(_REGISTRY.keys())


# ---------------------------------------------------------------------------
# Built-in analyses
# ---------------------------------------------------------------------------

register(
    "inductances",
    module=".inductances",
    mtypes=["magnet", "site"],
    help="Self and mutual inductances",
)
register(
    "flow_params",
    module=".flow_params",
    mtypes=["magnet"],
    help="Flow parameters from records",
)
register(
    "hoop_stress",
    module=".hoop_stress",
    mtypes=["part"],
    help="Hoop stress history (sequential)",
)
register(
    "hoop_stress_parallel",
    module=".hoop_stress_parallel",
    mtypes=["part"],
    help="Hoop stress history (parallel)",
)

# ---------------------------------------------------------------------------
# Third-party extension via entry points
# ---------------------------------------------------------------------------

try:
    from importlib.metadata import entry_points as _entry_points

    for _ep in _entry_points(group="python_magnetapi.analysis"):
        register(_ep.name, module=_ep.value, mtypes=[], help=_ep.name)
except Exception:
    pass
