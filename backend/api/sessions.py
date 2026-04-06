"""
会话管理 API：会话列表（分页+筛选）、会话详情（元数据+消息）
"""

import json
import math
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import func, desc, asc
from sqlalchemy.orm import Session

from models.database import get_db
from models.interview import InterviewSession, Message, Report
from models.resume import Resume
from services.text_utils import extract_candidate_name

router = APIRouter(prefix="/api/sessions", tags=["会话管理"])


@router.get("")
def list_sessions(
    status: Optional[str] = Query(None, description="筛选状态: in_progress / completed"),
    position: Optional[str] = Query(None, description="筛选岗位（模糊匹配）"),
    search: Optional[str] = Query(None, description="搜索候选人姓名"),
    date_from: Optional[str] = Query(None, description="起始日期 YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="截止日期 YYYY-MM-DD"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at", description="排序字段"),
    sort_order: str = Query("desc", description="asc / desc"),
    db: Session = Depends(get_db),
):
    """获取面试会话列表（分页 + 筛选）"""
    # 子查询：每个会话的消息数
    msg_count_sub = (
        db.query(Message.session_id, func.count(Message.id).label("msg_count"))
        .group_by(Message.session_id)
        .subquery()
    )

    query = (
        db.query(
            InterviewSession,
            Resume.parsed_json,
            Resume.filename,
            Report.overall_score,
            msg_count_sub.c.msg_count,
        )
        .join(Resume, InterviewSession.resume_id == Resume.id)
        .outerjoin(Report, Report.session_id == InterviewSession.id)
        .outerjoin(msg_count_sub, msg_count_sub.c.session_id == InterviewSession.id)
    )

    # 筛选
    if status:
        query = query.filter(InterviewSession.status == status)
    if position:
        query = query.filter(InterviewSession.position.contains(position))
    if date_from:
        try:
            dt = datetime.strptime(date_from, "%Y-%m-%d")
            query = query.filter(InterviewSession.created_at >= dt)
        except ValueError:
            pass
    if date_to:
        try:
            dt = datetime.strptime(date_to, "%Y-%m-%d")
            dt = dt.replace(hour=23, minute=59, second=59)
            query = query.filter(InterviewSession.created_at <= dt)
        except ValueError:
            pass

    # 搜索候选人姓名（在内存中过滤，因为 parsed_json 是 TEXT 字段）
    # 先获取总量和排序
    sort_col = getattr(InterviewSession, sort_by, InterviewSession.created_at)
    order_func = desc if sort_order == "desc" else asc
    query = query.order_by(order_func(sort_col))

    # 如果有搜索条件，需要先查全部再过滤
    if search:
        all_rows = query.all()
        filtered = [
            row for row in all_rows
            if search.lower() in extract_candidate_name(row[1]).lower()
        ]
        total = len(filtered)
        total_pages = max(1, math.ceil(total / page_size))
        offset = (page - 1) * page_size
        page_rows = filtered[offset : offset + page_size]
    else:
        total = query.count()
        total_pages = max(1, math.ceil(total / page_size))
        offset = (page - 1) * page_size
        page_rows = query.offset(offset).limit(page_size).all()

    items = []
    for session, parsed_json, filename, score, msg_count in page_rows:
        items.append({
            "id": session.id,
            "resume_id": session.resume_id,
            "candidate_name": extract_candidate_name(parsed_json),
            "resume_filename": filename,
            "position": session.position,
            "status": session.status,
            "current_stage": session.current_stage,
            "overall_score": score,
            "created_at": session.created_at.isoformat() if session.created_at else None,
            "ended_at": session.ended_at.isoformat() if session.ended_at else None,
            "message_count": msg_count or 0,
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.get("/{session_id}/detail")
def get_session_detail(session_id: int, db: Session = Depends(get_db)):
    """获取会话详情：元数据 + 全部消息 + 报告摘要"""
    session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    resume = db.query(Resume).filter(Resume.id == session.resume_id).first()
    candidate_name = extract_candidate_name(resume.parsed_json) if resume else "未知"

    messages = (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(asc(Message.created_at))
        .all()
    )

    report = db.query(Report).filter(Report.session_id == session_id).first()

    report_data = None
    if report:
        report_data = {
            "overall_score": report.overall_score,
            "report_json": json.loads(report.report_json) if report.report_json else None,
            "created_at": report.created_at.isoformat() if report.created_at else None,
        }

    return {
        "session": {
            "id": session.id,
            "resume_id": session.resume_id,
            "candidate_name": candidate_name,
            "position": session.position,
            "status": session.status,
            "current_stage": session.current_stage,
            "created_at": session.created_at.isoformat() if session.created_at else None,
            "ended_at": session.ended_at.isoformat() if session.ended_at else None,
        },
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "stage": m.stage,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in messages
        ],
        "report": report_data,
    }
