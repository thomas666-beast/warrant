"""Tests for Level 1 static effect analysis."""

from __future__ import annotations

from pathlib import Path

from warrant.ir import read_module
from warrant.levels import check_level1
from warrant.schema.spec import (
    Effect,
    Expression,
    FunctionSpec,
    Signature,
    Spec,
)
from warrant.verify.result import Severity


def _spec(fname: str, sig: str, effects: set[Effect] | None = None) -> Spec:
    return Spec(
        module="m",
        functions={
            fname: FunctionSpec(
                signature=Signature.parse(sig),
                effects=frozenset(effects or set()),
            )
        },
    )


def _write(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(content)
    return p


# ---------------------------------------------------------------------------
# Effect matching
# ---------------------------------------------------------------------------


def test_correct_effects_no_findings(tmp_path: Path) -> None:
    p = _write(
        tmp_path,
        "m.py",
        (
            "def read_file() -> str:\n"
            "    try:\n"
            "        return open('x').read()\n"
            "    except OSError:\n"
            "        return ''\n"
        ),
    )
    mod = read_module(p)
    spec = _spec("read_file", "read_file() -> str", {Effect.READ_FS})
    findings = check_level1(spec, mod, impl_path=p)
    assert findings == ()


def test_undeclared_effect_is_error(tmp_path: Path) -> None:
    p = _write(
        tmp_path,
        "m.py",
        (
            "def read_file() -> str:\n"
            "    try:\n"
            "        return open('x').read()\n"
            "    except OSError:\n"
            "        return ''\n"
        ),
    )
    mod = read_module(p)
    spec = _spec("read_file", "read_file() -> str", set())
    findings = check_level1(spec, mod, impl_path=p)
    effect_findings = [f for f in findings if "undeclared effect" in f.message]
    assert len(effect_findings) == 1
    f = effect_findings[0]
    assert f.severity is Severity.ERROR
    assert f.function == "read_file"
    assert "read_fs" in f.message
    assert f.location is not None
    assert f.location[1] == 3  # open() is on line 3


def test_declared_but_not_detected_is_warning(tmp_path: Path) -> None:
    p = _write(tmp_path, "m.py", "def f() -> int:\n    return 1\n")
    mod = read_module(p)
    spec = _spec("f", "f() -> int", {Effect.READ_FS})
    findings = check_level1(spec, mod, impl_path=p)
    assert len(findings) == 1
    assert findings[0].severity is Severity.WARNING
    assert "not detected" in findings[0].message


def test_missing_function_is_error(tmp_path: Path) -> None:
    p = _write(tmp_path, "m.py", "def other() -> int:\n    return 1\n")
    mod = read_module(p)
    spec = _spec("f", "f() -> int")
    findings = check_level1(spec, mod, impl_path=p)
    assert len(findings) == 1
    assert findings[0].severity is Severity.ERROR
    assert "not found" in findings[0].message


def test_multiple_effects_one_finding_each(tmp_path: Path) -> None:
    p = _write(
        tmp_path,
        "m.py",
        (
            "import requests\n"
            "import time\n"
            "def f() -> int:\n"
            "    try:\n"
            "        requests.get('x')\n"
            "    except Exception:\n"
            "        pass\n"
            "    return int(time.time())\n"
        ),
    )
    mod = read_module(p)
    spec = _spec("f", "f() -> int", set())
    findings = check_level1(spec, mod, impl_path=p)
    effects_reported = {
        f.message.split("'")[1] for f in findings if "undeclared effect" in f.message
    }
    assert effects_reported == {"network", "clock"}


def test_one_finding_per_effect_not_per_call(tmp_path: Path) -> None:
    p = _write(
        tmp_path,
        "m.py",
        (
            "import time\n"
            "def f() -> int:\n"
            "    a = time.time()\n"
            "    b = time.time()\n"
            "    c = time.time()\n"
            "    return int(a + b + c)\n"
        ),
    )
    mod = read_module(p)
    spec = _spec("f", "f() -> int", set())
    findings = check_level1(spec, mod, impl_path=p)
    clock_findings = [f for f in findings if "clock" in f.message]
    assert len(clock_findings) == 1


# ---------------------------------------------------------------------------
# The reference example
# ---------------------------------------------------------------------------


def test_example_max_passes() -> None:
    root = Path(__file__).resolve().parents[2]
    spec = Spec(
        module="max",
        functions={
            "max_of": FunctionSpec(
                signature=Signature.parse("max_of(xs: List[int]) -> int"),
                requires=(Expression(text="len(xs) > 0"),),
                ensures=(Expression(text="result in xs"),),
            )
        },
    )
    impl = root / "examples" / "max" / "src" / "max.py"
    module = read_module(impl)
    findings = check_level1(spec, module, impl_path=impl)
    assert findings == ()
