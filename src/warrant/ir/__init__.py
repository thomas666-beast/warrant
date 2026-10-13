"""Language-agnostic intermediate representation of an implementation module."""

from warrant.ir.module import FunctionIR, ModuleIR, ParameterIR
from warrant.ir.reader import ReadError, read_module

__all__ = [
    "FunctionIR",
    "ModuleIR",
    "ParameterIR",
    "ReadError",
    "read_module",
]
