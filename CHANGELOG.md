# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial repository scaffolding (Task 1)
- `pyproject.toml` with hatchling build backend, ruff, mypy, pytest config
- Package skeleton under `src/warrant/`
- CLI entry point (`warrant`) with `--version` and a `verify` stub
- GitHub Actions CI: ruff, mypy, pytest across Python 3.11 and 3.12
- Smoke tests for package import and CLI wiring
- README, LICENSE (MIT), .gitignore, CHANGELOG

- Task 2 — Spec schema: pydantic models for `Spec`, `FunctionSpec`, `Signature`, `Property`, `Expression`, `Complexity`, `Effect`
- Task 2 — Type-expression parser (`parse_type`) handling `List[...]`, `Dict[...]`, `Optional[...]`, primitives, and preserving unknown types as `OpaqueType`
- Task 3 — YAML spec loader with `ruamel.yaml`, preserving line/column info
- Task 3 — Structured `SpecLoadError` with file, line, column, path, and hint fields
- Task 3 — Loader never raises on user input; returns `Spec | SpecLoadError`
- Task 4 — CLI `verify` command now loads specs and reports structured results
- Task 4 — Defined exit-code contract: `0` success, `1` verification failed, `2` usage error
- Task 4 — `VerifyResult` and `Finding` types; every level will produce these
- Task 4 — Reference example under `examples/max/`
