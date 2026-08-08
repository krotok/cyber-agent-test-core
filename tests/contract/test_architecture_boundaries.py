"""Executable dependency and public-boundary architecture contracts."""

import ast
from pathlib import Path

import cyber_agent_test_core
from cyber_agent_test_core import api, checks, flows, markers, models


def _framework_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            if node.module.startswith("cyber_agent_test_core."):
                imports.add(node.module)
        elif isinstance(node, ast.Import):
            imports.update(
                alias.name
                for alias in node.names
                if alias.name.startswith("cyber_agent_test_core.")
            )
    return imports


def test_transport_layer_has_no_reverse_dependencies() -> None:
    root = Path(__file__).resolve().parents[2] / "src/cyber_agent_test_core/transports"
    forbidden = (
        "agent",
        "backend",
        "checks",
        "controllers",
        "execution",
        "fixtures",
        "flows",
        "inventory",
        "platforms",
        "reporting",
    )

    imports = set().union(*(_framework_imports(path) for path in root.glob("*.py")))

    assert not {
        value
        for value in imports
        if value.split(".")[1] in forbidden
    }


def test_public_modules_export_no_private_module_objects() -> None:
    public_modules = (api, checks, flows, markers, models)
    allowed = tuple(
        f"cyber_agent_test_core.{name}"
        for name in ("api", "checks", "flows", "markers", "models")
    )

    for module in public_modules:
        for name in module.__all__:
            value = getattr(module, name)
            owner = getattr(value, "__module__", module.__name__)
            assert owner.startswith(allowed), f"{module.__name__}.{name} leaks {owner}"

    assert cyber_agent_test_core.__all__ == ["CORE_VERSION"]
