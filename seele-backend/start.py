#!/usr/bin/env python3
import os
import subprocess
import sys


def kill_process_on_port(port):
    try:
        result = subprocess.run(
            ['powershell', '-Command', f'netstat -ano | findstr :{port}'],
            capture_output=True, text=True
        )
        for line in result.stdout.strip().split('\n'):
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 5 and parts[1].endswith(f':{port}'):
                try:
                    pid = int(parts[-1])
                    if pid != os.getpid():
                        subprocess.run(['taskkill', '/PID', str(pid), '/F'], capture_output=True)
                except ValueError:
                    continue
    except Exception:
        pass


if __name__ == '__main__':
    kill_process_on_port(9000)
    subprocess.run([
        sys.executable, '-m', 'uvicorn',
        'app.main:app',
        '--reload',
        '--port', '9000'
    ])
