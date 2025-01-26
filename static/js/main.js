// 全局状态管理
let currentState = null;
let instructionHistory = [];

// DOM 元素缓存
const elements = {
    uploadForm: document.getElementById('uploadForm'),
    fileInput: document.getElementById('fileInput'),
    uploadStatus: document.getElementById('uploadStatus'),
    currentFile: document.getElementById('currentFile'),
    registers: document.getElementById('registers'),
    memory: document.getElementById('memory'),
    instructionLog: document.getElementById('instructionLog'),
    statistics: document.getElementById('statistics'),
    stepBtn: document.getElementById('stepBtn'),
    runBtn: document.getElementById('runBtn'),
    resetBtn: document.getElementById('resetBtn'),
    messageArea: document.getElementById('messageArea')
};

// 格式化十六进制数字
function formatHex(num, padLength = 2) {
    return `0x${BigInt(num).toString(16).padStart(padLength, '0')}`;
}


// 更新寄存器显示
function updateRegisters(registers) {
    if (!registers) return;

    const registerOrder = [
        'rax', 'rcx', 'rdx', 'rbx',
        'rsp', 'rbp', 'rsi', 'rdi',
        'r8', 'r9', 'r10', 'r11',
        'r12', 'r13', 'r14'
    ];

    elements.registers.innerHTML = registerOrder
        .map(reg => `
            <div class="register-row ${registers[reg] !== 0 ? 'highlight' : ''}">
                <span class="reg-name">${reg}</span>
                <span class="reg-value">${formatHex(registers[reg], 16)}</span>
            </div>
        `)
        .join('');
}



// 更新内存显示
function updateMemory(memory) {
    if (!memory) return;

    const sortedAddresses = Object.keys(memory).sort((a, b) => Number(a) - Number(b));

    elements.memory.innerHTML = sortedAddresses
        .map(addr => `
            <div class="memory-row">
                <span class="mem-addr">${formatHex(addr, 4)}</span>
                <span class="mem-value">${formatHex(memory[addr], 2)}</span>
            </div>
        `)
        .join('') || '<div class="no-data">No non-zero memory values</div>';
}

// 添加指令执行日志
function addInstructionLog(state) {
    const logEntry = document.createElement('div');
    logEntry.className = 'instruction-log-entry';

    const instruction = state.current_instruction || {};

    logEntry.innerHTML = `
        <div class="log-header">
            <span class="pc">PC: ${formatHex(state.pc, 4)}</span>
            <span class="status">Status: ${state.status}</span>
        </div>
        <div class="log-details">
            <span>icode: ${instruction.icode || 'N/A'}</span>
            <span>ifun: ${instruction.ifun || 'N/A'}</span>
        </div>
    `;

    elements.instructionLog.appendChild(logEntry);
    elements.instructionLog.scrollTop = elements.instructionLog.scrollHeight;
}

// 文件上传处理
elements.uploadForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const file = elements.fileInput.files[0];
    if (!file || !file.name.endsWith('.yo')) {
        showMessage('error', 'Please select a valid .yo file');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
        elements.uploadStatus.textContent = 'Uploading...';

        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (!response.ok) throw new Error(data.error || 'Upload failed');

        elements.currentFile.textContent = file.name;
        updateUI(data.states[0]);
        enableControls(true);
        showMessage('success', 'File uploaded successfully');

    } catch (error) {
        showMessage('error', error.message);
    } finally {
        elements.uploadStatus.textContent = '';
    }
});

// 更新状态统计
function updateStatistics(stats) {
    if (!stats) return;

    if (elements.instructionCount) {
        elements.instructionCount.textContent = stats.instruction_count;
    }
    if (elements.executionTime) {
        elements.executionTime.textContent = (stats.execution_time * 1000).toFixed(2);
    }
    if (elements.cpuStatus) {
        elements.cpuStatus.textContent = stats.status;
    }
}

