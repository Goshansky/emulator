"""Второй проход ассемблера: кодирование инструкций и карта строк."""

from __future__ import annotations

import re

from ..core import Instruction, encode
from .operands import branch_target, literal, memory_operand, register
from .parser import LabelDefinition, ParsedLine, Token, parse_source
from .types import AssemblyResult, SourceMapEntry


def _encode_line(line: ParsedLine, labels: dict[str, LabelDefinition]) -> int:
    op = line.op
    operands = line.operands
    first = operands[0] if len(operands) > 0 else None
    second = operands[1] if len(operands) > 1 else None
    third = operands[2] if len(operands) > 2 else None

    if op == "HALT":
        instruction = Instruction(op)
    elif op == "MOV":
        assert first is not None and second is not None
        instruction = _move_instruction(first, second)
    elif op == "LD":
        assert first is not None and second is not None
        instruction = Instruction(op, {"d": register(first), **memory_operand(second)})
    elif op == "ST":
        assert first is not None and second is not None
        instruction = Instruction(op, {**memory_operand(first), "d": register(second)})
    elif op == "CMP":
        assert first is not None and second is not None
        instruction = Instruction(op, {"a": register(first), "b": register(second)})
    elif op == "SAR":
        assert first is not None and second is not None and third is not None
        instruction = Instruction(
            op, {"d": register(first), "a": register(second), "shift": literal(third, "shift")}
        )
    elif op in ("JMP", "JZ", "JNZ"):
        assert first is not None
        instruction = Instruction(op, {"target": branch_target(first, labels)})
    else:
        assert first is not None and second is not None and third is not None
        instruction = Instruction(
            op, {"d": register(first), "a": register(second), "b": register(third)}
        )
    return encode(instruction)


def _move_instruction(destination: Token, source: Token) -> Instruction:
    if re.match(r"^r", source.text, re.IGNORECASE):
        fields = {"mode": "register", "value": register(source)}
    else:
        fields = {"mode": "immediate", "value": literal(source, "immediate")}
    return Instruction("MOV", {"d": register(destination), **fields})


def assemble(source: str) -> AssemblyResult:
    """Чистая сборка: не загружает и не изменяет машину, ошибочный образ не возвращается."""
    parsed = parse_source(source)
    instructions: list[int] = []
    source_map: list[SourceMapEntry] = []
    for address, line in enumerate(parsed.lines):
        instructions.append(_encode_line(line, parsed.labels))
        source_map.append(
            SourceMapEntry(address, line.location.line, line.location.column, line.text)
        )
    labels = {name: definition.address for name, definition in parsed.labels.items()}
    return AssemblyResult(tuple(instructions), labels, tuple(source_map))
