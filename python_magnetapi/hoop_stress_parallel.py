"""
Hoop stress history — parallelised version
==========================================
Drop-in replacement for ``hoop_stress.compute``.  All statistics and plotting
helpers are re-exported from the sequential module unchanged.

Parallelisation strategy
------------------------
The computation splits into two phases:

Phase 1 — sequential, main process
    For each site:
      • download geometry files  (network I/O)
      • ``msite_setup``          (disk I/O + lightweight C++)
      • ``HoopBasis(...)``       (n_sources C++ calls, typically 2–3)
      • download all record files (network I/O)
      • enqueue one Task per record

Phase 2 — parallel, ProcessPoolExecutor
    Each worker receives a ``_RecordTask`` (fully picklable):
      site_name, record_name, housing, filepath, HoopBasis

    The worker:
      1. parses the record file with MagnetRun
      2. calls basis.eval_dataframe(...)  — pure numpy, no C++
      3. returns a partial DataFrame

Phase 3 — sequential, main process
    pd.concat(partial frames) → sort by timestamp → attach attrs

Why ProcessPoolExecutor, not ThreadPoolExecutor?
    Phase 2 workers do real CPU work (numpy matrix multiply) and file I/O.
    The GIL would prevent true CPU parallelism with threads.  Processes give
    genuine concurrency.

Why HoopBasis is safely picklable
    Its attributes are: comp_names (list[str]), source_names (list[str]),
    C (np.ndarray), I_own_idx (np.ndarray).  No C++ objects, no file handles.
    pickle serialises these without issue across process boundaries.

Why C++ objects are NOT passed to workers
    pybind11-wrapped objects (Tubes, Helices, …) do not implement ``__reduce__``
    and are not pickle-serialisable.  Even if they were, ``set_currents``
    mutates them in place, which is unsafe across a shared-memory fork.
    Keeping C++ entirely in Phase 1 sidesteps both issues.
"""

from __future__ import annotations

import os
import warnings
import tempfile
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Sequence

import numpy as np
import pandas as pd
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn

# Re-export stats and plot helpers unchanged — no need to duplicate them
from .hoop_stress import (          # noqa: F401  (re-exported for callers)
    HoopBasis,
    _ObjectCache,
    hoop_columns,
    hoop_stats,
    plot_hoop_history,
    plot_hoop_stats,
)
from . import utils
from python_magnetsetup.ana import msite_setup
from python_magnetsetup.config import appenv
from python_magnetrun.MagnetRun import MagnetRun
import magnettools.magnettools as mt


# ---------------------------------------------------------------------------
# Worker task descriptor  (must be picklable → plain dataclass, no C++ refs)
# ---------------------------------------------------------------------------

@dataclass
class _RecordTask:
    """All data a worker needs to process one record file."""
    site_name:   str
    record_name: str
    housing:     str
    filepath:    str
    basis:       HoopBasis   # picklable: only numpy arrays + lists


# ---------------------------------------------------------------------------
# Worker function  (module-level so ProcessPoolExecutor can pickle it)
# ---------------------------------------------------------------------------

