# from typing import Dict, List, Tuple, Union
from .memory import Memory
from .utils import Y86Error, MemoryError, InvalidInstructionError

# import logging
#
# # 配置logging
# logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class Y86CPU:
    def __init__(self):
        # 初始化寄存器
        self.registers = {
            'rax': 0, 'rcx': 0, 'rdx': 0, 'rbx': 0,
            'rsp': 0, 'rbp': 0, 'rsi': 0, 'rdi': 0,
            'r8': 0, 'r9': 0, 'r10': 0, 'r11': 0,
            'r12': 0, 'r13': 0, 'r14': 0
        }

        # 寄存器编号映射
        self.reg_map = {
            0: 'rax', 1: 'rcx', 2: 'rdx', 3: 'rbx',
            4: 'rsp', 5: 'rbp', 6: 'rsi', 7: 'rdi',
            8: 'r8', 9: 'r9', 10: 'r10', 11: 'r11',
            12: 'r12', 13: 'r13', 14: 'r14'
        }

        # 状态标志
        self.flags = {'ZF': 0, 'SF': 0, 'OF': 0}

        # CPU状态
        self.status = 'AOK'
        self.pc = 0

        # 内存管理器
        self.memory = Memory()

        # 当前指令信息
        self.curr_inst = {
            'icode': 0,
            'ifun': 0,
            'rA': 0,
            'rB': 0,
            'valC': 0,
            'valP': 0
        }

    def load_program(self, program):
        """加载程序到内存"""
        try:
            # 重置CPU状态
            self.reset()

            if not program:
                raise Y86Error("Empty program")

            # 找到程序的最小起始地址
            min_addr = min(program.keys())

            # 将程序加载到内存
            for addr, value in program.items():
                # print(f"Loading byte: addr=0x{addr:x}, value=0x{value:02x}")  # Debug print
                self.memory.write_byte(addr, value)

            # 设置PC为程序的起始地址
            self.pc = min_addr
            # print(f"Setting initial PC to: 0x{self.pc:x}")  # Debug print

            # 获取初始状态
            initial_state = self.get_state()
            # print(f"Initial CPU state: {initial_state}")  # Debug print

            return True

        except Exception as e:
            raise Y86Error(f"Failed to load program: {str(e)}")

    def reset(self):
        """重置CPU状态"""
        # 保存当前PC值
        current_pc = self.pc

        # 重置寄存器
        for reg in self.registers:
            self.registers[reg] = 0

        # 重置标志位
        self.flags = {'ZF': 0, 'SF': 0, 'OF': 0}

        # 重置状态（但保持PC不变）
        self.status = 'AOK'

        # 清空内存
        self.memory = Memory()

        # 重置当前指令信息
        self.curr_inst = {
            'icode': 0,
            'ifun': 0,
            'rA': 0,
            'rB': 0,
            'valC': 0,
            'valP': 0
        }

        # 恢复PC值
        self.pc = current_pc

    def fetch(self):
        """取指阶段"""
        try:
            # 读取指令的第一个字节
            byte1 = self.memory.read_byte(self.pc)
            self.curr_inst['icode'] = byte1 >> 4  # 高4位为指令码
            self.curr_inst['ifun'] = byte1 & 0xF  # 低4位为功能码

            next_pc = self.pc + 1

            # 根据不同指令获取额外字节
            if self.curr_inst['icode'] in [0x2, 0x3, 0x4, 0x5, 0x6]:  # 需要寄存器字节
                regbyte = self.memory.read_byte(next_pc)
                self.curr_inst['rA'] = regbyte >> 4
                self.curr_inst['rB'] = regbyte & 0xF
                next_pc += 1

            if self.curr_inst['icode'] in [0x3, 0x4, 0x5]:  # 需要常数字节
                # 使用小端序读取8字节常数
                bytes_list = []
                for i in range(8):
                    bytes_list.append(self.memory.read_byte(next_pc + i))

                # 将字节列表转换为整数值
                value = int.from_bytes(bytes_list, byteorder='little', signed=True)
                self.curr_inst['valC'] = value
                next_pc += 8

            self.curr_inst['valP'] = next_pc

            # print(f"\nFetch Debug Info:")
            # print(f"PC: 0x{self.pc:x}")
            # print(f"Instruction: icode={hex(self.curr_inst['icode'])}, ifun={hex(self.curr_inst['ifun'])}")
            # print(f"rA: {self.curr_inst.get('rA', 'N/A')}")
            # print(f"rB: {self.curr_inst.get('rB', 'N/A')}")
            # print(f"valC: {hex(self.curr_inst.get('valC', 0))}")
            # print(f"Raw bytes: {[hex(b) for b in bytes_list] if 'bytes_list' in locals() else 'N/A'}")
            # print(f"Next PC: 0x{next_pc:x}")

            return True

        except Exception as e:
            # print(f"Fetch error: {str(e)}")
            self.status = 'HLT'
            return False


    def execute(self):
        """执行阶段"""
        try:
            icode = self.curr_inst['icode']

            # print(f"Executing instruction with icode: {hex(icode)}")  # 调试输出

            if icode == 0x0:  # halt
                self.status = 'HLT'

            elif icode == 0x1:  # nop
                pass

            elif icode == 0x2:  # rrmovq/cmovXX
                self.execute_move()

            elif icode == 0x3:  # irmovq
                self.execute_immediate_move()

            elif icode == 0x4:  # rmmovq
                self.execute_memory_store()

            elif icode == 0x5:  # mrmovq
                self.execute_memory_load()

            elif icode == 0x6:  # OPq
                self.execute_operation()

            elif icode == 0x7:  # jXX
                self.execute_jump()

            elif icode == 0x8:  # call
                self.execute_call()

            elif icode == 0x9:  # ret
                self.execute_return()

            elif icode == 0xA:  # pushq
                self.execute_push()

            elif icode == 0xB:  # popq
                self.execute_pop()

            else:
                raise InvalidInstructionError(f"Invalid instruction code: {icode}")

        except Exception as e:
            self.status = 'INS'
            raise Y86Error(f"Execute error: {str(e)}")
    def execute_move(self):
        """执行移动指令"""
        rA = self.reg_map[self.curr_inst['rA']]
        rB = self.reg_map[self.curr_inst['rB']]
        ifun = self.curr_inst['ifun']

        should_move = False
        if ifun == 0:  # 无条件移动
            should_move = True
        elif ifun == 1:  # le
            should_move = (self.flags['SF'] ^ self.flags['OF']) | self.flags['ZF']
        elif ifun == 2:  # l
            should_move = self.flags['SF'] ^ self.flags['OF']
        elif ifun == 3:  # e
            should_move = self.flags['ZF']
        elif ifun == 4:  # ne
            should_move = not self.flags['ZF']
        elif ifun == 5:  # ge
            should_move = not (self.flags['SF'] ^ self.flags['OF'])
        elif ifun == 6:  # g
            should_move = not (self.flags['SF'] ^ self.flags['OF']) and not self.flags['ZF']

        if should_move:
            self.registers[rB] = self.registers[rA]

    def execute_operation(self):
        """执行算术运算"""
        rA = self.reg_map[self.curr_inst['rA']]
        rB = self.reg_map[self.curr_inst['rB']]
        ifun = self.curr_inst['ifun']

        valA = self.registers[rA]
        valB = self.registers[rB]

        # print(f"Debug - operation:")
        # print(f"  Operation type: {'addq' if ifun == 0 else 'subq'}")
        # print(f"  Register A ({rA}): {valA}")
        # print(f"  Register B ({rB}): {valB}")

        try:
            if ifun == 0:  # addq
                result = valB + valA
            elif ifun == 1:  # subq
                result = valB - valA

            # print(f"  Result before masking: {result}")

            result = result & ((1 << 64) - 1)
            self.registers[rB] = result

            # print(f"  Final result: {result}")
            # print(f"  Updated register {rB}: {self.registers[rB]}")

        except Exception as e:
            raise Y86Error(f"Operation error: {str(e)}")

    def step(self):
        """执行一个指令周期"""
        try:
            if self.fetch():
                self.execute()
                self.pc = self.curr_inst['valP']
                return self.status == 'AOK'
            return False

        except Exception as e:
            # print(f"Step error: {str(e)}")  # 调试输出
            return False

    def get_state(self):
        """获取CPU当前状态"""
        return {
            'registers': self.registers.copy(),
            'flags': self.flags.copy(),
            'pc': self.pc,
            'status': self.status,
            'memory': self.memory.get_nonzero_memory(),  # 获取非零内存值
            'current_instruction': self.curr_inst.copy()  # 添加当前指令信息
        }

    def execute_jump(self):
        """执行跳转指令"""
        ifun = self.curr_inst['ifun']
        dest = self.curr_inst['valC']

        should_jump = False

        if ifun == 0:  # jmp
            should_jump = True
        elif ifun == 1:  # jle
            should_jump = (self.flags['SF'] ^ self.flags['OF']) | self.flags['ZF']
        elif ifun == 2:  # jl
            should_jump = self.flags['SF'] ^ self.flags['OF']
        elif ifun == 3:  # je
            should_jump = self.flags['ZF']
        elif ifun == 4:  # jne
            should_jump = not self.flags['ZF']
        elif ifun == 5:  # jge
            should_jump = not (self.flags['SF'] ^ self.flags['OF'])
        elif ifun == 6:  # jg
            should_jump = not (self.flags['SF'] ^ self.flags['OF']) and not self.flags['ZF']

        if should_jump:
            self.curr_inst['valP'] = dest

    def execute_immediate_move(self):
        """执行irmovq指令"""
        try:
            rB = self.reg_map[self.curr_inst['rB']]
            value = self.curr_inst['valC']

            # 如果值超过有符号64位整数范围，进行符号扩展
            if value & (1 << 63):
                value = value - (1 << 64)

            # print(f"\nirmovq Debug Info:")
            # print(f"Target register: {rB}")
            # print(f"Raw value (hex): 0x{self.curr_inst['valC']:x}")
            # print(f"Processed value (decimal): {value}")
            # print(f"Register state before: {self.registers[rB]}")

            self.registers[rB] = value

            # print(f"Register state after: {self.registers[rB]}")
            # print(f"All registers after execution: {self.registers}")

        except Exception as e:
            # print(f"irmovq execution error: {str(e)}")
            raise Y86Error(f"irmovq execution error: {str(e)}")


    def execute_memory_load(self):
        """执行内存加载指令"""
        rA = self.reg_map[self.curr_inst['rA']]
        rB = self.reg_map[self.curr_inst['rB']]
        addr = self.registers[rB] + self.curr_inst['valC']
        value = self.memory.read_quad(addr)
        self.registers[rA] = value




    def execute_push(self):
        """执行压栈指令"""
        rA = self.reg_map[self.curr_inst['rA']]
        self.registers['rsp'] -= 8
        self.memory.write_quad(self.registers['rsp'], self.registers[rA])

    def execute_pop(self):
        """执行出栈指令"""
        rA = self.reg_map[self.curr_inst['rA']]
        value = self.memory.read_quad(self.registers['rsp'])
        self.registers[rA] = value
        self.registers['rsp'] += 8

    def execute_memory_store(self):
        """执行内存存储指令"""
        try:
            rA = self.reg_map[self.curr_inst['rA']]
            rB = self.reg_map[self.curr_inst['rB']]
            addr = self.registers[rB] + self.curr_inst.get('valC', 0)
            value = self.registers[rA]
            self.memory.write_quad(addr, value)
        except Exception as e:
            raise Y86Error(f"Memory store error: {str(e)}")

    def execute_call(self):
        """执行调用指令"""
        try:
            # 保存返回地址
            self.registers['rsp'] -= 8
            self.memory.write_quad(self.registers['rsp'], self.curr_inst['valP'])
            # 跳转到目标地址
            self.curr_inst['valP'] = self.curr_inst['valC']
        except Exception as e:
            raise Y86Error(f"Call instruction error: {str(e)}")

    def execute_return(self):
        """执行返回指令"""
        try:
            # 读取返回地址
            ret_addr = self.memory.read_quad(self.registers['rsp'])
            self.registers['rsp'] += 8
            # 跳转到返回地址
            self.curr_inst['valP'] = ret_addr
        except Exception as e:
            raise Y86Error(f"Return instruction error: {str(e)}")