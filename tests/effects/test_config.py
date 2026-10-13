"""Tests for the effect config."""

from __future__ import annotations

from pathlib import Path

import pytest

from warrant.effects.config import (
    EffectPattern,
    EffectsConfig,
    load_config,
    load_default_config,
    parse_config,
)
from warrant.schema.spec import Effect


def test_load_default_config() -> None:
    cfg = load_default_config()
    assert len(cfg.patterns) > 0
    # Should contain the builtin open
    p = cfg.matching_bare("open")
    assert p is not None
    assert p.effect is Effect.READ_FS


def test_matching_bare_unknown() -> None:
    cfg = load_default_config()
    assert cfg.matching_bare("this_does_not_exist") is None


def test_matching_module_attr_exact() -> None:
    cfg = load_default_config()
    p = cfg.matching_module_attr("socket", "socket")
    assert p is not None
    assert p.effect is Effect.NETWORK


def test_matching_module_attr_glob() -> None:
    cfg = load_default_config()
    p = cfg.matching_module_attr("requests", "get")
    assert p is not None
    assert p.effect is Effect.NETWORK
    p2 = cfg.matching_module_attr("requests", "post")
    assert p2 is not None
    assert p2.effect is Effect.NETWORK


def test_matching_module_attr_miss() -> None:
    cfg = load_default_config()
    assert cfg.matching_module_attr("json", "loads") is None


def test_parse_config_minimal() -> None:
    text = """
effects:
  - pattern: open
    effect: read_fs
"""
    cfg = parse_config(text)
    assert len(cfg.patterns) == 1
    assert cfg.patterns[0].pattern == "open"
    assert cfg.patterns[0].effect is Effect.READ_FS


def test_parse_config_empty() -> None:
    cfg = parse_config("")
    assert cfg.patterns == ()


def test_parse_config_rejects_bad_effect() -> None:
    text = """
effects:
  - pattern: open
    effect: teleport
"""
    with pytest.raises(ValueError, match="unknown effect"):
        parse_config(text)


def test_parse_config_rejects_duplicate() -> None:
    text = """
effects:
  - pattern: open
    effect: read_fs
  - pattern: open
    effect: write_fs
"""
    with pytest.raises(ValueError, match="duplicate"):
        parse_config(text)


def test_parse_config_rejects_malformed() -> None:
    with pytest.raises(ValueError):
        parse_config("effects:\n  - just_a_string\n")


def test_load_config_missing_file() -> None:
    with pytest.raises(ValueError, match="not found"):
        load_config(Path("/nonexistent/effects.yaml"))


def test_pattern_properties() -> None:
    p = EffectPattern(pattern="requests.get", effect=Effect.NETWORK)
    assert p.module_glob == "requests"
    assert p.function_glob == "get"
    assert p.is_bare is False

    p2 = EffectPattern(pattern="open", effect=Effect.READ_FS)
    assert p2.module_glob is None
    assert p2.function_glob == "open"
    assert p2.is_bare is True