def _process_record(task: _RecordTask) -> pd.DataFrame | None:
    """
    Parse one record file and evaluate hoop stress via the precomputed basis.

    Runs entirely in a worker process.  No C++ calls.

    Returns
    -------
    pd.DataFrame or None
        Columns: timestamp, site, record, Field[T] (if present),
        current columns, then one hoop column per component.
        Returns ``None`` on any unrecoverable error (warning already issued).
    """
    try:
        if task.filepath.endswith(".txt"):
            rundata = MagnetRun.fromtxt(task.housing, task.site_name, task.filepath)
        else:
            rundata = MagnetRun.fromcsv(task.housing, task.site_name, task.filepath)
    except Exception as exc:
        warnings.warn(f"[{task.record_name}] cannot parse: {exc}")
        return None

    raw_df = rundata.MagnetData.Data

    current_cols = [c for c in task.basis.source_names if c in raw_df.columns]
    if not current_cols:
        warnings.warn(
            f"[{task.record_name}] no matching current columns "
            f"(need {task.basis.source_names}) – skipped"
        )
        return None

    ih_arr = raw_df["IH_ref"].to_numpy() if "IH_ref" in raw_df.columns else None
    ib_arr = raw_df["IB_ref"].to_numpy() if "IB_ref" in raw_df.columns else None
    is_arr = raw_df["IS_ref"].to_numpy() if "IS_ref" in raw_df.columns else None

    try:
        hoop_df = task.basis.eval_dataframe(ih_arr, ib_arr, is_arr)
    except Exception as exc:
        warnings.warn(f"[{task.record_name}] eval_dataframe failed: {exc}")
        return None

    # Prepend metadata columns
    n = len(hoop_df)
    hoop_df.insert(0, "timestamp", raw_df["timestamp"].to_numpy() if "timestamp" in raw_df.columns else np.arange(n))
    hoop_df.insert(1, "site",      task.site_name)
    hoop_df.insert(2, "record",    task.record_name)
    if "Field" in raw_df.columns:
        hoop_df.insert(3, "Field[T]", raw_df["Field"].to_numpy())
    for col in current_cols:
        hoop_df[col] = raw_df[col].to_numpy()

    return hoop_df


# ---------------------------------------------------------------------------
# Main parallel compute function
# ---------------------------------------------------------------------------

