"""Effect detection: mapping call sites in code to abstract effects."""

from warrant.effects.config import EffectPattern, EffectsConfig, load_default_config
from warrant.effects.detector import detect_calls, resolve_calls

__all__ = [
    "EffectPattern",
    "EffectsConfig",
    "detect_calls",
    "load_default_config",
    "resolve_calls",
]
