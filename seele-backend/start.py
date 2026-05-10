#!/usr/bin/env python3
import os
import subprocess
import sys
import time


def is_port_in_use(port, host='127.0.0.1'):
    """检查端口是否被占用"""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) == 0


def get_pids_on_port(port):
    """获取占用指定端口的所有进程 PID 列表（仅 Listen 状态）"""
    cmd = [
        'powershell', '-NoProfile', '-Command',
        f'Try {{ '
        f'  $conns = Get-NetTCPConnection -LocalPort {port} -State Listen -ErrorAction Stop; '
        f'  $conns | ForEach-Object {{ $_.OwningProcess }} | Select-Object -Unique '
        f'}} Catch {{ }}'
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        pids = []
        for line in result.stdout.strip().split('\n'):
            line = line.strip()
            if line.isdigit():
                pids.append(int(line))
        return pids
    except Exception:
        return []


def kill_process_on_port(port, max_wait=5):
    """强制关闭占用指定端口的所有进程，并等待端口释放"""
    if not is_port_in_use(port):
        return

    current_pid = os.getpid()
    pids = get_pids_on_port(port)
    killed = []

    for pid in pids:
        if pid == current_pid:
            continue
        subprocess.run(['taskkill', '/PID', str(pid), '/F'],
                       capture_output=True)
        killed.append(pid)
        print(f'[cleanup] Killed PID {pid} occupying port {port}')

    # 等待端口释放，最多等待 max_wait 秒
    for i in range(max_wait):
        if not is_port_in_use(port):
            if killed:
                print(f'[cleanup] Port {port} is now free (killed: {killed})')
            return
        time.sleep(1)

    if is_port_in_use(port):
        print(f'[cleanup] WARNING: Port {port} is still in use after cleanup')


if __name__ == '__main__':
    kill_process_on_port(9000)
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    subprocess.run([
        sys.executable, '-m', 'uvicorn',
        'app.main:app',
        '--reload',
        '--port', '9000',
        '--app-dir', BASE_DIR,
        '--reload-dir', BASE_DIR
    ])
