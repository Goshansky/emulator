"""Интерпретация готовых слов памяти как длинного знакового числа."""

from __future__ import annotations

from ..core import WORD_BITS

_WORD_MAX = (1 << WORD_BITS) - 1


def signed_result(words: list[int] | tuple[int, ...]) -> int:
    """Слова от младшего к старшему → знаковое 32- или 48-битное число."""
    if len(words) not in (2, 3):
        raise ValueError("Результат должен содержать два или три слова.")
    value = 0
    for index, word in enumerate(words):
        if not isinstance(word, int) or not 0 <= word <= _WORD_MAX:
            raise ValueError(f"Слово результата должно быть целым числом 0…{_WORD_MAX}.")
        value |= word << (index * WORD_BITS)
    bits = len(words) * WORD_BITS
    sign = 1 << (bits - 1)
    return value - (1 << bits) if value & sign else value
