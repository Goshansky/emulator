"""Интеграционные проверки обеих программ массивов с независимым эталоном."""

import pytest

from app.api.data_input import parse_initial_data
from app.assembler import assemble
from app.core import Cpu
from app.programs import DOT_SOURCE, EXAMPLES, SUM_SOURCE, signed_result

RESULT_BASE = 0x0300


def load_program(source: str, data_text: str) -> Cpu:
    assembly = assemble(source)
    data = parse_initial_data(data_text)
    cpu = Cpu()
    cpu.load({"instructions": list(assembly.instructions), "entryPoint": 0, "data": data})
    return cpu


def run_program(cpu: Cpu, limit: int = 100_000) -> None:
    for _ in range(limit):
        result = cpu.step()
        if not result.executed:
            break
    assert cpu.snapshot().status == "halted"


def result_words(cpu: Cpu, count: int) -> list[int]:
    return [cpu.read_data(RESULT_BASE + i) for i in range(count)]


def data_line(base: int, values: list[int]) -> str:
    return f"0x{base:04X}: " + ", ".join(map(str, values))


# --- Сумма массива -----------------------------------------------------------

SUM_CASES = [
    ("смешанные знаки", [10, 1, -2, 3, -4, 5, -6, 7, -8, 9, -10], -5, [0xFFFB, 0xFFFF], 81),
    ("минимум", [10] + [-32768] * 10, -327680, [0x0000, 0xFFFB], 81),
    ("максимум длины", [15] + [32767] * 15, 491505, [0x7FF1, 0x0007], 116),
    ("пустой цикл", [0], 0, [0x0000, 0x0000], 11),
]


@pytest.mark.parametrize("name,array,expected,words,steps", SUM_CASES)
def test_array_sum(name, array, expected, words, steps):
    cpu = load_program(SUM_SOURCE, data_line(0x0100, array))
    run_program(cpu)
    assert signed_result(result_words(cpu, 2)) == expected
    assert result_words(cpu, 2) == words
    assert cpu.snapshot().steps == steps


def test_sum_preserves_source_array():
    array = [10, 1, -2, 3, -4, 5, -6, 7, -8, 9, -10]
    cpu = load_program(SUM_SOURCE, data_line(0x0100, array))
    run_program(cpu)
    for i, value in enumerate(array):
        assert cpu.read_data(0x0100 + i) == value % 65536


def test_sum_random_seed_cases():
    # Детерминированный набор: эталон считается независимо от CPU.
    import random

    for seed in range(16):
        random.seed(seed)
        length = random.randint(0, 15)
        elements = [random.randint(-32768, 32767) for _ in range(length)]
        cpu = load_program(SUM_SOURCE, data_line(0x0100, [length] + elements))
        run_program(cpu)
        assert signed_result(result_words(cpu, 2)) == sum(elements)


# --- Свёртка двух массивов ---------------------------------------------------

def dot_data(a: list[int], b: list[int]) -> str:
    return data_line(0x0100, a) + "\n" + data_line(0x0200, b)


DOT_CASES = [
    (
        "смешанные знаки",
        [10, 1, -2, 3, -4, 5, -6, 7, -8, 9, -10],
        [10, 10, 9, -8, -7, 6, 5, -4, -3, 2, 1],
        0,
        [0x0000, 0x0000, 0x0000],
    ),
    ("положительная", [10] + [1] * 10, [10] + [1] * 10, 10, [0x000A, 0x0000, 0x0000]),
    ("отрицательная", [10] + [-1] * 10, [10] + [1] * 10, -10, [0xFFF6, 0xFFFF, 0xFFFF]),
    (
        "максимум",
        [10] + [-32768] * 10,
        [10] + [-32768] * 10,
        10737418240,
        [0x0000, 0x8000, 0x0002],
    ),
    (
        "минимум",
        [10] + [-32768] * 10,
        [10] + [32767] * 10,
        -10737090560,
        [0x0000, 0x8005, 0xFFFD],
    ),
    (
        "перенос из младшего слова",
        [10] + [32767] * 10,
        [10] + [32767] * 10,
        10736762890,
        [0x000A, 0x7FF6, 0x0002],
    ),
]


@pytest.mark.parametrize("name,a,b,expected,words", DOT_CASES)
def test_array_dot(name, a, b, expected, words):
    cpu = load_program(DOT_SOURCE, dot_data(a, b))
    run_program(cpu)
    assert signed_result(result_words(cpu, 3)) == expected
    assert result_words(cpu, 3) == words
    assert cpu.read_data(0x0303) == 0
    assert cpu.snapshot().steps == 139


@pytest.mark.parametrize(
    "len_a,len_b,expected_steps",
    [(9, 10, 12), (10, 9, 15), (0, 0, 12)],
)
def test_dot_invalid_length(len_a, len_b, expected_steps):
    a = [len_a] + [1] * len_a
    b = [len_b] + [1] * len_b
    cpu = load_program(DOT_SOURCE, dot_data(a, b))
    run_program(cpu, limit=100)
    assert cpu.read_data(0x0303) == 1
    assert cpu.snapshot().steps == expected_steps
    assert cpu.snapshot().status == "halted"


def test_dot_random_seed_cases():
    import random

    for seed in range(16):
        random.seed(seed)
        a_elems = [random.randint(-32768, 32767) for _ in range(10)]
        b_elems = [random.randint(-32768, 32767) for _ in range(10)]
        cpu = load_program(DOT_SOURCE, dot_data([10] + a_elems, [10] + b_elems))
        run_program(cpu)
        expected = sum(x * y for x, y in zip(a_elems, b_elems))
        assert signed_result(result_words(cpu, 3)) == expected


def test_reset_reruns():
    cpu = load_program(
        SUM_SOURCE, data_line(0x0100, [10, 1, -2, 3, -4, 5, -6, 7, -8, 9, -10])
    )
    run_program(cpu)
    cpu.reset()
    run_program(cpu)
    assert signed_result(result_words(cpu, 2)) == -5


def test_examples_assemble_and_run():
    for example in EXAMPLES:
        cpu = load_program(example.source, example.data)
        run_program(cpu)
        assert cpu.snapshot().status == "halted", example.id
