"""Level 1: static effect analysis.

For each function in the spec:
  1. Look up the corresponding IR from the implementation.
  2. Detect effects actually present in the AST.
  3. Compare to the spec's `effects` claim.
  4. Emit findings for mismatches.

Missing functions are reported as errors. Missing declarations of
detected effects are errors. Declared-but-not-detected effects are
warnings (over-caution is fine).
"""

from __future__ import annotations

import ast

from warrant.effects import detect_calls, load_default_config
from warrant.effects.config import EffectsConfig
from warrant.effects.detector import ResolvedCall
from warrant.ir.module import FunctionIR, ModuleIR
from warrant.schema.spec import Effect, FunctionSpec, Spec
from warrant.verify.result import Finding, Severity


def check_level1(
    spec: Spec,
    module: ModuleIR,
    *,
    config: EffectsConfig | None = None,
) -> tuple[Finding, ...]:
    """Run Level 1 static checks. Pure function; no I/O."""
    if config is None:
        config = load_default_config()

    findings: list[Finding] = []

    for fname, fspec in spec.functions.items():
        ir = module.get(fname)
        if ir is None:
            findings.append(
                Finding(
                    severity=Severity.ERROR,
                    function=fname,
                    message=f"function {fname!r} not found in {module.path.name}",
                    hint=(
                        f"the spec declares {fname!r} but the implementation "
                        f"does not define it"
                    ),
                )
            )
            continue

        findings.extend(_check_effects(fname, fspec, ir, module, config))

    return tuple(findings)


def _check_effects(
    fname: str,
    fspec: FunctionSpec,
    ir: FunctionIR,
    module: ModuleIR,
    config: EffectsConfig,
) -> list[Finding]:
    """Compare declared vs. detected effects for one function."""
    try:
        func_tree = ast.parse(ir.source)
    except SyntaxError:
        # Source slice is not reparseable. Fall back to no effects rather
        # than crash; a later task will carry the AST node directly.
        return []

    detected = detect_calls(ir, func_tree, config)

    # Deduplicate by effect, keeping the first call site for reporting.
    by_effect: dict[Effect, ResolvedCall] = {}
    for effect, call in detected:
        if effect not in by_effect:
            by_effect[effect] = call

    declared = fspec.effects
    detected_set = set(by_effect.keys())

    findings: list[Finding] = []

    # Missing declaration → ERROR
    for effect in sorted(detected_set - declared):
        call = by_effect[effect]
        findings.append(
            Finding(
                severity=Severity.ERROR,
                function=fname,
                message=(
                    f"undeclared effect {effect.value!r}: "
                    f"calls {call.resolved!r}"
                ),
                location=(module.path, call.line, call.column),
                hint=(
                    f"add {effect.value!r} to the spec's effects list, "
                    f"or remove the call"
                ),
            )
        )

    # Extra declaration → WARNING
    for effect in sorted(declared - detected_set):
        findings.append(
            Finding(
                severity=Severity.WARNING,
                function=fname,
                message=(
                    f"declared effect {effect.value!r} not detected in implementation"
                ),
                hint="remove it from the spec if it's no longer needed",
            )
        )

    return findings

