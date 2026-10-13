"""Reference implementation of max_of.

This file exists so the warrant toolchain has something to run against
during development. It is intentionally correct — Task 6+ will add a
deliberately-broken variant under examples/max-broken/ to exercise the
failure paths.
"""

from __future__ import annotations


def max_of(xs: list[int]) -> int:
    """Return the maximum element of xs.

    Precondition: xs is non-empty (see max.warrant.yaml).
    """
    result = xs[0]
    for x in xs[1:]:
        if x > result:
            result = x
    return result
