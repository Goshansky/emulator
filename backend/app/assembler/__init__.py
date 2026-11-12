"""Ассемблер: разбор исходников, метки и диагностика ошибок."""

from .assemble import assemble
from .errors import AssemblyDiagnostic, AssemblyError, AssemblyErrorCode, SourceLocation
from .parser import LabelDefinition, ParsedLine, Token, parse_source
from .types import AssemblyResult, SourceMapEntry

__all__ = [
    "AssemblyDiagnostic",
    "AssemblyError",
    "AssemblyErrorCode",
    "AssemblyResult",
    "LabelDefinition",
    "ParsedLine",
    "SourceLocation",
    "SourceMapEntry",
    "Token",
    "assemble",
    "parse_source",
]
