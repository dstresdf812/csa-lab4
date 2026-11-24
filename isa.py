"""Представление исходного и машинного кода.

Определено два представления:
- Бинарное
- JSON
"""

import json
from collections import namedtuple
from enum import Enum


class Opcode(str, Enum):
    """Opcode для инструкций.

    Можно разделить на две группы:

    1. Непосредственно представленные на уровне языка: `RIGHT`, `LEFT`, `INC`, `DEC`, `INPUT`, `PRINT`.
    2. Инструкции для управления, где:
        - `JMP`, `JZ` -- безусловный и условный переходы:

            | Operator Position | Исходный код | Машинный код |
            |-------------------|--------------|--------------|
            | n                 | `[`          | `JZ (k+1)`   |
            | ...               | ...          |              |
            | k                 |              |              |
            | k+1               | `]`          | `JMP n`      |

        - `HALT` -- остановка машины.
    """
    PUSHI = "push immediate"
    DROP = "drop"
    LEA = "lea"
    LDW = "ldw"
    LDB = "ldb"
    STW = "stw"
    STB = "stb"
    ADD = "add"
    SUB = "sub"
    MUL = "mul"
    DIV = "div"
    MOD = "mod"
    EQ = "eq"
    SLT = "slt"
    ULT = "ult"
    JMP = "jmp"
    JZ = "jz"
    CALL = "call"
    RET = "ret"
    IN = "in"
    OUT = "out"
    IRET = "iret"
    HALT = "halt"
    def __str__(self):
        """Переопределение стандартного поведения `__str__` для `Enum`: вместо
        `Opcode.INC` вернуть `increment`.
        """
        return str(self.value)


class Term(namedtuple("Term", "line pos symbol")):
    """Описание выражения из исходного текста программы.

    Сделано через класс, чтобы был docstring.
    """


# Словарь соответствия кодов операций их бинарному представлению
opcode_to_binary = {
    Opcode.PUSHI: 0x01,  # 0000 0001
    Opcode.DROP:  0x02,  # 0000 0010
    Opcode.LEA:   0x03,  # 0000 0011
    Opcode.LDW:   0x04,  # 0000 0100
    Opcode.LDB:   0x05,  # 0000 0101
    Opcode.STW:   0x06,  # 0000 0110
    Opcode.STB:   0x07,  # 0000 0111
    Opcode.ADD:   0x10,  # 0001 0000
    Opcode.SUB:   0x11,  # 0001 0001
    Opcode.MUL:   0x12,  # 0001 0010
    Opcode.DIV:   0x13,  # 0001 0011
    Opcode.MOD:   0x14,  # 0001 0100
    Opcode.EQ:    0x15,  # 0001 0101
    Opcode.SLT:   0x16,  # 0001 0110
    Opcode.ULT:   0x17,  # 0001 0111
    Opcode.JMP:   0x20,  # 0010 0000
    Opcode.JZ:    0x21,  # 0010 0001
    Opcode.CALL:  0x22,  # 0010 0010
    Opcode.RET:   0x23,  # 0010 0011
    Opcode.IN:    0x30,  # 0011 0000
    Opcode.OUT:   0x31,  # 0011 0001
    Opcode.IRET:  0x32,  # 0011 0010
    Opcode.HALT:  0xFF,  # 1111 1111
}

binary_to_opcode = {
    0x01: Opcode.PUSHI,  # 0000 0001
    0x02: Opcode.DROP,   # 0000 0010
    0x03: Opcode.LEA,    # 0000 0011
    0x04: Opcode.LDW,    # 0000 0100
    0x05: Opcode.LDB,    # 0000 0101
    0x06: Opcode.STW,    # 0000 0110
    0x07: Opcode.STB,    # 0000 0111
    0x10: Opcode.ADD,    # 0001 0000
    0x11: Opcode.SUB,    # 0001 0001
    0x12: Opcode.MUL,    # 0001 0010
    0x13: Opcode.DIV,    # 0001 0011
    0x14: Opcode.MOD,    # 0001 0100
    0x15: Opcode.EQ,     # 0001 0101
    0x16: Opcode.SLT,    # 0001 0110
    0x17: Opcode.ULT,    # 0001 0111
    0x20: Opcode.JMP,    # 0010 0000
    0x21: Opcode.JZ,     # 0010 0001
    0x22: Opcode.CALL,   # 0010 0010
    0x23: Opcode.RET,    # 0010 0011
    0x30: Opcode.IN,     # 0011 0000
    0x31: Opcode.OUT,    # 0011 0001
    0x32: Opcode.IRET,   # 0011 0010
    0xFF: Opcode.HALT,   # 1111 1111
}


