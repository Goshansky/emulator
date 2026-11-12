"""Единый справочник кодов для кодека, ассемблера и API."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

# Параметры машины
WORD_BITS = 16
INSTRUCTION_BITS = 32
REGISTER_COUNT = 16
CODE_SIZE = 1024
DATA_SIZE = 4096
DEFAULT_STEP_LIMIT = 100_000

WORD_MAX = 0xFFFF
INSTRUCTION_MAX = 0xFFFF_FFFF

InstructionFormat = Literal["R", "S", "X", "J", "H"]


@dataclass(frozen=True)
class OpDef:
    opcode: int
    format: InstructionFormat


# Таблица ISA: мнемоника -> код операции и формат слова.
ISA: dict[str, OpDef] = {
    "HALT": OpDef(0x00, "H"),
    "MOV": OpDef(0x01, "X"),
    "LD": OpDef(0x02, "X"),
    "ST": OpDef(0x03, "X"),
    "ADD": OpDef(0x10, "R"),
    "ADC": OpDef(0x11, "R"),
    "SUB": OpDef(0x12, "R"),
    "MULLO": OpDef(0x13, "R"),
    "MULHI": OpDef(0x14, "R"),
    "SAR": OpDef(0x15, "S"),
    "AND": OpDef(0x16, "R"),
    "OR": OpDef(0x17, "R"),
    "XOR": OpDef(0x18, "R"),
    "CMP": OpDef(0x19, "R"),
    "JMP": OpDef(0x20, "J"),
    "JZ": OpDef(0x21, "J"),
    "JNZ": OpDef(0x22, "J"),
}

OPCODE_TO_MNEMONIC = {definition.opcode: name for name, definition in ISA.items()}

ADDRESS_MODES = {
    "register": 0,
    "immediate": 1,
    "direct": 2,
    "indirect": 3,
}

BINARY_OPS = {"ADD", "ADC", "SUB", "MULLO", "MULHI", "AND", "OR", "XOR"}
ALU_OPS = BINARY_OPS | {"CMP", "SAR"}


@dataclass(frozen=True)
class Instruction:
    """Декодированная инструкция: мнемоника + поля операндов."""

    op: str
    fields: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"op": self.op, **self.fields}


@dataclass(frozen=True)
class DecodedInstruction:
    word: int
    format: InstructionFormat
    fields: dict[str, int]
    instruction: Instruction
    assembly: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "word": self.word,
            "format": self.format,
            "fields": dict(self.fields),
            "instruction": self.instruction.to_dict(),
            "assembly": self.assembly,
        }
