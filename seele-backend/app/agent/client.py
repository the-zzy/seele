"""
Moonshot API 客户端封装
"""

from openai import AsyncOpenAI

from app.config import get_settings


class MoonshotClient:
    """Moonshot (Kimi) 异步客户端"""

    def __init__(self):
        settings = get_settings()
        self.api_key = settings.moonshot_api_key
        self.model = settings.moonshot_model
        # 使用 dummy key 避免模块导入时初始化异常，实际调用前会校验真实 key
        base_url = (
            'https://api.kimi.com/coding/v1'
            if self.api_key and self.api_key.startswith('sk-kimi-')
            else 'https://api.moonshot.cn/v1'
        )
        self.client = AsyncOpenAI(
            api_key=self.api_key or 'dummy',
            base_url=base_url,
            timeout=60.0,
            default_headers={'User-Agent': 'claude-code/1.0 (Coding Agent)'},
        )

    async def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        temperature: float = 1.0,
        stream: bool = False,
    ):
        """调用聊天补全接口"""
        kwargs = {
            'model': self.model,
            'messages': messages,
            'temperature': temperature,
            'stream': stream,
        }
        if tools:
            kwargs['tools'] = tools
            kwargs['tool_choice'] = 'auto'
        return await self.client.chat.completions.create(**kwargs)
