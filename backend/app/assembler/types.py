"""Типы результата сборки."""

from __future__ import annotations

from dataclasses import dataclass

from .errors import SourceLocation


@dataclass(frozen=True)
class SourceMapEntry:
    address: int
    line: int
    column: int
    text: str

    def to_dict(self) -> dict[str, object]:
        return {
            "address": self.address,
            "line": self.line,
            "column": self.column,
            "text": self.text,
        }


@dataclass(frozen=True)
class AssemblyResult:
    instructions: tuple[int, ...]
    labels: dict[str, int]
    source_map: tuple[SourceMapEntry, ...]

    def image_dict(self) -> dict[str, object]:
        return {"instructions": list(self.instructions), "entryPoint": 0, "data": []}

    def to_dict(self) -> dict[str, object]:
        return {
            "instructions": list(self.instructions),
            "labels": dict(self.labels),
            "sourceMap": [entry.to_dict() for entry in self.source_map],
        }
