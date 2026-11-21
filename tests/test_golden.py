"""Committed generator output, with opt-in updates and read-only checks."""

from pathlib import Path

import pytest

from linkml_csharp.generator import CSharpGenerator

ROOT = Path(__file__).parent


@pytest.mark.parametrize("schema", sorted((ROOT / "input").glob("*.yaml")), ids=lambda p: p.stem)
def test_committed_goldens(schema: Path, request: pytest.FixtureRequest) -> None:
    """Each input schema generates exactly the committed ``tests/golden/<stem>/*.cs`` files."""
    golden = ROOT / "golden" / schema.stem
    generator = CSharpGenerator(str(schema), package="Golden")
    actual = generator.render()
    if request.config.getoption("--update-goldens"):
        for obsolete in golden.glob("*.cs"):
            obsolete.unlink()
        generator.serialize(golden)
    expected = {path.name: path.read_text(encoding="utf-8") for path in golden.glob("*.cs")}
    command = "nix develop --command golden --update-goldens"
    assert expected.keys() == actual.keys(), f"Golden filenames differ; review updates with `{command}`"
    for name in sorted(actual):
        assert expected[name] == actual[name], f"Golden content differs: {name}; review updates with `{command}`"
