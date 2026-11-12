"""Разбор текстового ввода начальных данных: «адрес: слово, слово»."""

from __future__ import annotations

import re

from ..core import DATA_SIZE, WORD_BITS

_WORD_SIGN = 1 << (WORD_BITS - 1)
_WORD_MASK = (_WORD_SIGN << 1) - 1
_HEX_DIGITS = WORD_BITS // 4

HEX_PATTERN = re.compile(r"^0x[0-9a-f]+$", re.IGNORECASE)
DECIMAL_PATTERN = re.compile(r"^[+-]?[0-9]+$")
LINE_PATTERN = re.compile(r"^(0x[0-9a-f]+|[0-9]+)\s*:\s*(.+)$", re.IGNORECASE)


class DataInputError(Exception):
    def __init__(self, line: int, message: str) -> None:
        super().__init__(f"Строка данных {line}: {message}")
        self.line = line
        self.reason = message


def _parse_address(text: str, line: int) -> int:
    address = int(text, 16) if HEX_PATTERN.match(text) else int(text, 10)
    if address >= DATA_SIZE:
        raise DataInputError(line, f"адрес должен быть в диапазоне 0…{DATA_SIZE - 1}.")
    return address


def _parse_word(text: str, line: int) -> int:
    is_hex = bool(HEX_PATTERN.match(text))
    if not is_hex and not DECIMAL_PATTERN.match(text):
        raise DataInputError(line, f"неверное значение «{text}».")
    value = int(text, 16) if is_hex else int(text, 10)
    minimum = 0 if is_hex else -_WORD_SIGN
    maximum = _WORD_MASK if is_hex else _WORD_SIGN - 1
    if value < minimum or value > maximum:
        hex_max = format(_WORD_MASK, "X").zfill(_HEX_DIGITS)
        raise DataInputError(
            line,
            f"значение должно быть {minimum}…{maximum} или 0x{'0' * _HEX_DIGITS}…0x{hex_max}.",
        )
    return value % (1 << WORD_BITS)


def parse_initial_data(text: str) -> list[dict[str, int]]:
    """Формат строки: адрес: слово, слово. Адреса не пересекаются."""
    data: list[dict[str, int]] = []
    occupied: set[int] = set()

    for index, raw in enumerate(re.split(r"\r\n|\n|\r", text)):
        line = index + 1
        source = raw.split(";", 1)[0].strip()
        if not source:
            continue
        match = LINE_PATTERN.match(source)
        if match is None:
            raise DataInputError(line, "ожидается «адрес: значение, значение».")
        start = _parse_address(match.group(1), line)

        for offset, raw_value in enumerate(match.group(2).split(",")):
            word = _parse_word(raw_value.strip(), line)
            address = start + offset
            if address >= DATA_SIZE:
                raise DataInputError(line, f"данные выходят за адрес {DATA_SIZE - 1}.")
            if address in occupied:
                raise DataInputError(line, f"ячейка {address} указана повторно.")
            occupied.add(address)
            data.append({"address": address, "value": word})
    return data
