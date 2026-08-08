"""Validate the built wheel from an isolated virtual environment."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.package
def test_wheel_installs_and_runs_minimal_pytest(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[2]
    wheel_dir = tmp_path / "wheel"
    venv_dir = tmp_path / "venv"

    supplied_wheel = os.environ.get("CORE_WHEEL_PATH")
    if supplied_wheel is None:
        subprocess.run(
            [sys.executable, "-m", "build", "--wheel", "--outdir", str(wheel_dir)],
            cwd=project_root,
            check=True,
        )
    else:
        wheel_dir.mkdir()
        shutil.copy2(Path(supplied_wheel), wheel_dir)
    subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)

    if os.name == "nt":
        venv_python = venv_dir / "Scripts" / "python.exe"
    else:
        venv_python = venv_dir / "bin" / "python"

    wheels = list(wheel_dir.glob("*.whl"))
    assert len(wheels) == 1
    if supplied_wheel is not None:
        subprocess.run(
            [
                str(venv_python),
                "-m",
                "pip",
                "install",
                "-r",
                str(project_root / "requirements/ci.lock"),
            ],
            check=True,
        )
    subprocess.run(
        [
            str(venv_python),
            "-m",
            "pip",
            "install",
            *(["--no-deps"] if supplied_wheel is not None else []),
            str(wheels[0]),
        ],
        check=True,
    )

    smoke_test = tmp_path / "test_installed_core.py"
    smoke_test.write_text(
        """\
from cyber_agent_test_core import api, checks, fixtures, flows, markers, models


def test_installed_public_api(core_version: str) -> None:
    assert api.CORE_VERSION == core_version
    assert checks is not None
    assert fixtures is not None
    assert flows is not None
    assert markers.FRAMEWORK_CONTRACT == "framework_contract"
    assert models is not None
""",
        encoding="utf-8",
    )
    subprocess.run(
        [
            str(venv_python),
            "-m",
            "pytest",
            "-p",
            "no:cacheprovider",
            "-q",
            str(smoke_test),
        ],
        cwd=tmp_path,
        check=True,
    )
