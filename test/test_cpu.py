# test/test_cpu.py

import unittest
from src.cpu import Y86CPU
from src.utils import Y86Error


class TestY86CPU(unittest.TestCase):
    def setUp(self):
        self.cpu = Y86CPU()

    def test_arithmetic(self):
        """测试算术运算"""
        # 测试加法
        self.cpu.registers['rax'] = 5
        self.cpu.registers['rbx'] = 3
        self.cpu.curr_inst = {
            'icode': 0x6,
            'ifun': 0,  # addq
            'rA': 0,  # rax
            'rB': 3,  # rbx
            'valP': 0
        }
        self.cpu.execute()
        self.assertEqual(self.cpu.registers['rbx'], 8)
        self.assertEqual(self.cpu.flags['ZF'], 0)

        # 测试减法
        self.cpu.registers['rax'] = 3
        self.cpu.registers['rbx'] = 3
        self.cpu.curr_inst['ifun'] = 1  # subq
        self.cpu.execute()
        self.assertEqual(self.cpu.registers['rbx'], 0)
        self.assertEqual(self.cpu.flags['ZF'], 1)

    def test_memory_operations(self):
        """测试内存操作"""
        # 测试rmmovq
        self.cpu.registers['rax'] = 0x12345678
        self.cpu.registers['rbx'] = 0x100
        self.cpu.curr_inst = {
            'icode': 0x4,  # rmmovq
            'ifun': 0,  # 添加ifun字段
            'rA': 0,  # rax
            'rB': 3,  # rbx
            'valC': 0,
            'valP': 0
        }
        self.cpu.execute()
        value = self.cpu.memory.read_quad(0x100)
        self.assertEqual(value, 0x12345678)

    def test_jumps(self):
        """测试跳转指令"""
        # 测试无条件跳转
        self.cpu.curr_inst = {
            'icode': 0x7,
            'ifun': 0,  # jmp
            'valC': 0x200,
            'valP': 0x100
        }
        self.cpu.execute()
        self.assertEqual(self.cpu.curr_inst['valP'], 0x200)

        # 测试条件跳转
        self.cpu.flags['ZF'] = 1
        self.cpu.curr_inst['ifun'] = 3  # je
        self.cpu.curr_inst['valC'] = 0x300
        self.cpu.execute()
        self.assertEqual(self.cpu.curr_inst['valP'], 0x300)

    def test_call_return(self):
        """测试调用和返回指令"""
        # 测试call
        self.cpu.registers['rsp'] = 0x1000
        self.cpu.curr_inst = {
            'icode': 0x8,  # call
            'ifun': 0,     # 添加ifun字段
            'valC': 0x200,
            'valP': 0x100
        }
        self.cpu.execute()
        self.assertEqual(self.cpu.curr_inst['valP'], 0x200)
        self.assertEqual(self.cpu.registers['rsp'], 0xFF8)
        ret_addr = self.cpu.memory.read_quad(0xFF8)
        self.assertEqual(ret_addr, 0x100)

        # 测试ret
        self.cpu.curr_inst = {
            'icode': 0x9,  # ret
            'ifun': 0,     # 添加ifun字段
            'valP': 0      # 添加valP字段
        }
        self.cpu.execute()
        self.assertEqual(self.cpu.curr_inst['valP'], 0x100)
        self.assertEqual(self.cpu.registers['rsp'], 0x1000)


def run_tests():
    unittest.main()


if __name__ == '__main__':
    run_tests()