#!/usr/bin/env python3
"""
calcul_DT_helices_from_api.py
==============================
Compute helix conductor temperature rise for a resistive magnet by fetching
geometry and material data from MagnetDB, then applying the same physical
model as calcul_DT_helices_HL31.py.

Two geometry backends are supported (selected automatically):

  1. **magnettools** (preferred) — when ``--dfile PATH`` points to a pre-generated
     ``.d`` input file.  ``mt.read_dfile`` populates ``VectorOfTubes`` and
     ``VectorOfBitters``; all geometry (r_int, r_ext) and physical parameters
     (Σ → ρ, k_thermal, T_water, h_conv) are read directly from those objects.

  2. **API + YAML** (fallback) — geometry is obtained by downloading the
     per-helix YAML attachments from MagnetDB and parsing them with PyYAML;
     material properties (ρ, λ) come from the ``material`` sub-object of each
     part API response.

Physical model (identical to calcul_DT_helices_HL31.py)
---------------------------------------------------------
  j        [A/m²]   = I / (e · h_spire)
  P_vol    [W/m³]   = ρ · j²
  flux     [W/m²]   = P_vol · (Dext − Dint) / 4
  DT_paroi [°C]     = flux / h_conv
  DT_plane [°C]     = P_vol · e² / (8 · λ)
  DT_cyl   [°C]     = DT_plane · [1 + (Dext−Dint)² / (16·Dint·Dext)]
  Tmax     [°C]     = Teau + DT_paroi + DT_plane
  Tmoy     [°C]     = Teau + DT_paroi + 2/3 · DT_plane

Matthiessen consistency check uses ρ_IACS_20 = 1.7241×10⁻⁸ Ω·m, T0 = 219.33 °C.

Usage
-----
  # API-only (YAML fallback):
  python calcul_DT_helices_from_api.py M9 --current 31000

  # With a pre-generated magnettools .d file (preferred path):
  python calcul_DT_helices_from_api.py M9 --current 31000 --dfile M9.d

  # Override cooling defaults:
  python calcul_DT_helices_from_api.py M9 --current 31000 --h_conv 85000 --Teau 30

  # Full server specification:
  python calcul_DT_helices_from_api.py M9 --current 31000 \\
      --server magnetdb.lncmi.local --https

Authentication
--------------
  export MAGNETDB_API_KEY=<your_key>
"""

from __future__ import annotations

import argparse
import math
import os
import sys
import tempfile
import warnings
from dataclasses import dataclass
from typing import Optional

import pandas as pd
import requests
import yaml

from python_magnetapi import utils, cache

# ── Optional magnettools import ──────────────────────────────────────────────
try:
    import magnettools as mt  # pybind11 bindings
    HAS_MT = True
except ImportError:
    HAS_MT = False
    warnings.warn(
        "magnettools not importable — .d-file backend unavailable; "
        "falling back to API-YAML geometry."
    )

# ---------------------------------------------------------------------------
# Physical constants (shared with calcul_DT_helices_HL31.py)
# ---------------------------------------------------------------------------
RHO_IACS_20 = 1.7241e-8    # 100 % IACS resistivity at 20 °C  [Ω·m]
T0_MATTHIESSEN = 219.33    # Matthiessen offset temperature  [°C]

# Fallback cooling defaults (LNCMI resistive magnets)
DEFAULT_H_CONV = 85_000.0  # W/(m²·°C)
DEFAULT_TEAU   = 30.0      # °C


# ---------------------------------------------------------------------------
# Dataclasses (identical interface to calcul_DT_helices_HL31.py)
# ---------------------------------------------------------------------------
@dataclass
class HelixInput:
    name: str
    rho: float          # Electrical resistivity [Ω·m] at operating temperature
    I: float            # Current [A]
    h_conv: float       # Convective HTC [W/(m²·°C)]
    Dint: float         # Inner diameter [m]
    Dext: float         # Outer diameter [m]
    lam: float          # Thermal conductivity [W/(m·°C)]
    Teau: float         # Cooling water temperature [°C]
    h_spire: float      # Coil pitch [m]
    rapport: Optional[float] = None    # conductivity / IACS → T_moy_ro derived
    T_moy_ro: Optional[float] = None   # mean temp from ρ → rapport derived


@dataclass
class HelixResult:
    name: str
    h_spire: float
    j: float
    P_vol: float
    flux: float
    DT_paroi: float
    DT_plane: float
    DT_cyl: float
    Tmax: float
    Tmoy: float
    T_moy_ro: float
    rapport: float


# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------
def compute_helix(inp: HelixInput) -> HelixResult:
    e = (inp.Dext - inp.Dint) / 2.0
    j     = inp.I / (e * inp.h_spire)
    P_vol = inp.rho * j**2
    flux  = P_vol * (inp.Dext - inp.Dint) / 4.0
    DT_paroi = flux / inp.h_conv
    DT_plane = P_vol * e**2 / (8.0 * inp.lam)
    DT_cyl   = DT_plane * (
        1.0 + (inp.Dext - inp.Dint)**2 / (16.0 * inp.Dint * inp.Dext)
    )
    Tmax = inp.Teau + DT_paroi + DT_plane
    Tmoy = inp.Teau + DT_paroi + (2.0 / 3.0) * DT_plane

    if inp.rapport is not None:
        T_moy_ro = _t_from_rapport(inp.rho, inp.rapport)
        rapport  = inp.rapport
    elif inp.T_moy_ro is not None:
        rapport  = _rapport_from_T(inp.rho, inp.T_moy_ro)
        T_moy_ro = inp.T_moy_ro
    else:
        T_moy_ro = math.nan
        rapport  = math.nan

    return HelixResult(
        name=inp.name, h_spire=inp.h_spire,
        j=j, P_vol=P_vol, flux=flux,
        DT_paroi=DT_paroi, DT_plane=DT_plane, DT_cyl=DT_cyl,
        Tmax=Tmax, Tmoy=Tmoy, T_moy_ro=T_moy_ro, rapport=rapport,
    )


def _t_from_rapport(rho, rapport):
    return (20.0 + T0_MATTHIESSEN) * (rho / RHO_IACS_20 - 1.0 / rapport + 1.0) - T0_MATTHIESSEN


def _rapport_from_T(rho, T_moy_ro):
    denom = rho / RHO_IACS_20 - (T_moy_ro + T0_MATTHIESSEN) / (20.0 + T0_MATTHIESSEN) + 1.0
    return 1.0 / denom


def results_to_dataframe(results: list[HelixResult]) -> pd.DataFrame:
    rows = [
        {
            "Helix":         r.name,
            "h_spire [m]":   r.h_spire,
            "j [A/m²]":      r.j,
            "P_vol [W/m³]":  r.P_vol,
            "Flux [W/m²]":   r.flux,
            "DT_paroi [°C]": r.DT_paroi,
            "DT_plane [°C]": r.DT_plane,
            "DT_cyl [°C]":   r.DT_cyl,
            "Tmax [°C]":     r.Tmax,
            "Tmoy [°C]":     r.Tmoy,
            "T_moy_ro [°C]": r.T_moy_ro,
            "Rapport IACS":  r.rapport,
        }
        for r in results
    ]
    return pd.DataFrame(rows).set_index("Helix")


