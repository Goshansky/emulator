"""Первый проход ассемблера: строки, метки и операнды."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..core import CODE_SIZE, ISA
from .errors import AssemblyError, SourceLocation

LABEL_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

NON_WS = re.compile(r"\S")
FIRST_TOKEN = re.compile(r"\S+")


@dataclass(frozen=True)
class Token:
    text: str
    location: SourceLocation


@dataclass(frozen=True)
class ParsedLine:
    op: str
    location: SourceLocation
    operands: tuple[Token, ...]
    text: str


@dataclass(frozen=True)
class LabelDefinition:
    location: SourceLocation
    address: int


@dataclass
class ParseResult:
    lines: list[ParsedLine] = field(default_factory=list)
    labels: dict[str, LabelDefinition] = field(default_factory=dict)


def _parse_label(
    content: str, line: int, address: int, labels: dict[str, LabelDefinition], offset: int
) -> int | None:
    colon = content.find(":", offset)
    if colon == -1:
        return offset

    label = content[offset:colon].strip()
    location = SourceLocation(line, offset + 1)
    if not LABEL_PATTERN.match(label):
        raise AssemblyError(
            "INVALID_LABEL",
            location,
            "Метка должна начинаться с латинской буквы или подчёркивания "
            "и содержать только буквы, цифры и подчёркивания.",
        )
    previous = labels.get(label)
    if previous is not None:
        raise AssemblyError(
            "DUPLICATE_LABEL",
            location,
            f"Метка «{label}» уже определена в строке {previous.location.line}.",
        )
    labels[label] = LabelDefinition(location, address)

    rest = content[colon + 1 :]
    match = NON_WS.search(rest)
    if match is None:
        return None
    instruction_offset = colon + 1 + match.start()
    if content.find(":", instruction_offset) != -1:
        raise AssemblyError(
            "INVALID_LABEL",
            SourceLocation(line, instruction_offset + 1),
            "На одной строке допускается одна метка.",
        )
    return instruction_offset


def _operand_count(op: str) -> int:
    fmt = ISA[op].format
    return 0 if fmt == "H" else 1 if fmt == "J" else 2 if fmt == "X" or op == "CMP" else 3


def _parse_operands(rest: str, op: str, location: SourceLocation) -> tuple[Token, ...]:
    expected = _operand_count(op)
    operands: list[Token] = []
    column = location.column + len(op)
    if rest.strip():
        for part in rest.split(","):
            padding = NON_WS.search(part)
            operands.append(
                Token(part.strip(), SourceLocation(location.line, column + (padding.start() if padding else 0)))
            )
            column += len(part) + 1
    if len(operands) != expected or any(token.text == "" for token in operands):
        raise AssemblyError(
            "OPERAND_COUNT",
            location,
            f"Команда {op} требует {expected} операндов, разделённых запятыми.",
        )
    return tuple(operands)


def _parse_instruction(text: str, content: str, line: int, offset: int, address: int) -> ParsedLine:
    match = FIRST_TOKEN.match(content, offset)
    assert match is not None
    name = match.group(0).upper()
    location = SourceLocation(line, offset + 1)
    if name not in ISA:
        raise AssemblyError("UNKNOWN_INSTRUCTION", location, f"Неизвестная команда «{match.group(0)}».")
    if address >= CODE_SIZE:
        raise AssemblyError(
            "PROGRAM_TOO_LARGE", location, f"Программа превышает {CODE_SIZE} инструкции."
        )
    rest = content[match.end() :]
    operands = _parse_operands(rest, name, location)
    return ParsedLine(name, location, operands, text)


def parse_source(source: str) -> ParseResult:
    """Первый проход: строки и метки, без разрешения ссылок на будущие команды."""
    result = ParseResult()
    for index, text in enumerate(re.split(r"\r\n|\n|\r", source)):
        line = index + 1
        content = text.split(";", 1)[0]
        first = NON_WS.search(content)
        if first is None:
            continue
        offset = _parse_label(content, line, len(result.lines), result.labels, first.start())
        if offset is None:
            continue
        result.lines.append(_parse_instruction(text, content, line, offset, len(result.lines)))

    if not result.lines:
        raise AssemblyError(
            "EMPTY_PROGRAM", SourceLocation(1, 1), "Программа не содержит инструкций."
        )
    for name, definition in result.labels.items():
        if definition.address >= len(result.lines):
            raise AssemblyError(
                "INVALID_LABEL",
                definition.location,
                f"После метки «{name}» должна находиться инструкция.",
            )
    return result
