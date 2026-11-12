"""Диагностика ассемблера: коды ошибок и исключение с позицией в исходнике."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

AssemblyErrorCode = Literal[
    "EMPTY_PROGRAM",
    "PROGRAM_TOO_LARGE",
    "INVALID_LABEL",
    "DUPLICATE_LABEL",
    "UNDEFINED_LABEL",
    "UNKNOWN_INSTRUCTION",
    "OPERAND_COUNT",
    "INVALID_REGISTER",
    "INVALID_LITERAL",
    "INVALID_OPERAND",
    "OUT_OF_RANGE",
]


@dataclass(frozen=True)
class SourceLocation:
    line: int
    column: int

    def to_dict(self) -> dict[str, int]:
        return {"line": self.line, "column": self.column}


@dataclass(frozen=True)
class AssemblyDiagnostic:
    code: AssemblyErrorCode
    line: int
    column: int
    message: str

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "line": self.line,
            "column": self.column,
            "message": self.message,
        }


class AssemblyError(Exception):
    def __init__(self, code: AssemblyErrorCode, location: SourceLocation, message: str) -> None:
        super().__init__(f"Строка {location.line}, позиция {location.column}: {message}")
        self.diagnostic = AssemblyDiagnostic(code, location.line, location.column, message)