// 更新UI的主函数
// 更新UI的主函数
function updateUI(state) {
    if (!state) {
        console.warn('Attempted to update UI with null state');
        return;
    }

    // 更新寄存器显示
    if (state.registers) {
        updateRegisters(state.registers);
    }

    // 更新内存显示
    if (state.memory) {
        updateMemory(state.memory);
    }



    // 更新CPU状态
    if (elements.cpuStatus && state.status) {
        elements.cpuStatus.textContent = state.status;
    }

    // 保存当前状态
    currentState = state;
}

// 添加到指令日志
function addToLog(state) {
    if (!elements.instructionLog || !state) return;

    const logEntry = document.createElement('div');
    logEntry.className = 'log-entry';
    logEntry.innerHTML = `
        <div class="log-header">
            <strong>PC: ${state.pc ? formatHex(state.pc, 4) : 'N/A'}</strong>
            <span class="status">Status: ${state.status || 'Unknown'}</span>
        </div>
        <div class="log-registers">
            ${state.registers ? Object.entries(state.registers)
                .filter(([_, value]) => value !== 0)
                .map(([reg, value]) => `
                    <span class="log-register">${reg}: ${formatHex(value, 16)}</span>
                `).join(' ') : ''}
        </div>
        <div class="log-memory">
            ${state.memory ? Object.entries(state.memory)
                .map(([addr, value]) => `
                    <span class="log-memory-entry">${formatHex(parseInt(addr), 4)}: ${formatHex(value, 2)}</span>
                `).join(' ') : ''}
        </div>
    `;

    elements.instructionLog.appendChild(logEntry);
    elements.instructionLog.scrollTop = elements.instructionLog.scrollHeight;
}

// 单步执行处理
elements.stepBtn.addEventListener('click', async () => {
    try {
        const response = await fetch('/api/step', {
            method: 'POST'
        });

        const data = await response.json();

        if (response.ok) {
            updateUI(data.state);
            updateStatistics(data.statistics);
            addToLog(data.state);

            if (data.state.status !== 'AOK') {
                showMessage('info', `Program ${data.state.status}`);
                enableControls(false);
            }
        } else {
            throw new Error(data.error);
        }
    } catch (error) {
        showMessage('error', error.message);
    }
});

// 连续执行处理
elements.runBtn.addEventListener('click', async () => {
    try {
        const response = await fetch('/api/run', {
            method: 'POST'
        });

        const data = await response.json();

        if (response.ok) {
            data.states.forEach(state => {
                updateUI(state);
                addToLog(state);
            });
            updateStatistics(data.statistics);

            if (data.states[data.states.length - 1].status !== 'AOK') {
                showMessage('info', `Program ${data.states[data.states.length - 1].status}`);
                enableControls(false);
            }
        } else {
            throw new Error(data.error);
        }
    } catch (error) {
        showMessage('error', error.message);
    }
});

// 重置处理
elements.resetBtn.addEventListener('click', async () => {
    try {
        const response = await fetch('/api/reset', {
            method: 'POST'
        });

        if (response.ok) {
            // 清空日志
            elements.instructionLog.innerHTML = '';

            // 重置文件显示
            elements.currentFile.textContent = 'No file loaded';

            // 更新UI为初始状态
            updateUI({
                registers: {},
                memory: {},
                status: 'AOK',
                pc: 0
            });

            // 更新统计信息
            updateStatistics({
                instruction_count: 0,
                execution_time: 0,
                status: 'AOK'
            });

            // 禁用控制按钮
            enableControls(false);

            showMessage('success', 'Simulator reset successfully');
        } else {
            throw new Error('Failed to reset simulator');
        }
    } catch (error) {
        showMessage('error', error.message);
    }
});

// 显示消息
function showMessage(type, message) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type === 'error' ? 'danger' : 'success'} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    elements.messageArea.appendChild(alertDiv);

    // 3秒后自动消失
    setTimeout(() => {
        alertDiv.remove();
    }, 3000);
}

// 启用/禁用控制按钮
function enableControls(enabled) {
    elements.stepBtn.disabled = !enabled;
    elements.runBtn.disabled = !enabled;
    elements.resetBtn.disabled = !enabled;
}