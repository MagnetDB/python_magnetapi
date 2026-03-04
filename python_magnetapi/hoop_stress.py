"""
Hoop stress history for a magnet part
======================================
Computes, across the full operational lifetime of a ``part``, the hoop stress
at every timestamp stored in every measurement record, then provides statistics
and plotting helpers.

Public API
----------
compute(session, api_server, auth_headers, oid, mtype="part", ...)
    → pd.DataFrame   (full time-series, one column per sub-component)

hoop_stats(df, quantiles=(0.25, 0.50, 0.75, 0.90, 0.95, 0.99))
    → pd.DataFrame   (min / mean / max / quantiles per hoop column)

plot_hoop_history(df, part_name, ...)
    → matplotlib Figure

plot_hoop_stats(stats_df, part_name, ...)
    → matplotlib Figure


Speedup: precomputed coefficient matrix (linearity argument)
------------------------------------------------------------
Hoop stress for component k is:

    σ_k = r_k · j_θ,k · B_total(r_k)

Both j_θ and B are **linear** in the currents:

    j_θ,k      =  j̃_k · I_own_k
    B_total(r_k) =  Σ_i  B̃_i(r_k) · I_i       (sum over current sources H, B, S)

so σ_k is quadratic in the currents but factors as:

    σ_k(I_H, I_B, …)  =  I_own_k · Σ_i  C[k, i] · I_i

where the **coefficient matrix** C[k, i] = r_k · j̃_k · B̃_i(r_k) depends only
on the site geometry and is precomputed with n_sources calls to ``getHoop``
(one per basis current: set I_i = 1 A, all others = 0).

``getHoop`` already returns ``r[m]``, ``j[A/m²]``, ``Bz[T]`` as separate
columns, so all ingredients are available even when j = 0 (e.g. helix row
during a bitter-only basis call still provides the Bz contribution from the
bitters at the helix radius).

The inner loop over every timestamp row then reduces to:

    σ_vec = I_own_vec * (C @ I_vec)     # pure numpy, zero C++ calls

This replaces O(N_rows × N_sources) C++ round-trips with a single matrix–
vector multiply per row, giving a speedup of ~N_rows (typically 1000–10000×
for a 30-minute run at 1 Hz).


Notes on thread / process safety
---------------------------------
``mt.set_currents`` **mutates** the shared C++ objects (Tubes, Helices, …) in
place.  With the precomputed-coefficient approach, ``set_currents`` and
``getHoop`` are only called during the *precomputation* phase (n_sources times,
sequentially).  The hot inner loop is pure numpy and trivially thread-safe.

If the precomputation itself needs to be parallelised across sites, use
``ProcessPoolExecutor`` where every worker re-initialises its own magnettools
objects by calling ``msite_setup`` independently (fork-safety of pybind11
objects is not guaranteed; passing live C++ objects across process boundaries
is unsafe).
"""

from __future__ import annotations

import os
import sys
import tempfile
import warnings
from typing import Sequence

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.gridspec import GridSpec
from rich.progress import track

from . import utils
from python_magnetsetup.ana import msite_setup
from python_magnetsetup.config import appenv
from python_magnetrun.MagnetRun import MagnetRun
import magnettools.Bmap as bmap
import magnettools.magnettools as mt


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

class _ObjectCache:
    """Simple request-level cache for API objects (avoids redundant HTTP calls)."""

    def __init__(self):
        self._store: dict[tuple, dict] = {}

    def get_object(self, session, api_server, auth_headers, mtype, obj_id,
                   verbose=False, debug=False) -> dict:
        key = (mtype, obj_id)
        if key not in self._store:
            self._store[key] = utils.get_object(
                session, api_server, headers=auth_headers,
                mtype=mtype, id=obj_id, verbose=verbose, debug=debug,
            )
        return self._store[key]




