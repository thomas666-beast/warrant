# warrant

**Specs you can check. Code you can trust.**

> Write the spec. Let the AI write the code. Verify the code against the spec.

`warrant` is a language-agnostic verification toolchain designed for the age of AI-generated code. You write a machine-checkable specification of what a function should do. Your code — human- or AI-written — is verified against it at three levels of rigor.

## Why

AI can now produce code faster than humans can meaningfully review. Existing quality tools (code review, tests, linters) assume human-speed authorship. `warrant` shifts the human's job from **reading code** to **writing intent** — and lets a machine verify the implementation matches.

## Status

**Pre-alpha.** Nothing works yet. Follow along as we build it in public.

- ✅ Task 1 — Repo scaffolding & CI
- ✅ Task 2 — Spec schema (pydantic models)
- ✅ Task 3 — YAML spec loader
- ✅ Task 4 — CLI skeleton
- ✅ Task 5 — Python adapter
- ✅ Task 6 — L1: static effect analysis
- ⬜ Task 7 — L1: example test generation
- ⬜ Task 8 — Rich counterexample reporter
- ⬜ Task 9 — L2: property-based testing
- ⬜ Task 10 — Counterexample shrinker
- ⬜ Task 11 — L3: SMT bridge
- ⬜ Task 12 — End-to-end demo

## The Three Levels

| Level | Method | Cost | Catches |
|-------|--------|------|---------|
| **1** | Static effect checks + generated example tests | seconds | precondition violations, effect mismatches, obvious bugs |
| **2** | Property-based testing + fuzzing | minutes | subtle logic errors, edge cases, discovered via minimal counterexamples |
| **3** | SMT proofs (linear arithmetic subset) | minutes–hours | mathematical certainty for critical code |

## Example (aspirational)

```yaml
# specs/max.warrant.yaml
module: max
functions:
  max_of:
    signature: "max_of(xs: List[int]) -> int"
    requires:
      - "len(xs) > 0"
    ensures:
      - "result in xs"
      - "forall y in xs: result >= y"
```

```bash
$ warrant verify specs/max.warrant.yaml --impl src/max.py --level=2

✗ PROPERTY FAILED: idempotent
  Counterexample: x = -5
  Shrunk input: [-5]
  Expected: -5
  Got:      0
```

## Development

Requires Python 3.11+ and [uv](https://github.com/astral-sh/uv).

```bash
uv sync --extra dev
uv run pytest
uv run ruff check .
uv run mypy
```

## License

MIT
