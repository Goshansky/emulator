"""Ядро эмулятора: модель процессора, АЛУ, кодек, память.

Гарвардская архитектура, 16-битные данные, 32-битные инструкции,
трёхадресная арифметика. Модуль не зависит от FastAPI и HTTP.
"""

from .alu import AluResult, Flags, calculate, signed, word
from .codec import decode, encode, format_instruction, hex_word
from .cpu import Cpu
from .errors import CpuFault, ErrorCode, MachineError, is_unsigned
from .image import validate_image
from .isa import (
    ADDRESS_MODES,
    ALU_OPS,
    BINARY_OPS,
    CODE_SIZE,
    DATA_SIZE,
    DEFAULT_STEP_LIMIT,
    INSTRUCTION_BITS,
    ISA,
    OPCODE_TO_MNEMONIC,
    REGISTER_COUNT,
    WORD_BITS,
    DecodedInstruction,
    Instruction,
    OpDef,
)
from .run import RunResult, run
from .types import (
    CpuSnapshot,
    CpuStatus,
    DataCell,
    ProgramImage,
    StepResult,
    WriteEvent,
)

__all__ = [
    "ADDRESS_MODES",
    "ALU_OPS",
    "BINARY_OPS",
    "CODE_SIZE",
    "DATA_SIZE",
    "DEFAULT_STEP_LIMIT",
    "INSTRUCTION_BITS",
    "ISA",
    "OPCODE_TO_MNEMONIC",
    "REGISTER_COUNT",
    "WORD_BITS",
    "AluResult",
    "Cpu",
    "CpuFault",
    "CpuSnapshot",
    "CpuStatus",
    "DataCell",
    "DecodedInstruction",
    "ErrorCode",
    "Flags",
    "Instruction",
    "MachineError",
    "OpDef",
    "ProgramImage",
    "RunResult",
    "StepResult",
    "WriteEvent",
    "calculate",
    "decode",
    "encode",
    "format_instruction",
    "hex_word",
    "is_unsigned",
    "run",
    "signed",
    "validate_image",
    "word",
]
