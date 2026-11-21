"""Mapping rules of docs/MAPPING.md, checked on generated source."""

from pathlib import Path

import click
import pytest
from click.testing import CliRunner

from linkml_csharp.generator import CSharpGenerator, cli

# A root schema that defines nothing, its module, and the "shared-model" schema the module imports.
IMPORTING = str(Path(__file__).parent / "input" / "imports" / "app.yaml")


def generate(classes: str = "", enums: str = "", **kwargs) -> dict[str, str]:
    """Render a minimal schema built from YAML fragments."""
    schema = f"""id: https://example.org/test
name: test
imports: [linkml:types]
prefixes: {{linkml: https://w3id.org/linkml/}}
default_range: string
classes: {{{classes}}}
enums: {{{enums}}}
"""
    return CSharpGenerator(schema, **kwargs).render()


def test_one_file_per_class_and_enum(kitchen_sink: dict[str, str]) -> None:
    assert sorted(kitchen_sink) == [
        "Address.cs",
        "Dataset.cs",
        "Event.cs",
        "HasAliases.cs",
        "LifeStatus.cs",
        "NamedThing.cs",
        "Person.cs",
        "Pet.cs",
    ]
    assert all("namespace Kitchen.Sink;" in code for code in kitchen_sink.values())


@pytest.mark.parametrize(
    "line",
    [
        "public int? Age { get; set; }",
        "public float? Height { get; set; }",
        "public double? Weight { get; set; }",
        "public required bool IsPlayer { get; set; }",
        "public global::System.DateOnly? BirthDate { get; set; }",
        "public global::System.TimeOnly? WakeTime { get; set; }",
        "public global::System.DateTimeOffset? LastSeen { get; set; }",
        "public decimal? Balance { get; set; }",
        "public float? Luck { get; set; }",  # custom type uses its base type
        "public LifeStatus? Status { get; set; }",
        "public Person? BestFriend { get; set; }",
        "public global::System.Collections.Generic.List<Pet>? Pets { get; set; }",
        "public required global::System.Collections.Generic.List<Event> History { get; set; }",
        "public string? LuckyCharm { get; set; }",
        "public object? Extra { get; set; }",
        "public global::System.Collections.Generic.List<string>? Aliases { get; set; }",  # flattened mixin
        "public partial class Person : NamedThing",
    ],
)
def test_person_properties(kitchen_sink: dict[str, str], line: str) -> None:
    assert f"{line}\n" in kitchen_sink["Person.cs"]


def test_inherited_slots_are_not_redeclared(kitchen_sink: dict[str, str]) -> None:
    assert "public required global::System.Uri Id { get; set; }" in kitchen_sink["NamedThing.cs"]
    assert "public abstract partial class NamedThing\n" in kitchen_sink["NamedThing.cs"]
    assert " Id " not in kitchen_sink["Person.cs"]


def test_enum_members_keep_their_text(kitchen_sink: dict[str, str]) -> None:
    code = kitchen_sink["LifeStatus.cs"]
    assert '[global::System.Runtime.Serialization.EnumMember(Value = "in limbo")]\n    InLimbo,\n' in code
    assert '(Value = "say \\"cheese\\" \\\\o/")]\n    Smiling,\n' in code


def test_descriptions_are_escaped_xml_doc(kitchen_sink: dict[str, str]) -> None:
    assert "/// This description spans two lines &amp; has &lt;markup&gt;.\n" in kitchen_sink["NamedThing.cs"]


def test_aliases_are_opt_in() -> None:
    classes = "Thing: {attributes: {slot_definitions: {alias: slots}}}"
    assert " SlotDefinitions " in generate(classes)["Thing.cs"]
    assert " Slots " in generate(classes, use_aliases=True)["Thing.cs"]


