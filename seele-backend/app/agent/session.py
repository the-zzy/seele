"""
会话管理（内存存储，TTL 过期）
"""

from datetime import datetime, timedelta
from typing import List


class SessionManager:
    """基于内存的会话管理器"""

    def __init__(self, ttl_minutes: int = 60, max_messages: int = 50):
        self._sessions: dict[str, dict] = {}
        self._ttl = timedelta(minutes=ttl_minutes)
        self._max_messages = max_messages

    def get(self, session_id: str) -> List[dict]:
        """获取会话历史消息"""
        sess = self._sessions.get(session_id)
        if not sess:
            return []
        if datetime.now() - sess['last_access'] > self._ttl:
            del self._sessions[session_id]
            return []
        return sess['messages']

    def append(self, session_id: str, messages: List[dict]):
        """追加消息到会话"""
        if session_id not in self._sessions:
            self._sessions[session_id] = {'messages': [], 'last_access': datetime.now()}
        self._sessions[session_id]['messages'].extend(messages)
        # 截断历史，保留最近 max_messages 条
        if len(self._sessions[session_id]['messages']) > self._max_messages:
            self._sessions[session_id]['messages'] = self._sessions[session_id]['messages'][-self._max_messages:]
        self._sessions[session_id]['last_access'] = datetime.now()

    def clear(self, session_id: str):
        """清除会话"""
        self._sessions.pop(session_id, None)


session_manager = SessionManager()
