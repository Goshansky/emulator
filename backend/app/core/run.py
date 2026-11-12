"""Ограниченный синхронный запуск для API и тестов."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .cpu import Cpu
from .errors import MachineError
from .isa import DEFAULT_STEP_LIMIT
from .types import CpuSnapshot


@dataclass(frozen=True)
class RunResult:
    reason: Literal["halted", "faulted", "limit"]
    executed_steps: int
    state: CpuSnapshot


def run(cpu: Cpu, max_steps: int = DEFAULT_STEP_LIMIT) -> RunResult:
    if not isinstance(max_steps, int) or isinstance(max_steps, bool) or max_steps < 1:
        raise MachineError("INVALID_STEP_LIMIT", "Лимит команд должен быть положительным целым числом.")
    state = cpu.snapshot()
    executed = 0
    while state.status == "ready" and executed < max_steps:
        result = cpu.step()
        state = result.state
        if result.executed:
            executed += 1
    reason: Literal["halted", "faulted", "limit"] = "limit" if state.status == "ready" else state.status
    return RunResult(reason, executed, state)
