"""Shared fixtures."""

from pathlib import Path

import pytest

KITCHEN_SINK = Path(__file__).parent / "input" / "kitchen_sink.yaml"


def pytest_addoption(parser: pytest.Parser) -> None:
    """Make accepting new golden output an explicit developer action."""
    parser.addoption("--update-goldens", action="store_true", help="Regenerate committed C# expectations")


@pytest.fixture(scope="session")
def kitchen_sink() -> dict[str, str]:
    """Generated C# for the kitchen sink schema, covering every construct of docs/MAPPING.md."""
    from linkml_csharp.generator import CSharpGenerator

    return CSharpGenerator(str(KITCHEN_SINK), package="Kitchen.Sink").render()
