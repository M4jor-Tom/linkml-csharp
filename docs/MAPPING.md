# LinkML → C# mapping

## Contract

Generate **structural C# data classes**, not a LinkML runtime. The mapping
follows upstream [`gen-java`](https://linkml.io/linkml/generators/java.html)
(`JavaGenerator`, built on `OOCodeGenerator`) wherever C# allows, so the
generator can later be proposed upstream as `gen-csharp`.

One `.cs` file is written per class and enum, all in one namespace (see
[Imports](#imports) for types generated elsewhere). Generated
code has no runtime dependencies beyond the .NET base class library and needs
C# 11 (`required` members). It is tested with the .NET 10 SDK.

Validation, JSON/YAML loading and saving, and reference resolution belong to the
caller. Keep the source schema for semantic validation.

## Types

Built-in types are mapped from their XSD URI, as in `gen-java`. A custom type
(`typeof`) uses the mapping of its base type.

| LinkML | XSD URI | Java (`gen-java`) | C# |
|---|---|---|---|
| `string`, `curie`, `ncname` | `xsd:string` | `String` | `string` |
| `integer` | `xsd:integer` | `Integer` | `int` |
| `float` | `xsd:float` | `Float` | `float` |
| `double` | `xsd:double` | `Double` | `double` |
| `boolean` | `xsd:boolean` | `Boolean` | `bool` |
| `datetime` | `xsd:dateTime` | `ZonedDateTime` | `System.DateTimeOffset` |
| `date` | `xsd:date` | `LocalDate` | `System.DateOnly` |
| `time` | `xsd:time` | `LocalTime` | `System.TimeOnly` |
| `uri`, `uriorcurie` | `xsd:anyURI` | `URI` | `System.Uri` |
| `decimal` | `xsd:decimal` | `BigDecimal` | `decimal` |
| class `linkml:Any` | | `Object` | `object` |

Like Java's `Integer`, `int` is 32-bit although `xsd:integer` is unbounded, and
`decimal` has 28–29 significant digits where `BigDecimal` is arbitrary.
Framework types are written fully qualified (`global::System.Uri`) so schema
classes named `Uri`, `List` or `System` cannot shadow them.

## Slots

| LinkML | C# |
|---|---|
| slot | public auto-property `{ get; set; }` |
| optional (default) | nullable `T?`: absence stays distinct from `0`, `false` or `""` |
| `required: true` | non-nullable `required T` |
| `multivalued: true` | `System.Collections.Generic.List<T>`, nullable unless required |
| class range | the generated class, whether inlined or referenced |
| enum range | the generated enum |
| `any_of` without `range` | the schema `default_range` (`string` if unset) |
| `description` | XML documentation comment |

Every file enables `#nullable enable`, so `T?` is `Nullable<T>` for value types and
a nullable annotation for reference types. Java's boxed-versus-primitive choice
becomes this nullable-versus-`required` choice.

As in `gen-java`, a reference by identifier is still typed as the target class,
dictionary-inlined collections are lists, and `ifabsent`, `pattern`, ranges and
cardinalities are not enforced or initialized.

## Classes

| LinkML | C# |
|---|---|
| class | `public partial class`, so handwritten members can live in another file |
| `is_a` | base class |
| `mixins` | flattened slots, without multiple inheritance (as in `gen-java`) |
| inherited slots | inherited, not redeclared; a `slot_usage` refinement keeps the parent's type |
| `abstract: true` | `abstract` |
| `mixin: true` | an ordinary class, like `gen-java` |
| `tree_root: true` | no special treatment |

## Enums

Enums are always real C# `enum` types (`gen-java`'s `--true-enums`; there is no
string mode). Each member carries its original text in
`[System.Runtime.Serialization.EnumMember(Value = "...")]`, which serializers can
use to round-trip values such as `in limbo`.

## Naming

- Classes, enums, properties and enum members are PascalCase, using LinkML's
  `camelcase` (`in limbo` → `InLimbo`, `is_player` → `IsPlayer`, `ALIVE` → `ALIVE`).
  Enum labels use `title` when present, and the `OOCodeGenerator` sanitization
  (`1` → `Number1`, punctuation spelled out by its Unicode name).
- `--use-aliases` names properties after slot aliases, as in `gen-java`.
- Output filenames are the type name plus `.cs`; the namespace comes from
  `--namespace` (default `Example`) and must be dot-separated C# identifiers
  that are not keywords.

Generation fails, naming the elements involved, instead of emitting code that
does not compile:

- a name that is not a valid identifier;
- two types whose filenames differ only by case;
- two properties of a class (including inherited ones) or two enum members with
  the same name after PascalCase (`foo_bar` and `fooBar`);
- a property named like its class (C# error CS0542).

## Imports

Imported schemas are merged: their classes and enums are generated in the same
namespace. As for every LinkML generator, `--no-mergeimports` generates only the
classes and enums the given schema file defines itself.

`--import-namespace SCHEMA_NAME=NAMESPACE` (repeatable; `import_namespaces` in
Python) declares that the types of the imported schema named `SCHEMA_NAME` are
already generated in `NAMESPACE`, in the spirit of `gen-pydantic`'s split mode:

- classes and enums defined by that schema are not generated;
- references to them (property types, list elements, base classes) are written
  `global::NAMESPACE.Name`, so a type of the same name in the generated
  namespace cannot shadow them;
- its types still map to their C# primitive, and slots of its mixins are still
  flattened into the classes that use them.

A malformed value, an invalid namespace, or a name that is not a schema of the
imports closure is a usage error.

## Not supported

`gen-java`'s template variants, `--template-dir`/`--template-file`, extra
templates, visitors, custom type maps and `--config-file` are not provided.
Regeneration does not delete obsolete files: generate into a fresh directory.
