#!/usr/bin/env python3
import os
import sys


if __name__ == '__main__':
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, BASE_DIR)

    from app.config import get_settings
    settings = get_settings()

    import uvicorn
    uvicorn.run(
        'app.main:app',
        reload=settings.uvicorn_reload,
        port=settings.app_port,
        app_dir=BASE_DIR,
        reload_dirs=[BASE_DIR] if settings.uvicorn_reload else None
    )

