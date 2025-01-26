import os
import yaml
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from src.cpu import Y86CPU
from src.utils import parse_yo_file, Y86Error
import time

app = Flask(__name__)

# 配置文件上传
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'yo'}
# 确保上传文件夹存在
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# 添加输出目录配置
OUTPUT_FOLDER = 'output'
if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)



app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 限制文件大小为16MB


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def generate_yaml_output(filename, state):
    """生成YAML格式的输出文件，所有数值使用十进制格式"""
    try:
        if not filename or not isinstance(filename, str):
            filename = "output"
        safe_filename = "".join(c for c in filename if c.isalnum() or c in ('-', '_')) or "output"

        # 确保所有值都转换为整数
        registers = {
            'rax': int(state.get('registers', {}).get('rax', 0)),
            'rcx': int(state.get('registers', {}).get('rcx', 0)),
            'rdx': int(state.get('registers', {}).get('rdx', 0)),
            'rbx': int(state.get('registers', {}).get('rbx', 0)),
            'rsp': int(state.get('registers', {}).get('rsp', 0)),
            'rbp': int(state.get('registers', {}).get('rbp', 0)),
            'rsi': int(state.get('registers', {}).get('rsi', 0)),
            'rdi': int(state.get('registers', {}).get('rdi', 0)),
            'r8': int(state.get('registers', {}).get('r8', 0)),
            'r9': int(state.get('registers', {}).get('r9', 0)),
            'r10': int(state.get('registers', {}).get('r10', 0)),
            'r11': int(state.get('registers', {}).get('r11', 0)),
            'r12': int(state.get('registers', {}).get('r12', 0)),
            'r13': int(state.get('registers', {}).get('r13', 0)),
            'r14': int(state.get('registers', {}).get('r14', 0))
        }

        # 构建输出数据
        output_data = [{
            'PC': int(state.get('pc', 0)),
            'REG': registers,
            'CC': {
                'ZF': int(state.get('flags', {}).get('ZF', 0)),
                'SF': int(state.get('flags', {}).get('SF', 0)),
                'OF': int(state.get('flags', {}).get('OF', 0))
            },
            'MEM': format_memory_dump(state.get('memory', {})),
            'STAT': 1 if state.get('status') == 'HLT' else 2
        }]

        # 使用特定的YAML格式化选项
        class NoAliasDumper(yaml.SafeDumper):
            def ignore_aliases(self, data):
                return True

        output_path = os.path.join(OUTPUT_FOLDER, f"{safe_filename}.yml")

        # 使用自定义的表示样式
        def represent_int(dumper, data):
            return dumper.represent_scalar('tag:yaml.org,2002:int', str(data))

        NoAliasDumper.add_representer(int, represent_int)

        # 写入文件时使用自定义的dumper
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(output_data, f,
                      Dumper=NoAliasDumper,
                      default_flow_style=False,
                      sort_keys=False,
                      width=float("inf"))  # 防止长行被折断

        return output_path

    except Exception as e:
        # print(f"Error generating output file: {str(e)}")
        raise Y86Error(f"Failed to generate output file: {str(e)}")

def format_memory_dump(memory):
    """
    格式化内存转储:
    - 按8字节对齐
    - 使用小端法解释为十进制有符号整数
    - 只保留非零值
    """
    non_zero_memory = {}
    if not memory:
        return non_zero_memory

    # 获取所有地址并按8字节对齐
    all_addresses = set(memory.keys())
    aligned_addresses = set(addr - (addr % 8) for addr in all_addresses)

    for base_addr in sorted(aligned_addresses):
        # 使用小端法读取8字节
        value = 0
        bytes_present = False
        for i in range(8):
            curr_addr = base_addr + i
            if curr_addr in memory:
                bytes_present = True
                value |= (memory[curr_addr] & 0xFF) << (i * 8)

        # 只在实际有字节的地址处保存值
        if bytes_present:
            # 转换为有符号整数（64位）
            if value & (1 << 63):  # 如果最高位为1（负数）
                value = -(((~value) + 1) & ((1 << 64) - 1))
            non_zero_memory[base_addr] = value

    return non_zero_memory

