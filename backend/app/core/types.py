"""Типы состояния машины и результатов шагов."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from .alu import Flags
from .errors import CpuFault
from .isa import DecodedInstruction

CpuStatus = Literal["ready", "halted", "faulted"]


@dataclass(frozen=True)
class DataCell:
    address: int
    value: int


@dataclass(frozen=True)
class ProgramImage:
    instructions: tuple[int, ...]
    entry_point: int
    data: tuple[DataCell, ...] = ()


@dataclass(frozen=True)
class WriteEvent:
    kind: Literal["register", "data"]
    address: int
    before: int
    after: int

    def to_dict(self) -> dict[str, object]:
        return {"kind": self.kind, "address": self.address, "before": self.before, "after": self.after}


@dataclass(frozen=True)
class CpuSnapshot:
    registers: tuple[int, ...]
    pc: int
    ir: int
    instruction_address: int | None
    decoded: DecodedInstruction | None
    flags: Flags
    status: CpuStatus
    steps: int
    loaded_instructions: int
    fault: CpuFault | None

    def to_dict(self) -> dict[str, object]:
        return {
            "registers": list(self.registers),
            "pc": self.pc,
            "ir": self.ir,
            "instructionAddress": self.instruction_address,
            "decoded": self.decoded.to_dict() if self.decoded else None,
            "flags": self.flags.to_dict(),
            "status": self.status,
            "steps": self.steps,
            "loadedInstructions": self.loaded_instructions,
            "fault": None
            if self.fault is None
            else {
                "code": self.fault.code,
                "message": self.fault.message,
                "address": self.fault.address,
                **({"word": self.fault.word} if self.fault.word is not None else {}),
            },
        }


@dataclass(frozen=True)
class StepResult:
    executed: bool
    state: CpuSnapshot
    writes: tuple[WriteEvent, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "executed": self.executed,
            "state": self.state.to_dict(),
            "writes": [write.to_dict() for write in self.writes],
        }
