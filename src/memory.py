class Memory:
    def __init__(self):
        self.memory = {}
        self.max_address = (1 << 64) - 1

    def write_byte(self, addr, value):
        """写入一个字节"""
        if not (0 <= addr <= self.max_address):
            raise MemoryError(f"Invalid memory address: {addr}")
        if value != 0:  # 只存储非零值
            self.memory[addr] = value & 0xFF

    def read_byte(self, addr):
        """读取一个字节"""
        if not (0 <= addr <= self.max_address):
            raise MemoryError(f"Invalid memory address: {addr}")
        return self.memory.get(addr, 0)

    def write_quad(self, addr, value):
        """写入八字节"""
        for i in range(8):
            byte_val = (value >> (i * 8)) & 0xFF
            if byte_val != 0:  # 只存储非零值
                self.write_byte(addr + i, byte_val)

    def read_quad(self, addr):
        """读取八字节"""
        value = 0
        for i in range(8):
            value |= self.read_byte(addr + i) << (i * 8)
        return value

    def get_nonzero_memory(self):
        """获取所有非零内存值，并按地址排序"""
        return dict(sorted(
            ((addr, value) for addr, value in self.memory.items() if value != 0),
            key=lambda x: x[0]
        ))

    def clear(self):
        """清空内存"""
        self.memory.clear()

    def dump_memory(self):
        """返回内存内容的格式化字符串"""
        memory_dump = []
        for addr, value in sorted(self.memory.items()):
            memory_dump.append(f"0x{addr:04x}: 0x{value:02x}")
        return "\n".join(memory_dump)