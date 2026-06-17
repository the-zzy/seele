"""
LLM API 客户端封装
"""

from openai import AsyncOpenAI

from app.config import get_settings


class LlmClient:
    """统一 LLM 异步客户端，支持 Kimi 与 DeepSeek"""

    def __init__(self, model: str | None = None, timeout: float = 60.0, max_retries: int = 0):
        settings = get_settings()
        self.model = model or settings.moonshot_model

        if self.model.startswith(('kimi-', 'moonshot-')):
            api_key = settings.moonshot_api_key
            base_url = (
                'https://api.kimi.com/coding/v1'
                if api_key and api_key.startswith('sk-kimi-')
                else 'https://api.moonshot.cn/v1'
            )
        elif self.model.startswith('deepseek-'):
            api_key = settings.deepseek_api_key
            base_url = settings.deepseek_base_url
        else:
            # 默认使用 Moonshot
            api_key = settings.moonshot_api_key
            base_url = 'https://api.moonshot.cn/v1'

        self.client = AsyncOpenAI(
            api_key=api_key or 'dummy',
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
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


class MoonshotClient(LlmClient):
    """兼容旧调用方式的 Moonshot 客户端"""

    def __init__(self, timeout: float = 60.0, max_retries: int = 2):
        super().__init__(timeout=timeout, max_retries=max_retries)
