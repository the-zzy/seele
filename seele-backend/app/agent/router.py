"""
Agent FastAPI 路由
"""

import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from openai import APIError, AuthenticationError, PermissionDeniedError, RateLimitError
from sqlalchemy.orm import Session

from app.agent.client import MoonshotClient
from app.agent.context import DB_SCHEMA_CONTEXT
from app.agent.executor import ToolExecutor
from app.agent.schemas import ChatRequest, ChatResponse, ChatEvent
from app.agent.session import session_manager
from app.agent.tools import registry
from app.config import get_settings
from app.database import SessionLocal, get_db
from app.response import success

router = APIRouter(prefix='/agent', tags=['AI Agent'])

client = MoonshotClient(model=get_settings().llm_model)


def _handle_llm_error(exc: APIError) -> HTTPException:
    """将 openai 异常转换为友好的 HTTP 异常"""
    if isinstance(exc, PermissionDeniedError):
        return HTTPException(status_code=403, detail=f'LLM API 权限被拒绝: {exc.body.get("error", {}).get("message", str(exc))}')
    if isinstance(exc, AuthenticationError):
        return HTTPException(status_code=401, detail='LLM API Key 无效或已过期')
    if isinstance(exc, RateLimitError):
        return HTTPException(status_code=429, detail='LLM API 速率限制，请稍后再试')
    return HTTPException(status_code=502, detail=f'LLM API 调用失败: {getattr(exc, "message", str(exc))}')


def _build_assistant_message(assistant_msg):
    """将 OpenAI 的 assistant message 转为 dict"""
    msg = {
        'role': 'assistant',
        'content': assistant_msg.content or '',
    }
    # Kimi Code 模型会返回 reasoning_content，二次调用时必须保留
    reasoning = getattr(assistant_msg, 'reasoning_content', None)
    if reasoning:
        msg['reasoning_content'] = reasoning
    if assistant_msg.tool_calls:
        msg['tool_calls'] = [
            {
                'id': tc.id,
                'type': tc.type,
                'function': {
                    'name': tc.function.name,
                    'arguments': tc.function.arguments,
                },
            }
            for tc in assistant_msg.tool_calls
        ]
    return msg


@router.post('/chat')
async def chat(req: ChatRequest, db: Session = Depends(get_db)):
    """Agent 对话接口"""
    if not client.api_key or client.api_key.strip() == '' or client.api_key == 'dummy':
        raise HTTPException(status_code=503, detail='Moonshot API Key 未配置，请在 .env 中设置 MOONSHOT_API_KEY')

    session_id = req.session_id or str(uuid.uuid4())
    history = session_manager.get(session_id)

    messages = [
        {'role': 'system', 'content': DB_SCHEMA_CONTEXT},
        *history,
        {'role': 'user', 'content': req.message},
    ]

    allowed = {'read'}
    if req.allow_write:
        allowed.add('write')
    tools = registry.get_openai_tools(allowed_categories=allowed)

    # 第一次 LLM 调用
    try:
        response = await client.chat(messages=messages, tools=tools if tools else None)
    except APIError as exc:
        raise _handle_llm_error(exc)
    choice = response.choices[0]
    assistant_msg = choice.message

    # 需要工具调用
    if assistant_msg.tool_calls:
        session_manager.append(session_id, [_build_assistant_message(assistant_msg)])

        executor = ToolExecutor(db, allow_write=req.allow_write)
        tool_results = await executor.run(assistant_msg.tool_calls)
        session_manager.append(session_id, tool_results)

        # 第二次 LLM 调用（带入工具结果）
        messages.append(_build_assistant_message(assistant_msg))
        messages.extend(tool_results)
        try:
            final_response = await client.chat(messages=messages, tools=None)
        except APIError as exc:
            raise _handle_llm_error(exc)
        final_content = final_response.choices[0].message.content
        session_manager.append(session_id, [{'role': 'assistant', 'content': final_content}])

        return ChatResponse(
            session_id=session_id,
            reply=final_content or '',
            tool_calls=[
                ChatEvent(
                    name=tc.function.name,
                    arguments=json.loads(tc.function.arguments),
                    result=next(
                        (json.loads(r['content']) for r in tool_results if r.get('tool_call_id') == tc.id),
                        None,
                    ),
                )
                for tc in assistant_msg.tool_calls
            ],
        )

    # 无需工具调用
    session_manager.append(session_id, [{'role': 'assistant', 'content': assistant_msg.content or ''}])
    return ChatResponse(
        session_id=session_id,
        reply=assistant_msg.content or '',
        tool_calls=[],
    )


