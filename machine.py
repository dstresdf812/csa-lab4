#!/usr/bin/python3
"""Модель процессора, позволяющая выполнить машинный код полученный из программы
на языке Brainfuck.

Модель включает в себя три основных компонента:

- `DataPath` -- работа с памятью данных и вводом-выводом.

- `ControlUnit` -- работа с памятью команд и их интерпретация.

- и набор вспомогательных функций: `simulation`, `main`.
"""

import logging
import sys
from enum import Enum

from isa import Opcode, from_bytes, opcode_to_binary

class State(Enum):
    FETCH = "FETCH"
    T1 = "T1"
    T2 = "T2"
    T3 = "T3"
    STOP = "STOP"
    FAULT = "FAULT"

class DataPath:
    memory_size = None

    memory = None

    data_address = None

    sp = None
    a = None
    b = None
    t = None

    input_buffer = None
    output_buffer = None
    receive_ready = False
    receive_byte = None
    def __init__(self, memory_size, binary_code):
        assert memory_size > 0, "memory size should be non-zero"
        self.memory_size = memory_size
        self.memory = bytearray(memory_size)
        self.memory[:len(binary_code)] = binary_code
        self.data_address = 0
        self.sp = 0x8000
        self.output_buffer = []

    def read_bytes(self, size, addr):
        return self.memory[addr:addr + size]

    def read(self, size, addr, signed=False):
        return int.from_bytes(self.read_bytes(size,addr), byteorder="little", signed=signed)

    def write(self, size, addr, data):
        data_bytes = (data & 0xFFFFFFFF).to_bytes(4, "little")
        self.memory[addr:addr + size] = data_bytes[:size]

    def receive_input(self, byte):
        self.receive_ready = True
        self.receive_byte = byte