class CPUSimulator:
    def __init__(self):
        self.cpu = Y86CPU()
        self.instruction_count = 0
        self.execution_time = 0
        self.instruction_log = []

    def reset(self):
        """重置模拟器状态"""
        self.cpu.reset()
        self.instruction_count = 0
        self.execution_time = 0
        self.instruction_log = []

    def load_program(self, program):
        """加载程序到CPU"""
        try:
            # 重置模拟器
            self.reset()

            if not program:
                raise Y86Error("Empty program")

            # 找到程序的最小起始地址
            min_addr = min(program.keys())

            # 打印程序加载信息
            # print(f"\nLoading program:")
            # print(f"Start address: 0x{min_addr:x}")
            # print("Program content:")
            # for addr in sorted(program.keys()):
            #     print(f"0x{addr:03x}: {program[addr]:02x}")

            # 设置PC并加载程序
            self.cpu.pc = min_addr  # 确保PC设置为程序的起始地址
            success = self.cpu.load_program(program)

            if success:
                # 确保初始状态被正确记录
                initial_state = self.cpu.get_state()
                self.instruction_log = [initial_state]  # 重置指令日志
                # print(f"\nProgram loaded successfully")
                # print(f"Initial PC: 0x{self.cpu.pc:x}")
                # print(f"Initial state: {initial_state}")
                return True
            else:
                raise Y86Error("Failed to load program")

        except Exception as e:
            raise Y86Error(f"Failed to load program: {str(e)}")

    def step(self):
        """执行单个指令步骤"""
        try:
            start_time = time.time()
            success = self.cpu.step()
            self.execution_time += time.time() - start_time

            if success:
                self.instruction_count += 1
                current_state = self.cpu.get_state()
                self.instruction_log.append(current_state)

                # 添加调试信息
                # print(f"Step executed successfully:")
                # print(f"PC: 0x{current_state['pc']:x}")
                # print(f"Registers: {current_state['registers']}")
                # print(f"Status: {current_state['status']}")

                return success, current_state
            return False, self.cpu.get_state()
        except Exception as e:
            # print(f"Error during step execution: {str(e)}")
            return False, self.cpu.get_state()

    def get_statistics(self):
        return {
            'instruction_count': self.instruction_count,
            'execution_time': self.execution_time,
            'status': self.cpu.status
        }

    def run_and_generate_output(self, filename):
        """运行程序并生成输出文件"""
        try:
            states = []
            initial_state = self.cpu.get_state()
            states.append(initial_state)
            # print(f"\nStarting execution:")
            # print(f"Initial PC: 0x{initial_state['pc']:x}")

            step_count = 0
            while step_count < 10000:  # 防止无限循环
                # print(f"\nStep {step_count + 1}:")
                # print(f"Current PC: 0x{self.cpu.pc:x}")

                success, state = self.step()
                states.append(state)

                # print(f"Instruction executed at 0x{state['pc']:x}")
                # print(f"Status: {state['status']}")
                # print(f"Registers: {state['registers']}")

                if not success:
                    if state['status'] == 'HLT':
                        # print(f"\nProgram halted normally")
                        # print(f"Final state: {state}")
                        output_path = generate_yaml_output(filename, state)
                        # print(f"Generated output file: {output_path}")
                        return states
                    else:
                        raise Y86Error(f"Program failed: {state['status']}")

                step_count += 1

            raise Y86Error("Program exceeded maximum step count")

        except Exception as e:
            # print(f"Error in run_and_generate_output: {str(e)}")
            raise


simulator = CPUSimulator()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/docs')
def docs():
    return render_template('docs.html')


@app.route('/api/upload', methods=['POST'])
def upload_program():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400

        filename = secure_filename(file.filename)
        base_filename = os.path.splitext(filename)[0]

        # 保存文件到 uploads 文件夹
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        # print(f"File saved to: {file_path}")

        # 读取保存的文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        program = parse_yo_file(content)
        # print(f"Processing file: {filename}")

        program = parse_yo_file(content)

        if not program:
            return jsonify({'error': 'No valid instructions found in file'}), 400

        # print(f"Program loaded with addresses: {sorted(program.keys())}")

        if not simulator.load_program(program):
            return jsonify({'error': 'Failed to load program into simulator'}), 400

        try:
            states = simulator.run_and_generate_output(base_filename)
            # 确保states不为None且包含必要的数据
            if not states or not all('pc' in state for state in states):
                return jsonify({'error': 'Invalid program state generated'}), 400

            output_file = f"{base_filename}.yml"
            output_path = os.path.join(OUTPUT_FOLDER, output_file)

            if os.path.exists(output_path):
                # print(f"Output file successfully generated at: {output_path}")
                # 添加状态验证的日志
                # print(f"Number of states: {len(states)}")
                # print(f"First state PC: {states[0].get('pc', 'missing')}")

                return jsonify({
                    'message': 'Program executed and output generated successfully',
                    'states': states,
                    'statistics': simulator.get_statistics(),
                    'output_file': output_file
                })
            else:
                return jsonify({'error': 'Failed to generate output file'}), 500

        except Y86Error as e:
            # print(f"Y86Error: {str(e)}")
            return jsonify({'error': str(e)}), 400

    except Exception as e:
        # print(f"Unexpected error: {str(e)}")
        return jsonify({'error': f'Error: {str(e)}'}), 400


@app.route('/api/step', methods=['POST'])
def step():
    try:
        before_state = simulator.cpu.get_state()
        success = simulator.step()
        after_state = simulator.cpu.get_state()

        # print(f"\nStep execution:")
        # print(f"Before state: {before_state}")
        # print(f"After state: {after_state}")

        return jsonify({
            'success': success,
            'state': after_state,
            'statistics': simulator.get_statistics(),
            'debug_info': {
                'pc': hex(simulator.cpu.pc),
                'instruction': simulator.cpu.curr_inst,
                'status': simulator.cpu.status
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/run', methods=['POST'])
def run():
    try:
        states = []
        while True:
            success, state = simulator.step()
            states.append(state)
            if not success:
                break

        return jsonify({
            'states': states,
            'statistics': simulator.get_statistics()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/reset', methods=['POST'])
def reset():
    simulator.reset()
    return jsonify({'message': 'Simulator reset successfully'})


if __name__ == '__main__':
    app.run(debug=True)