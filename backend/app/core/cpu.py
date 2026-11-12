"""Модель процессора: загрузка образа, шаг исполнения, снимок состояния."""

from __future__ import annotations

from typing import Any

from .alu import Flags, calculate
from .codec import decode
from .errors import CpuFault, MachineError, is_unsigned
from .image import validate_image
from .isa import CODE_SIZE, DATA_SIZE, REGISTER_COUNT, DecodedInstruction
from .types import CpuSnapshot, CpuStatus, ProgramImage, StepResult, WriteEvent


class Cpu:
    def __init__(self, image: ProgramImage | dict[str, Any] | None = None) -> None:
        self._registers = [0] * REGISTER_COUNT
        self._code = [0] * CODE_SIZE
        self._data = [0] * DATA_SIZE
        self._pc = 0
        self._ir = 0
        self._instruction_address: int | None = None
        self._decoded: DecodedInstruction | None = None
        self._flags = Flags()
        self._status: CpuStatus = "ready"
        self._steps = 0
        self._loaded_instructions = 0
        self._fault: CpuFault | None = None
        self._initial_image: ProgramImage | None = None
        if image is not None:
            self.load(image)

    def load(self, image: ProgramImage | dict[str, Any]) -> CpuSnapshot:
        # До этой проверки не меняется ни машина, ни сохранённый образ сброса.
        validated = image if isinstance(image, ProgramImage) else validate_image(image)
        self._initial_image = validated
        return self.reset()

    def reset(self) -> CpuSnapshot:
        self._registers = [0] * REGISTER_COUNT
        self._code = [0] * CODE_SIZE
        self._data = [0] * DATA_SIZE
        self._pc = self._initial_image.entry_point if self._initial_image else 0
        self._ir = 0
        self._instruction_address = None
        self._decoded = None
        self._flags = Flags()
        self._status = "ready"
        self._steps = 0
        self._fault = None
        self._loaded_instructions = (
            len(self._initial_image.instructions) if self._initial_image else 0
        )
        if self._initial_image is not None:
            self._code[: len(self._initial_image.instructions)] = self._initial_image.instructions
            for cell in self._initial_image.data:
                self._data[cell.address] = cell.value
        return self.snapshot()

    def snapshot(self) -> CpuSnapshot:
        return CpuSnapshot(
            registers=tuple(self._registers),
            pc=self._pc,
            ir=self._ir,
            instruction_address=self._instruction_address,
            decoded=self._decoded,
            flags=self._flags,
            status=self._status,
            steps=self._steps,
            loaded_instructions=self._loaded_instructions,
            fault=self._fault,
        )

    def read_data(self, address: int) -> int:
        self._check_data_address(address)
        return self._data[address]

    def read_instruction(self, address: int) -> int:
        if not is_unsigned(address, CODE_SIZE - 1):
            raise MachineError("FETCH_OUT_OF_BOUNDS", f"Адрес команд {address} вне диапазона 0…1023.")
        return self._code[address]

    def memory(self) -> dict[str, list[int]]:
        """Копии для просмотра ОЗУ: они не позволяют менять память машины."""
        return {"instructions": list(self._code), "data": list(self._data)}

    def step(self) -> StepResult:
        if self._status != "ready":
            return StepResult(False, self.snapshot(), ())

        writes: list[WriteEvent] = []
        fetched = False
        try:
            if not is_unsigned(self._pc, CODE_SIZE - 1) or self._pc >= self._loaded_instructions:
                raise MachineError(
                    "FETCH_OUT_OF_BOUNDS",
                    f"По адресу команд {self._pc} нет загруженной инструкции.",
                )
            self._ir = self._code[self._pc]
            self._instruction_address = self._pc
            self._decoded = None
            fetched = True
            self._decoded = decode(self._ir)
            i = self._decoded.instruction
            f = i.fields

            next_pc = self._pc + 1
            next_flags = self._flags
            next_status: CpuStatus = "ready"
            pending_write: tuple[str, int, int] | None = None  # (kind, address, value)

            def read(register: int) -> int:
                return self._registers[register]

            if i.op == "HALT":
                next_status = "halted"
            elif i.op == "MOV":
                value = f["value"] if f["mode"] == "immediate" else read(f["value"])
                pending_write = ("register", f["d"], value)
            elif i.op in ("LD", "ST"):
                address = f["value"] if f["mode"] == "direct" else read(f["value"])
                self._check_data_address(address)
                pending_write = (
                    ("register", f["d"], self._data[address])
                    if i.op == "LD"
                    else ("data", address, read(f["d"]))
                )
            elif i.op == "JMP":
                next_pc = f["target"]
            elif i.op == "JZ":
                if self._flags.zf:
                    next_pc = f["target"]
            elif i.op == "JNZ":
                if not self._flags.zf:
                    next_pc = f["target"]
            else:
                operand_b = f["shift"] if i.op == "SAR" else read(f["b"])
                result = calculate(i.op, read(f["a"]), operand_b, self._flags)
                next_flags = result.flags
                if i.op != "CMP":
                    pending_write = ("register", f["d"], result.value)

            # Все потенциальные ошибки проверены; применять эффекты можно целиком.
            if pending_write is not None:
                kind, address, value = pending_write
                target = self._registers if kind == "register" else self._data
                before = target[address]
                target[address] = value
                if before != value:
                    writes.append(WriteEvent(kind, address, before, value))
            self._flags = next_flags
            self._pc = next_pc
            self._status = next_status
            self._steps += 1
            return StepResult(True, self.snapshot(), tuple(writes))
        except MachineError as error:
            self._status = "faulted"
            self._fault = CpuFault(
                code=error.code,
                message=str(error),
                address=self._pc,
                word=self._ir if fetched else None,
            )
            return StepResult(False, self.snapshot(), ())

    def _check_data_address(self, address: int) -> None:
        if not is_unsigned(address, DATA_SIZE - 1):
            raise MachineError("DATA_OUT_OF_BOUNDS", f"Адрес данных {address} вне диапазона 0…4095.")
