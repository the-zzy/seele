"""
Agent 请求/响应模型
"""

from typing import Optional, List, Any
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """聊天请求"""
    message: str = Field(..., description='用户消息')
    session_id: Optional[str] = Field(None, description='已有会话 ID')
    allow_write: bool = Field(False, description='是否允许写操作')


class ChatEvent(BaseModel):
    """工具调用事件"""
    name: str
    arguments: dict
    result: Any


class ChatResponse(BaseModel):
    """聊天响应"""
    session_id: str
    reply: str
    tool_calls: List[ChatEvent] = Field(default_factory=list)
