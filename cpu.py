import sys
import yaml

from app import format_memory_dump
from src.cpu import Y86CPU
from src.utils import parse_yo_file, Y86Error


def main(input_file, output_file):
    """处理命令行输入并执行Y86程序"""
    try:
        # 从文件读取.yo文件内容
        with open(input_file, 'r') as file:
            content = file.read()

        # 初始化CPU和解析程序
        cpu = Y86CPU()
        program = parse_yo_file(content)

        if not program:
            raise Y86Error("No valid program found in input")

        # 加载并执行程序
        cpu.load_program(program)
        final_state = None

        while cpu.status == 'AOK':
            success = cpu.step()
            if not success:
                final_state = cpu.get_state()
                break

        # 生成YAML格式输出
        if final_state:
            output_data = [{
                'PC': int(final_state.get('pc', 0)),
                'REG': {
                    reg: int(val) for reg, val in final_state.get('registers', {}).items()
                },
                'CC': {
                    'ZF': int(final_state.get('flags', {}).get('ZF', 0)),
                    'SF': int(final_state.get('flags', {}).get('SF', 0)),
                    'OF': int(final_state.get('flags', {}).get('OF', 0))
                },
                'MEM': format_memory_dump(final_state.get('memory', {})),
                'STAT': 1 if final_state.get('status') == 'HLT' else 2
            }]

            # 使用yaml库输出到文件
            with open(output_file, 'w') as file:
                yaml.dump(output_data, file, default_flow_style=False, sort_keys=False)

    except Exception as e:
        # print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    if len(sys.argv) != 3:
        # print("Usage: python cpu.py <input_file> <output_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]
    main(input_file, output_file)