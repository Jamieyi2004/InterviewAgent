"""
管理后台 API：系统统计概览
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from models.database import get_db
from models.interview import InterviewSession, Message, Report
from models.resume import Resume
from services.text_utils import extract_candidate_name

router = APIRouter(prefix="/api/admin", tags=["管理后台"])


@router.get("/stats")
def get_admin_stats(db: Session = Depends(get_db)):
    """获取系统管理统计数据"""
    total_sessions = db.query(func.count(InterviewSession.id)).scalar() or 0
    total_resumes = db.query(func.count(Resume.id)).scalar() or 0
    total_messages = db.query(func.count(Message.id)).scalar() or 0
    total_reports = db.query(func.count(Report.id)).scalar() or 0

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
        "avg_score": round(avg_score, 1) if avg_score else None,
        "recent_sessions": recent_sessions,
        "position_distribution": position_distribution,
        "daily_sessions": daily_sessions,
    }