class HoopBasis:
    """
    Precomputed coefficient matrix for fast hoop-stress evaluation.

    Builds the matrix C[k, i] = r_k · j̃_k · B̃_i(r_k) by making exactly
    n_sources calls to ``getHoop`` at unit currents (one per current source).

    After construction, ``eval(I_vec)`` returns the hoop stress vector for
    an arbitrary operating point using only numpy operations — no further
    C++ calls are needed.

    Parameters
    ----------
    Tubes, Helices, OHelices, BMagnets, UMagnets
        Magnettools objects for the site, already loaded by ``msite_setup``.
    icurrents_template : list[float]
        Nominal current vector (used to determine source ordering).

    Attributes
    ----------
    comp_names : list[str]
        Output column names, e.g. ``["H0", "H1", "B0"]``.
    source_names : list[str]
        Current source labels in the order expected by ``eval``,
        e.g. ``["IH_ref", "IB_ref"]``.
    C : np.ndarray, shape (n_components, n_sources)
        Coefficient matrix in Pa / A²  (converted to MPa inside ``eval``).
    I_own_idx : np.ndarray, shape (n_components,)
        Index into the source vector for the component's own current.
    """

    def __init__(
        self,
        Tubes, Helices, OHelices, BMagnets, UMagnets,
        icurrents_template: list[float],
    ):
        # ── which component types are present? ─────────────────────────────
        mdata: dict[str, object] = {}
        if len(Tubes) != 0:
            mdata["H"] = Tubes
        if len(BMagnets) != 0:
            mdata["B"] = BMagnets
        if len(UMagnets) != 0:
            mdata["S"] = UMagnets

        # ── source ordering mirrors set_currents argument order ─────────────
        source_labels: list[str] = []
        if len(Tubes) != 0:
            source_labels.append("IH_ref")
        if len(BMagnets) != 0:
            source_labels.append("IB_ref")
        if len(UMagnets) != 0:
            source_labels.append("IS_ref")

        n_sources = len(source_labels)

        # ── probe call at [1,0,…] to discover component layout ─────────────
        # (all currents = 0 gives j = 0 for every type, so we need I_H=1 or
        #  I_B=1 depending on type; we always get r and Bz regardless of j)
        #
        # Strategy: for each component type T we need j̃_T (= j at I_own=1 A).
        # We read j̃_T from the basis call where source_T = 1.
        # We read B̃_i at each component position from every basis call.

        # First pass: collect component names and own-source index
        comp_names: list[str] = []
        comp_own_src: list[int] = []     # index into source_labels
        comp_r:       list[float] = []
        comp_j_unit:  list[float] = []   # j at own source = 1 A

        # own-source index for each type
        type_to_src_idx = {"H": 0, "B": source_labels.index("IB_ref") if "IB_ref" in source_labels else -1,
                           "S": source_labels.index("IS_ref") if "IS_ref" in source_labels else -1}

        # Perform n_sources basis calls; collect Bz[T] per component
        # basis_Bz[src_idx][comp_name] = B̃_src at component radius (in T/A)
        basis_Bz: list[dict[str, float]] = [{} for _ in range(n_sources)]

        n0 = list(icurrents_template)

        for src_idx, src_label in enumerate(source_labels):
            # unit current vector: 1 A in source src_idx, 0 elsewhere
            v = [0.0] * n_sources
            v[src_idx] = 1.0
            cvec = mt.DoubleVector(v)
            mt.set_currents(Tubes, Helices, BMagnets, UMagnets, OHelices, cvec)

            for mtype, Magnets in mdata.items():
                hoop_cols, hoop_vals = bmap.getHoop(
                    Magnets, Tubes, Helices, BMagnets, UMagnets, mtype
                )
                _df = pd.DataFrame.from_records(hoop_vals)
                _df.columns = hoop_cols

                for _, row in _df.iterrows():
                    cname = f"{mtype}{row['num']}"
                    basis_Bz[src_idx][cname] = float(row["Bz[T]"])

                    # on own-source call: harvest r and j̃
                    if src_idx == type_to_src_idx[mtype]:
                        if cname not in comp_names:
                            comp_names.append(cname)
                            comp_own_src.append(src_idx)
                            comp_r.append(float(row["r[m]"]))
                            comp_j_unit.append(float(row["j[A/m\u00b2]"]))

        # ── build coefficient matrix C ─────────────────────────────────────
        # C[k, i] = r_k · j̃_k · B̃_i(r_k)
        # Units: m · (A/m²) · (T/A) = m · A/m² · kg/(A·s²)
        #      = kg/(m·s²) = Pa   (at I²)
        # We convert to MPa inside eval by multiplying by 1e-6.

        n_comp = len(comp_names)
        C = np.zeros((n_comp, n_sources), dtype=np.float64)
        for k, cname in enumerate(comp_names):
            r_k = comp_r[k]
            j_k = comp_j_unit[k]     # j at own source = 1 A
            for i in range(n_sources):
                C[k, i] = r_k * j_k * basis_Bz[i].get(cname, 0.0)

        self.comp_names: list[str]  = comp_names
        self.source_names: list[str] = source_labels
        self.C: np.ndarray           = C                      # (n_comp, n_src)
        self.I_own_idx: np.ndarray   = np.array(comp_own_src, dtype=np.intp)

        # restore nominal currents so the caller's objects are undisturbed
        mt.set_currents(
            Tubes, Helices, BMagnets, UMagnets, OHelices,
            mt.DoubleVector(n0),
        )

    def eval(self, I_vec: np.ndarray) -> np.ndarray:
        """
        Evaluate hoop stress [MPa] for a 1-D current vector ``I_vec``
        (length = n_sources, order = self.source_names).

        Returns a 1-D array of length n_components (order = self.comp_names).
        """
        # σ_k = I_own_k · Σ_i C[k,i] · I_i   (in Pa)
        # converted to MPa via 1e-6
        I_own = I_vec[self.I_own_idx]
        return I_own * (self.C @ I_vec) * 1e-6

    def eval_dataframe(
        self,
        ih_arr:  np.ndarray | None,
        ib_arr:  np.ndarray | None,
        is_arr:  np.ndarray | None,
    ) -> pd.DataFrame:
        """
        Vectorised evaluation over arrays of current values.

        Parameters
        ----------
        ih_arr, ib_arr, is_arr
            1-D arrays of current values (or ``None`` if source absent).
            All present arrays must have the same length N.

        Returns
        -------
        pd.DataFrame, shape (N, n_components), columns = self.comp_names.
        """
        # Build current matrix  I_mat: shape (N, n_sources)
        n = None
        parts: dict[str, np.ndarray] = {}
        for arr, label in zip(
            [ih_arr, ib_arr, is_arr], ["IH_ref", "IB_ref", "IS_ref"]
        ):
            if arr is not None and label in self.source_names:
                parts[label] = arr
                n = len(arr)

        if n is None:
            raise ValueError("At least one current array must be provided.")

        I_mat = np.zeros((n, len(self.source_names)), dtype=np.float64)
        for i, label in enumerate(self.source_names):
            if label in parts:
                I_mat[:, i] = parts[label]

        # σ_mat[row, k] = I_own[k] · Σ_i C[k,i]·I[row,i]
        # = (I_mat @ C.T) elementwise * I_own_mat
        # I_own_mat[row, k] = I_mat[row, I_own_idx[k]]
        CIt    = (I_mat @ self.C.T)                  # (N, n_comp)  in Pa·A
        I_own_mat = I_mat[:, self.I_own_idx]         # (N, n_comp)
        sigma_MPa = CIt * I_own_mat * 1e-6           # (N, n_comp)  in MPa

        return pd.DataFrame(sigma_MPa, columns=self.comp_names)



