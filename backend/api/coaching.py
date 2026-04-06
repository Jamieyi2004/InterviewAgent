"""
面试辅导 API —— 答案对比与提升路径
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth import get_current_user, verify_session_owner
from models.database import get_db
from models.user import User
from services.coaching_generator import generate_coaching, get_coaching

router = APIRouter(prefix="/api/coaching", tags=["面试辅导"])


@router.post("/generate/{session_id}")
async def api_generate_coaching(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """生成面试辅导内容"""
    verify_session_owner(session_id, current_user.id, db)
    try:
        result = await generate_coaching(session_id, db)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"辅导生成失败：{e}")


@router.get("/{session_id}")
def api_get_coaching(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取已有的辅导内容"""
    verify_session_owner(session_id, current_user.id, db)
    result = get_coaching(session_id, db)
    if not result:
        raise HTTPException(status_code=404, detail="暂无辅导内容")
    return result
