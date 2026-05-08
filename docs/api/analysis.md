# analysis

Registry-based analysis subpackage. Provides a lightweight mechanism for
registering, discovering, and lazily loading post-processing computations.
Heavy optional dependencies (`magnettools`, `python_magnetcooling`, …) are
only imported when an analysis is actually executed.

## Registry API

```{automodule} python_magnetapi.analysis
:members: register, get, names
:undoc-members:
:show-inheritance:
```

## Built-in analyses

```{toctree}
:maxdepth: 1

inductances
flow_params
hoop_stress
hoop_stress_parallel
```

## Extending the registry

New analyses can be added in two ways:

**At runtime** — call {func}`python_magnetapi.analysis.register` directly:

```python
from python_magnetapi.analysis import register

register(
    "my_analysis",
    module="my_package.my_module",
    mtypes=["magnet", "site"],
    help="My custom post-processing",
)
```

**Via entry points** — declare in `pyproject.toml` for automatic discovery
when the package is installed:

```toml
[project.entry-points."python_magnetapi.analysis"]
my_analysis = "my_package.my_module"
```

The target module must expose a `compute` function (or a different name
passed via the `function` argument to {func}`~python_magnetapi.analysis.register`).
