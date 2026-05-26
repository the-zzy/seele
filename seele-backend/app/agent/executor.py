"""
工具执行引擎
"""

import json
from typing import Any

from sqlalchemy.orm import Session

from app.agent.tools import registry


MAX_LIST_ITEMS = 20  # 工具结果列表最大保留条数，超出截断以减少 LLM token


def _truncate_output(output: Any) -> Any:
    """截断过长的工具结果，控制传入 LLM 的 token 量"""
    if not isinstance(output, dict):
        return output
    result = dict(output)
    if 'list' in result and isinstance(result['list'], list) and len(result['list']) > MAX_LIST_ITEMS:
        result['list'] = result['list'][:MAX_LIST_ITEMS]
        result['_truncated'] = True
        result['_total'] = len(output['list'])
    return result


class ToolExecutor:
    """工具执行器，带权限校验"""

    def __init__(self, db: Session, allow_write: bool = False, max_calls: int = 10):
        self.db = db
        self.allow_write = allow_write
        self.max_calls = max_calls

    async def run(self, tool_calls: list) -> list[dict]:
        """执行工具调用列表"""
        results = []
        for idx, tc in enumerate(tool_calls):
            if idx >= self.max_calls:
                results.append({
                    'tool_call_id': tc.id,
                    'role': 'tool',
                    'content': json.dumps({'error': '超过单次最大工具调用次数限制'}, ensure_ascii=False),
                })
                continue

            name = tc.function.name
            meta = registry._tools.get(name)
            if not meta:
                results.append({
                    'tool_call_id': tc.id,
                    'role': 'tool',
                    'content': json.dumps({'error': f'未知工具: {name}'}, ensure_ascii=False),
                })
                continue

            if meta.category == 'write' and not self.allow_write:
                results.append({
                    'tool_call_id': tc.id,
                    'role': 'tool',
                    'content': json.dumps({'error': '写操作未授权，请开启写入权限后重试'}, ensure_ascii=False),
                })
                continue

            try:
                args = json.loads(tc.function.arguments)
                output = await meta.func(self.db, **args)
                output = _truncate_output(output)
                results.append({
                    'tool_call_id': tc.id,
                    'role': 'tool',
                    'name': name,
                    'content': json.dumps(output, default=str, ensure_ascii=False),
                })
            except Exception as e:
                results.append({
                    'tool_call_id': tc.id,
                    'role': 'tool',
                    'name': name,
                    'content': json.dumps({'error': str(e)}, ensure_ascii=False),
                })
        return results
