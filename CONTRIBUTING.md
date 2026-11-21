# Contributing

By participating you agree to the [Code of Conduct](CODE_OF_CONDUCT.md).

## Implementing the mapping

Start with [docs/MAPPING.md](docs/MAPPING.md), the mapping contract. The
generator extends LinkML's `OOCodeGenerator` exactly like upstream `gen-java`
(`linkml/generators/javagen.py`): when a C# choice is not dictated by the
language, follow what `gen-java` does and record any difference in the mapping.

Mapping logic lives in `src/linkml_csharp/generator.py` and `templates/`.
Add a failing test in `tests/test_generator.py` before changing a mapping;
`tests/test_dotnet.py` checks that generated code compiles and runs.

## Setup

```shell
uv sync
uv run pytest --ignore=tests/test_dotnet.py
uv run ruff check && uv run ruff format --check
```

Install the Ruff and golden-output hooks with `nix develop --command pre-commit install`.
For intentional output changes, follow the [golden workflow](README.md#golden-output).

### With Nix

`nix develop` gives a shell with uv, Python 3.14 and 3.11, ruff, pre-commit and
the .NET 10 SDK. On NixOS it is the supported way to work: call `ruff` directly
instead of `uv run ruff` (the ruff binary uv installs cannot run), and test
another interpreter with `uv run --isolated --python 3.11 pytest`. The shell
exposes the C++ runtime that LinkML's PyOxigraph dependency needs.

## Code conventions

These follow [linkml/linkml](https://linkml.io/linkml/maintainers/contributing.html)
and its `AGENTS.md`, so the generator can be proposed upstream without rework:

- pytest in functional style, never `unittest`; `@pytest.mark.parametrize` for input combinations
- no mocks; do not weaken a test to make it pass
- doctests for small examples
- type hints and docstrings on every function and class
- fail fast: no `try`/`except` that could hide a bug
- Ruff with the upstream rule set and line length (see `pyproject.toml`)

## Git conventions

- [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/): `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`, `ci:` ...
- Gitflow: branch `feat/*` and `fix/*` from `develop`; merge `develop` into `main` at release, with `--ff-only`.

## Proposing upstream

Upstream requires PRs to be linked to an issue on the
[LinkML issue tracker](https://github.com/linkml/linkml/issues), opened as drafts
until tests pass, and reviewed by the core team. A new generator also needs a
`docs/generators/csharp.rst` page and a maintainer entry in
`docs/maintainers/generator-governance.md`.

## Use of AI

This project follows the LinkML
[AI Covenant](https://github.com/linkml/linkml/blob/main/AI_COVENANT.md):
you own, understand and can defend everything you submit, whatever tools helped;
issues and discussion comments are written by humans; AI co-author trailers in
commits are discouraged.
