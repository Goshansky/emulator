"""Проверки ассемблера: кодирование, метки, диагностика ошибок."""

import pytest

from app.assembler import AssemblyError, assemble


def words(source: str) -> list[int]:
    return list(assemble(source).instructions)


def test_minimal_program_words():
    assert words("MOV R1, 2\nMOV R2, 3\nADD R0, R1, R2\nHALT") == [
        0x01110002,
        0x01210003,
        0x10012000,
        0x00000000,
    ]


def test_labels_and_jumps():
    result = assemble(
        "loop:\n"
        "    MOV R0, 0\n"
        "    JZ done\n"
        "    JNZ loop\n"
        "done: HALT\n"
    )
    assert result.labels == {"loop": 0, "done": 3}
    assert list(result.instructions) == [0x01010000, 0x21000003, 0x22000000, 0x00000000]


def test_all_addressing_modes():
    assert words("MOV R1, 0x0101")[0] == 0x01110101      # непосредственная
    assert words("MOV R1, R2")[0] == 0x01100002        # регистровая
    assert words("LD R1, [0x0100]")[0] == 0x02120100   # прямая
    assert words("LD R1, [R4]")[0] == 0x02130004       # косвенно-регистровая
    assert words("ST [0x0300], R0")[0] == 0x03020300
    assert words("ST [R4], R6")[0] == 0x03630004


def test_case_insensitive_and_comments():
    assert words("  mov r0, 5 ; комментарий") == [0x01010005]


def test_signed_immediate():
    assert words("MOV R6, -1") == [0x0161FFFF]
    assert words("MOV R6, -32768") == [0x01618000]


def test_source_map():
    result = assemble("; комментарий\nMOV R0, 1\n\nHALT\n")
    assert [(e.address, e.line) for e in result.source_map] == [(0, 2), (1, 4)]


ERRORS = {
    "": "EMPTY_PROGRAM",
    "FOO R0, R1": "UNKNOWN_INSTRUCTION",
    "MOV R0": "OPERAND_COUNT",
    "MOV R16, 1": "INVALID_REGISTER",
    "MOV R0, abc": "INVALID_LITERAL",
    "MOV R0, 40000": "OUT_OF_RANGE",
    "MOV R0, 0x110000": "OUT_OF_RANGE",
    "LD R0, 0x0100": "INVALID_OPERAND",
    "LD R0, [0x1000]": "OUT_OF_RANGE",
    "JMP missing": "UNDEFINED_LABEL",
    "m: MOV R0, 1\nm: HALT": "DUPLICATE_LABEL",
    "1bad: HALT": "INVALID_LABEL",
    "end:": "EMPTY_PROGRAM",
    "MOV R0, R1\nextra:": "INVALID_LABEL",
    "SAR R0, R0, 16": "OUT_OF_RANGE",
    "JMP 1024": "OUT_OF_RANGE",
}


@pytest.mark.parametrize("source,code", ERRORS.items())
def test_assembly_errors(source, code):
    with pytest.raises(AssemblyError) as error:
        assemble(source)
    assert error.value.diagnostic.code == code


def test_program_too_large():
    source = "\n".join(["HALT"] * 1025)
    with pytest.raises(AssemblyError) as error:
        assemble(source)
    assert error.value.diagnostic.code == "PROGRAM_TOO_LARGE"
