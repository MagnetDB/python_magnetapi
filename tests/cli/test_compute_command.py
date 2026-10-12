"""Tests for compute command."""

import ast
import inspect
import sys
import types
from pathlib import Path
from unittest.mock import Mock, patch

import python_magnetapi
from python_magnetapi.cli.commands.compute import ComputeCommand
from python_magnetapi.cli.context import CLIContext


def make_context():
    ctx = Mock(spec=CLIContext)
    ctx.session = Mock()
    ctx.web = "http://test:8000"
    ctx.headers = {"Authorization": "test-key"}
    ctx.debug = True
    return ctx


def compute_signature(module: str) -> inspect.Signature:
    """Signature of module.compute, rebuilt from the source.

    The module itself needs magnettools/python_magnetsetup, so it is not imported.
    """
    source = Path(python_magnetapi.__file__).parent / f"{module}.py"
    for node in ast.parse(source.read_text()).body:
        if isinstance(node, ast.FunctionDef) and node.name == "compute":
            names = [arg.arg for arg in node.args.args]
            n_required = len(names) - len(node.args.defaults)
            return inspect.Signature(
                [
                    inspect.Parameter(
                        name,
                        inspect.Parameter.POSITIONAL_OR_KEYWORD,
                        default=inspect.Parameter.empty if i < n_required else None,
                    )
                    for i, name in enumerate(names)
                ]
            )
    raise AssertionError(f"no compute function in {source}")


def test_hoop_stress_call_matches_signature():
    """compute --hoop_stress must call hoop_stress.compute with valid arguments."""
    fake = types.SimpleNamespace(compute=Mock())
    args = Mock(mtype="part", name="H1", inductances=False, flow_params=False, hoop_stress=True)

    with (
        patch.dict(sys.modules, {"python_magnetapi.hoop_stress": fake}),
        patch.object(python_magnetapi, "hoop_stress", fake, create=True),
        patch.object(ComputeCommand, "get_object_by_name", return_value={"id": 3}),
    ):
        assert ComputeCommand().execute(args, make_context()) == 0

    call = fake.compute.call_args
    # TypeError on a wrong keyword or a missing required argument
    bound = compute_signature("hoop_stress").bind(*call.args, **call.kwargs)
    assert bound.arguments["auth_headers"] == {"Authorization": "test-key"}
    assert bound.arguments["oid"] == 3
    assert bound.arguments["debug"] is True