# ---------------------------------------------------------------------------
# Backend A: magnettools .d-file
# ---------------------------------------------------------------------------
def _load_from_dfile(
    dfile: str,
    I: float,
    h_conv_override: Optional[float],
    Teau_override: Optional[float],
    debug: bool,
) -> list[HelixInput]:
    """
    Load helix parameters from a magnettools .d input file.

    Geometry  — ``BitterMagnet.get_R_int/ext()``  [m]
    Pitch     — ``Tube.get_pitch(i)``              [mm] × ``get_nturn(i)`` turns
    ρ         — 1 / ``Tube.get_physical_params(0)``  (Sigma [S/m])
    λ         — ``Tube.get_physical_params(2)``       (k [W/m/°C])
    Teau      — ``Tube.get_cooling_params(0)``         [°C]
    h_conv    — ``Tube.get_cooling_params(1)``         [W/m²/°C]

    The rapport / T_moy_ro consistency check is skipped here (NaN) because
    the .d file does not carry IACS ratio metadata; supply it via --rapport if
    needed.
    """
    Tubes   = mt.VectorOfTubes()
    Helices = mt.VectorOfBitters()
    OHelices = mt.VectorOfBitters()
    BMagnets = mt.VectorOfBitters()
    UMagnets = mt.VectorOfUnifs()
    Shims    = mt.VectorOfShims()

    mt.read_dfile(dfile, Tubes, Helices, OHelices, BMagnets, UMagnets, Shims)

    if debug:
        print(f"[dfile] loaded {dfile}: #Tubes={Tubes.size()}, #Helices={Helices.size()}")

    inputs: list[HelixInput] = []
    for ti in range(Tubes.size()):
        tube = Tubes[ti]
        idx  = tube.get_index()  # starting index into Helices vector
        bm   = Helices[idx]      # first (innermost) BitterMagnet section

        # ── geometry ──
        R_int = bm.get_R_int()   # [m]
        R_ext = bm.get_R_ext()   # [m]
        Dint  = 2.0 * R_int
        Dext  = 2.0 * R_ext

        # ── coil pitch (weighted average over sections) ──
        n_sec = tube.get_n_pitch()
        pitches = [tube.get_pitch(i) for i in range(n_sec)]
        nturns  = [tube.get_nturn(i) for i in range(n_sec)]
        total_turns  = sum(nturns)
        total_height = sum(p * n for p, n in zip(pitches, nturns))
        h_spire = (total_height / total_turns) * 1e-3  # mm → m

        # ── material ──
        sigma = tube.get_physical_params(0)  # [S/m]
        rho   = 1.0 / sigma if sigma > 0 else math.nan
        lam   = tube.get_physical_params(2)  # [W/m/°C]

        # ── cooling ──
        Teau   = Teau_override   if Teau_override   is not None else tube.get_cooling_params(0)
        h_conv = h_conv_override if h_conv_override is not None else tube.get_cooling_params(1)

        if debug:
            print(
                f"  H{ti+1}: R_int={R_int*1e3:.2f} mm, R_ext={R_ext*1e3:.2f} mm, "
                f"h_spire={h_spire*1e3:.3f} mm, rho={rho:.3e}, lam={lam:.1f}, "
                f"Teau={Teau}, h_conv={h_conv}"
            )

        inputs.append(HelixInput(
            name=f"H{ti+1}",
            rho=rho, I=I, h_conv=h_conv,
            Dint=Dint, Dext=Dext, lam=lam,
            Teau=Teau, h_spire=h_spire,
        ))
    return inputs


# ---------------------------------------------------------------------------
# Backend B: API + YAML
# ---------------------------------------------------------------------------
def _parse_helix_yaml(yaml_path: str, debug: bool) -> dict:
    """
    Parse a Helix YAML geometry file (the ``!<Helix>`` format used by magnettools).

    Returns a dict with keys: name, Dint [m], Dext [m], h_spire [m].
    ``h_spire`` is the effective pitch per turn, computed as the
    turn-weighted average of the per-section pitches.
    """
    with open(yaml_path) as f:
        data = yaml.safe_load(f)

    r = data.get("r", [])   # [r_int_mm, r_ext_mm]
    if len(r) < 2:
        raise ValueError(f"{yaml_path}: expected r: [r_int, r_ext], got {r}")

    axi    = data.get("axi", {})
    pitches = axi.get("pitch", axi.get("h", []))
    nturns  = axi.get("turns", [1] * len(pitches))

    if not pitches:
        raise ValueError(f"{yaml_path}: no pitch/turns data found in axi block")

    total_turns  = sum(nturns)
    total_height = sum(p * n for p, n in zip(pitches, nturns))
    h_spire = (total_height / total_turns) * 1e-3  # mm → m

    if debug:
        print(
            f"  YAML {os.path.basename(yaml_path)}: r={r} mm, "
            f"pitches={pitches}, turns={nturns} → h_spire={h_spire*1e3:.3f} mm"
        )

    return {
        "name":   data.get("name", os.path.splitext(os.path.basename(yaml_path))[0]),
        "Dint":   2.0 * r[0] * 1e-3,
        "Dext":   2.0 * r[1] * 1e-3,
        "h_spire": h_spire,
    }


def _extract_material_params(material: dict, debug: bool) -> dict:
    """
    Extract ρ [Ω·m], λ [W/(m·°C)], and rapport from a MagnetDB material object.

    Field name candidates (tries each in order):
      ρ      : rho, electrical_resistivity, rho20
      λ      : thermal_conductivity, kappa, k, lam
      rapport: alpha, conductivity_ratio, iacs_ratio, rapport

    If a field is not found the returned value is None; the caller decides
    whether to fall back to CLI overrides or raise an error.
    """
    def first(*keys):
        for k in keys:
            if k in material and material[k] is not None:
                return float(material[k])
        return None

    rho     = first("rho", "electrical_resistivity", "rho20")
    lam     = first("thermal_conductivity", "kappa", "k", "lam")
    rapport = first("alpha", "conductivity_ratio", "iacs_ratio", "rapport")

    if debug:
        print(f"  material '{material.get('name', '?')}': "
              f"rho={rho}, lam={lam}, rapport={rapport}")
        if rho is None or lam is None:
            print(f"  available material keys: {list(material.keys())}")

    return {"rho": rho, "lam": lam, "rapport": rapport}


