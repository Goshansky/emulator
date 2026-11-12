"""АЛУ: 16-битная знаковая арифметика в дополнительном коде и флаги."""

from __future__ import annotations

from dataclasses import dataclass

WORD_SIZE = 0x1_0000
WORD_MAX = WORD_SIZE - 1


def word(value: int) -> int:
    """Ограничить значение 16 битами: результат 0…65535."""
    return value % WORD_SIZE


def signed(value: int) -> int:
    """Знаковая интерпретация 16-битного слова."""
    return value if value < 0x8000 else value - WORD_SIZE


@dataclass(frozen=True)
class Flags:
    zf: bool = False
    nf: bool = False
    cf: bool = False
    of: bool = False

    def to_dict(self) -> dict[str, bool]:
        return {"zf": self.zf, "nf": self.nf, "cf": self.cf, "of": self.of}


@dataclass(frozen=True)
class AluResult:
    value: int
    flags: Flags


def _overflows(value: int) -> bool:
    return value < -32768 or value > 32767


def calculate(op: str, a: int, b: int, flags: Flags) -> AluResult:
    """Внутренняя операция: a/b — проверенные слова; для SAR b — сдвиг 0…15."""
    cf = False
    of = False

    if op in ("ADD", "ADC"):
        carry = 1 if op == "ADC" and flags.cf else 0
        result = a + b + carry
        cf = result > WORD_MAX
        of = _overflows(signed(a) + signed(b) + carry)
    elif op in ("SUB", "CMP"):
        result = a - b
        cf = a < b
        of = _overflows(signed(a) - signed(b))
    elif op in ("MULLO", "MULHI"):
        product = signed(a) * signed(b)
        result = product if op == "MULLO" else product // WORD_SIZE
        cf = of = _overflows(product)
    elif op == "SAR":
        if b == 0:
            return AluResult(a, flags)
        result = signed(a) >> b
        cf = ((a >> (b - 1)) & 1) != 0
    elif op == "AND":
        result = a & b
    elif op == "OR":
        result = a | b
    elif op == "XOR":
        result = a ^ b
    else:
        raise ValueError(f"Неизвестная операция АЛУ: {op}")

    value = word(result)
    return AluResult(value, Flags(zf=value == 0, nf=value >= 0x8000, cf=cf, of=of))