class ControlUnit:
    program_counter = None

    data_path = None

    _tick = None

    IR = None

    is_int = False
    SPC = 0
    def __init__(self, data_path):
        self.program_counter = 4
        self.data_path = data_path
        self._tick = 0
        self.state = State.FETCH

    def tick(self):
        self._tick += 1

    def current_tick(self):
        return self._tick

    def process_next_tick(self):
        if self.state == State.STOP or self.state == State.FAULT:
            raise StopIteration()
        if self.state == State.FETCH:
            if self.is_int == 0 and self.data_path.receive_ready:
                self.SPC = self.program_counter
                self.is_int = True
                self.program_counter = self.data_path.read(4,0)
                self.tick()
                return
            instr = self.data_path.read_bytes(4,self.program_counter)
            self.program_counter += 4
            self.IR = instr
            self.next_state()
            self.tick()
            return
        instr = from_bytes(self.IR)[0]
        opcode = instr["opcode"]
        if opcode is Opcode.HALT:
            self.state = State.STOP
            self.tick()
            return

        if opcode is Opcode.PUSHI:
            if self.state == State.T1:
                arg = instr["arg"]
                self.data_path.write(4,self.data_path.sp,arg)
                self.data_path.sp += 4
                self.state = State.FETCH
                self.tick()
                return
            else:
                raise ValueError("illegal state")

        if opcode is Opcode.DROP:
            if self.state == State.T1:
                self.data_path.sp -= 4
                self.state = State.FETCH
                self.tick()
                return
            else:
                raise ValueError("illegal state")

        if opcode is Opcode.LEA:
            if self.state == State.T1:
                arg = instr["arg"]
                off = self.data_path.sp + arg
                self.data_path.write(4, self.data_path.sp, off)
                self.data_path.sp += 4
                self.state = State.FETCH
                self.tick()
                return
            else:
                raise ValueError("illegal state")

        if opcode is Opcode.LDW:
            if self.state == State.T1:
                self.data_path.a = self.data_path.read(4,self.data_path.sp-4)
                self.next_state()
                self.tick()
                return
            if self.state == State.T2:
                self.data_path.t = self.data_path.read(4,self.data_path.a)
                self.next_state()
                self.tick()
                return
            if self.state == State.T3:
                self.data_path.write(4, self.data_path.sp-4, self.data_path.t)
                self.next_state()
                self.tick()
                return

        if opcode is Opcode.LDB:
            if self.state == State.T1:
                self.data_path.a = self.data_path.read(4,self.data_path.sp-4)
                self.next_state()
                self.tick()
                return
            if self.state == State.T2:
                self.data_path.t = self.data_path.read(1,self.data_path.a)
                self.next_state()
                self.tick()
                return
            if self.state == State.T3:
                self.data_path.write(4, self.data_path.sp-4, self.data_path.t)
                self.next_state()
                self.tick()
                return

        if opcode is Opcode.STW:
            if self.state == State.T1:
                self.data_path.a = self.data_path.read(4,self.data_path.sp-4)
                self.next_state()
                self.tick()
                return
            if self.state == State.T2:
                self.data_path.t = self.data_path.read(4,self.data_path.sp-8)
                self.next_state()
                self.tick()
                return
            if self.state == State.T3:
                self.data_path.write(4, self.data_path.a, self.data_path.t)
                self.data_path.sp -= 4
                self.next_state()
                self.tick()
                return

        if opcode is Opcode.STB:
            if self.state == State.T1:
                self.data_path.a = self.data_path.read(4, self.data_path.sp - 4)
                self.next_state()
                self.tick()
                return
            if self.state == State.T2:
                self.data_path.t = self.data_path.read(4, self.data_path.sp - 8)
                self.next_state()
                self.tick()
                return
            if self.state == State.T3:
                self.data_path.write(1, self.data_path.a, self.data_path.t)
                self.data_path.sp -= 4
                self.next_state()
                self.tick()
                return

        if opcode is Opcode.ADD:
            if self.state == State.T1:
                self.data_path.b = self.data_path.read(4, self.data_path.sp-4, True)
                self.next_state()
                self.tick()
                return
            if self.state == State.T2:
                self.data_path.a = self.data_path.read(4, self.data_path.sp - 8, True)
                self.next_state()
                self.tick()
                return
            if self.state == State.T3:
                self.data_path.sp-=4
                self.data_path.write(4, self.data_path.sp-4, (self.data_path.a + self.data_path.b))
                self.next_state()
                self.tick()
                return

        if opcode is Opcode.SUB:
            if self.state == State.T1:
                self.data_path.b = self.data_path.read(4, self.data_path.sp-4, True)
                self.next_state()
                self.tick()
                return
            if self.state == State.T2:
                self.data_path.a = self.data_path.read(4, self.data_path.sp - 8, True)
                self.next_state()
                self.tick()
                return
            if self.state == State.T3:
                self.data_path.sp-=4
                self.data_path.write(4, self.data_path.sp - 4, (self.data_path.a - self.data_path.b))
                self.next_state()
                self.tick()
                return

        if opcode is Opcode.MUL:
            if self.state == State.T1:
                self.data_path.b = self.data_path.read(4, self.data_path.sp-4, True)
                self.next_state()
                self.tick()
                return
            if self.state == State.T2:
                self.data_path.a = self.data_path.read(4, self.data_path.sp - 8, True)
                self.next_state()
                self.tick()
                return
            if self.state == State.T3:
                self.data_path.sp-=4
                self.data_path.write(4, self.data_path.sp - 4, (self.data_path.a * self.data_path.b))
                self.next_state()
                self.tick()
                return

        if opcode is Opcode.DIV:
            if self.state == State.T1:
                self.data_path.b = self.data_path.read(4, self.data_path.sp-4, True)
                self.next_state()
                self.tick()
                return
            if self.state == State.T2:
                self.data_path.a = self.data_path.read(4, self.data_path.sp - 8, True)
                self.next_state()
                self.tick()
                return
            if self.state == State.T3:
                self.data_path.sp-=4
                result = int(self.data_path.a / self.data_path.b) if self.data_path.b != 0 else 0
                self.data_path.write(4, self.data_path.sp-4, result)
                self.next_state()
                self.tick()
                return

        if opcode is Opcode.MOD:
            if self.state == State.T1:
                self.data_path.b = self.data_path.read(4, self.data_path.sp-4, True)
                self.next_state()
                self.tick()
                return
            if self.state == State.T2:
                self.data_path.a = self.data_path.read(4, self.data_path.sp - 8, True)
                self.next_state()
                self.tick()
                return
            if self.state == State.T3:
                self.data_path.sp-=4
                result = self.data_path.a % self.data_path.b if self.data_path.b != 0 else 0
                self.data_path.write(4, self.data_path.sp-4, result)
                self.next_state()
                self.tick()
                return

        if opcode is Opcode.EQ:
            if self.state == State.T1:
                self.data_path.b = self.data_path.read(4, self.data_path.sp-4, True)
                self.next_state()
                self.tick()
                return
            if self.state == State.T2:
                self.data_path.a = self.data_path.read(4, self.data_path.sp - 8, True)
                self.next_state()
                self.tick()
                return
            if self.state == State.T3:
                self.data_path.sp-=4
                self.data_path.write(4, self.data_path.sp - 4, (self.data_path.a == self.data_path.b))
                self.next_state()
                self.tick()
                return

        if opcode is Opcode.SLT:
            if self.state == State.T1:
                self.data_path.b = self.data_path.read(4, self.data_path.sp-4, True)
                self.next_state()
                self.tick()
                return
            if self.state == State.T2:
                self.data_path.a = self.data_path.read(4, self.data_path.sp - 8, True)
                self.next_state()
                self.tick()
                return
            if self.state == State.T3:
                self.data_path.sp-=4
                self.data_path.write(4, self.data_path.sp - 4, (self.data_path.a < self.data_path.b))
                self.next_state()
                self.tick()
                return

        if opcode is Opcode.ULT:
            if self.state == State.T1:
                self.data_path.b = self.data_path.read(4, self.data_path.sp-4, False)
                self.next_state()
                self.tick()
                return
            if self.state == State.T2:
                self.data_path.a = self.data_path.read(4, self.data_path.sp - 8, False)
                self.next_state()
                self.tick()
                return
            if self.state == State.T3:
                self.data_path.sp-=4
                self.data_path.write(4, self.data_path.sp - 4, (self.data_path.a < self.data_path.b))
                self.next_state()
                self.tick()
                return

        if opcode is Opcode.JMP:
            if self.state == State.T1:
                arg = instr["arg"]
                self.program_counter = arg
                self.state = State.FETCH
                self.tick()
                return

        if opcode is Opcode.JZ:
            if self.state == State.T1:
                self.data_path.a = self.data_path.read(4, self.data_path.sp - 4)
                self.data_path.sp -= 4
                self.next_state()
                self.tick()
                return
            if self.state == State.T2:
                if self.data_path.a == 0:
                    arg = instr["arg"]
                    self.program_counter = arg
                self.state = State.FETCH
                self.tick()
                return

        if opcode is Opcode.CALL:
            if self.state == State.T1:
                arg = instr["arg"]
                self.data_path.write(4, self.data_path.sp, self.program_counter)
                self.data_path.sp += 4
                self.program_counter = arg
                self.state = State.FETCH
                self.tick()
                return

        if opcode is Opcode.RET:
            if self.state == State.T1:
                self.data_path.t = self.data_path.read(4, self.data_path.sp - 4)
                self.data_path.sp -= 4
                self.next_state()
                self.tick()
                return
            if self.state == State.T2:
                self.data_path.b = self.data_path.read(4, self.data_path.sp - 4)
                arg = instr["arg"]
                self.data_path.sp += arg
                self.next_state()
                self.tick()
                return
            if self.state == State.T3:
                self.data_path.write(4, self.data_path.sp - 4, self.data_path.t)
                self.program_counter = self.data_path.b
                self.next_state()
                self.tick()
                return

        if opcode is Opcode.IN:
            if self.state == State.T1:
                if self.data_path.receive_ready == 1:
                    self.data_path.t = self.data_path.receive_byte
                    self.data_path.receive_ready = 0
                self.next_state()
                self.tick()
                return
            if self.state == State.T2:
                self.data_path.write(4, self.data_path.sp, self.data_path.t)
                self.data_path.sp += 4
                self.state = State.FETCH
                self.tick()
                return

        if opcode is Opcode.OUT:
            if self.state == State.T1:
                self.data_path.a = self.data_path.read(4, self.data_path.sp - 4)
                self.next_state()
                self.tick()
                return
            if self.state == State.T2:
                byte = self.data_path.a & 0xFF
                self.data_path.output_buffer.append(byte)
                self.state = State.FETCH
                self.tick()
                return

        if opcode is Opcode.IRET:
            if self.state == State.T1:
                self.program_counter = self.SPC
                self.is_int = False
                self.state = State.FETCH
                self.tick()
                return



    def next_state(self):
        if self.state == State.FETCH:
            self.state = State.T1
            return
        elif self.state == State.T1:
            self.state = State.T2
            return
        elif self.state == State.T2:
            self.state = State.T3
            return
        elif self.state == State.T3:
            self.state = State.FETCH
            return

    def __repr__(self):
        """Вернуть строковое представление состояния процессора."""
        state_repr = "TICK: {:3} PC: {:3}/ ADDR: {:3} MEM_OUT: {} SP: {} STATE: {}".format(
            self._tick,
            self.program_counter,
            self.data_path.data_address,
            self.data_path.memory[self.data_path.data_address],
            self.data_path.sp,
            self.state
        )

        if self.IR is None: return state_repr
        instr = from_bytes(self.IR)[0]
        opcode = instr["opcode"]
        instr_repr = str(opcode)

        if "arg" in instr:
            instr_repr += " {}".format(instr["arg"])

        instr_hex = f"{opcode_to_binary[opcode] << 24 | (instr.get('arg', 0) & 0x00FFFFFF):08X}"
        if self.state == State.FETCH or self.state == State.STOP or self.state == State.FAULT:
            instr_repr = ""
            instr_hex = ""
        return "{} \t{:<19} [{}]".format(state_repr, instr_repr, instr_hex)


