# src/utils.py

class Y86Error(Exception):
    """Y86 CPU错误基类"""
    pass

class MemoryError(Y86Error):
    """内存访问错误"""
    pass

class InvalidInstructionError(Y86Error):
    """无效指令错误"""
    pass


def parse_yo_file(content):
    """解析.yo文件内容"""
    memory = {}
    try:
        for line in content.splitlines():
            # 跳过空行、注释行和不包含':'的行
            line = line.strip()
            if not line or not ':' in line:
                continue

            # 分离地址和指令部分
            parts = line.split('|')[0].strip()
            if not parts:
                continue

            # 分离地址和指令码
            addr_str, instr = parts.split(':', 1)
            if not addr_str or not instr.strip():
                continue

            # 解析地址（去掉0x前缀）
            addr = int(addr_str.replace('0x', ''), 16)

            # 解析指令码（移除所有空格）
            instr = instr.strip().replace(' ', '')

            # 每两个字符转换为一个字节
            for i in range(0, len(instr), 2):
                if i + 2 <= len(instr):
                    byte = int(instr[i:i + 2], 16)
                    memory[addr + (i // 2)] = byte

        # 打印调试信息
        # print("\nParsed memory content:")
        # for addr in sorted(memory.keys()):
        #     print(f"0x{addr:03x}: {memory[addr]:02x}")

        return memory

    except Exception as e:
        # print(f"Error parsing .yo file: {str(e)}")
        return {}


def format_hex(num):
    """将数字格式化为十六进制字符串"""
    return f"0x{num:02x}"

