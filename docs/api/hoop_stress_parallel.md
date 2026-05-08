# hoop_stress_parallel

Parallelised drop-in replacement for {mod}`python_magnetapi.analysis.hoop_stress`.
Uses `concurrent.futures.ProcessPoolExecutor` to distribute per-record
computations across CPU cores. Statistics and plotting helpers are re-exported
from the sequential module unchanged.

```{automodule} python_magnetapi.analysis.hoop_stress_parallel
:members:
:undoc-members:
:show-inheritance:
```