# ---------------------------------------------------------------------------
# Main compute function
# ---------------------------------------------------------------------------

def compute(
    session,
    api_server: str,
    auth_headers: dict,
    oid: int,
    mtype: str = "part",
    verbose: bool = False,
    debug: bool = False,
) -> pd.DataFrame | None:
    """
    Compute the full hoop-stress history for *oid* (a part id).

    Returns
    -------
    pd.DataFrame
        Columns: ``timestamp``, ``site``, ``record``, current columns
        (``IH_ref``, ``IB_ref``, ``IS_ref`` when present), then one
        ``{type}{num}`` column per sub-component (e.g. ``H0``, ``H1``,
        ``B0``).  The DataFrame is sorted by ``timestamp``.

    Returns ``None`` if the part type is unsupported or no data is found.
    """
    if mtype != "part":
        print(f"hoop_stress.compute: expected a part – got '{mtype}'")
        return None

    cache = _ObjectCache()

    part = cache.get_object(
        session, api_server, auth_headers, "part", oid, verbose=verbose, debug=debug
    )
    if debug:
        print(f"part: {part}")

    part_type = part.get("type", "")
    if part_type not in ("helix", "bitter", "supra"):
        print(
            f"hoop_stress.compute: unsupported part type '{part_type}' "
            f"for part '{part['name']}'"
        )
        return None

    print(
        f"\nhoop_stress.compute: part='{part['name']}' (type={part_type})"
        f"  api={api_server}"
    )

    sites = utils.get_history(
        session, api_server, auth_headers, oid,
        mtype=mtype, otype="site", debug=debug,
    )
    if not sites:
        print("  No sites found – nothing to process.")
        return None

    if debug:
        print(f"sites ({len(sites)}): {[s.get('name', s.get('id')) for s in sites]}")

    cwd = os.getcwd()
    all_frames: list[pd.DataFrame] = []
    # pnames_by_site[site_name] = {part_api_name: positional_label}
    # preserved in result.attrs for downstream label mapping
    pnames_by_site: dict[str, dict[str, str]] = {}

    with tempfile.TemporaryDirectory() as tempdir:
        os.chdir(tempdir)
        data_dir = os.path.join(tempdir, "data")
        os.makedirs(os.path.join(data_dir, "geometries"), exist_ok=True)

        for site_stub in track(sites, description="Sites"):
            site = cache.get_object(
                session, api_server, auth_headers, "site", site_stub["id"],
                verbose=verbose, debug=debug,
            )
            site_name = site.get("name", str(site["id"]))

            # ── geometry setup ──────────────────────────────────────────────
            config_data = utils.get_data(
                session, api_server, auth_headers,
                oid=site["id"], mtype="site", debug=debug,
            )

            # pnames: part_name → positional label (H1, B2, …) — local to this site
            pnames: dict[str, str] = {}
            num_by_type: dict[str, int] = {"H": 0, "B": 0, "S": 0}
            for magnet_stub in site.get("site_magnets", []):
                magnet_id = magnet_stub["magnet_id"]
                magnet = cache.get_object(
                    session, api_server, auth_headers, "magnet", magnet_id,
                    verbose=verbose, debug=debug,
                )

                # download magnet geometry yaml
                geom_data = magnet.get("geometry", {})
                if geom_data:
                    utils.download(
                        session, api_server, auth_headers,
                        geom_data["id"],
                        wd=os.path.join(data_dir, "geometries"),
                        debug=debug,
                    )

                # download part geometries and build pnames
                for part_stub in magnet.get("magnet_parts", []):
                    _pid = part_stub["part_id"]
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
                    type_key = _ptype.upper()[0]  # H / B / S
                    num_by_type[type_key] += 1
                    pnames[_pobj["name"]] = f"{type_key}{num_by_type[type_key]}"

            # record the site-local name mapping for later reference
            pnames_by_site[site_name] = pnames

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
                warnings.warn(
                    f"msite_setup failed for site '{site_name}': {exc} – skipping"
                )
                continue

            Tubes, Helices, OHelices, BMagnets, UMagnets, Shims = site_data
            icurrents_template = list(mt.get_currents(Tubes, Helices, BMagnets, UMagnets))

            # ── precompute coefficient matrix (n_sources getHoop calls only) ─
            try:
                basis = HoopBasis(
                    Tubes, Helices, OHelices, BMagnets, UMagnets,
                    icurrents_template,
                )
            except Exception as exc:
                warnings.warn(
                    f"HoopBasis precomputation failed for site '{site_name}': {exc} – skipping"
                )
                continue

            if debug:
                print(
                    f"  [{site_name}] basis: {len(basis.comp_names)} components, "
                    f"{len(basis.source_names)} sources\n"
                    f"  C =\n{basis.C}"
                )

            # ── records loop  (no C++ calls inside) ─────────────────────────
            records = site.get("records", [])
            for rec in track(
                records,
                description=f"  Records [{site_name}]",
                transient=True,
            ):
                attach = rec.get("attachment_id")
                if attach is None:
                    continue

                filename = utils.download(
                    session, api_server, auth_headers,
                    attach,
                    wd=tempdir,
                    debug=debug,
                )
                if filename is None:
                    continue

                housing = os.path.basename(filename).split("_")[0]
                try:
                    if filename.endswith(".txt"):
                        rundata = MagnetRun.fromtxt(housing, site_name, filename)
                    else:
                        rundata = MagnetRun.fromcsv(housing, site_name, filename)
                except Exception as exc:
                    warnings.warn(f"Cannot parse record '{rec.get('name')}': {exc}")
                    continue

                raw_df = rundata.MagnetData.Data

                # select available, relevant columns
                base_cols = ["timestamp", "Field"]
                current_cols = [c for c in basis.source_names if c in raw_df.columns]
                available = [c for c in base_cols + current_cols if c in raw_df.columns]
                if not current_cols:
                    warnings.warn(
                        f"Record '{rec.get('name')}': no matching current columns "
                        f"(need {basis.source_names}) – skipping"
                    )
                    continue
                df_run = raw_df[available].copy()

                # ── vectorised hoop stress (pure numpy, no C++ in hot path) ──
                ih_arr = df_run["IH_ref"].to_numpy() if "IH_ref" in df_run.columns else None
                ib_arr = df_run["IB_ref"].to_numpy() if "IB_ref" in df_run.columns else None
                is_arr = df_run["IS_ref"].to_numpy() if "IS_ref" in df_run.columns else None

                hoop_df = basis.eval_dataframe(ih_arr, ib_arr, is_arr)
                # hoop_df: shape (N, n_components), columns = basis.comp_names

                # attach metadata columns
                hoop_df.insert(0, "timestamp", df_run["timestamp"].to_numpy())
                hoop_df.insert(1, "site",      site_name)
                hoop_df.insert(2, "record",    rec.get("name", str(rec.get("id"))))
                if "Field" in df_run.columns:
                    hoop_df.insert(3, "Field[T]", df_run["Field"].to_numpy())
                for col in current_cols:
                    hoop_df[col] = df_run[col].to_numpy()

                all_frames.append(hoop_df)

        os.chdir(cwd)

    if not all_frames:
        print("No data collected.")
        return None

    result = pd.concat(all_frames, ignore_index=True)
    result.sort_values("timestamp", inplace=True)
    result.reset_index(drop=True, inplace=True)

    # Attach metadata as DataFrame attrs for downstream use
    result.attrs["part_name"] = part["name"]
    result.attrs["part_type"] = part_type
    result.attrs["pnames_by_site"] = pnames_by_site  # {site_name: {api_name: label}}

    print(
        f"\nDone – {len(result):,} rows across "
        f"{result['site'].nunique()} site(s) / "
        f"{result['record'].nunique()} record(s)."
    )
    return result


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

