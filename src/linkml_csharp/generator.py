"""Generate C# classes from a LinkML schema, after the model of ``gen-java``.

See ``docs/MAPPING.md`` for the mapping contract.
"""

import json
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

import click
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from linkml.generators.oocodegen import OOCodeGenerator, OODocument, OOEnum
from linkml.utils.generator import shared_arguments
from linkml_runtime.linkml_model.meta import ClassDefinition, EnumDefinition, EnumDefinitionName, TypeDefinition
from linkml_runtime.utils.formatutils import camelcase

ENV = Environment(
    loader=FileSystemLoader(Path(__file__).parent / "templates"),
    undefined=StrictUndefined,
    keep_trailing_newline=True,
    trim_blocks=True,
    lstrip_blocks=True,
)

TYPEMAP = {
    "xsd:string": "string",
    "xsd:integer": "int",
    "xsd:float": "float",
    "xsd:double": "double",
    "xsd:boolean": "bool",
    "xsd:dateTime": "global::System.DateTimeOffset",
    "xsd:date": "global::System.DateOnly",
    "xsd:time": "global::System.TimeOnly",
    "xsd:anyURI": "global::System.Uri",
    "xsd:decimal": "decimal",
}

# Reserved (not contextual) C# keywords: https://learn.microsoft.com/dotnet/csharp/language-reference/keywords/
CSHARP_KEYWORDS = frozenset(
    """abstract as base bool break byte case catch char checked class const continue decimal default delegate do
    double else enum event explicit extern false finally fixed float for foreach goto if implicit in int interface
    internal is lock long namespace new null object operator out override params private protected public readonly
    ref return sbyte sealed short sizeof stackalloc static string struct switch this throw true try typeof uint ulong
    unchecked unsafe ushort using virtual void volatile while""".split()
)


def is_valid_namespace(namespace: str) -> bool:
    """Return True if ``namespace`` is dot-separated C# identifiers, none of them a keyword.

    >>> is_valid_namespace("Org.Example.Model")
    True
    >>> is_valid_namespace("Org.class.Model"), is_valid_namespace("1Bad"), is_valid_namespace("Org..Model")
    (False, False, False)
    """
    return all(part.isidentifier() and part not in CSHARP_KEYWORDS for part in namespace.split("."))


def cs_string(text: str) -> str:
    """Render ``text`` as a C# regular string literal.

    JSON escapes are valid C# escapes; ASCII-only output also escapes line
    separators such as U+2028, which would end a C# literal.

    >>> print(cs_string('say "hi" \\\\ \\u2028'))
    "say \\"hi\\" \\\\ \\u2028"
    """
    return json.dumps(text)


def xml_doc(text: str, indent: str = "") -> str:
    """Render ``text`` as an XML documentation ``<summary>`` comment.

    >>> print(xml_doc("a < b\\nand c"))
    /// <summary>
    /// a &lt; b
    /// and c
    /// </summary>
    """
    lines = ["<summary>", *escape(text).splitlines(), "</summary>"]
    return "\n".join(f"{indent}/// {line}".rstrip() for line in lines)


ENV.filters.update(cs_string=cs_string, xml_doc=xml_doc)


