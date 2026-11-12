"""Каталог программ массивов и интерпретация результатов."""

from .catalog import EXAMPLES, ProgramExample
from .result import signed_result
from .sources import DOT_SOURCE, SUM_SOURCE

__all__ = [
    "DOT_SOURCE",
    "EXAMPLES",
    "ProgramExample",
    "SUM_SOURCE",
    "signed_result",
]