def compute(
    session,
    api_server: str,
    auth_headers: dict,
    oid: int,
    mtype: str = "part",
    max_workers: int | None = None,
    verbose: bool = False,
    debug: bool = False,
) -> pd.DataFrame | None:
    """
    Parallel version of ``hoop_stress.compute``.

    Phase 1 (this process): geometry downloads + ``HoopBasis`` precomputation
    per site, then record file downloads.

    Phase 2 (worker pool): one task per record, evaluated with pure numpy.

    Parameters
    ----------
    max_workers : int or None
        Number of worker processes.  ``None`` lets Python choose
        (typically ``os.cpu_count()``).  A value of 1 effectively runs
        sequentially but still exercises the multiprocessing path.

    All other parameters identical to ``hoop_stress.compute``.

    Returns
    -------
    pd.DataFrame or None
        Identical schema to the sequential version.
    """
    if mtype != "part":
        print(f"hoop_stress_parallel.compute: expected a part – got '{mtype}'")
        return None

    cache = _ObjectCache()

    part = cache.get_object(
        session, api_server, auth_headers, "part", oid,
        verbose=verbose, debug=debug,
    )
    part_type = part.get("type", "")
    if part_type not in ("helix", "bitter", "supra"):
        print(
            f"hoop_stress_parallel.compute: unsupported part type '{part_type}' "
            f"for part '{part['name']}'"
        )
        return None

    print(
        f"\nhoop_stress_parallel.compute: part='{part['name']}' (type={part_type})"
        f"  api={api_server}  max_workers={max_workers or 'auto'}"
    )

    sites = utils.get_history(
        session, api_server, auth_headers, oid,
        mtype=mtype, otype="site", debug=debug,
    )
    if not sites:
        print("  No sites found – nothing to process.")
        return None

    cwd = os.getcwd()
    tasks:          list[_RecordTask]         = []
    pnames_by_site: dict[str, dict[str, str]] = {}

    # =========================================================================
    # Phase 1 — sequential: geometry + basis precomputation, file downloads
    # =========================================================================
    with tempfile.TemporaryDirectory() as tempdir:
        os.chdir(tempdir)
        data_dir = os.path.join(tempdir, "data")
        os.makedirs(os.path.join(data_dir, "geometries"), exist_ok=True)

        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            TimeElapsedColumn(),
        ) as progress:

            site_bar = progress.add_task("Phase 1 – sites", total=len(sites))

            for site_stub in sites:
                site = cache.get_object(
                    session, api_server, auth_headers, "site", site_stub["id"],
                    verbose=verbose, debug=debug,
                )
                site_name = site.get("name", str(site["id"]))
                progress.update(site_bar, description=f"Phase 1 – {site_name}")

                # ── geometry files ──────────────────────────────────────────
                config_data = utils.get_data(
                    session, api_server, auth_headers,
                    oid=site["id"], mtype="site", debug=debug,
                )

                pnames: dict[str, str] = {}
                num_by_type: dict[str, int] = {"H": 0, "B": 0, "S": 0}

                for magnet_stub in site.get("site_magnets", []):
                    magnet = cache.get_object(
                        session, api_server, auth_headers,
                        "magnet", magnet_stub["magnet_id"],
                        verbose=verbose, debug=debug,
                    )
                    geom_data = magnet.get("geometry", {})
                    if geom_data:
                        utils.download(
                            session, api_server, auth_headers,
                            geom_data["id"],
                            wd=os.path.join(data_dir, "geometries"),
                            debug=debug,
                        )
                    for part_stub in magnet.get("magnet_parts", []):
                        _pid   = part_stub["part_id"]
                        _ptype = part_stub["part"].get("type", "")
                        if _ptype not in ("helix", "bitter", "supra"):
                            continue
                        _pobj = cache.get_object(
                            session, api_server, auth_headers, "part", _pid,
                            verbose=verbose, debug=debug,
                        )
                        for geom in _pobj.get("geometries", []):
                            attach = geom.get("attachment", {})
                            if attach:
                                utils.download(
                                    session, api_server, auth_headers,
                                    attach["id"],
                                    wd=os.path.join(data_dir, "geometries"),
                                    debug=debug,
                                )
                        type_key = _ptype.upper()[0]
                        num_by_type[type_key] += 1
                        pnames[_pobj["name"]] = f"{type_key}{num_by_type[type_key]}"

                pnames_by_site[site_name] = pnames

                # ── magnettools setup ───────────────────────────────────────
                env = appenv(
                    envfile=None,
                    url_api=data_dir,
                    yaml_repo=os.path.join(data_dir, "geometries"),
                    cad_repo=os.path.join(data_dir, "cad"),
                    mesh_repo=data_dir,
                    simage_repo=data_dir,
                    mrecord_repo=data_dir,
                    optim_repo=data_dir,
                )
                try:
                    site_data = msite_setup(env, config_data["results"], debug)
                except Exception as exc:
                    warnings.warn(f"msite_setup failed for '{site_name}': {exc} – skipping")
                    progress.advance(site_bar)
                    continue

                Tubes, Helices, OHelices, BMagnets, UMagnets, Shims = site_data
                icurrents = list(mt.get_currents(Tubes, Helices, BMagnets, UMagnets))

                # ── HoopBasis precomputation  (C++ calls happen here, once) ─
                try:
                    basis = HoopBasis(
                        Tubes, Helices, OHelices, BMagnets, UMagnets, icurrents
                    )
                except Exception as exc:
                    warnings.warn(f"HoopBasis failed for '{site_name}': {exc} – skipping")
                    progress.advance(site_bar)
                    continue

                if debug:
                    print(
                        f"\n  [{site_name}] basis: "
                        f"{len(basis.comp_names)} components × "
                        f"{len(basis.source_names)} sources"
                        f"\n  C =\n{basis.C}"
                    )

                # ── download record files + build tasks ─────────────────────
                records = site.get("records", [])
                rec_bar = progress.add_task(
                    f"  ↳ downloading records [{site_name}]",
                    total=len(records),
                )
                for rec in records:
                    attach = rec.get("attachment_id")
                    if attach is None:
                        progress.advance(rec_bar)
                        continue
                    filepath = utils.download(
                        session, api_server, auth_headers,
                        attach,
                        wd=tempdir,
                        debug=debug,
                    )
                    if filepath is None:
                        progress.advance(rec_bar)
                        continue
                    housing = os.path.basename(filepath).split("_")[0]
                    tasks.append(_RecordTask(
                        site_name=site_name,
                        record_name=rec.get("name", str(rec.get("id"))),
                        housing=housing,
                        filepath=filepath,
                        basis=basis,   # picklable numpy struct
                    ))
                    progress.advance(rec_bar)

                progress.advance(site_bar)

            # ── summary ──────────────────────────────────────────────────────
            n_sites   = len(pnames_by_site)
            n_records = len(tasks)
            print(
                f"\nPhase 1 complete: {n_sites} site(s), "
                f"{n_records} record task(s) queued."
            )

        if not tasks:
            print("No record tasks – nothing to process.")
            os.chdir(cwd)
            return None

        # =====================================================================
        # Phase 2 — parallel: one worker process per record task
        # =====================================================================
        all_frames: list[pd.DataFrame] = []

        print(f"\nPhase 2 – parallel evaluation  ({max_workers or 'auto'} workers) …")

        with Progress(
            SpinnerColumn(),
            TextColumn("[bold green]Phase 2"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total} records"),
            TimeElapsedColumn(),
        ) as progress:
            eval_bar = progress.add_task("evaluating", total=len(tasks))

            with ProcessPoolExecutor(max_workers=max_workers) as pool:
                futures = {pool.submit(_process_record, t): t for t in tasks}

                for future in as_completed(futures):
                    task_desc = futures[future]
                    try:
                        result_df = future.result()
                    except Exception as exc:
                        warnings.warn(
                            f"Worker error for record '{task_desc.record_name}' "
                            f"in site '{task_desc.site_name}': {exc}"
                        )
                        result_df = None

                    if result_df is not None:
                        all_frames.append(result_df)

                    progress.advance(eval_bar)

        os.chdir(cwd)

    # =========================================================================
    # Phase 3 — assemble final DataFrame
    # =========================================================================
    if not all_frames:
        print("No data collected.")
        return None

    result = pd.concat(all_frames, ignore_index=True)
    result.sort_values("timestamp", inplace=True)
    result.reset_index(drop=True, inplace=True)

    result.attrs["part_name"]     = part["name"]
    result.attrs["part_type"]     = part_type
    result.attrs["pnames_by_site"] = pnames_by_site

    print(
        f"\nDone – {len(result):,} rows across "
        f"{result['site'].nunique()} site(s) / "
        f"{result['record'].nunique()} record(s)."
    )
    return result


