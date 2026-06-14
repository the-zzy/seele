"""
Seele 股票数据管理后端
"""

from pathlib import Path

_version_path = Path(__file__).resolve().parents[2] / 'VERSION'
__version__ = _version_path.read_text(encoding='utf-8').strip() if _version_path.exists() else '2.3.0'