def _build_helix_inputs_from_api(
    session,
    api_server: str,
    auth_headers: dict,
    magnet_name: str,
    I: float,
    h_conv_override: Optional[float],
    Teau_override: Optional[float],
    rho_override: Optional[float],
    lam_override: Optional[float],
    debug: bool,
) -> list[HelixInput]:
    """
    Fetch magnet → helix parts → geometry YAMLs + material data from MagnetDB.
    Returns a list of ``HelixInput`` ready for ``compute_helix()``.
    """
    # ── locate the magnet ──────────────────────────────────────────────────
    all_magnets = utils.get_list(
        session, api_server, auth_headers, mtype="magnet", debug=debug
    )
    if magnet_name not in all_magnets:
        raise ValueError(
            f"Magnet '{magnet_name}' not found in MagnetDB. "
            f"Available: {sorted(all_magnets.keys())}"
        )
    magnet = cache.get_object(
        session, api_server, auth_headers, "magnet", all_magnets[magnet_name],
        debug=debug,
    )
    if debug:
        print(f"[API] magnet '{magnet_name}' id={all_magnets[magnet_name]}, "
              f"parts={len(magnet.get('magnet_parts', []))}")

    inputs: list[HelixInput] = []
    helix_counter = 0

    with tempfile.TemporaryDirectory() as geom_dir:
        for part_stub in magnet.get("magnet_parts", []):
            ptype = part_stub.get("part", {}).get("type", "")
            if ptype != "helix":
                continue

            pid   = part_stub["part_id"]
            pobj  = cache.get_object(
                session, api_server, auth_headers, "part", pid, debug=debug
            )
            pname = pobj.get("name", f"part_{pid}")
            helix_counter += 1
            label = f"H{helix_counter}"

            # ── geometry YAML ──────────────────────────────────────────────
            yaml_path: Optional[str] = None
            for geom in pobj.get("geometries", []):
                attach = geom.get("attachment", {})
                if attach:
                    fname = utils.download(
                        session, api_server, auth_headers,
                        attach["id"], wd=geom_dir, debug=debug,
                    )
                    if fname and fname.endswith(".yaml"):
                        yaml_path = os.path.join(geom_dir, fname)
                        break

            if yaml_path is None or not os.path.exists(yaml_path):
                warnings.warn(f"{label} ({pname}): no geometry YAML found — skipped.")
                continue

            geom_params = _parse_helix_yaml(yaml_path, debug=debug)

            # ── material ──────────────────────────────────────────────────
            mat = pobj.get("material", {})
            mat_params = _extract_material_params(mat, debug=debug)

            rho   = rho_override if rho_override is not None else mat_params["rho"]
            lam   = lam_override if lam_override is not None else mat_params["lam"]
            h_conv = h_conv_override if h_conv_override is not None else DEFAULT_H_CONV
            Teau   = Teau_override   if Teau_override   is not None else DEFAULT_TEAU

            if rho is None:
                warnings.warn(
                    f"{label} ({pname}): ρ not found in material; "
                    "provide --rho or check MagnetDB material fields."
                )
                continue
            if lam is None:
                warnings.warn(
                    f"{label} ({pname}): λ not found in material; "
                    "provide --lam or check MagnetDB material fields."
                )
                continue

            inputs.append(HelixInput(
                name=label,
                rho=rho, I=I, h_conv=h_conv,
                Dint=geom_params["Dint"],
                Dext=geom_params["Dext"],
                lam=lam, Teau=Teau,
                h_spire=geom_params["h_spire"],
                rapport=mat_params.get("rapport"),
            ))

    return inputs


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Compute helix temperature rise for a MagnetDB magnet.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("magnet", help="Magnet name (e.g. M9, HL31)")
    p.add_argument("--current", "-I", type=float, required=True,
                   help="Operating current [A]")

    # ── magnettools backend ──
    mt_grp = p.add_argument_group("magnettools backend (preferred)")
    mt_grp.add_argument(
        "--dfile", metavar="PATH",
        help="Path to a pre-generated magnettools .d input file. "
             "When supplied, geometry and material params are read from "
             "Tube/BitterMagnet objects (magnettools bindings) instead of the API."
    )

    # ── server ──
    srv_grp = p.add_argument_group("API server")
    srv_grp.add_argument("--server", default=os.getenv("MAGNETDB_API_SERVER", "magnetdb.lncmi.local"))
    srv_grp.add_argument("--port",   type=int, default=None)
    srv_grp.add_argument("--https",  action="store_true")

    # ── cooling overrides ──
    cool_grp = p.add_argument_group("cooling overrides (API fallback defaults)")
    cool_grp.add_argument("--h_conv", type=float, default=None,
                          help=f"Heat-transfer coefficient [W/m²/°C] "
                               f"(default {DEFAULT_H_CONV:.0f})")
    cool_grp.add_argument("--Teau",   type=float, default=None,
                          help=f"Cooling water temperature [°C] (default {DEFAULT_TEAU})")

    # ── material overrides (API fallback) ──
    mat_grp = p.add_argument_group("material overrides (API fallback)")
    mat_grp.add_argument("--rho", type=float, default=None,
                         help="Override resistivity ρ [Ω·m] for all helices")
    mat_grp.add_argument("--lam", type=float, default=None,
                         help="Override thermal conductivity λ [W/m/°C] for all helices")

    p.add_argument("--debug",   action="store_true")
    p.add_argument("--verbose", action="store_true")
    return p