def hoop_columns(df: pd.DataFrame) -> list[str]:
    """Return the hoop-stress column names (H*, B*, S*) from the result DataFrame."""
    return [c for c in df.columns if len(c) >= 2 and c[0] in "HBS" and c[1:].isdigit()]


def hoop_stats(
    df: pd.DataFrame,
    quantiles: Sequence[float] = (0.25, 0.50, 0.75, 0.90, 0.95, 0.99),
) -> pd.DataFrame:
    """
    Compute statistics for every hoop-stress column.

    Returns
    -------
    pd.DataFrame
        Index = column name (e.g. H0, H1, B0).
        Columns = count, min, mean, max, std, then one per quantile.
    """
    hcols = hoop_columns(df)
    if not hcols:
        raise ValueError("No hoop-stress columns found in DataFrame.")

    rows = []
    for col in hcols:
        series = df[col].dropna()
        row = {
            "component": col,
            "count": len(series),
            "min [MPa]": series.min(),
            "mean [MPa]": series.mean(),
            "max [MPa]": series.max(),
            "std [MPa]": series.std(),
        }
        for q in quantiles:
            row[f"q{int(q * 100):02d} [MPa]"] = series.quantile(q)
        rows.append(row)

    stats_df = pd.DataFrame(rows).set_index("component")
    return stats_df


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------