def simulation(binary_code, input_tokens, memory_size, limit):
    """Подготовка модели и запуск симуляции процессора.

    Длительность моделирования ограничена:

    - количеством выполненных тактов (`limit`);

    - количеством данных ввода (`input_tokens`, если ввод используется), через
      исключение `EOFError`;

    - инструкцией `Halt`, через исключение `StopIteration`.
    """
    data_path = DataPath(memory_size, binary_code)
    control_unit = ControlUnit(data_path)

    logging.debug("%s", control_unit)
    try:
        while control_unit._tick < limit:
            if input_tokens and control_unit._tick == input_tokens[0][0]:
                data_path.receive_input(ord(input_tokens[0][1]))
                input_tokens.pop(0)
            control_unit.process_next_tick()
            logging.debug("%s", control_unit)
    except EOFError:
        logging.warning("Input buffer is empty!")
    except StopIteration:
        pass

    if control_unit._tick >= limit:
        logging.warning("Limit exceeded!")
    logging.info("output_buffer: %s", repr("".join(data_path.output_buffer)))
    return "".join(data_path.output_buffer), control_unit.current_tick()


def main(code_file, input_file):
    """Функция запуска модели процессора. Параметры -- имена файлов с машинным
    кодом и с входными данными для симуляции.
    """
    logging.basicConfig(level=logging.DEBUG, format="%(message)s")
    with open(code_file, "rb") as file:
        binary_code = file.read()

    with open(input_file, encoding="utf-8") as file:
        input_text = file.read()
        input_token = []
        for char in input_text:
            input_token.append(char)

    output, ticks = simulation(
        binary_code,
        input_tokens=input_token,
        memory_size=0x10000,
        limit=2000,
    )

    print("".join(output))
    print("ticks:", ticks)

if __name__ == "__main__":
    logging.getLogger().setLevel(logging.DEBUG)
    assert len(sys.argv) == 3, "Wrong arguments: machine.py <code_file> <input_file>"
    _, code_file, input_file = sys.argv
    main(code_file, input_file)