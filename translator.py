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

global halt_addr
def translate(text):
    def emit(expr, params=[], h=0):
        if (isinstance(expr, int)):
            code.append({"opcode": Opcode.PUSHI, "arg": expr})
            return
        if not isinstance(expr, list) and not isinstance(expr[0], str):
            raise ValueError("wrong expression!")

        if isinstance(expr, str) and expr in params:
            offset = 4 * (params.index(expr) - len(params) - 1 - h)
            code.append({"opcode": Opcode.LEA, "arg": offset})
            code.append({"opcode": Opcode.LDW})
            return
        operator, *args = expr

        if (operator in functions):
            for i, arg in enumerate(args):
                emit(arg, params, h+i)
            call_index = len(code)
            code.append({"opcode": Opcode.CALL, "arg": -1})
            calls.setdefault(operator, []).append(call_index)
            return
        if (operator == "defword"):
            name, value = args
            if variables.get(name) != None:
                raise ValueError("varible already exists!")
            variables[name] = value
            return
        if (operator == "setq"):
            name, value = args
            if variables.get(name) == None:
                raise ValueError("varible is not exists!")
            variables[name] = value
            return

        if (operator == "if"):
            condition, then_br, else_br = args
            emit(condition, params, h)
            jz_index = len(code)
            code.append({"opcode": Opcode.JZ, "arg": -1})

            emit(then_br, params, h)
            jmp_index = len(code)
            code.append({"opcode": Opcode.JMP, "arg": -1})

            code[jz_index] = {"opcode": Opcode.JZ, "arg": 4 + 4 * len(code)}
            emit(else_br, params, h)
            code[jmp_index] = {"opcode": Opcode.JMP, "arg": 4 + 4 * len(code)}
            return

        if operator not in operands:
            raise ValueError("wrong operand!")

        left, right = args
        emit(left,params,h)
        emit(right,params,h+1)
        code.append({"opcode": operands.get(operator)})

    operands = {"+": Opcode.ADD, "-": Opcode.SUB, "*": Opcode.MUL,
                "div": Opcode.DIV, "mod": Opcode.MOD, "=": Opcode.EQ,
                "<": Opcode.SLT, "u<": Opcode.ULT}
    code = []
    terms = text2terms(text)
    forms = []
    index = 0
    functions = {}
    calls = {}
    variables = {}
    global halt_addr
    while index < len(terms):
        expression, index = parse_expression(terms, index)
        if (isinstance(expression, list) and expression and expression[0] == "defun"):
            name, params, *body = expression[1:]
            functions[name] = {"params": params, "body": body}
            continue

        forms.append(expression)

    for expression in forms:
        emit(expression)
        code.append({"opcode": Opcode.DROP})
    code.append({"opcode": Opcode.HALT})
    halt_addr = 0x0004 + 4 * (len(code) - 1)

    for function in functions.values():
        function["addr"] = 4 + 4 * len(code)
        for form in function["body"]:
            emit(form, function["params"])
        code.append({"opcode": Opcode.RET, "arg": -4*len(function["params"])})

    for name, indices in calls.items():
        for index in indices:
            code[index]["arg"] = functions[name]["addr"]
    return code

# print(translate("(+ 10 (if (= (+ 2 3) 5) 7 9))"))
# print(translate("(div 2 (+ 5 3))"))
# print(to_bytes(translate("(+ 2 (+ 3 4))")))


def main(source, target):
    """Функция запуска транслятора. Параметры -- исходный и целевой файлы."""
    with open(source, encoding="utf-8") as f:
        source = f.read()

    code = translate(source)
    global halt_addr
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