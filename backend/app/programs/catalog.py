"""Каталог готовых программ для интерфейса эмулятора."""

from __future__ import annotations

from dataclasses import dataclass

from .sources import DOT_SOURCE, SUM_SOURCE


@dataclass(frozen=True)
class ProgramExample:
    id: str
    name: str
    description: str
    source: str
    data: str
    result_words: int | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "source": self.source,
            "data": self.data,
            "resultWords": self.result_words,
        }


EXAMPLES: tuple[ProgramExample, ...] = (
    ProgramExample(
        id="countdown",
        name="Сумма в цикле",
        description="3 + 2 + 1 → ячейка 0x0300",
        source=(
            "; Сумма чисел в цикле\n"
            "    MOV R0, 0\n"
            "    MOV R3, 3\n"
            "    MOV R4, 1\n"
            "loop:\n"
            "    ADD R0, R0, R3\n"
            "    SUB R3, R3, R4\n"
            "    JNZ loop\n"
            "    ST [0x0300], R0\n"
            "    HALT"
        ),
        data="; Начальные данные можно задать ниже\n; 0x0100: 10, -2, 3",
    ),
    ProgramExample(
        id="memory",
        name="Работа с памятью",
        description="−7 + 12 → ячейка 0x0300",
        source=(
            "; Загрузка, сложение и сохранение\n"
            "    LD R0, [0x0100]\n"
            "    LD R1, [0x0101]\n"
            "    ADD R0, R0, R1\n"
            "    ST [0x0300], R0\n"
            "    HALT"
        ),
        data="0x0100: -7, 12",
    ),
    ProgramExample(
        id="carry",
        name="Перенос между словами",
        description="0x0000FFFF + 1 → 0x00010000",
        source=(
            "; R1:R0 — число из двух слов\n"
            "    MOV R0, 0xFFFF\n"
            "    MOV R1, 0\n"
            "    MOV R2, 1\n"
            "    MOV R4, 0\n"
            "    ADD R0, R0, R2\n"
            "    ADC R1, R1, R4\n"
            "    ST [0x0300], R0\n"
            "    ST [0x0301], R1\n"
            "    HALT"
        ),
        data="",
    ),
    ProgramExample(
        id="array-sum",
        name="Сумма массива · 32 бита",
        description="10 знаковых элементов → два слова с адреса 0x0300",
        source=SUM_SOURCE,
        data="0x0100: 10, 1, -2, 3, -4, 5, -6, 7, -8, 9, -10",
        result_words=2,
    ),
    ProgramExample(
        id="array-dot",
        name="Свёртка массивов · 48 бит",
        description="10 пар элементов → три слова и статус с адреса 0x0300",
        source=DOT_SOURCE,
        data=(
            "0x0100: 10, -32768, -32768, -32768, -32768, -32768, -32768, -32768, -32768, -32768, -32768\n"
            "0x0200: 10, -32768, -32768, -32768, -32768, -32768, -32768, -32768, -32768, -32768, -32768"
        ),
        result_words=3,
    ),
)
