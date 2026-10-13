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