# ---------------------------------------------------------------------------
# Convenience: run full pipeline
# ---------------------------------------------------------------------------

def run(
    session,
    api_server: str,
    auth_headers: dict,
    oid: int,
    quantiles: Sequence[float] = (0.25, 0.50, 0.75, 0.90, 0.95, 0.99),
    max_workers: int | None = None,
    verbose: bool = False,
    debug: bool = False,
    show_plots: bool = True,
    output_prefix: str | None = None,
) -> tuple[pd.DataFrame | None, pd.DataFrame | None]:
    """
    Full pipeline with parallel compute: compute → stats → plots.

    Returns ``(history_df, stats_df)``.
    """
    df = compute(
        session, api_server, auth_headers, oid,
        mtype="part", max_workers=max_workers,
        verbose=verbose, debug=debug,
    )
    if df is None:
        return None, None

    stats_df = hoop_stats(df, quantiles=quantiles)
    pname    = df.attrs.get("part_name", str(oid))

    history_savepath = f"{output_prefix}_history.png" if output_prefix else None
    stats_savepath   = f"{output_prefix}_stats.png"   if output_prefix else None

    plot_hoop_history(df, part_name=pname, show=show_plots, savepath=history_savepath)
    plot_hoop_stats(stats_df, part_name=pname, show=show_plots, savepath=stats_savepath)

    if output_prefix:
        df.to_csv(f"{output_prefix}_history.csv", index=False)
        stats_df.to_csv(f"{output_prefix}_stats.csv")
        print(f"Saved CSV  → {output_prefix}_history.csv")
        print(f"Saved CSV  → {output_prefix}_stats.csv")
        print(f"Saved PNG  → {history_savepath}")
        print(f"Saved PNG  → {stats_savepath}")

    return df, stats_df
