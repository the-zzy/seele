#!/usr/bin/env python3
import subprocess
import sys

# 强制使用 9000 端口启动后端服务
subprocess.run([
    sys.executable, '-m', 'uvicorn',
    'app.main:app',
    '--reload',
    '--port', '9000'
])