@dataclass
class CSharpGenerator(OOCodeGenerator):
    """Generate one C# file per LinkML class and enum.

    Like ``JavaGenerator``, :meth:`render` returns the files in memory and
    :meth:`serialize` writes them to a directory.
    """

    generatorname = Path(__file__).name
    generatorversion = version("linkml-csharp")
    valid_formats = ["cs"]
    file_extension = "cs"

    true_enums: bool = True
    package: str = "Example"

    def __post_init__(self) -> None:
        """Validate the namespace, which is stored in ``package`` like gen-java's package."""
        super().__post_init__()
        if not is_valid_namespace(self.package):
            raise ValueError(f"{self.package!r} is not a valid C# namespace")

    @classmethod
    def validate_generator_args(cls, args: Mapping[str, Any]) -> None:
        """Report a bad ``--namespace`` as a usage error before loading the schema, like gen-java."""
        if not is_valid_namespace(args["namespace"]):
            raise click.UsageError(f"{args['namespace']!r} is not a valid C# namespace")

    def default_value_for_type(self, typ: str) -> str:
        """Unused: optional properties default to null and required ones must be set."""
        return "null"

    def get_slot_name(self, sn: str) -> str:
        """Properties are PascalCase."""
        return camelcase(sn)

    def map_class(self, c: ClassDefinition) -> str | None:
        """Represent ``linkml:Any`` as ``object``, as gen-java uses ``Object``."""
        return "object" if c.class_uri == "linkml:Any" else None

    def map_type(self, t: TypeDefinition, required: bool = False) -> str:
        """Map a type by its XSD URI, else by its base type; nullability is added by the template."""
        if t.uri in TYPEMAP:
            return TYPEMAP[t.uri]
        if t.typeof:
            return self.map_type(self.schemaview.get_type(t.typeof))
        raise ValueError(f"Type {t.name!r} cannot be mapped to a C# type")

    @staticmethod
    def make_multivalued(range: str) -> str:
        """Collections are lists, as in gen-java."""
        return f"global::System.Collections.Generic.List<{range}>"

    def generate_enum_label(self, value: str) -> str:
        """Enum members are PascalCase."""
        return camelcase(super().generate_enum_label(value))

    def generate_enum_objects(self, all_enums: dict[EnumDefinitionName, EnumDefinition]) -> dict[str, OOEnum]:
        """Keep the raw permissible value text; templates escape it with :func:`cs_string`."""
        enums = super().generate_enum_objects(all_enums)
        for name, enum in enums.items():
            for value, pv in zip(enum.values, all_enums[name].permissible_values.values()):
                # ponytail: undoes OOCodeGenerator's Java-only quote escaping; drop once upstream moves it to gen-java
                value.text = pv.text
        return enums

    def render(self) -> dict[str, str]:
        """Render the schema to C# source, keyed by filename (e.g. ``"Person.cs"``)."""
        docs = self.create_documents()
        validate_names(docs)
        return {
            f"{doc.name}.cs": ENV.get_template("class.jinja2").render(doc=doc, cls=doc.classes[0], gen=self)
            if doc.classes
            else ENV.get_template("enum.jinja2").render(doc=doc, enum=doc.enums[0], gen=self)
            for doc in docs
        }

    def serialize(self, directory: str | Path, **kwargs) -> None:
        """Write one file per class and enum into ``directory``."""
        Path(directory).mkdir(parents=True, exist_ok=True)
        for filename, code in self.render().items():
            Path(directory, filename).write_text(code, encoding="utf-8")


def check_unique(names: list[str], what: str) -> None:
    """Fail on names that collide after PascalCase conversion.

    >>> check_unique(["FooBar", "FooBar"], "properties of class 'X'")
    Traceback (most recent call last):
    ValueError: Duplicate properties of class 'X': FooBar
    """
    duplicates = sorted(name for name, count in Counter(names).items() if count > 1)
    if duplicates:
        raise ValueError(f"Duplicate {what}: {', '.join(duplicates)}")


def validate_names(docs: list[OODocument]) -> None:
    """Fail, naming the elements, instead of emitting C# that does not compile.

    This runs on rendered names, whichever ``OOCodeGenerator`` path built them.
    PascalCase names never clash with (lowercase) C# keywords.
    """
    check_unique([doc.name.lower() for doc in docs], "type file names (case-insensitive)")
    for doc in docs:
        if doc.classes:
            cls = doc.classes[0]
            names = [f.name for f in cls.all_fields]
            check_unique(names, f"properties of class {cls.name!r}")
            if cls.name in names:
                raise ValueError(f"Class {cls.name!r} has a property with its own name, which C# forbids")
        else:
            names = [value.label for value in doc.enums[0].values]
            check_unique(names, f"members of enum {doc.name!r}")
        for name in [doc.name, *names]:
            if not name.isidentifier():
                raise ValueError(f"{name!r} in {doc.name!r} is not a valid C# identifier")


@shared_arguments(CSharpGenerator)
@click.option("--output-directory", "-d", default="output", show_default=True, help="Directory for the .cs files")
@click.option("--namespace", default="Example", show_default=True, help="Namespace of the generated types")
@click.option("--use-aliases/--no-use-aliases", default=False, help="Use aliases when available to name properties")
@click.version_option(version("linkml-csharp"), "-V", "--version")
@click.command(name="csharp")
def cli(yamlfile: str, output_directory: str, namespace: str, **args) -> None:
    """Generate C# classes to represent a LinkML model."""
    CSharpGenerator.validate_generator_args({"namespace": namespace})
    CSharpGenerator(yamlfile, package=namespace, **args).serialize(output_directory)


if __name__ == "__main__":
    cli()