_PALETTE = [
    "#2563EB", "#DC2626", "#16A34A", "#D97706",
    "#7C3AED", "#0891B2", "#DB2777", "#65A30D",
]


def plot_hoop_history(
    df: pd.DataFrame,
    part_name: str | None = None,
    figsize: tuple[int, int] = (14, 5),
    show: bool = True,
    savepath: str | None = None,
) -> plt.Figure:
    """
    Time-series plot of hoop stress for every sub-component.

    Light vertical bands mark site boundaries.
    """
    hcols = hoop_columns(df)
    if not hcols:
        raise ValueError("No hoop-stress columns found.")

    pname = part_name or df.attrs.get("part_name", "part")

    fig, ax = plt.subplots(figsize=figsize)
    ax.set_facecolor("#F8FAFC")
    fig.patch.set_facecolor("#FFFFFF")

    # shade site bands
    sites = df["site"].unique()
    site_colors = ["#EFF6FF", "#F0FDF4", "#FFF7ED", "#FDF4FF"]
    site_df = df.sort_values("timestamp")
    for k, sname in enumerate(sites):
        mask = site_df["site"] == sname
        t_min = site_df.loc[mask, "timestamp"].min()
        t_max = site_df.loc[mask, "timestamp"].max()
        ax.axvspan(t_min, t_max, color=site_colors[k % len(site_colors)], alpha=0.6,
                   label=f"site: {sname}" if k < 4 else None)

    # hoop stress lines
    for i, col in enumerate(hcols):
        color = _PALETTE[i % len(_PALETTE)]
        ax.plot(
            df["timestamp"], df[col],
            color=color, linewidth=0.8, alpha=0.85,
            label=col,
        )

    ax.set_xlabel("Time", fontsize=11)
    ax.set_ylabel("Hoop stress [MPa]", fontsize=11)
    ax.set_title(f"Hoop stress history — {pname}", fontsize=13, fontweight="bold")
    ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.6)
    ax.legend(loc="upper left", fontsize=9, framealpha=0.9)

    # Format x-axis as dates if timestamps are datetime-like
    try:
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        fig.autofmt_xdate()
    except Exception:
        pass

    fig.tight_layout()
    if savepath:
        fig.savefig(savepath, dpi=150, bbox_inches="tight")
    if show:
        plt.show()
    return fig


