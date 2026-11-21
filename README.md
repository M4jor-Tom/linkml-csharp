# linkml-csharp

Generate structural C# data classes from [LinkML](https://linkml.io) schemas.
The mapping follows LinkML's own [Java generator](https://linkml.io/linkml/generators/java.html)
(`gen-java`), so this generator can later be proposed upstream as `gen-csharp`.
Generated code depends only on the .NET base class library, needs C# 11, and is
tested with the .NET 10 SDK.

## Usage

```shell
uv tool install git+https://github.com/M4jor-Tom/linkml-csharp
gen-csharp my_schema.yaml -d src/MyApp/Model/ --namespace MyApp.Model
```

One `.cs` file is written per class and enum. Slots become PascalCase
properties; optional slots are nullable, `required` slots use C# `required`
members, multivalued slots are lists, and enums keep their original text in
`[EnumMember]`:

```csharp
var person = new Person { Id = new Uri("ks:alice"), Name = "Alice", IsPlayer = false, History = new() };
Debug.Assert(person.Age == null);
person.Status = LifeStatus.InLimbo; // [EnumMember(Value = "in limbo")]
```

Classes are `partial`, so handwritten members can live in a separate file.
Inheritance, flattened mixins, abstract classes, aliases (`--use-aliases`) and
custom types are supported; names that would not compile fail generation.

This is **not a LinkML runtime**: validation, reference resolution and JSON/YAML
loading and saving remain the caller's responsibility. Keep the source schema
for validation. See [the mapping contract](docs/MAPPING.md) for every
representation, how it compares with `gen-java`, and what is not supported.

Regeneration overwrites files but does not delete obsolete ones: generate into a
dedicated directory and clear it first when classes are removed.

## Development

```shell
nix develop --command uv run pytest
nix develop --command ruff check
nix develop --command ruff format --check
```

The suite compiles generated code with warnings as errors and runs it on a real
.NET SDK (`tests/test_dotnet.py`); the test fails rather than skips when `dotnet`
is missing. Python-only tests run with `uv run pytest --ignore=tests/test_dotnet.py`.

### Golden output

Committed examples live in `tests/golden/<input-name>/`, one directory per
`tests/input/*.yaml` schema. Normal pytest runs and the pre-commit hook compare
them read-only. After an intentional generator change:

```shell
nix develop --command golden --update-goldens
git diff -- tests/golden/
```

and commit the expectations together with the change. Never update goldens from
hooks or CI.

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT
