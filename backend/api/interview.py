"""
面试对话 API —— REST + WebSocket
"""

import asyncio
import base64
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.orm import Session

from auth import get_current_user, verify_session_owner, authenticate_websocket
from models.database import get_db, SessionLocal
from models.interview import InterviewSession
from models.schemas import InterviewStartRequest, InterviewStartResponse
from models.user import User
from services.interview_agent import (
    create_interview_session,
    get_agent,
    remove_agent,
    save_message,
)
from services.tts_service import synthesize_to_bytes
from services.text_utils import split_sentences, clean_llm_output, extract_stage_marker
from services.problem_loader import get_random_problem

router = APIRouter(prefix="/api/interview", tags=["面试对话"])
logger = logging.getLogger(__name__)

# 缓存当前会话的题目
_session_problems: dict[int, dict] = {}


@router.post("/start", response_model=InterviewStartResponse)
async def start_interview(
    req: InterviewStartRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    创建面试会话

    - 根据 resume_id 加载简历
    - 创建面试 Agent 实例
    - 返回 session_id
    """
    try:
        session_id = await create_interview_session(
            resume_id=req.resume_id,
            position=req.position,
            db=db,
            persona_name=req.persona_name,
            user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return InterviewStartResponse(
        session_id=session_id,
        message="面试会话已创建，请通过 WebSocket 开始对话",
    )


@router.websocket("/chat/{session_id}")
async def interview_chat(websocket: WebSocket, session_id: int):
    """
    WebSocket 面试对话

    认证方式：query param ?token=xxx

    协议：
    - 客户端连接后，服务端先推送面试官开场白（流式）
    - 客户端发送 JSON: {"content": "候选人回答"}
    - 服务端流式推送: {"type": "token", "content": "..."} 逐token
    - 服务端推送完成: {"type": "done", "stage": "当前阶段", "state": {...}}
    - 面试结束时:    {"type": "finished", "session_id": ...}
    """
    # ---- WebSocket 认证 ----
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="缺少认证 token")
        return

    db_auth = SessionLocal()
    try:
        user = authenticate_websocket(token, db_auth)
        # 校验会话归属
        session = db_auth.query(InterviewSession).filter(
            InterviewSession.id == session_id
        ).first()
        if not session:
            await websocket.close(code=4004, reason="会话不存在")
            return
        if session.user_id is not None and session.user_id != user.id:
            await websocket.close(code=4003, reason="无权访问此会话")
            return
    except Exception:
        await websocket.close(code=4003, reason="认证失败")
        return
    finally:
        db_auth.close()

    await websocket.accept()

    agent = get_agent(session_id)
    if not agent:
        await websocket.send_json({"type": "error", "content": "面试会话不存在或已过期"})
        await websocket.close()
        return

    db = SessionLocal()

    try:
        # ---- 1. 发送开场白 ----
        async for token in agent.generate_opening():
            await websocket.send_json({"type": "token", "content": token})

        state = agent.get_state()
        raw_opening = agent.memory.get_messages()[-1].content if agent.memory.get_messages() else ""
        # 确保开场白不包含阶段标记
        opening_text, _ = extract_stage_marker(raw_opening)
        opening_text = clean_llm_output(opening_text)
        await websocket.send_json({
            "type": "done",
            "stage": state["current_stage"],
            "state": state,
        })

        # 持久化开场白
        await save_message(session_id, "interviewer", opening_text, state["current_stage"], db)

        # 异步触发开场白 TTS（按句分段）
        round_counter = 0
        if opening_text:
            opening_round_id = f"{session_id}-round-{round_counter}"
            round_counter += 1

            async def _run_opening_tts(text: str, sid: int, rid: str):
                loop_inner = asyncio.get_event_loop()
                for idx, sent in enumerate(split_sentences(text)):
                    audio_bytes = await loop_inner.run_in_executor(
                        None, lambda s=sent: synthesize_to_bytes(s)
                    )
                    if audio_bytes:
                        await websocket.send_json({
                            "type": "tts_segment",
                            "session_id": sid,
                            "round_id": rid,
                            "segment_index": idx,
                            "audio_base64": base64.b64encode(audio_bytes).decode(),
                            "text": sent,
                        })

            asyncio.create_task(_run_opening_tts(opening_text, session_id, opening_round_id))

        # ---- 2. 对话循环 ----
        while True:
            logger.info("[WS:%s] 等待候选人消息...", session_id)
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                candidate_content = msg.get("content", "")
            except json.JSONDecodeError:
                candidate_content = data

            if not candidate_content.strip():
                continue

            logger.info("[WS:%s] 收到候选人消息，长度=%d", session_id, len(candidate_content))

            # 持久化候选人消息
            current_stage = agent.state_machine.stage.value
            await save_message(session_id, "candidate", candidate_content, current_stage, db)

            # 生成面试官回复（流式）
            logger.info("[WS:%s] 开始生成面试官回复...", session_id)
            full_response = []
            async for token in agent.chat(candidate_content):
                full_response.append(token)
                await websocket.send_json({"type": "token", "content": token})

            logger.info("[WS:%s] 面试官回复完成，长度=%d", session_id, len("".join(full_response)))

            # 持久化面试官回复（清理标记和格式）
            raw_text = "".join(full_response)
            interviewer_text, _ = extract_stage_marker(raw_text)
            interviewer_text = clean_llm_output(interviewer_text)
            new_stage = agent.state_machine.stage.value
            await save_message(session_id, "interviewer", interviewer_text, new_stage, db)

            # 检查面试是否结束
            if agent.state_machine.is_finished:
                await websocket.send_json({
                    "type": "finished",
                    "session_id": session_id,
                })
                break
            else:
                state = agent.get_state()
                await websocket.send_json({
                    "type": "done",
                    "stage": state["current_stage"],
                    "state": state,
                })

                # 异步触发 TTS
                if interviewer_text:
                    current_round_id = f"{session_id}-round-{round_counter}"
                    round_counter += 1

                    async def _run_tts_and_push_by_sentence(text: str, sid: int, rid: str):
                        loop_inner = asyncio.get_event_loop()
                        for idx, sent in enumerate(split_sentences(text)):
                            audio_bytes = await loop_inner.run_in_executor(
                                None, lambda s=sent: synthesize_to_bytes(s)
                            )
                            if audio_bytes:
                                await websocket.send_json({
                                    "type": "tts_segment",
                                    "session_id": sid,
                                    "round_id": rid,
                                    "segment_index": idx,
                                    "audio_base64": base64.b64encode(audio_bytes).decode(),
                                    "text": sent,
                                })

                    asyncio.create_task(
                        _run_tts_and_push_by_sentence(interviewer_text, session_id, current_round_id)
                    )

    except WebSocketDisconnect:
        logger.info("[WebSocket] 客户端断开连接: session_id=%s", session_id)
    except Exception as e:
        logger.exception("[WebSocket] 异常: %s", e)
        await websocket.send_json({"type": "error", "content": str(e)})
    finally:
        db.close()


@router.post("/end/{session_id}")
async def end_interview(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """手动结束面试"""
    verify_session_owner(session_id, current_user.id, db)
    agent = get_agent(session_id)
    if agent:
        remove_agent(session_id)
    _session_problems.pop(session_id, None)
    return {"message": "面试已结束", "session_id": session_id}


@router.get("/problem/{session_id}")
async def get_current_problem(
    session_id: int,
    current_user: User = Depends(get_current_user),
):
    """获取当前会话的算法题目"""
    if session_id in _session_problems:
        return _session_problems[session_id]

    problem = get_random_problem()
    if not problem:
        return {"error": "题库为空"}

    _session_problems[session_id] = problem
    return problem
