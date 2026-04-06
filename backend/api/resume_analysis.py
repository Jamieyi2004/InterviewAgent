"""
简历分析 API —— 简历优化建议
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from auth import get_current_user, verify_resume_owner
from models.database import get_db
from models.user import User
from services.resume_analyzer import analyze_resume, get_resume_analysis

router = APIRouter(prefix="/api/resume-analysis", tags=["简历分析"])


@router.post("/analyze/{resume_id}")
async def api_analyze_resume(
    resume_id: int,
    target_position: str = Query("通用岗位", description="目标岗位"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """触发简历分析"""
    verify_resume_owner(resume_id, current_user.id, db)
    try:
        result = await analyze_resume(resume_id, db, target_position)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"简历分析失败：{e}")


@router.get("/{resume_id}")
def api_get_resume_analysis(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取已有的简历分析结果"""
    verify_resume_owner(resume_id, current_user.id, db)
    result = get_resume_analysis(resume_id, db)
    if not result:
        raise HTTPException(status_code=404, detail="暂无分析结果")
    return result
