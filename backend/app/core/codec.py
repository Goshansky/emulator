"""Кодек машинных слов: декодирование, кодирование и текст инструкции."""

from __future__ import annotations

from .errors import MachineError, is_unsigned
from .isa import (
    ADDRESS_MODES,
    BINARY_OPS,
    CODE_SIZE,
    DATA_SIZE,
    ISA,
    OPCODE_TO_MNEMONIC,
    REGISTER_COUNT,
    DecodedInstruction,
    Instruction,
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise MachineError("INVALID_ENCODING", message)


def _field(value: int, maximum: int, name: str) -> int:
    _require(is_unsigned(value, maximum), f"Поле {name}: требуется целое число от 0 до {maximum}.")
    return value


def hex_word(value: int, width: int = 4) -> str:
    return format(value, "X").zfill(width)


def format_instruction(instruction: Instruction) -> str:
    i = instruction
    f = i.fields
    op = i.op
    if op == "HALT":
        return "HALT"
    if op == "MOV":
        source = f"R{f['value']}" if f["mode"] == "register" else f"0x{hex_word(f['value'])}"
        return f"MOV R{f['d']}, {source}"
    if op in ("LD", "ST"):
        address = f"0x{hex_word(f['value'])}" if f["mode"] == "direct" else f"R{f['value']}"
        return f"LD R{f['d']}, [{address}]" if op == "LD" else f"ST [{address}], R{f['d']}"
    if op in ("JMP", "JZ", "JNZ"):
        return f"{op} 0x{hex_word(f['target'])}"
    if op == "CMP":
        return f"CMP R{f['a']}, R{f['b']}"
    if op == "SAR":
        return f"SAR R{f['d']}, R{f['a']}, {f['shift']}"
    return f"{op} R{f['d']}, R{f['a']}, R{f['b']}"


def decode(word_value: int) -> DecodedInstruction:
    """На входе только сырое машинное слово, без исходного текста программы."""
    _require(is_unsigned(word_value, 0xFFFF_FFFF), "Инструкция должна быть беззнаковым 32-битным целым.")
    opcode = word_value >> 24
    op = OPCODE_TO_MNEMONIC.get(opcode)
    if op is None:
        raise MachineError("INVALID_OPCODE", f"Неизвестный код операции 0x{hex_word(opcode, 2)}.")
    fmt = ISA[op].format
    d = (word_value >> 20) & 15
    a = (word_value >> 16) & 15
    b = (word_value >> 12) & 15
    v = word_value & 0xFFFF

    if op == "HALT":
        _require(word_value == 0, "Резервные биты HALT должны быть нулевыми.")
        instruction = Instruction(op)
        fields = {"OP": opcode, "reserved": 0}
    elif op in ("MOV", "LD", "ST"):
        fields = {"OP": opcode, "D": d, "M": a, "V": v}
        if op == "MOV":
            _require(
                a in (ADDRESS_MODES["register"], ADDRESS_MODES["immediate"]),
                "MOV допускает только регистр или непосредственное значение.",
            )
            if a == ADDRESS_MODES["register"]:
                _require(v < REGISTER_COUNT, "Номер регистра MOV содержит лишние биты.")
            mode = "register" if a == ADDRESS_MODES["register"] else "immediate"
        else:
            _require(
                a in (ADDRESS_MODES["direct"], ADDRESS_MODES["indirect"]),
                f"{op} требует прямой или косвенно-регистровый адрес.",
            )
            limit = DATA_SIZE if a == ADDRESS_MODES["direct"] else REGISTER_COUNT
            _require(v < limit, f"{op}: адрес или номер регистра содержит лишние биты.")
            mode = "direct" if a == ADDRESS_MODES["direct"] else "indirect"
        instruction = Instruction(op, {"d": d, "mode": mode, "value": v})
    elif op in ("JMP", "JZ", "JNZ"):
        _require(
            (word_value & 0x00FF_0000) == 0 and v < CODE_SIZE,
            "Переход: ненулевой резерв или адрес вне памяти команд.",
        )
        instruction = Instruction(op, {"target": v})
        fields = {"OP": opcode, "reserved": 0, "T": v}
    else:
        _require((word_value & 0xFFF) == 0, f"{op}: резервные биты должны быть нулевыми.")
        fields = {"OP": opcode, "D": d, "A": a, "n" if op == "SAR" else "B": b, "reserved": 0}
        if op == "CMP":
            _require(d == 0, "CMP не имеет получателя: поле D должно быть нулевым.")
            instruction = Instruction(op, {"a": a, "b": b})
        elif op == "SAR":
            instruction = Instruction(op, {"d": d, "a": a, "shift": b})
        elif op in BINARY_OPS:
            instruction = Instruction(op, {"d": d, "a": a, "b": b})
        else:  # pragma: no cover - таблица ISA исключает попадание сюда
            raise MachineError("INVALID_OPCODE", f"Неизвестная операция {op}.")

    return DecodedInstruction(
        word=word_value,
        format=fmt,
        fields=fields,
        instruction=instruction,
        assembly=format_instruction(instruction),
    )


def encode(instruction: Instruction) -> int:
    """Операнды уже разобраны; разбор ассемблерных строк — отдельный модуль."""
    i = instruction
    f = i.fields
    definition = ISA.get(i.op)
    if definition is None:
        raise MachineError("INVALID_OPCODE", "Неизвестная операция кодирования.")
    word_value = definition.opcode * 0x100_0000

    def register(value: int, name: str) -> int:
        return _field(value, REGISTER_COUNT - 1, name)

    if i.op == "HALT":
        pass
    elif i.op in ("MOV", "LD", "ST"):
        mode = f.get("mode")
        valid = (
            mode in ("register", "immediate") if i.op == "MOV" else mode in ("direct", "indirect")
        )
        _require(bool(valid), f"Недопустимая адресация {i.op}.")
        maximum = (
            0xFFFF
            if mode == "immediate"
            else DATA_SIZE - 1
            if mode == "direct"
            else REGISTER_COUNT - 1
        )
        word_value += (
            register(f["d"], "D") * 0x10_0000
            + ADDRESS_MODES[mode] * 0x1_0000
            + _field(f["value"], maximum, "V")
        )
    elif i.op in ("JMP", "JZ", "JNZ"):
        word_value += _field(f["target"], CODE_SIZE - 1, "T")
    elif i.op == "CMP":
        word_value += register(f["a"], "A") * 0x1_0000 + register(f["b"], "B") * 0x1000
    elif i.op == "SAR":
        word_value += (
            register(f["d"], "D") * 0x10_0000
            + register(f["a"], "A") * 0x1_0000
            + _field(f["shift"], 15, "n") * 0x1000
        )
    else:
        word_value += (
            register(f["d"], "D") * 0x10_0000
            + register(f["a"], "A") * 0x1_0000
            + register(f["b"], "B") * 0x1000
        )
    # Единые ограничения для сборки и чтения слова.
    return decode(word_value).word