def main() -> None:
    parser = build_parser()
    args   = parser.parse_args()

    # ── auth ──────────────────────────────────────────────────────────────
    api_key = os.getenv("MAGNETDB_API_KEY")
    if not api_key:
        sys.exit("Error: MAGNETDB_API_KEY environment variable not set.")

    auth_headers = {"Authorization": api_key}

    protocol = "https" if args.https else "http"
    api_server = (
        f"{protocol}://{args.server}"
        if args.port is None
        else f"{protocol}://{args.server}:{args.port}"
    )
    verify = "/etc/ssl/certs" if args.https else True

    # ── build HelixInput list ─────────────────────────────────────────────
    with requests.Session() as session:
        session.verify = verify

        if args.dfile:
            # ─ magnettools .d-file backend ─────────────────────────────
            if not HAS_MT:
                sys.exit("Error: magnettools is required for --dfile but could not be imported.")
            if not os.path.isfile(args.dfile):
                sys.exit(f"Error: .d file not found: {args.dfile}")
            print(f"[magnettools] Reading geometry from {args.dfile}")
            helix_inputs = _load_from_dfile(
                args.dfile, args.current,
                h_conv_override=args.h_conv,
                Teau_override=args.Teau,
                debug=args.debug,
            )
        else:
            # ─ API + YAML backend ──────────────────────────────────────
            print(f"[API] Fetching geometry for magnet '{args.magnet}' from {api_server}")
            helix_inputs = _build_helix_inputs_from_api(
                session, api_server, auth_headers,
                magnet_name=args.magnet,
                I=args.current,
                h_conv_override=args.h_conv,
                Teau_override=args.Teau,
                rho_override=args.rho,
                lam_override=args.lam,
                debug=args.debug,
            )

    if not helix_inputs:
        sys.exit(f"No helix inputs assembled for magnet '{args.magnet}'. "
                 "Check API data or geometry files.")

    # ── compute ───────────────────────────────────────────────────────────
    results = [compute_helix(h) for h in helix_inputs]
    df = results_to_dataframe(results)

    # ── display ───────────────────────────────────────────────────────────
    pd.set_option("display.float_format", "{:.4g}".format)
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 220)

    sep = "=" * 100
    print(f"\n{sep}")
    print(f"Calcul températures hélices — {args.magnet}  (I = {args.current:.0f} A)")
    print(sep)
    if args.verbose:
        print(df.T.to_string())
    else:
        summary = df[["DT_paroi [°C]", "DT_plane [°C]", "DT_cyl [°C]",
                       "Tmax [°C]", "Tmoy [°C]",
                       "T_moy_ro [°C]", "Rapport IACS"]].copy()
        for col in summary.columns:
            if col == "Rapport IACS":
                summary[col] = summary[col].map(lambda x: f"{x:.4f}" if x == x else "—")
            else:
                summary[col] = summary[col].map(lambda x: f"{x:.2f}" if x == x else "—")
        print(summary.to_string())

    print(f"\nTmax range: {df['Tmax [°C]'].min():.1f} … {df['Tmax [°C]'].max():.1f} °C")
    print(f"Tmoy range: {df['Tmoy [°C]'].min():.1f} … {df['Tmoy [°C]'].max():.1f} °C")
    print()


if __name__ == "__main__":
    main()
