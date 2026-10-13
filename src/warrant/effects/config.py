"""The effect pattern config: which functions produce which effects.

Shipped as a YAML file. Users can extend it via `--effects-config` on the
CLI, or place a `warrant.effects.yaml` next to their spec (Task 7+).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from warrant.schema.spec import Effect


@dataclass(frozen=True, slots=True)
class EffectPattern:
    """A rule: calls matching `pattern` produce effect `effect`.

    `pattern` is either:
      - `name`                 — a builtin like `open`, `print`
      - `module.name`          — exact: `socket.socket`
      - `module.*`             — glob: any attribute of `module`
      - `*.name`               — any module, that attribute name
    """

    pattern: str
    effect: Effect
    note: str | None = None

    @property
    def module_glob(self) -> str | None:
        """The module portion, or None for bare names."""
        if "." not in self.pattern:
            return None
        return self.pattern.rsplit(".", 1)[0]

    @property
    def function_glob(self) -> str:
        """The function/attribute portion."""
        if "." not in self.pattern:
            return self.pattern
        return self.pattern.rsplit(".", 1)[1]

    @property
    def is_bare(self) -> bool:
        """True if this pattern has no module part (e.g. `open`)."""
        return "." not in self.pattern


@dataclass(frozen=True, slots=True)
class EffectsConfig:
    """The full config: a list of patterns."""

    patterns: tuple[EffectPattern, ...]

    def matching_bare(self, name: str) -> EffectPattern | None:
        """Find a pattern for a bare name like `open`."""
        for p in self.patterns:
            if p.is_bare and p.function_glob == name:
                return p
        return None

    def matching_module_attr(
        self, module: str, attr: str
    ) -> EffectPattern | None:
        """Find a pattern for `module.attr`."""
        for p in self.patterns:
            if p.is_bare:
                continue
            mg = p.module_glob
            fg = p.function_glob
            if mg is None:
                continue
            if not _module_matches(mg, module):
                continue
            if fg != "*" and fg != attr:
                continue
            return p
        return None


def _module_matches(pattern: str, module: str) -> bool:
    """Match a module pattern against an actual module path.

    `requests` matches `requests`. `os.path` matches `os.path`.
    `requests.*` matches `requests` (we treat it as "the module itself").
    """
    if pattern == module:
        return True
    # Allow a trailing `.*` in the module part to mean "this module or below"
    if pattern.endswith(".*"):
        prefix = pattern[:-2]
        return module == prefix or module.startswith(prefix + ".")
    return False


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

_DEFAULT_CONFIG_PATH = Path(__file__).parent / "default_effects.yaml"


def load_default_config() -> EffectsConfig:
    """Load the bundled default config."""
    return load_config(_DEFAULT_CONFIG_PATH)


def load_config(path: str | Path) -> EffectsConfig:
    """Load an effect config from a YAML file. Raises `ValueError` on error."""
    p = Path(path)
    if not p.exists():
        raise ValueError(f"effect config not found: {p}")
    text = p.read_text(encoding="utf-8")
    return parse_config(text)


def parse_config(text: str) -> EffectsConfig:
    """Parse an effect config from YAML text."""
    yaml = YAML(typ="safe", pure=True)
    data: Any = yaml.load(text)
    if data is None:
        return EffectsConfig(patterns=())
    if not isinstance(data, dict):
        raise ValueError("effect config root must be a mapping")
    raw_patterns = data.get("effects", [])
    if not isinstance(raw_patterns, list):
        raise ValueError("effect config 'effects' must be a list")

    out: list[EffectPattern] = []
    seen: set[str] = set()
    for entry in raw_patterns:
        if not isinstance(entry, dict):
            raise ValueError("each effect pattern must be a mapping")
        pattern = entry.get("pattern")
        effect_name = entry.get("effect")
        note = entry.get("note")
        if not isinstance(pattern, str) or not pattern:
            raise ValueError(f"invalid pattern entry: {entry!r}")
        if not isinstance(effect_name, str) or not effect_name:
            raise ValueError(f"pattern {pattern!r} missing 'effect'")
        if pattern in seen:
            raise ValueError(f"duplicate effect pattern: {pattern!r}")
        seen.add(pattern)
        try:
            effect = Effect(effect_name)
        except ValueError as e:
            raise ValueError(
                f"unknown effect {effect_name!r} in pattern {pattern!r}"
            ) from e
        out.append(
            EffectPattern(
                pattern=pattern,
                effect=effect,
                note=note if isinstance(note, str) else None,
            )
        )
    return EffectsConfig(patterns=tuple(out))
