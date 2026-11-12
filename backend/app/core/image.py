"""Проверка образа программы перед загрузкой в машину."""

from __future__ import annotations

from typing import Any

from .errors import MachineError, is_unsigned
from .isa import CODE_SIZE, DATA_SIZE
from .types import DataCell, ProgramImage


def _invalid(message: str) -> None:
    raise MachineError("INVALID_IMAGE", message)


def validate_image(image: Any) -> ProgramImage:
    """Проверить весь образ и отделить его от изменяемых структур вызывающего кода."""
    if not isinstance(image, dict):
        _invalid("Образ программы должен быть объектом.")

    raw_instructions = image.get("instructions")
    if not isinstance(raw_instructions, (list, tuple)) or not 1 <= len(raw_instructions) <= CODE_SIZE:
        _invalid(f"Образ должен содержать от 1 до {CODE_SIZE} инструкций.")
    instructions: list[int] = []
    for value in raw_instructions:
        if not is_unsigned(value, 0xFFFF_FFFF):
            _invalid("Машинное слово должно быть целым числом от 0 до 4294967295.")
        instructions.append(value)

    entry_point = image.get("entryPoint")
    if not is_unsigned(entry_point, len(instructions) - 1):
        _invalid("Точка входа должна указывать на загруженную инструкцию.")

    raw_data = image.get("data")
    if not isinstance(raw_data, (list, tuple)):
        _invalid("Начальные данные должны быть списком ячеек.")
    data: list[DataCell] = []
    addresses: set[int] = set()
    for cell in raw_data:
        if not isinstance(cell, dict):
            _invalid("Начальные данные содержат неверную ячейку.")
        address, value = cell.get("address"), cell.get("value")
        if not is_unsigned(address, DATA_SIZE - 1):
            _invalid("Адрес начальных данных должен быть в диапазоне 0…4095.")
        if not is_unsigned(value, 0xFFFF):
            _invalid("Слово данных должно быть целым числом от 0 до 65535.")
        if address in addresses:
            _invalid(f"Начальные данные повторно задают ячейку {address}.")
        addresses.add(address)
        data.append(DataCell(address, value))

    return ProgramImage(tuple(instructions), entry_point, tuple(data))