@router.post('/chat/stream')
async def chat_stream(req: ChatRequest):
    """Agent 对话流式接口 (SSE)

    不在路由参数中注入 db 会话，避免 SSE 长连接长时间占用连接池。
    工具执行时在 event_generator 内部独立创建并立即关闭会话。
    """
    if not client.api_key or client.api_key.strip() == '' or client.api_key == 'dummy':
        raise HTTPException(status_code=503, detail='Moonshot API Key 未配置，请在 .env 中设置 MOONSHOT_API_KEY')

    session_id = req.session_id or str(uuid.uuid4())
    history = session_manager.get(session_id)

    messages = [
        {'role': 'system', 'content': DB_SCHEMA_CONTEXT},
        *history,
        {'role': 'user', 'content': req.message},
    ]

    allowed = {'read'}
    if req.allow_write:
        allowed.add('write')
    tools = registry.get_openai_tools(allowed_categories=allowed)

    async def event_generator():
        # 立即通知前端连接成功，AI 开始思考
        yield f"event: thinking\ndata: {json.dumps({'message': '正在分析问题...'}, ensure_ascii=False)}\n\n"
        try:
            # 第一次 LLM 调用（非流式，判断是否需要工具）
            response = await client.chat(messages=messages, tools=tools if tools else None)
            if not response.choices:
                yield f"event: error\ndata: {json.dumps({'message': 'LLM 返回空响应'}, ensure_ascii=False)}\n\n"
                return
            choice = response.choices[0]
            assistant_msg = choice.message

            if assistant_msg.tool_calls:
                session_manager.append(session_id, [_build_assistant_message(assistant_msg)])

                # 通知前端工具开始执行
                for tc in assistant_msg.tool_calls:
                    yield f"event: tool_start\ndata: {json.dumps({'name': tc.function.name, 'arguments': json.loads(tc.function.arguments)}, ensure_ascii=False)}\n\n"

                db = SessionLocal()
                try:
                    executor = ToolExecutor(db, allow_write=req.allow_write)
                    tool_results = await executor.run(assistant_msg.tool_calls)
                finally:
                    db.close()
                session_manager.append(session_id, tool_results)

                # 通知前端工具执行完成
                for tc in assistant_msg.tool_calls:
                    result = next(
                        (json.loads(r['content']) for r in tool_results if r.get('tool_call_id') == tc.id),
                        None,
                    )
                    yield f"event: tool_end\ndata: {json.dumps({'name': tc.function.name, 'result': result}, ensure_ascii=False)}\n\n"

                # 第二次 LLM 调用（流式）
                messages.append(_build_assistant_message(assistant_msg))
                messages.extend(tool_results)
                stream_response = await client.chat(messages=messages, tools=None, stream=True)

                full_content = ''
                async for chunk in stream_response:
                    if not chunk.choices:
                        continue
                    delta = chunk.choices[0].delta.content or ''
                    if delta:
                        full_content += delta
                        yield f"event: content\ndata: {json.dumps({'delta': delta}, ensure_ascii=False)}\n\n"

                session_manager.append(session_id, [{'role': 'assistant', 'content': full_content}])

                tool_calls_meta = [
                    ChatEvent(
                        name=tc.function.name,
                        arguments=json.loads(tc.function.arguments),
                        result=next(
                            (json.loads(r['content']) for r in tool_results if r.get('tool_call_id') == tc.id),
                            None,
                        ),
                    )
                    for tc in assistant_msg.tool_calls
                ]
                yield f"event: done\ndata: {json.dumps({'session_id': session_id, 'reply': full_content, 'tool_calls': [tc.model_dump() for tc in tool_calls_meta]}, ensure_ascii=False)}\n\n"
            else:
                # 无需工具，直接流式返回
                stream_response = await client.chat(messages=messages, tools=None, stream=True)
                full_content = ''
                async for chunk in stream_response:
                    if not chunk.choices:
                        continue
                    delta = chunk.choices[0].delta.content or ''
                    if delta:
                        full_content += delta
                        yield f"event: content\ndata: {json.dumps({'delta': delta}, ensure_ascii=False)}\n\n"

                session_manager.append(session_id, [{'role': 'assistant', 'content': full_content}])
                yield f"event: done\ndata: {json.dumps({'session_id': session_id, 'reply': full_content, 'tool_calls': []}, ensure_ascii=False)}\n\n"
        except Exception as exc:
            yield f"event: error\ndata: {json.dumps({'message': str(exc)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type='text/event-stream')


@router.delete('/session/{session_id}')
async def clear_session(session_id: str):
    """清除会话"""
    session_manager.clear(session_id)
    return success(message='会话已清除')
