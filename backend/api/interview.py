"""
面试对话 API —— REST + WebSocket
"""

import asyncio
import base64
import json
import logging
import os
from datetime import datetime

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
from services.tts_service import get_current_provider, synthesize_to_bytes
from services.asr_service import transcribe_to_text
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
    - 客户端发送 JSON（二选一）：
      - 文字：{"content": "候选人回答"}
      - 语音：{"audio_base64": "...", "audio_format": "pcm"|"wav"}（pcm 为 16kHz mono s16le）
    - 语音会先 ASR 转写，再推送 {"type": "asr_result", "text": "..."}，再走与文字相同的流式回复
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
        await websocket.send_json({
            "type": "error",
            "content": "面试会话不可用：后端已重启、本场已在其他页结束，或会话已过期。请返回首页重新开启面试。",
        })
        await websocket.close()
        return

    # Step-Audio 首包冷启动极慢：在生成开场白 LLM 流式输出的同时，后台跑极短文本预热引擎，
    # 开场 TTS 开始前再 await，使「首句语音」尽量落在已预热路径上。
    step_audio_warmup: asyncio.Future | None = None
    if (
        get_current_provider() == "step-audio"
        and os.environ.get("TTS_STEP_AUDIO_WARMUP", "1").strip() != "0"
    ):
        loop = asyncio.get_running_loop()
        step_audio_warmup = loop.run_in_executor(
            None,
            lambda: synthesize_to_bytes("嗯", quiet=True),
        )
        logger.info("[WS:%s] step-audio：已开始并行预热（与开场 LLM 同步）", session_id)

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

            async def _run_opening_tts(text: str, sid: int, rid: str, warmup: asyncio.Future | None):
                if warmup is not None:
                    try:
                        await warmup
                    except Exception:
                        logger.debug("[WS:%s] step-audio 预热 await 异常（忽略）", sid, exc_info=True)
                # 逐句顺序合成并推送，保证 segment_index 与播放顺序一致（勿并行 run 多句）
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
                _run_opening_tts(opening_text, session_id, opening_round_id, step_audio_warmup)
            )

        # ---- 2. 对话循环 ----
        while True:
            logger.info("[WS:%s] 等待候选人消息...", session_id)
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "content": "消息格式应为 JSON"})
                continue

            candidate_content = ""

            audio_b64 = msg.get("audio_base64")
            if audio_b64:
                try:
                    audio_bytes = base64.b64decode(audio_b64)
                except Exception:
                    await websocket.send_json({"type": "error", "content": "音频 Base64 无效"})
                    continue
                if not audio_bytes:
                    await websocket.send_json({"type": "error", "content": "空音频"})
                    continue

                audio_fmt = (msg.get("audio_format") or "pcm").lower()
                raw_pcm = audio_fmt == "pcm"

                loop_exec = asyncio.get_event_loop()
                try:
                    candidate_content = await loop_exec.run_in_executor(
                        None,
                        lambda: transcribe_to_text(
                            audio_bytes,
                            raw_pcm=raw_pcm,
                        )
                        or "",
                    )
                except Exception as asr_exc:
                    logger.warning("[WS:%s] ASR 异常: %s", session_id, asr_exc)
                    candidate_content = ""

                if not candidate_content.strip():
                    await websocket.send_json({
                        "type": "error",
                        "content": "未能识别语音，请重试或改用文字输入（需配置 DASHSCOPE_API_KEY 与 ASR）",
                    })
                    continue

                await websocket.send_json({"type": "asr_result", "text": candidate_content})
            else:
                candidate_content = msg.get("content", "")
                if isinstance(candidate_content, str):
                    candidate_content = candidate_content.strip()
                else:
                    candidate_content = ""

                if not candidate_content:
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
                        # 逐句顺序合成并推送，保证 segment_index 顺序（勿并行）
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
    session_row = verify_session_owner(session_id, current_user.id, db)
    agent = get_agent(session_id)
    if agent:
        remove_agent(session_id)
    _session_problems.pop(session_id, None)
    session_row.status = "completed"
    session_row.ended_at = datetime.utcnow()
    db.commit()
    return {"message": "面试已结束", "session_id": session_id}


@router.get("/problem/{session_id}")
async def get_current_problem(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前会话的算法题目"""
    verify_session_owner(session_id, current_user.id, db)
    if session_id in _session_problems:
        return _session_problems[session_id]

    problem = get_random_problem()
    if not problem:
        return {"error": "题库为空"}

    _session_problems[session_id] = problem
    return problem