@pytest.mark.parametrize(
    ("classes", "enums", "message"),
    [
        ("Thing: {attributes: {foo_bar: {}, fooBar: {}}}", "", "Duplicate properties of class 'Thing': FooBar"),
        ("Base: {attributes: {foo_bar: {}}}, Sub: {is_a: Base, attributes: {fooBar: {}}}", "", "class 'Sub'"),
        ("Thing: {attributes: {thing: {}}}", "", "property with its own name"),
        ("", "E: {permissible_values: {a b: {}, a_b: {}}}", "Duplicate members of enum 'E': AB"),
        ("Status: {}", "status: {permissible_values: {a: {}}}", "Duplicate type file names"),
        ("Thing: {attributes: {'1st': {}}}", "", "'1st' in 'Thing' is not a valid C# identifier"),
        ("", "my-enum: {permissible_values: {a: {}}}", "'My-enum' in 'My-enum' is not a valid C# identifier"),
    ],
)
def test_uncompilable_names_fail(classes: str, enums: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        generate(classes, enums)


@pytest.mark.parametrize("namespace", ["Org.class", "1Org", "Org..Model", ""])
def test_invalid_namespace_fails(namespace: str) -> None:
    with pytest.raises(ValueError, match="not a valid C# namespace"):
        generate(package=namespace)


def test_cli_writes_files(tmp_path: Path) -> None:
    schema = tmp_path / "schema.yaml"
    schema.write_text("id: https://example.org/test\nname: test\nclasses: {Thing: {}}\n", encoding="utf-8")
    result = CliRunner().invoke(cli, [str(schema), "-d", str(tmp_path / "out"), "--namespace", "My.Model"])
    assert result.exit_code == 0, result.output
    assert "namespace My.Model;" in (tmp_path / "out" / "Thing.cs").read_text(encoding="utf-8")


def test_cli_rejects_namespace_as_usage_error(tmp_path: Path) -> None:
    schema = tmp_path / "schema.yaml"
    schema.write_text("id: https://example.org/test\nname: test\n", encoding="utf-8")
    result = CliRunner().invoke(cli, [str(schema), "--namespace", "Org.class"])
    assert result.exit_code == 2 and "not a valid C# namespace" in result.output


def test_imports_are_merged_by_default() -> None:
    files = CSharpGenerator(IMPORTING).render()
    assert sorted(files) == ["Entity.cs", "Mode.cs", "Probe.cs", "Tagged.cs", "Unit.cs", "Vector.cs"]
    assert "global::Example" not in "".join(files.values())
    assert "public partial class Probe : Entity\n" in files["Probe.cs"]
    assert files == CSharpGenerator(IMPORTING, import_namespaces={}).render()


def test_no_mergeimports_leaves_out_imported_classes_and_enums() -> None:
    module = IMPORTING.replace("app.yaml", "module.yaml")
    assert sorted(CSharpGenerator(module, mergeimports=False).render()) == ["Mode.cs", "Probe.cs"]
    assert CSharpGenerator(IMPORTING, mergeimports=False).render() == {}


@pytest.mark.parametrize(
    "line",
    [
        "public partial class Probe : global::Shared.Model.Entity",
        "public required global::Shared.Model.Vector Position { get; set; }",
        "public global::System.Collections.Generic.List<global::Shared.Model.Vector>? Waypoints { get; set; }",
        "public global::Shared.Model.Unit? Unit { get; set; }",
        "public global::System.Collections.Generic.List<global::Shared.Model.Unit>? Units { get; set; }",
        "public double? Reach { get; set; }",  # an imported type still maps to its primitive
        "public Mode? Mode { get; set; }",
        "public Probe? Next { get; set; }",
        "public global::System.Collections.Generic.List<string>? Tags { get; set; }",  # flattened imported mixin
    ],
)
def test_import_namespace_qualifies_references(line: str) -> None:
    files = CSharpGenerator(IMPORTING, package="App", import_namespaces={"shared-model": "Shared.Model"}).render()
    assert sorted(files) == ["Mode.cs", "Probe.cs"]
    assert f"{line}\n" in files["Probe.cs"]
    assert " Id " not in files["Probe.cs"]


@pytest.mark.parametrize(
    ("import_namespaces", "message"),
    [
        ({"unknown": "Shared.Model"}, "'unknown' is not an imported schema; choose from: app-module, shared-model"),
        ({"app": "Shared.Model"}, "'app' is not an imported schema"),
        ({"shared-model": "Shared.class"}, "'Shared.class' is not a valid C# namespace"),
    ],
)
def test_invalid_import_namespace_fails(import_namespaces: dict[str, str], message: str) -> None:
    with pytest.raises(click.UsageError, match=message):
        CSharpGenerator(IMPORTING, import_namespaces=import_namespaces)


def test_cli_import_namespace(tmp_path: Path) -> None:
    args = [IMPORTING, "-d", str(tmp_path), "--namespace", "App", "--import-namespace", "shared-model=Shared.Model"]
    result = CliRunner().invoke(cli, args)
    assert result.exit_code == 0, result.output
    assert sorted(path.name for path in tmp_path.iterdir()) == ["Mode.cs", "Probe.cs"]
    assert ": global::Shared.Model.Entity\n" in (tmp_path / "Probe.cs").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ("shared-model", "'shared-model' is not SCHEMA_NAME=NAMESPACE"),
        ("=Shared.Model", "is not SCHEMA_NAME=NAMESPACE"),
        ("shared-model=", "is not SCHEMA_NAME=NAMESPACE"),
        ("shared-model=Shared.class", "'Shared.class' is not a valid C# namespace"),
        ("unknown=Shared.Model", "'unknown' is not an imported schema"),
    ],
)
def test_cli_rejects_import_namespace_as_usage_error(tmp_path: Path, value: str, message: str) -> None:
    result = CliRunner().invoke(cli, [IMPORTING, "-d", str(tmp_path), "--import-namespace", value])
    assert result.exit_code == 2 and message in result.output
    assert not list(tmp_path.iterdir())
