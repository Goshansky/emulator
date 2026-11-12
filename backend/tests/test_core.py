"""Проверки ядра: кодек, АЛУ, флаги, шаги и ошибки CPU."""

import pytest

from app.core import (
    Cpu,
    Flags,
    MachineError,
    calculate,
    decode,
    encode,
    format_instruction,
    run,
)
from app.core.isa import Instruction


def image(instructions, data=()):
    return {
        "instructions": list(instructions),
        "entryPoint": 0,
        "data": [{"address": a, "value": v} for a, v in data],
    }


# --- Кодирование: контрольные примеры из спецификации -----------------------

ENCODE_CASES = [
    (Instruction("MOV", {"d": 4, "mode": "immediate", "value": 0x0101}), 0x01410101),
    (Instruction("MOV", {"d": 5, "mode": "register", "value": 4}), 0x01500004),
    (Instruction("MOV", {"d": 6, "mode": "immediate", "value": 0xFFFF}), 0x0161FFFF),
    (Instruction("LD", {"d": 3, "mode": "direct", "value": 0x0100}), 0x02320100),
    (Instruction("LD", {"d": 6, "mode": "indirect", "value": 4}), 0x02630004),
    (Instruction("ST", {"d": 0, "mode": "direct", "value": 0x0300}), 0x03020300),
    (Instruction("ST", {"d": 6, "mode": "indirect", "value": 4}), 0x03630004),
    (Instruction("ADD", {"d": 0, "a": 1, "b": 2}), 0x10012000),
    (Instruction("ADC", {"d": 2, "a": 2, "b": 10}), 0x1122A000),
    (Instruction("MULHI", {"d": 9, "a": 6, "b": 7}), 0x14967000),
    (Instruction("SAR", {"d": 10, "a": 9, "shift": 15}), 0x15A9F000),
    (Instruction("CMP", {"a": 3, "b": 15}), 0x1903F000),
    (Instruction("JNZ", {"target": 0x000A}), 0x2200000A),
    (Instruction("HALT"), 0x00000000),
]


@pytest.mark.parametrize("instruction,expected", ENCODE_CASES)
def test_encode(instruction, expected):
    assert encode(instruction) == expected
    assert decode(expected).instruction == instruction


DECODE_ERRORS = {
    0xFF000000: "INVALID_OPCODE",      # неизвестный OP
    0x10012001: "INVALID_ENCODING",    # ненулевой резерв
    0x01020000: "INVALID_ENCODING",    # запрещённый режим MOV
    0x02031000: "INVALID_ENCODING",    # лишние биты номера регистра
    0x20000400: "INVALID_ENCODING",    # адрес перехода вне памяти команд
}


@pytest.mark.parametrize("word,code", DECODE_ERRORS.items())
def test_decode_errors(word, code):
    with pytest.raises(MachineError) as error:
        decode(word)
    assert error.value.code == code


# --- АЛУ и флаги ------------------------------------------------------------

def flags(zf=False, nf=False, cf=False, of=False):
    return Flags(zf=zf, nf=nf, cf=cf, of=of)


def test_add_carry_without_overflow():
    result = calculate("ADD", 0xFFFF, 1, Flags())
    assert result.value == 0
    assert result.flags == flags(zf=True, cf=True)


def test_add_signed_overflow():
    result = calculate("ADD", 0x7FFF, 1, Flags())
    assert result.value == 0x8000
    assert result.flags == flags(nf=True, of=True)


def test_adc_uses_input_carry():
    result = calculate("ADC", 0, 0, flags(cf=True))
    assert result.value == 1
    result = calculate("ADC", 0xFFFF, 0, flags(cf=True))
    assert result.value == 0
    assert result.flags == flags(zf=True, cf=True)


def test_adc_signed_overflow_with_carry():
    result = calculate("ADC", 0x7FFF, 0, flags(cf=True))
    assert result.value == 0x8000
    assert result.flags == flags(nf=True, of=True)


