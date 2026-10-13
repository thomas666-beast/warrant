"""Verification levels. Each level takes (spec, impl IR) and produces findings."""

from warrant.levels.level1_static import check_level1

__all__ = ["check_level1"]
