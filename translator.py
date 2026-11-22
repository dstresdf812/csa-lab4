#!/usr/bin/python3
"""Транслятор brainfuck в машинный код.
"""

import os
import sys
from operator import index

from isa import Opcode, Term, to_bytes, to_hex, write_json


def symbols():
    """Полное множество символов языка brainfuck."""
    return {"<", ">", "+", "-", ",", ".", "[", "]"}


def symbol2opcode(symbol):
    """Отображение операторов исходного кода в коды операций."""
    return {
        "<": Opcode.LEFT,
        ">": Opcode.RIGHT,
        "+": Opcode.INC,
        "-": Opcode.DEC,
        ",": Opcode.INPUT,
        ".": Opcode.PRINT,
    }.get(symbol)


def text2terms(text):
    """Трансляция текста в последовательность операторов языка (токенов).

    Включает в себя:

    - отсеивание всех незначимых символов (считаются комментариями);
    - проверка формальной корректности программы (парность оператора цикла).
    """
    terms = []
    for line_num, line in enumerate(text.split(), 1):
        for pos, char in enumerate(line, 1):
            if char in symbols():
                terms.append(Term(line_num, pos, char))

    deep = 0
    for term in terms:
        if term.symbol == "[":
            deep += 1
        if term.symbol == "]":
            deep -= 1
        assert deep >= 0, "Unbalanced brackets!"
    assert deep == 0, "Unbalanced brackets!"

    return terms

def text2terms(text):
    terms = []
    for line_num, line in enumerate(text.split("\n"), 1):
        index = 0
        string = ""
        while (index <= len(line) - 1):
            symbol = line[index]
            if symbol.isspace():
                if (string != ""):
                    terms.append(Term(line_num, index - len(string) + 1, string))
                string = ""
                index += 1
                continue
            if symbol in "()":
                if (string != ""):
                    terms.append(Term(line_num, index - len(string) + 1, string))
                    string = ""
                terms.append(Term(line_num, index - len(string) + 1, symbol))
                index += 1
                continue
            else:
                string += symbol
                index += 1
        if (string != ""):
            terms.append(Term(line_num, index - len(string) + 1, string))
    return terms

def parse_expression(terms, index):
    if (index < len(terms)):
        if (terms[index].symbol == ")"):
            raise ValueError("unbalanced brackets!")
    if (terms[index].symbol == "("):
        index = index + 1
        items = []
        while index < len(terms) and terms[index].symbol != ")":
            item, index = parse_expression(terms, index)
            items.append(item)

        if index == len(terms):
            raise ValueError("unbalanced brackets!")

        return items, index + 1
    try:
        return (int(terms[index].symbol), index+1)
    except ValueError:
        return (terms[index].symbol, index+1)

def translate(text):
    expression, _ = parse_expression(text2terms(text), 0)
    # Транслируем термы в машинный код.
    code = []
    operands = {"+": Opcode.ADD, "-": Opcode.SUB, "*": Opcode.MUL, "div": Opcode.DIV, "mod": Opcode.MOD, "=":Opcode.EQ}

    def emit(expr):
        if (isinstance(expr, int)):
            code.append({"opcode": Opcode.PUSHI, "arg": expr})
            return
        operator, left, right = expr
        emit(left)
        emit(right)
        if (operator not in operands):
            raise ValueError("wrong operand!")
        code.append({"opcode": operands.get(operator)})
    emit(expression)
    code.append({"opcode": Opcode.HALT})
    return code

# print(translate("(div 2 (+ 5 3))"))
# print(to_bytes(translate("(+ 2 (+ 3 4))")))


def main(source, target):
    """Функция запуска транслятора. Параметры -- исходный и целевой файлы."""
    with open(source, encoding="utf-8") as f:
        source = f.read()

    code = translate(source)
    halt_addr = 0x0004 + 4 * (len(code) - 1)
    binary_code = halt_addr.to_bytes(4, "little") + to_bytes(code)
    hex_code = to_hex(code)

    # Убедимся, что каталог назначения существует
    os.makedirs(os.path.dirname(os.path.abspath(target)) or ".", exist_ok=True)

    # Запишим выходные файлы
    if target.endswith(".bin"):
        with open(target, "wb") as f:
            f.write(binary_code)
        with open(target + ".hex", "w") as f:
            f.write(hex_code)
    else:
        write_json(target, code)

    # Обратите внимание, что память данных не экспортируется в файл, так как
    # в случае brainfuck она может быть инициализирована только 0.
    print("source LoC:", len(source.split("\n")), "code instr:", len(code))


if __name__ == "__main__":
    assert len(sys.argv) == 3, "Wrong arguments: translator.py <input_file> <target_file>"
    _, source, target = sys.argv
    main(source, target)