def to_bytes(code):
    """Преобразует машинный код в бинарное представление.

    Бинарное представление инструкций:

    ┌─────────┬─────────────────────────────────────────────────────────────┐
    │ 31...24 │ 23                                                        0 │
    ├─────────┼─────────────────────────────────────────────────────────────┤
    │  опкод  │                      адрес перехода                         │
    └─────────┴─────────────────────────────────────────────────────────────┘
    """
    binary_bytes = bytearray()
    for instr in code:
        # Получаем бинарный код операции
        opcode_bin = opcode_to_binary[instr["opcode"]] << 24

        # Добавляем адрес перехода, если он есть
        arg = instr.get("arg", 0)

        # Формируем 32-битное слово: опкод (4 бита) + адрес (28 бит)
        binary_instr = opcode_bin | (arg & 0x00FFFFFF)

        # Преобразуем 32-битное целое число в 4 байта (big-endian)

        binary_bytes.extend(
            (binary_instr & 0xFF, (binary_instr >> 8) & 0xFF, (binary_instr >> 16) & 0xFF, (binary_instr >> 24) & 0xFF)
        )

    return bytes(binary_bytes)


def to_hex(code, start_addr=0x0004):
    """Преобразует машинный код в текстовый файл с шестнадцатеричным представлением.

    Формат вывода:
    <address> - <HEXCODE> - <mnemonic>
    Например:
    20 - 03340301 - add #01 <- 34 + #03
    """
    binary_code = to_bytes(code)
    result = []
    decoded = from_bytes(binary_code)
    for i in range(0, len(binary_code), 4):
        if i + 3 >= len(binary_code):
            break

        # Формируем 32-битное слово из 4 байтов
        word = (binary_code[i]) | (binary_code[i + 1] << 8) | (binary_code[i + 2] << 16) | binary_code[i + 3] << 24

        # Преобразуем опкод и адрес в мнемонику
        instr = decoded[i // 4]
        mnemonic = instr["opcode"].name
        if "arg" in instr:
            mnemonic = f"{mnemonic} {instr['arg']}"

        # Формируем строку в требуемом формате
        hex_word = f"{word:08X}"
        address = f"{start_addr+i:04X}"
        line = f"{address} - {hex_word} - {mnemonic}"
        result.append(line)

    return "\n".join(result)


def from_bytes(binary_code):
    """Преобразует бинарное представление машинного кода в структурированный формат.

    Бинарное представление инструкций:

    ┌─────────┬─────────────────────────────────────────────────────────────┐
    │ 31...24 │ 23                                                        0 │
    ├─────────┼─────────────────────────────────────────────────────────────┤
    │  опкод  │                      адрес перехода                         │
    └─────────┴─────────────────────────────────────────────────────────────┘
    """
    structured_code = []
    # Обрабатываем байты по 4 за раз для получения 32-битных инструкций
    for i in range(0, len(binary_code), 4):
        if i + 3 >= len(binary_code):
            break

        # Формируем 32-битное слово из 4 байтов
        binary_instr = (
            (binary_code[i]) | (binary_code[i + 1] << 8) | (binary_code[i + 2] << 16) | binary_code[i + 3] << 24
        )

        # Извлекаем опкод (старшие 4 бита)
        opcode_bin = (binary_instr >> 24) & 0xFF
        opcode = binary_to_opcode[opcode_bin]

        # Извлекаем адрес перехода (младшие 28 бит)
        arg = binary_instr & 0x00FFFFFF

        # Формируем структуру инструкции
        instr = {"index": i // 4, "opcode": opcode}

        # Добавляем адрес перехода только для инструкций перехода
        if opcode in (Opcode.JMP, Opcode.JZ, Opcode.PUSHI, Opcode.LEA, Opcode.RET, Opcode.CALL):
            if opcode in (Opcode.PUSHI, Opcode.LEA, Opcode.RET) and (arg & 0x800000):
                arg -= 0x1000000
            instr["arg"] = arg

        structured_code.append(instr)

    return structured_code


def write_json(filename, code):
    """Записать машинный код в JSON файл.

    - Список JSON. Один элемент списка -- одна инструкция.
    - Индекс списка соответствует:
         - адресу оператора в исходном коде;
         - адресу инструкции в машинном коде.

    Пример:

    ```json
    [
        { "index": 0, "opcode": "jz", "arg": 5, "term": [ 1, 5, "]" ] },
    ]
    ```

    где:

    - `index` -- номер в машинном коде, необходим для того, чтобы понимать, куда делается условный переход;
    - `opcode` -- строка с кодом операции (тип: `Opcode`);
    - `arg` -- аргумент инструкции (если требуется);
    - `term` -- информация о связанном месте в исходном коде (если есть).
    """
    with open(filename, "w", encoding="utf-8") as file:
        # Почему не: `file.write(json.dumps(code, indent=4))`?
        # Чтобы одна инструкция была на одну строку.
        buf = []
        for instr in code:
            buf.append(json.dumps(instr))
        file.write("[" + ",\n ".join(buf) + "]")