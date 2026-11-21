"""Acceptance: generated code compiles warning-free and behaves as documented on a real .NET SDK."""

import shutil
import subprocess
from pathlib import Path

SENTINEL = "LINKML_CSHARP_OK"

PROJECT = """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net10.0</TargetFramework>
    <Nullable>enable</Nullable>
    <TreatWarningsAsErrors>true</TreatWarningsAsErrors>
  </PropertyGroup>
</Project>
"""

PROGRAM = f"""using System.Reflection;
using System.Runtime.Serialization;
using Kitchen.Sink;

static void Check(bool condition, string what)
{{
    if (!condition) throw new System.Exception("Failed: " + what);
}}

var person = new Person
{{
    Id = new System.Uri("ks:alice"),
    Name = "Alice",
    IsPlayer = false,
    History = new(),
}};
Check(person.Age == null && person.Status == null && person.Aliases == null, "optional values start null");
person.Age = 0;
person.Aliases = new() {{ "Al" }};
person.Pets = new() {{ new Pet {{ Id = new System.Uri("ks:rex"), Name = "Rex" }} }};
person.Status = LifeStatus.InLimbo;
Check(person.Age == 0 && person is NamedThing, "values and inheritance");
Check(typeof(NamedThing).IsAbstract && !typeof(HasAliases).IsAbstract, "abstract classes");
var member = typeof(LifeStatus).GetField(nameof(LifeStatus.Smiling))!.GetCustomAttribute<EnumMemberAttribute>()!;
Check(member.Value == "say \\"cheese\\" \\\\o/", "enum member text");
System.Console.WriteLine("{SENTINEL}");
"""


def test_generated_code_compiles_and_runs(tmp_path: Path, kitchen_sink: dict[str, str]) -> None:
    """Never skips: a missing SDK is a failed acceptance, not a pass."""
    dotnet = shutil.which("dotnet")
    assert dotnet, "dotnet not found; run inside `nix develop`"
    (tmp_path / "Generated").mkdir()
    for name, code in kitchen_sink.items():
        (tmp_path / "Generated" / name).write_text(code, encoding="utf-8")
    (tmp_path / "Check.csproj").write_text(PROJECT, encoding="utf-8")
    (tmp_path / "Program.cs").write_text(PROGRAM, encoding="utf-8")
    result = subprocess.run([dotnet, "run"], cwd=tmp_path, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip().endswith(SENTINEL), result.stdout
