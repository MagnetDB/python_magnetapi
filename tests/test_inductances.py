"""Unit tests for python_magnetapi.inductances (no server, no magnettools needed)."""

import os
import sys
import types
from unittest.mock import Mock, patch

import pytest

from python_magnetapi import inductances

RESULT = {
    "labels": ["H_0", "B_0"],
    "matrix": [[2.0e-3, 2.0e-5], [2.0e-5, 4.0e-7]],
    "L_H": 2.0e-3,
    "L_B": 4.0e-7,
    "L_S": 0.0,
    "M_HB": 2.0e-5,
    "M_HS": 0.0,
    "M_BS": 0.0,
}
SETUP_DATA = ("tubes", "helices", "ohelices", "bmagnets", "umagnets", "shims")


@pytest.fixture
def deps():
    """Fake magnettools/python_magnetsetup functions returned by _import_magnettools."""
    fakes = types.SimpleNamespace(
        compute_inductance_matrix=Mock(return_value=RESULT),
        magnet_setup=Mock(return_value=SETUP_DATA),
        msite_setup=Mock(return_value=SETUP_DATA),
        appenv=Mock(return_value="env"),
    )
    with patch.object(
        inductances,
        "_import_magnettools",
        return_value=(
            fakes.compute_inductance_matrix,
            fakes.magnet_setup,
            fakes.msite_setup,
            fakes.appenv,
        ),
    ):
        yield fakes


@pytest.fixture
def api():
    """Fake MagnetDB API calls made through utils."""
    magnet = {"id": 1, "name": "M1"}
    config = {"results": {"geom": "M1.yaml"}}
    with (
        patch.object(inductances.utils, "get_object", return_value=magnet) as get_object,
        patch.object(inductances.utils, "get_data", return_value=config) as get_data,
        patch.object(
            inductances.utils, "get_magnets_for_site", return_value=[magnet]
        ) as get_magnets_for_site,
        patch.object(inductances, "_fetch_geometries") as fetch,
    ):
        yield types.SimpleNamespace(
            get_object=get_object,
            get_data=get_data,
            get_magnets_for_site=get_magnets_for_site,
            fetch=fetch,
        )


def test_rejects_unsupported_type():
    with patch.object(inductances, "_import_magnettools") as import_deps:
        assert inductances.compute(None, "http://api", {}, oid=1, mtype="record") is None
    import_deps.assert_not_called()


def test_magnet(deps, api, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    result = inductances.compute(
        None, "http://api", {}, oid=1, mtype="magnet", debug=True, csvfile="L.csv"
    )

    assert result is RESULT
    deps.magnet_setup.assert_called_once_with("env", {"geom": "M1.yaml"}, True)
    deps.msite_setup.assert_not_called()
    api.get_magnets_for_site.assert_not_called()
    assert api.fetch.call_args.args[3] == [{"id": 1, "name": "M1"}]
    deps.compute_inductance_matrix.assert_called_once_with(
        "tubes", "helices", "bmagnets", "umagnets",
        csvfile=str(tmp_path / "L.csv"), verbose=False,
    )
    assert os.getcwd() == str(tmp_path)


def test_site(deps, api, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    assert inductances.compute(None, "http://api", {}, oid=7, mtype="site") is RESULT

    api.get_data.assert_called_once_with(None, "http://api", {}, oid=7, mtype="site")
    api.get_magnets_for_site.assert_called_once_with(None, "http://api", {}, 7)
    deps.msite_setup.assert_called_once_with("env", {"geom": "M1.yaml"}, False)
    deps.magnet_setup.assert_not_called()


def test_restores_cwd_on_error(deps, api, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    deps.magnet_setup.side_effect = RuntimeError("setup failed")

    with pytest.raises(RuntimeError, match="setup failed"):
        inductances.compute(None, "http://api", {}, oid=1)

    assert os.getcwd() == str(tmp_path)


def test_missing_object(deps, api):
    api.get_object.return_value = None
    assert inductances.compute(None, "http://api", {}, oid=1) is None
    deps.magnet_setup.assert_not_called()


def _fake_modules(version, module="inductances"):
    """Stand-ins for the optional modules, to put in sys.modules.

    module: name of the magnettools module providing compute_inductance_matrix
    ("Mutual" up to 1.2.2, "inductances" afterwards).
    """
    ns = types.SimpleNamespace
    return {
        "magnettools": ns(__version__=version),
        f"magnettools.{module}": ns(compute_inductance_matrix=Mock(name=module)),
        "python_magnetsetup": ns(),
        "python_magnetsetup.ana": ns(magnet_setup=Mock(), msite_setup=Mock()),
        "python_magnetsetup.config": ns(appenv=Mock()),
    }


def test_requires_recent_magnettools():
    with patch.dict(sys.modules, _fake_modules("1.2.1", "Mutual")):
        with pytest.raises(RuntimeError, match="magnettools>=1.2.2"):
            inductances._import_magnettools()


@pytest.mark.parametrize(("version", "module"), [("1.2.3", "inductances"), ("1.2.2", "Mutual")])
def test_compute_inductance_matrix_module(version, module):
    modules = _fake_modules(version, module)
    with patch.dict(sys.modules, modules):
        compute_inductance_matrix, *_ = inductances._import_magnettools()
    assert compute_inductance_matrix is modules[f"magnettools.{module}"].compute_inductance_matrix


def test_missing_magnettools():
    with patch.dict(sys.modules, {"magnettools": None}):
        with pytest.raises(RuntimeError, match=r"python-magnetapi\[full\]"):
            inductances._import_magnettools()


def test_fetch_geometries(tmp_path):
    for d in ("geometries", "cad"):
        (tmp_path / d).mkdir()

    texts = {
        "http://api/api/magnets/1/geometry.yaml": "magnet: M1\n",
        "http://api/api/parts/10/geometry.yaml": "part: H1\n",
        "http://api/api/parts/11/geometry.yaml": "",  # no geometry
    }
    session = Mock()
    session.get.side_effect = lambda url, headers: Mock(status_code=200, text=texts[url])
    parts = [
        {
            "id": 10,
            "name": "H1",
            "modelaxi_attachment": {"id": 100},
            "shape_attachment": {"id": 101},
        },
        {"id": 11, "name": "R1", "modelaxi_attachment": None, "shape_attachment": None},
    ]
    magnets = [{"id": 1, "name": "M1"}]

    with (
        patch.object(inductances.utils, "get_parts_for_magnet", return_value=parts),
        patch.object(inductances.utils, "download") as download,
    ):
        inductances._fetch_geometries(session, "http://api", {}, magnets, str(tmp_path))

    assert (tmp_path / "geometries" / "M1.yaml").read_text() == "magnet: M1\n"
    assert (tmp_path / "geometries" / "H1.yaml").read_text() == "part: H1\n"
    assert not (tmp_path / "geometries" / "R1.yaml").exists()
    assert [c.args[3] for c in download.call_args_list] == ["100", "101"]
    assert all(c.kwargs["wd"] == str(tmp_path / "cad") for c in download.call_args_list)


def test_print_result(capsys):
    result = {
        "labels": ["H_0", "B_0", "S_0"],
        "matrix": [[1.0, 4.0, 5.0], [4.0, 2.0, 6.0], [5.0, 6.0, 3.0]],
        "L_H": 1.0, "L_B": 2.0, "L_S": 3.0, "M_HB": 4.0, "M_HS": 5.0, "M_BS": 6.0,
    }
    inductances._print_result("M1", result)
    out = capsys.readouterr().out
    assert "Supra" in out and "6.000000e+00" in out
    assert "inductance matrix" in out  # small enough to print in full

    big = dict(result, labels=[f"H_{i}" for i in range(7)] + ["B_0"])
    inductances._print_result("M1", big)
    assert "save it with --csv" in capsys.readouterr().out