def test_sub_borrow():
    result = calculate("SUB", 0, 1, Flags())
    assert result.value == 0xFFFF
    assert result.flags == flags(nf=True, cf=True)


def test_cmp_writes_nothing():
    result = calculate("CMP", 5, 5, Flags())
    assert result.value == 0
    assert result.flags.zf


@pytest.mark.parametrize(
    "a,b,lo,hi",
    [
        (-32768 & 0xFFFF, -32768 & 0xFFFF, 0, 0x4000),   # -32768 × -32768 = 2^30
        (-32768 & 0xFFFF, 0x7FFF, 0x8000, 0xC000),       # -32768 × 32767
        (0xFFFF, 1, 0xFFFF, 0xFFFF),                     # -1 × 1 = -1
    ],
)
def test_mul_halves(a, b, lo, hi):
    assert calculate("MULLO", a, b, Flags()).value == lo
    assert calculate("MULHI", a, b, Flags()).value == hi


def test_sar():
    assert calculate("SAR", 0x8000, 0, flags(nf=True)).flags.nf  # сдвиг 0 сохраняет флаги
    result = calculate("SAR", 0x8000, 1, Flags())
    assert result.value == 0xC000
    result = calculate("SAR", 0xFFFF, 15, Flags())
    assert result.value == 0xFFFF
    assert result.flags.cf and result.flags.nf


# --- CPU: загрузка, шаг, ошибки ----------------------------------------------

def test_minimal_program():
    cpu = Cpu(image([0x01110002, 0x01210003, 0x10012000, 0x00000000]))
    result = run(cpu)
    assert result.reason == "halted"
    assert result.executed_steps == 4
    state = result.state
    assert state.registers[0] == 5
    assert state.pc == 4
    assert state.ir == 0
    assert state.flags == Flags()


def test_fetch_out_of_bounds_without_halt():
    cpu = Cpu(image([0x01500004]))  # MOV R5, R4 — нет HALT
    result = run(cpu)
    assert result.reason == "faulted"
    assert result.state.fault is not None
    assert result.state.fault.code == "FETCH_OUT_OF_BOUNDS"


def test_step_after_halt_is_noop():
    cpu = Cpu(image([0x00000000]))
    cpu.step()
    result = cpu.step()
    assert not result.executed
    assert result.state.steps == 1


def test_data_out_of_bounds():
    cpu = Cpu(image([0x0141FFFF, 0x02630004]))  # MOV R4, 0xFFFF; LD R6, [R4]
    run(cpu)
    state = cpu.snapshot()
    assert state.fault is not None
    assert state.fault.code == "DATA_OUT_OF_BOUNDS"
    assert state.fault.word == 0x02630004


def test_load_and_reset():
    cpu = Cpu(image([0x01610001, 0x00000000], data=[(0x0100, 7)]))
    cpu.step()
    cpu.reset()
    state = cpu.snapshot()
    assert state.steps == 0
    assert state.status == "ready"
    assert cpu.read_data(0x0100) == 7


def test_invalid_image_rejected():
    cpu = Cpu(image([0x00000000]))
    with pytest.raises(MachineError):
        cpu.load({"instructions": [], "entryPoint": 0, "data": []})
    assert cpu.snapshot().status == "ready"  # прежняя машина сохранилась


def test_run_step_limit():
    cpu = Cpu(image([0x20000000]))  # JMP 0 — бесконечный цикл
    result = run(cpu, 100)
    assert result.reason == "limit"
    assert result.executed_steps == 100


def test_format_instruction():
    assert format_instruction(Instruction("HALT")) == "HALT"
    assert format_instruction(Instruction("MOV", {"d": 5, "mode": "register", "value": 4})) == "MOV R5, R4"
    assert format_instruction(Instruction("ST", {"d": 6, "mode": "indirect", "value": 4})) == "ST [R4], R6"
