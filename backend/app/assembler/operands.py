"""Разбор операндов: регистры, литералы, адреса памяти и цели переходов."""

from __future__ import annotations

import re

from ..core import CODE_SIZE, DATA_SIZE, REGISTER_COUNT
from .errors import AssemblyError, SourceLocation
from .parser import LABEL_PATTERN, LabelDefinition, Token

REGISTER_PATTERN = re.compile(r"^R(0|[1-9][0-9]*)$", re.IGNORECASE)
HEX_PATTERN = re.compile(r"^0x[0-9a-f]+$", re.IGNORECASE)
SIGNED_DECIMAL = re.compile(r"^[+-]?[0-9]+$")
UNSIGNED_DECIMAL = re.compile(r"^[0-9]+$")
MEMORY_PATTERN = re.compile(r"^\[\s*([^\[\]]+?)\s*\]$")


def register(token: Token) -> int:
    match = REGISTER_PATTERN.match(token.text)
    value = int(match.group(1)) if match else -1
    if not 0 <= value < REGISTER_COUNT:
        raise AssemblyError("INVALID_REGISTER", token.location, "Ожидается регистр R0…R15.")
    return value


def _literal_bounds(kind: str, is_hex: bool) -> tuple[int, int]:
    minimum = -32768 if kind == "immediate" and not is_hex else 0
    maximum = 65535 if kind == "immediate" and is_hex else 32767 if kind == "immediate" else 15 if kind == "shift" else 65535
    return minimum, maximum


def literal(token: Token, kind: str) -> int:
    """kind: 'immediate' | 'address' | 'shift'."""
    is_hex = bool(HEX_PATTERN.match(token.text))
    decimal = SIGNED_DECIMAL if kind == "immediate" else UNSIGNED_DECIMAL
    if not is_hex and not decimal.match(token.text):
        raise AssemblyError(
            "INVALID_LITERAL",
            token.location,
            "Ожидается десятичное число или hex-литерал 0x…; "
            "выражения и знаки перед hex не поддерживаются.",
        )
    value = int(token.text, 16) if is_hex else int(token.text, 10)
    minimum, maximum = _literal_bounds(kind, is_hex)
    if value < minimum or value > maximum:
        raise AssemblyError(
            "OUT_OF_RANGE", token.location, f"Значение должно быть в диапазоне {minimum}…{maximum}."
        )
    return value + 65536 if value < 0 else value


def _address(token: Token, limit: int) -> int:
    value = literal(token, "address")
    if value >= limit:
        raise AssemblyError(
            "OUT_OF_RANGE", token.location, f"Адрес должен быть в диапазоне 0…{limit - 1}."
        )
    return value


def memory_operand(token: Token) -> dict[str, object]:
    match = MEMORY_PATTERN.match(token.text)
    if match is None:
        raise AssemblyError(
            "INVALID_OPERAND",
            token.location,
            "Адрес памяти задаётся в скобках: [0x0100] или [R4].",
        )
    inner = match.group(1).strip()
    inner_token = Token(inner, SourceLocation(token.location.line, token.location.column + token.text.index(inner)))
    if re.match(r"^r", inner, re.IGNORECASE):
        return {"mode": "indirect", "value": register(inner_token)}
    return {"mode": "direct", "value": _address(inner_token, DATA_SIZE)}


def branch_target(token: Token, labels: dict[str, LabelDefinition]) -> int:
    if not LABEL_PATTERN.match(token.text):
        return _address(token, CODE_SIZE)
    definition = labels.get(token.text)
    if definition is None:
        raise AssemblyError(
            "UNDEFINED_LABEL",
            token.location,
            f"Метка «{token.text}» не определена; регистр букв имеет значение.",
        )
    return definition.address
