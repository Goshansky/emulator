"""Диагностика машины: коды ошибок и исключение уровня CPU."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ErrorCode = Literal[
    "INVALID_IMAGE",
    "FETCH_OUT_OF_BOUNDS",
    "INVALID_OPCODE",
    "INVALID_ENCODING",
    "DATA_OUT_OF_BOUNDS",
    "INVALID_STEP_LIMIT",
]


@dataclass(frozen=True)
class CpuFault:
    code: str
    message: str
    address: int
    word: int | None = None


class MachineError(Exception):
    """Ошибка модели машины: неверный образ, выборка, декодирование или данные."""

    def __init__(self, code: ErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code


def is_unsigned(value: object, maximum: int) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= maximum
