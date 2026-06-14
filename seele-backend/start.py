#!/usr/bin/env python3
import os
import sys
import threading
import time
import urllib.error
import urllib.request


def _verify_health(port: int, timeout: int = 10):
    """启动后验证端口真正可访问，避免 Windows 僵尸连接问题。"""
    deadline = time.time() + timeout
    url = f'http://127.0.0.1:{port}/health'
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    print(f'[start.py] 后端启动验证通过 ({url})')
                    return
        except (urllib.error.URLError, TimeoutError, ConnectionRefusedError):
            pass
        time.sleep(0.5)
    print(f'[start.py] 警告: {timeout}s 内无法访问 {url}，后端可能未正常启动')


if __name__ == '__main__':
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, BASE_DIR)

    from app.config import get_settings
    settings = get_settings()

    # 后台线程验证端口可用性
    threading.Thread(
        target=_verify_health,
        args=(settings.app_port,),
        daemon=True,
    ).start()

    import uvicorn
    uvicorn.run(
        'app.main:app',
        reload=settings.uvicorn_reload,
        port=settings.app_port,
        app_dir=BASE_DIR,
        reload_dirs=[BASE_DIR] if settings.uvicorn_reload else None
    )

