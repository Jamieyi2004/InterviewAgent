"""
管理后台 API：系统统计、用户管理、全局会话查看
"""

import json
import math
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import func, desc, asc
from sqlalchemy.orm import Session

from auth import require_admin
from models.database import get_db
from models.interview import InterviewSession, Message, Report
from models.resume import Resume
from models.user import User
from services.text_utils import extract_candidate_name

router = APIRouter(prefix="/api/admin", tags=["管理后台"])


@router.get("/stats")
def get_admin_stats(
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """获取系统管理统计数据"""
    total_sessions = db.query(func.count(InterviewSession.id)).scalar() or 0
    total_resumes = db.query(func.count(Resume.id)).scalar() or 0
    total_messages = db.query(func.count(Message.id)).scalar() or 0
    total_reports = db.query(func.count(Report.id)).scalar() or 0
    total_users = db.query(func.count(User.id)).scalar() or 0

    active_sessions = (
        db.query(func.count(InterviewSession.id))
        .filter(InterviewSession.status == "in_progress")
        .scalar() or 0
    )
    completed_sessions = (
        db.query(func.count(InterviewSession.id))
        .filter(InterviewSession.status == "completed")
        .scalar() or 0
    )

    avg_score = db.query(func.avg(Report.overall_score)).scalar()

    # 最近 10 个会话
    recent_rows = (
        db.query(InterviewSession, Resume.parsed_json)
        .join(Resume, InterviewSession.resume_id == Resume.id)
        .order_by(InterviewSession.created_at.desc())
        .limit(10)
        .all()
    )
    recent_sessions = [
        {
            "id": s.id,
            "candidate_name": extract_candidate_name(pj),
            "position": s.position,
            "status": s.status,
            "current_stage": s.current_stage,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s, pj in recent_rows
    ]

    # 岗位分布
    position_rows = (
        db.query(InterviewSession.position, func.count(InterviewSession.id))
        .group_by(InterviewSession.position)
        .all()
    )
    position_distribution = {pos: cnt for pos, cnt in position_rows}

    # 最近 30 天每日会话数
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    daily_rows = (
        db.query(
            func.date(InterviewSession.created_at).label("day"),
            func.count(InterviewSession.id),
        )
        .filter(InterviewSession.created_at >= thirty_days_ago)
        .group_by("day")
        .order_by("day")
        .all()
    )
    daily_sessions = [
        {"date": str(day), "count": cnt} for day, cnt in daily_rows
    ]

    return {
        "total_sessions": total_sessions,
        "total_resumes": total_resumes,
        "active_sessions": active_sessions,
        "completed_sessions": completed_sessions,
        "total_messages": total_messages,
        "total_reports": total_reports,
        "total_users": total_users,
        "avg_score": round(avg_score, 1) if avg_score else None,
        "recent_sessions": recent_sessions,
        "position_distribution": position_distribution,
        "daily_sessions": daily_sessions,
    }


# ========== 管理员会话管理 ==========

@router.get("/sessions")
def admin_list_sessions(
    status: Optional[str] = Query(None),
    position: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """管理员查看所有用户的会话列表"""
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

    # 不过滤 user_id —— 管理员看全部

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

    sort_col = getattr(InterviewSession, sort_by, InterviewSession.created_at)
    order_func = desc if sort_order == "desc" else asc
    query = query.order_by(order_func(sort_col))

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
            "user_id": session.user_id,
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


@router.get("/sessions/{session_id}/detail")
def admin_session_detail(
    session_id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """管理员查看任意会话详情"""
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
            "user_id": session.user_id,
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


# ========== 用户管理 ==========

@router.get("/users")
def admin_list_users(
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """管理员查看用户列表"""
    users = db.query(User).order_by(User.created_at.desc()).all()

    items = []
    for u in users:
        session_count = (
            db.query(func.count(InterviewSession.id))
            .filter(InterviewSession.user_id == u.id)
            .scalar() or 0
        )
        items.append({
            "id": u.id,
            "email": u.email,
            "username": u.username,
            "role": u.role,
            "is_active": u.is_active,
            "session_count": session_count,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        })

    return {"users": items, "total": len(items)}