def plot_hoop_stats(
    stats_df: pd.DataFrame,
    part_name: str | None = None,
    quantiles_to_show: Sequence[str] | None = None,
    figsize: tuple[int, int] = (14, 8),
    show: bool = True,
    savepath: str | None = None,
) -> plt.Figure:
    """
    Two-panel figure:
      • Left  – bar chart: min / mean / max per component, with std error bars
      • Right – CDF-style quantile heatmap (components × quantile levels)

    Also prints a formatted stats table to stdout.
    """
    import matplotlib.cm as cm
    from matplotlib.colors import Normalize

    pname = part_name or "part"

    # identify quantile columns
    q_cols = [c for c in stats_df.columns if c.startswith("q") and "[MPa]" in c]
    if quantiles_to_show:
        q_cols = [c for c in q_cols if c in quantiles_to_show]

    fig = plt.figure(figsize=figsize, facecolor="white")
    gs = GridSpec(1, 2, figure=fig, width_ratios=[1.4, 1], wspace=0.35)
    ax_bar  = fig.add_subplot(gs[0])
    ax_heat = fig.add_subplot(gs[1])

    # ── bar chart ────────────────────────────────────────────────────────────
    components = stats_df.index.tolist()
    x = np.arange(len(components))
    width = 0.25

    ax_bar.bar(x - width, stats_df["min [MPa]"],  width, label="min",  color="#93C5FD", zorder=3)
    ax_bar.bar(x,          stats_df["mean [MPa]"], width, label="mean", color="#2563EB",
               yerr=stats_df["std [MPa]"], capsize=4, zorder=3)
    ax_bar.bar(x + width,  stats_df["max [MPa]"],  width, label="max",  color="#1E3A5F", zorder=3)

    ax_bar.set_xticks(x)
    ax_bar.set_xticklabels(components, fontsize=10)
    ax_bar.set_ylabel("Hoop stress [MPa]", fontsize=11)
    ax_bar.set_title(f"Min / Mean / Max — {pname}", fontsize=12, fontweight="bold")
    ax_bar.legend(fontsize=9)
    ax_bar.set_facecolor("#F8FAFC")
    ax_bar.grid(axis="y", linestyle="--", linewidth=0.5, alpha=0.6, zorder=0)

    # ── quantile heatmap ─────────────────────────────────────────────────────
    if q_cols:
        heat_data = stats_df[q_cols].values
        norm = Normalize(vmin=heat_data.min(), vmax=heat_data.max())
        im = ax_heat.imshow(heat_data, aspect="auto", cmap="YlOrRd", norm=norm)

        ax_heat.set_xticks(np.arange(len(q_cols)))
        ax_heat.set_xticklabels(
            [c.replace(" [MPa]", "") for c in q_cols], rotation=45, ha="right", fontsize=9
        )
        ax_heat.set_yticks(np.arange(len(components)))
        ax_heat.set_yticklabels(components, fontsize=10)
        ax_heat.set_title("Quantiles [MPa]", fontsize=12, fontweight="bold")

        # annotate cells
        for r in range(heat_data.shape[0]):
            for c in range(heat_data.shape[1]):
                ax_heat.text(
                    c, r, f"{heat_data[r, c]:.1f}",
                    ha="center", va="center", fontsize=8,
                    color="white" if norm(heat_data[r, c]) > 0.6 else "black",
                )

        fig.colorbar(im, ax=ax_heat, shrink=0.8, label="MPa")
    else:
        ax_heat.axis("off")

    fig.suptitle(
        f"Hoop stress statistics — {pname}",
        fontsize=14, fontweight="bold", y=1.01,
    )
    fig.tight_layout()

    # ── stdout table ─────────────────────────────────────────────────────────
    try:
        from tabulate import tabulate
        print("\n" + tabulate(
            stats_df.round(2),
            headers="keys", tablefmt="rounded_outline",
        ))
    except ImportError:
        print("\n" + stats_df.round(2).to_string())

    if savepath:
        fig.savefig(savepath, dpi=150, bbox_inches="tight")
    if show:
        plt.show()
    return fig


# ---------------------------------------------------------------------------
# Convenience: run everything in one call
# ---------------------------------------------------------------------------

def run(
    session,
    api_server: str,
    auth_headers: dict,
    oid: int,
    quantiles: Sequence[float] = (0.25, 0.50, 0.75, 0.90, 0.95, 0.99),
    verbose: bool = False,
    debug: bool = False,
    show_plots: bool = True,
    output_prefix: str | None = None,
) -> tuple[pd.DataFrame | None, pd.DataFrame | None]:
    """
    Full pipeline: compute → stats → plots.

    Returns ``(history_df, stats_df)``.
    If *output_prefix* is given, saves CSV and PNG files.
    """
    df = compute(session, api_server, auth_headers, oid,
                 mtype="part", verbose=verbose, debug=debug)
    if df is None:
        return None, None

    stats_df = hoop_stats(df, quantiles=quantiles)
    pname = df.attrs.get("part_name", str(oid))

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
